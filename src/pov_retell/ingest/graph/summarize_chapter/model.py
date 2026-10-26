from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import BaseModel, ConfigDict, StringConstraints

from pov_retell.ingest.model import Chapter

SummaryText = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class SummarizeChapterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chapter_summary: SummaryText
    who_is_who: SummaryText
    where_is_where: SummaryText


class ChapterSummary(SummarizeChapterResponse):
    chapter_id: SummaryText


class BookMemory(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    who_is_who: SummaryText
    where_is_where: SummaryText
    core_memory: SummaryText


class SummarizeChapterState(TypedDict, total=False):
    title: str
    chapters: list[Chapter]
    output_dir: Path
    chapter_index: int
    who_is_who: str
    where_is_where: str
    proposed: SummarizeChapterResponse
    summary: ChapterSummary
    summaries: list[ChapterSummary]
    book_memory: BookMemory
