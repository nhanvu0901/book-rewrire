from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from pov_retell.infrastructure.llm import JsonLLM, TextLLM
from pov_retell.ingest.graph.extract_character import logic
from pov_retell.ingest.graph.extract_character.graph import (
    build_extract_character_graph,
    extract_character_recursion_limit,
)
from pov_retell.ingest.graph.summarize_chapter.graph import (
    build_summarize_chapter_graph,
    summarize_chapter_recursion_limit,
)
from pov_retell.ingest.model import IngestResult
from pov_retell.ingest.source import load_chapters, validate_directory_name


class CharacterWriter(Protocol):
    def write_characters(self, book_id: str, run_id: str, rows: list[dict[str, Any]]) -> None: ...


def ingest_book(
    book_id: str,
    character_llm: JsonLLM,
    writer: CharacterWriter | None,
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
    if on_step is not None:
        on_step(f"Build summarize_chapter graph: model={getattr(summary_llm, 'model', 'unknown')}")
    # WHO IS WHO / WHERE IS WHERE card updates need JSON, so they use the extract client.
    summary_graph = build_summarize_chapter_graph(summary_llm, character_llm, on_step)
    summary_state = summary_graph.invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir},
        {
            "recursion_limit": summarize_chapter_recursion_limit(len(chapters)),
            "run_name": "summarize_chapter",
            "metadata": {"book_id": book_id, "run_id": run_id},
        },
    )
    if on_step is not None:
        on_step("extract_character")
        on_step(
            f"Build extract_character graph: model={getattr(character_llm, 'model', 'unknown')}"
        )
    character_graph = build_extract_character_graph(character_llm, on_step)
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
            "metadata": {"book_id": book_id, "run_id": run_id},
        },
    )
    if writer is None:
        if on_step is not None:
            on_step("skip_neo4j")
    else:
        if on_step is not None:
            on_step("save_neo4j")
        writer.write_characters(
            book_id,
            run_id,
            logic.character_rows(final["characters"]),
        )
    return IngestResult(
        book_id=book_id,
        run_id=run_id,
        characters_file=final["output_dir"] / "characters.json",
        character_count=len(final["characters"]),
    )
