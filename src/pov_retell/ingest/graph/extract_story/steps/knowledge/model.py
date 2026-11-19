from typing import Literal

from pov_retell.ingest.graph.base import StrictModel, Text
from pov_retell.ingest.graph.extract_story.steps.events.model import ClaimProposal, ClaimRecord

KnowledgeChannel = Literal[
    "prior", "witnessed", "told", "read", "overheard", "inferred", "learns_truth"
]
KnowledgeStance = Literal["believes", "doubts", "disbelieves"]


class AcquisitionProposal(StrictModel):
    character_id: Text
    claim_id: Text
    channel: KnowledgeChannel
    stance: KnowledgeStance
    segment_id: Text
    source_id: Text | None = None
    paragraph_ids: list[Text]


class ExtractKnowledgeResponse(StrictModel):
    claims: list[ClaimProposal]
    acquisitions: list[AcquisitionProposal]


class KnowledgeRecord(StrictModel):
    acquisition_id: Text
    character_id: Text
    claim_id: Text
    channel: KnowledgeChannel
    stance: KnowledgeStance
    segment_id: Text
    source_id: Text | None = None
    paragraph_ids: list[Text]


class ChapterKnowledge(StrictModel):
    chapter_id: Text
    acquisitions: list[KnowledgeRecord]
    claims: list[ClaimRecord]
