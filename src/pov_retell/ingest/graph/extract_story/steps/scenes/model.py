from typing import Literal

from pydantic import Field

from pov_retell.ingest.graph.base import StrictModel, Text

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
