from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import BaseModel, ConfigDict, StringConstraints

from pov_retell.ingest.model import Chapter

SummaryText = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
# No regex pattern here: strict structured outputs may reject it.
CardText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Card(BaseModel):
    """One line of WHO IS WHO or WHERE IS WHERE."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: CardText
    other_names: list[CardText]
    card: CardText


class CardUpdate(Card):
    id: CardText


class CardChanges(BaseModel):
    """What the LLM returns: only new and changed lines."""

    model_config = ConfigDict(extra="forbid", strict=True)

    add: list[Card]
    update: list[CardUpdate]


def upsert_cards(current: dict[str, Card], update: dict[str, Card]) -> dict[str, Card]:
    """LangGraph reducer: new ids are added, known ids are replaced, nothing is dropped."""
    return {**current, **update}


class ChapterSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chapter_summary: SummaryText
    # Rendered card lists; empty until a chapter names a character or place.
    who_is_who: str
    where_is_where: str
    chapter_id: SummaryText


class BookMemory(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    who_is_who: str
    where_is_where: str
    core_memory: SummaryText


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
