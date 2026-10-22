from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestResult:
    book_id: str
    run_id: str
    characters_file: Path
    character_count: int
