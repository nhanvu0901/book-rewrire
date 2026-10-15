"""Command line.

Phase A:  `pov extract <file|url> [--map heuristic|llm]`   `pov show <book_id>`
Ingest:   `pov ingest <book_id> [--resume] [--checkpoint sqlite]`   `pov graph`   `pov neo4j-status`
"""

import enum
from collections import Counter
from pathlib import Path
from typing import NoReturn, cast

import typer
from neo4j.exceptions import Neo4jError

from pov_retell.config import Settings
from pov_retell.cut import StructureMapError
from pov_retell.ingest_graph import (
    GraphWriter,
    IngestState,
    NodeEvent,
    build_graph,
    open_checkpointer,
    stream_events,
    thread_config,
)
from pov_retell.llm import DeepSeekClient, LLMError
from pov_retell.models import ExtractedBook
from pov_retell.neo4j_store import (
    Neo4jUnavailable,
    Neo4jWriter,
    books_overview,
    check_health,
    connect,
)
from pov_retell.output import load_extraction, save_extraction
from pov_retell.pipeline import extract_book

app = typer.Typer(
    help="Phase A (extract) and the Neo4j ingest base (ingest). See README.md.",
    no_args_is_help=True,
)


class MapChoice(enum.StrEnum):
    heuristic = "heuristic"  # generic typographic rules: free, offline, the default
    llm = "llm"  # DeepSeek classifies the candidates (needs DEEPSEEK_API_KEY)


class CheckpointChoice(enum.StrEnum):
    memory = "memory"  # default: forgotten when the process ends
    sqlite = "sqlite"  # a file under DATA_DIR: a crashed run can be resumed


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


# ----------------------------------------------------------------- ingest into Neo4j


@app.command()
def ingest(
    book_id: str = typer.Argument(..., help="Book id of an extraction made by `pov extract`"),
    resume: bool = typer.Option(False, "--resume", help="Continue the last unfinished run"),
    checkpoint: CheckpointChoice = typer.Option(
        CheckpointChoice.memory, "--checkpoint", help="Where LangGraph saves progress"
    ),
    replace: bool = typer.Option(False, "--replace", help="Delete the book's old nodes first"),
    analysis: bool = typer.Option(False, "--analysis", help="Run the (placeholder) analysis node"),
) -> None:
    """Write extracted/<book_id>/book.json into Neo4j with the LangGraph ingest graph."""
    settings = Settings()
    if resume and checkpoint is CheckpointChoice.memory:
        _fail("--resume needs --checkpoint sqlite: the memory checkpointer forgets on exit")
    try:
        driver = connect(settings)
        check_health(driver)
    except Neo4jUnavailable as exc:
        _fail(str(exc))

    with driver, open_checkpointer(checkpoint.value, settings.checkpoint_db) as saver:
        graph = build_graph(Neo4jWriter(driver), settings.extracted_dir, saver)
        config = thread_config(book_id)
        graph_input: IngestState | None = {
            "book_id": book_id,
            "replace": replace,
            "analysis": analysis,
        }
        if resume:
            if not graph.get_state(config).next:
                _fail("nothing to resume: there is no unfinished run for this book")
            graph_input = None  # None = continue from the last checkpoint
        try:
            for event in stream_events(graph, graph_input, config):
                _print_event(event)
        except (OSError, ValueError, Neo4jError) as exc:  # the failing node was already printed
            retry = f"\nFix the cause, then: pov ingest {book_id} --resume --checkpoint sqlite"
            _fail(f"{exc}{retry if checkpoint is CheckpointChoice.sqlite else ''}")
        final = graph.get_state(config).values

    if final.get("errors"):
        _fail("\n".join(final["errors"]))
    typer.echo(f"\nIngested {book_id}: {final['written']}")
    typer.echo(f"Explore it: {settings.neo4j_browser_url} (see docs/INGEST_BASE.md for queries)")


def _print_event(event: NodeEvent) -> None:
    if event.status == "start":
        typer.echo(f"  > {event.node}")
    else:
        mark = "ok " if event.status == "ok" else "ERR"
        typer.echo(f"  {mark} {event.node:<18} {event.seconds:6.2f}s  {event.detail}")


@app.command()
def graph() -> None:
    """Print the ingest graph as a Mermaid diagram (paste it into https://mermaid.live)."""
    no_writer = cast(GraphWriter, None)  # drawing never runs a node, so no database is needed
    typer.echo(build_graph(no_writer, Path(".")).get_graph().draw_mermaid())


@app.command(name="neo4j-status")
def neo4j_status() -> None:
    """Check that Neo4j is reachable and list the books it holds."""
    settings = Settings()
    try:
        driver = connect(settings)
        with driver:
            info = check_health(driver)
            books = books_overview(driver)
    except Neo4jUnavailable as exc:
        _fail(str(exc))
    typer.echo(f"Neo4j {info['version']} {info['edition']} at {settings.neo4j_uri}")
    typer.echo(f"Browser: {settings.neo4j_browser_url} (user {settings.NEO4J_USER})")
    for b in books or [{"id": "(no books yet)", "title": "", "units": 0, "paragraphs": 0}]:
        typer.echo(
            f"  {b['id']:<40} {b['units']:>4} units {b['paragraphs']:>6} paragraphs  {b['title']}"
        )
