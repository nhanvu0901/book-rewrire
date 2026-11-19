from typing import Literal

from pydantic import Field

from pov_retell.ingest.graph.base import StrictModel, Text

UtteranceMode = Literal["spoken", "written"]
ClaimTruth = Literal["unknown", "true", "false"]


class ClaimProposal(StrictModel):
    key: Text
    statement: Text
    about_ids: list[Text] = Field(default_factory=list)
    truth: ClaimTruth


class EventProposal(StrictModel):
    segment_id: Text
    summary: Text
    participant_ids: list[Text] = Field(default_factory=list)
    paragraph_ids: list[Text]
    claim_ids: list[Text] = Field(default_factory=list)


class UtteranceProposal(StrictModel):
    segment_id: Text
    mode: UtteranceMode
    speaker_id: Text | None = None
    addressee_ids: list[Text] = Field(default_factory=list)
    quote: Text
    paragraph_ids: list[Text]
    claim_ids: list[Text]


class TruthChange(StrictModel):
    claim_id: Text
    truth: Literal["true", "false"]
    paragraph_ids: list[Text]


class ExtractEventResponse(StrictModel):
    claims: list[ClaimProposal]
    events: list[EventProposal]
    utterances: list[UtteranceProposal]
    truth_changes: list[TruthChange]


class ClaimRecord(StrictModel):
    claim_id: Text
    statement: Text
    about_ids: list[Text] = Field(default_factory=list)
    truth: ClaimTruth
    first_chapter_id: Text
    truth_chapter_id: Text | None = None
    truth_paragraph_ids: list[Text] = Field(default_factory=list)


class EventRecord(StrictModel):
    event_id: Text
    segment_id: Text
    location_id: Text | None = None
    summary: Text
    participant_ids: list[Text] = Field(default_factory=list)
    paragraph_ids: list[Text]
    claim_ids: list[Text] = Field(default_factory=list)


class UtteranceRecord(StrictModel):
    utterance_id: Text
    segment_id: Text
    mode: UtteranceMode
    speaker_id: Text | None = None
    addressee_ids: list[Text] = Field(default_factory=list)
    quote: Text
    paragraph_ids: list[Text]
    claim_ids: list[Text]


class ChapterEvents(StrictModel):
    """What one chapter added: its events and utterances, and the claims it created or changed."""

    chapter_id: Text
    events: list[EventRecord]
    utterances: list[UtteranceRecord]
    claims: list[ClaimRecord]
