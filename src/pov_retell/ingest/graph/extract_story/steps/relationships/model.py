from typing import Literal

from pov_retell.ingest.graph.base import StrictModel, Text


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
