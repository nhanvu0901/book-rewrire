"""Command line: `pov extract <file|url> [--map heuristic|llm]` and `pov show <book_id>`."""

import enum
from collections import Counter
from pathlib import Path
from typing import NoReturn

import typer

from pov_retell.config import Settings
from pov_retell.cut import StructureMapError
from pov_retell.llm import DeepSeekClient, LLMError
from pov_retell.models import ExtractedBook
from pov_retell.output import load_extraction, save_extraction
from pov_retell.pipeline import extract_book

app = typer.Typer(
    help="Phase A: load a book and extract its units and paragraphs.", no_args_is_help=True
)


class MapChoice(enum.StrEnum):
    heuristic = "heuristic"  # generic typographic rules: free, offline, the default
    llm = "llm"  # DeepSeek classifies the candidates (needs DEEPSEEK_API_KEY)


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


@app.command()
def extract(
    source: str = typer.Argument(..., help="Path to an html/epub/txt file, or an http(s) URL"),
    map_method: MapChoice = typer.Option(MapChoice.heuristic, "--map", help="Structure map method"),
    book_id: str | None = typer.Option(None, "--id", help="Book id (default: slug of the title)"),
    out: Path | None = typer.Option(
        None, "--out", help="Output root (default: DATA_DIR/extracted)"
    ),
) -> None:
    """Extract units and paragraphs, and write book.json plus one readable file per chapter."""
    settings = Settings()
    try:
        llm = DeepSeekClient(settings) if map_method is MapChoice.llm else None
        extracted = extract_book(source, map_method.value, llm=llm, book_id=book_id)
        book_dir = save_extraction(extracted, out or settings.extracted_dir)
    except StructureMapError as exc:
        _fail(f"{exc}\nThe book could not be cut into valid units (see section A2c).")
    except (OSError, ValueError, LLMError) as exc:  # includes BookIdConflictError
        _fail(str(exc))

    typer.echo(_summary(extracted))
    typer.echo(f"\nWrote {book_dir}/")
    typer.echo(f"Next: uv run pov show {extracted.book.id}")


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
        extracted = load_extraction(out or Settings().extracted_dir, book_id)
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
