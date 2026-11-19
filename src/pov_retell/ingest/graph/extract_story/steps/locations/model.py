from pydantic import Field

from pov_retell.ingest.graph.base import StrictModel, Text


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
