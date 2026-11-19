from pathlib import Path
from typing import Annotated, TypedDict

from pov_retell.ingest.graph.summarize_chapter.model import BookMemory, Card, ChapterSummary
from pov_retell.ingest.model import Chapter


def upsert_cards(current: dict[str, Card], update: dict[str, Card]) -> dict[str, Card]:
    """LangGraph reducer: new ids are added, known ids are replaced, nothing is dropped."""
    return {**current, **update}


class SummarizeChapterInput(TypedDict):
    title: str
    chapters: list[Chapter]
    output_dir: Path


class SummarizeChapterState(TypedDict, total=False):
    title: str
    chapters: list[Chapter]
    output_dir: Path
    chapter_index: int
    chapter_summary: str
    who_cards: Annotated[dict[str, Card], upsert_cards]
    where_cards: Annotated[dict[str, Card], upsert_cards]
    who_is_who: str
    where_is_where: str
    summary: ChapterSummary
    summaries: list[ChapterSummary]
    book_memory: BookMemory
