from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest import extrac_character
from pov_retell.ingest.graph.character_discovery import build_character_graph
from pov_retell.ingest.models.ingest_result import IngestResult


class CharacterWriter(Protocol):
    def write_characters(self, book_id: str, run_id: str, rows: list[dict[str, Any]]) -> None: ...


def ingest_book(
    book_id: str,
    llm: JsonLLM,
    writer: CharacterWriter,
    *,
    extracted_dir: Path,
    ingest_dir: Path,
    run_id: str | None = None,
    on_step: Callable[[str], None] | None = None,
) -> IngestResult:
    extrac_character.validate_directory_name(book_id)
    run_id = run_id or f"run_{uuid4().hex}"
    extrac_character.validate_directory_name(run_id)
    chapter_count = len(list((extracted_dir / book_id / "units").glob("*.txt")))
    if on_step is not None:
        on_step("character_discovery")
    character_graph = build_character_graph(llm, extracted_dir, ingest_dir, on_step)
    final = character_graph.invoke(
        {"book_id": book_id, "run_id": run_id},
        {"recursion_limit": max(25, chapter_count * 4 + 10)},
    )
    if on_step is not None:
        on_step("save_neo4j")
    writer.write_characters(
        book_id,
        run_id,
        extrac_character.character_rows(final["characters"]),
    )
    return IngestResult(
        book_id=book_id,
        run_id=run_id,
        characters_file=final["output_dir"] / "characters.json",
        character_count=len(final["characters"]),
    )
