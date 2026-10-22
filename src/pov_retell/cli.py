"""Command line.

Phase A:  `pov extract <file|url>`   `pov show <book_id>`
Ingest:   `pov ingest <book_id>`   `pov neo4j-status`
"""

from collections import Counter
from pathlib import Path
from typing import NoReturn

import typer
from neo4j.exceptions import Neo4jError

from pov_retell.book.cut import StructureMapError
from pov_retell.book.models import ExtractedBook
from pov_retell.book.output import load_extraction, save_extraction
from pov_retell.book.pipeline import extract_book
from pov_retell.config import Settings
from pov_retell.infrastructure.llm import LLMError, OpenRouterClient
from pov_retell.infrastructure.neo4j_store import (
    Neo4jCharacterWriter,
    Neo4jUnavailable,
    check_health,
    connect,
)
from pov_retell.ingest.pipeline import ingest_book

app = typer.Typer(
    help="Book extraction and character discovery with OpenRouter and Neo4j. See README.md.",
    no_args_is_help=True,
)


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


@app.command()
def extract(
    source: str = typer.Argument(..., help="Path to an html/epub/txt file, or an http(s) URL"),
    book_id: str | None = typer.Option(None, "--id", help="Book id (default: slug of the title)"),
    out: Path | None = typer.Option(
        None, "--out", help="Output root (default: DATA_DIR/extracted)"
    ),
) -> None:
    """Extract units and paragraphs, and write book.json plus one readable file per chapter."""
    settings = Settings()  # type: ignore[call-arg]  # required fields come from .env
    try:
        llm = OpenRouterClient(settings)
        extracted = extract_book(source, llm, book_id=book_id)
        book_dir = save_extraction(extracted, out or settings.extracted_dir)
    except StructureMapError as exc:
        _fail(f"{exc}\nThe book could not be cut into valid units (see section A2c).")
    except (OSError, ValueError, LLMError) as exc:  # includes BookIdConflictError
        _fail(str(exc))

    typer.echo(_summary(extracted))
    typer.echo(f"\nWrote {book_dir}/")
    typer.echo(f"Next: uv run pov show {extracted.book.id}")


@app.command()
def ingest(
    book_id: str = typer.Argument(..., help="Book id of an extraction made by `pov extract`"),
) -> None:
    """Discover characters and save chapter JSON and Neo4j Character nodes."""
    settings = Settings()  # type: ignore[call-arg]
    try:
        driver = connect(settings)
        with driver:
            check_health(driver)
            result = ingest_book(
                book_id,
                OpenRouterClient(settings),
                Neo4jCharacterWriter(driver),
                extracted_dir=settings.extracted_dir,
                ingest_dir=settings.BOOK_CLONE_DATA_DIR / "ingest",
                on_step=typer.echo,
            )
    except (Neo4jUnavailable, Neo4jError, LLMError, OSError, ValueError) as exc:
        _fail(str(exc))
    typer.echo(f"Ingested {book_id}: {result.character_count} characters (run {result.run_id})")
    typer.echo(f"Wrote {result.characters_file}")


@app.command()
def show(
    book_id: str = typer.Argument(..., help="Book id, as printed by `pov extract`"),
    unit: str | None = typer.Argument(None, help="A unit id (u04) to print its paragraphs"),
    out: Path | None = typer.Option(
        None, "--out", help="Output root (default: DATA_DIR/extracted)"
    ),
) -> None:
    """Show an extracted book: its units, flagged paragraphs and warnings."""
    try:
        settings = Settings()  # type: ignore[call-arg]  # required fields come from .env
        extracted = load_extraction(out or settings.extracted_dir, book_id)
    except (OSError, ValueError) as exc:
        _fail(str(exc))

    if unit is not None:
        paragraphs = [p for p in extracted.paragraphs if p.unit_id == unit]
        if not paragraphs:
            _fail(f"unit {unit!r} has no paragraphs (a part, or an unknown id)")
        for p in paragraphs:
            typer.echo(f"[{p.id}] {p.text}\n")
        return

    typer.echo(_summary(extracted))
    typer.echo(f"\n{'ID':<5} {'KIND':<8} {'PARENT':<6} {'PARAS':>5} {'WORDS':>6}  TITLE")
    for u in extracted.units:
        mine = [p for p in extracted.paragraphs if p.unit_id == u.id]
        words = sum(len(p.text.split()) for p in mine)
        typer.echo(
            f"{u.id:<5} {u.kind:<8} {u.parent_id or '-':<6} {len(mine):>5} {words:>6}  {u.title}"
        )
    flagged = [p for p in extracted.paragraphs if p.flags]
    if flagged:
        typer.echo(f"\nFlagged paragraphs ({len(flagged)}):")
        for p in flagged:
            typer.echo(f"  {p.id}  {', '.join(p.flags)}  {p.text[:70]!r}")


def _summary(extracted: ExtractedBook) -> str:
    book = extracted.book
    kinds = Counter(u.kind for u in extracted.units)
    flagged = sum(1 for p in extracted.paragraphs if p.flags)
    lines = [
        f"Book:       {book.id} | {book.title} by {book.author}",
        f"File:       {book.format}, sha256 {book.sha256[:16]}...",
        f"Map:        {extracted.map_method}, {len(extracted.candidates)} candidates",
        f"Units:      {len(extracted.units)} ({', '.join(f'{n} {k}' for k, n in kinds.items())})",
        f"Paragraphs: {len(extracted.paragraphs)} ({flagged} flagged)",
    ]
    lines += [f"Warning:    {w}" for w in extracted.warnings]
    return "\n".join(lines)


@app.command(name="neo4j-status")
def neo4j_status() -> None:
    """Check that Neo4j is reachable."""
    settings = Settings()  # type: ignore[call-arg]  # required fields come from .env
    try:
        driver = connect(settings)
        with driver:
            info = check_health(driver)
    except Neo4jUnavailable as exc:
        _fail(str(exc))
    typer.echo(f"Neo4j {info['version']} {info['edition']} at {settings.neo4j_uri}")
    typer.echo(f"Browser: {settings.neo4j_browser_url} (user {settings.NEO4J_USER})")
