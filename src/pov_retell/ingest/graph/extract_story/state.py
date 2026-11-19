"""State of the extract_story graph. One chapter at a time; cumulative keys are overwritten."""

from pathlib import Path
from typing import TypedDict

from pov_retell.ingest.graph.extract_story.steps.characters.model import (
    CharacterRecord,
    ExtractCharacterResponse,
)
from pov_retell.ingest.graph.extract_story.steps.events.model import (
    ChapterEvents,
    ClaimRecord,
    EventRecord,
    ExtractEventResponse,
    UtteranceRecord,
)
from pov_retell.ingest.graph.extract_story.steps.knowledge.model import (
    ChapterKnowledge,
    ExtractKnowledgeResponse,
    KnowledgeRecord,
)
from pov_retell.ingest.graph.extract_story.steps.locations.model import (
    ExtractLocationResponse,
    LocationRecord,
)
from pov_retell.ingest.graph.extract_story.steps.relationships.model import (
    ExtractRelationshipResponse,
    RelationshipRecord,
)
from pov_retell.ingest.graph.extract_story.steps.scenes.model import (
    SceneMapResponse,
    SceneSegmentRecord,
)
from pov_retell.ingest.graph.summarize_chapter import ChapterSummary, format_previous_context
from pov_retell.ingest.model import Chapter


class StoryInput(TypedDict):
    book_id: str
    run_id: str
    title: str
    chapters: list[Chapter]
    summaries: list[ChapterSummary]
    output_dir: Path


class StoryState(TypedDict, total=False):
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
    scene_history: list[SceneSegmentRecord]
    proposed_events: ExtractEventResponse
    chapter_events: ChapterEvents
    claims: list[ClaimRecord]
    next_claim_number: int
    events: list[EventRecord]
    utterances: list[UtteranceRecord]
    proposed_knowledge: ExtractKnowledgeResponse
    chapter_knowledge: ChapterKnowledge
    knowledge: list[KnowledgeRecord]
    output_dir: Path


def current_chapter(state: StoryState) -> Chapter:
    return state["chapters"][state["chapter_index"]]


def earlier_summaries(state: StoryState) -> str:
    """Context from the chapters before the current one, as the prompts expect it."""
    return format_previous_context(state["summaries"][: state["chapter_index"]])
