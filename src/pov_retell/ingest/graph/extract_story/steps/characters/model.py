from typing import Literal

from pydantic import Field

from pov_retell.ingest.graph.base import StrictModel, Text


class CharacterAttributes(StrictModel):
    gender: Text | None = None
    species: Text | None = None
    age_description: Text | None = None
    physical_description: Text | None = None
    personality_traits: list[Text] = Field(default_factory=list)


class CharacterRecord(StrictModel):
    identity_context: Text | None = Field(default=None, exclude=True)
    character_id: Text
    candidate_name: Text
    aliases: list[Text] = Field(default_factory=list)
    attributes: CharacterAttributes = Field(default_factory=CharacterAttributes)
    resolution_status: Literal["candidate", "verified"] = "candidate"


class CharacterCandidate(CharacterRecord):
    merged_character_ids: list[Text] = Field(default_factory=list)


class ExtractCharacterResponse(StrictModel):
    characters: list[CharacterCandidate]


class CharacterIdentity(StrictModel):
    identity_context: Text | None = None
    character_id: Text
    candidate_name: Text
    names_in_chapter: list[Text] = Field(min_length=1)
    merged_character_ids: list[Text] = Field(default_factory=list)


class IdentityResponse(StrictModel):
    characters: list[CharacterIdentity]
