from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

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
