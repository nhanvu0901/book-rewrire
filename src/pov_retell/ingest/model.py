from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class Chapter:
    unit_id: str
    text: str
    paragraphs: dict[str, str]


@dataclass(frozen=True)
class IngestResult:
    book_id: str
    run_id: str
    characters_file: Path
    character_count: int


class GraphWriter(Protocol):
    """Writes a run's story graph. Each chapter snapshot replaces the run's previous graph."""

    def start_run(self, book_id: str, run_id: str, title: str, chapter_ids: list[str]) -> None: ...

    def write_chapter(self, book_id: str, run_id: str, snapshot: dict[str, Any]) -> None: ...

    def finish_run(self, book_id: str, run_id: str) -> None: ...

    def fail_run(self, book_id: str, run_id: str, error: str) -> None: ...
