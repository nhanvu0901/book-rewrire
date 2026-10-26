from pathlib import Path
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pov_retell.ingest.graph.summarize_chapter.model import ChapterSummary
from pov_retell.ingest.model import Chapter

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


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


class RelationshipSpan(StrictModel):
    chapter_id: Text
    paragraph_ids: list[Text]


class RelationshipRecord(StrictModel):
    relationship_id: Text
    source_id: Text
    target_id: Text
    kind: Text
    valid_from: RelationshipSpan
    valid_to: RelationshipSpan | None = None


class RelationshipChange(StrictModel):
    op: Literal["start", "end"]
    source_id: Text
    target_id: Text
    kind: Text
    paragraph_ids: list[Text]


class ExtractRelationshipResponse(StrictModel):
    relationships: list[RelationshipChange]


class LocationRecord(StrictModel):
    location_id: Text
    name: Text
    aliases: list[Text] = Field(default_factory=list)
    kind: Text | None = None
    part_of: Text | None = None


class LocationCandidate(LocationRecord):
    pass


class ExtractLocationResponse(StrictModel):
    locations: list[LocationCandidate]


SceneTimeRelation = Literal["continues", "later", "parallel", "flashback", "time_jump"]


class SceneTime(StrictModel):
    relation: SceneTimeRelation
    anchor: Text | None = None
    note: Text | None = None


class SceneSegmentProposal(StrictModel):
    start: Text
    end: Text
    location_id: Text | None = None
    present_ids: list[Text] = Field(default_factory=list)
    mentioned_ids: list[Text] = Field(default_factory=list)
    viewpoint_ids: list[Text] = Field(default_factory=list)
    time: SceneTime
    label: Text


class SceneSegmentRecord(StrictModel):
    segment_id: Text
    start: Text
    end: Text
    location_id: Text | None = None
    present_ids: list[Text] = Field(default_factory=list)
    mentioned_ids: list[Text] = Field(default_factory=list)
    viewpoint_ids: list[Text] = Field(default_factory=list)
    time: SceneTime
    label: Text


class SceneMapResponse(StrictModel):
    segments: list[SceneSegmentProposal]


class ExtractCharacterState(TypedDict, total=False):
    book_id: str
    run_id: str
    title: str
    chapters: list[Chapter]
    summaries: list[ChapterSummary]
    chapter_index: int
    characters: list[CharacterRecord]
    active_character_ids: list[str]
    proposed: ExtractCharacterResponse
    identity_redirects: dict[str, str]
    next_character_number: int
    relationships: list[RelationshipRecord]
    proposed_relationships: ExtractRelationshipResponse
    next_relationship_number: int
    locations: list[LocationRecord]
    proposed_locations: ExtractLocationResponse
    next_location_number: int
    proposed_scenes: SceneMapResponse
    scenes: list[SceneSegmentRecord]
    output_dir: Path
