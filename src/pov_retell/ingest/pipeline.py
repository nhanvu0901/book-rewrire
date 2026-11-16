from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from pov_retell.infrastructure.llm import JsonLLM, TextLLM
from pov_retell.ingest.graph.extract_character.graph import (
    build_extract_character_graph,
    extract_character_recursion_limit,
)
from pov_retell.ingest.graph.extract_character.model import ExtractCharacterState
from pov_retell.ingest.graph.summarize_chapter.graph import (
    build_summarize_chapter_graph,
    summarize_chapter_recursion_limit,
)
from pov_retell.ingest.model import Chapter, GraphWriter, IngestResult
from pov_retell.ingest.source import load_chapters, validate_directory_name

FAILURE_MESSAGE_LIMIT = 500


def ingest_book(
    book_id: str,
    character_llm: JsonLLM,
    writer: GraphWriter | None,
    *,
    summary_llm: TextLLM,
    extracted_dir: Path,
    ingest_dir: Path,
    run_id: str | None = None,
    on_step: Callable[[str], None] | None = None,
) -> IngestResult:
    validate_directory_name(book_id)
    run_id = run_id or f"run_{uuid4().hex}"
    validate_directory_name(run_id)
    if on_step is not None:
        on_step("load_chapters")
    title, chapters = load_chapters(extracted_dir, book_id)
    output_dir = ingest_dir / book_id / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    if on_step is not None:
        on_step(f"Run {run_id}: {output_dir}")
        on_step("skip_neo4j" if writer is None else "save_graph after each chapter")
    if writer is None:
        final = _run_graphs(
            book_id, run_id, title, chapters, output_dir, character_llm, summary_llm, None, on_step
        )
    else:
        writer.start_run(book_id, run_id, title, [c.unit_id for c in chapters])
        try:
            final = _run_graphs(
                book_id,
                run_id,
                title,
                chapters,
                output_dir,
                character_llm,
                summary_llm,
                writer,
                on_step,
            )
        except Exception as exc:
            writer.fail_run(book_id, run_id, f"{type(exc).__name__}: {exc}"[:FAILURE_MESSAGE_LIMIT])
            raise
        writer.finish_run(book_id, run_id)
    return IngestResult(
        book_id=book_id,
        run_id=run_id,
        characters_file=final["output_dir"] / "characters.json",
        character_count=len(final["characters"]),
    )


def _run_graphs(
    book_id: str,
    run_id: str,
    title: str,
    chapters: list[Chapter],
    output_dir: Path,
    character_llm: JsonLLM,
    summary_llm: TextLLM,
    writer: GraphWriter | None,
    on_step: Callable[[str], None] | None,
) -> ExtractCharacterState:
    metadata: dict[str, Any] = {"book_id": book_id, "run_id": run_id}
    if on_step is not None:
        on_step(f"Build summarize_chapter graph: model={getattr(summary_llm, 'model', 'unknown')}")
    # WHO IS WHO / WHERE IS WHERE card updates need JSON, so they use the extract client.
    summary_graph = build_summarize_chapter_graph(summary_llm, character_llm, on_step)
    summary_state = summary_graph.invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir},
        {
            "recursion_limit": summarize_chapter_recursion_limit(len(chapters)),
            "run_name": "summarize_chapter",
            "metadata": metadata,
        },
    )
    if on_step is not None:
        on_step("extract_character")
        on_step(
            f"Build extract_character graph: model={getattr(character_llm, 'model', 'unknown')}"
        )
    character_graph = build_extract_character_graph(character_llm, on_step, writer)
    final = character_graph.invoke(
        {
            "book_id": book_id,
            "run_id": run_id,
            "title": title,
            "chapters": chapters,
            "summaries": summary_state["summaries"],
            "output_dir": output_dir,
        },
        {
            "recursion_limit": extract_character_recursion_limit(len(chapters)),
            "run_name": "extract_character",
            "metadata": metadata,
        },
    )
    return cast(ExtractCharacterState, final)
