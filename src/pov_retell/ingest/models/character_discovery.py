from pathlib import Path
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pov_retell.ingest.models.chapter import Chapter

Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class CharacterAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gender: Text | None
    species: Text | None
    age_description: Text | None
    physical_description: Text | None
    personality_traits: list[Text]


class CharacterCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    character_id: Text
    merged_character_ids: list[Text] = Field(default_factory=list)
    candidate_name: Text
    aliases: list[Text]
    attributes: CharacterAttributes
    relationships: dict[Text, Text]
    resolution_status: Literal["candidate", "verified"]


class CharacterDiscoveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    characters: list[CharacterCandidate]


class CharacterRecord(CharacterCandidate):
    character_id: Text = Field(...)
    merged_character_ids: list[Text] = Field(default_factory=list, exclude=True)


class CharacterDiscoveryState(TypedDict, total=False):
    book_id: str
    run_id: str
    title: str
    chapters: list[Chapter]
    chapter_index: int
    characters: list[CharacterRecord]
    proposed: CharacterDiscoveryResponse
    next_character_number: int
    output_dir: Path
