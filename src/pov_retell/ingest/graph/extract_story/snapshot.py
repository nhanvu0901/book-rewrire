"""Plain rows describing a run's graph after one chapter, ready for a graph writer."""

from typing import Any

from pov_retell.ingest.graph.extract_story.state import StoryState
from pov_retell.ingest.graph.extract_story.steps.characters.model import CharacterRecord
from pov_retell.ingest.graph.extract_story.steps.events.logic import (
    resolve_claim,
    resolve_event,
    resolve_utterance,
)
from pov_retell.ingest.graph.extract_story.steps.events.model import (
    ClaimRecord,
    EventRecord,
    UtteranceRecord,
)
from pov_retell.ingest.graph.extract_story.steps.knowledge.logic import resolve_knowledge
from pov_retell.ingest.graph.extract_story.steps.knowledge.model import KnowledgeRecord
from pov_retell.ingest.graph.extract_story.steps.locations.model import LocationRecord
from pov_retell.ingest.graph.extract_story.steps.relationships.model import RelationshipRecord
from pov_retell.ingest.graph.extract_story.steps.scenes.logic import resolve_scene
from pov_retell.ingest.graph.extract_story.steps.scenes.model import SceneSegmentRecord


def character_rows(characters: list[CharacterRecord]) -> list[dict[str, Any]]:
    return [
        {
            "character_id": c.character_id,
            "canonical_name": c.candidate_name,
            "aliases": c.aliases,
            "gender": c.attributes.gender,
            "species": c.attributes.species,
            "age_description": c.attributes.age_description,
            "physical_description": c.attributes.physical_description,
            "personality": "; ".join(c.attributes.personality_traits) or None,
            "resolution_status": c.resolution_status,
        }
        for c in characters
    ]


def location_rows(locations: list[LocationRecord]) -> list[dict[str, Any]]:
    return [
        {
            "location_id": loc.location_id,
            "name": loc.name,
            "aliases": loc.aliases,
            "kind": loc.kind,
            "part_of": loc.part_of,
        }
        for loc in locations
    ]


def relationship_rows(relationships: list[RelationshipRecord]) -> list[dict[str, Any]]:
    return [
        {
            "relationship_id": r.relationship_id,
            "source_id": r.source_id,
            "target_id": r.target_id,
            "kind": r.kind,
            "valid_from_chapter_id": r.valid_from.chapter_id,
            "valid_from_paragraph_ids": r.valid_from.paragraph_ids,
            "valid_to_chapter_id": r.valid_to.chapter_id if r.valid_to else None,
            "valid_to_paragraph_ids": r.valid_to.paragraph_ids if r.valid_to else [],
        }
        for r in relationships
    ]


def scene_rows(scenes: list[SceneSegmentRecord]) -> list[dict[str, Any]]:
    return [
        {
            "segment_id": s.segment_id,
            "chapter_id": _chapter_of(s.segment_id),
            "order": order,
            "start": s.start,
            "end": s.end,
            "location_id": s.location_id,
            "present_ids": s.present_ids,
            "mentioned_ids": s.mentioned_ids,
            "viewpoint_ids": s.viewpoint_ids,
            "time_relation": s.time.relation,
            "time_anchor": s.time.anchor,
            "time_note": s.time.note,
            "label": s.label,
        }
        for order, s in enumerate(scenes, start=1)
    ]


def _chapter_of(record_id: str) -> str:
    return record_id.split("_", 1)[0]


def claim_rows(claims: list[ClaimRecord]) -> list[dict[str, Any]]:
    return [c.model_dump() for c in claims]


def event_rows(events: list[EventRecord]) -> list[dict[str, Any]]:
    return [
        {**e.model_dump(), "chapter_id": _chapter_of(e.event_id), "order": order}
        for order, e in enumerate(events, start=1)
    ]


def utterance_rows(utterances: list[UtteranceRecord]) -> list[dict[str, Any]]:
    return [
        {**u.model_dump(), "chapter_id": _chapter_of(u.utterance_id), "order": order}
        for order, u in enumerate(utterances, start=1)
    ]


def knowledge_rows(knowledge: list[KnowledgeRecord]) -> list[dict[str, Any]]:
    return [
        {**k.model_dump(), "chapter_id": _chapter_of(k.acquisition_id), "order": order}
        for order, k in enumerate(knowledge, start=1)
    ]


def chapter_snapshot(state: StoryState) -> dict[str, Any]:
    """The cumulative graph of the run after the current chapter."""
    index = state["chapter_index"]
    redirects = state["identity_redirects"]
    scenes = [resolve_scene(s, redirects) for s in state["scene_history"]]
    return {
        "chapter_id": state["chapters"][index].unit_id,
        "chapters_done": index + 1,
        "characters": character_rows(state["characters"]),
        "retired_character_ids": sorted(redirects),
        "locations": location_rows(state["locations"]),
        "relationships": relationship_rows(state["relationships"]),
        "scenes": scene_rows(scenes),
        "claims": claim_rows([resolve_claim(c, redirects) for c in state["claims"]]),
        "events": event_rows([resolve_event(e, redirects) for e in state["events"]]),
        "utterances": utterance_rows(
            [resolve_utterance(u, redirects) for u in state["utterances"]]
        ),
        "knowledge": knowledge_rows([resolve_knowledge(k, redirects) for k in state["knowledge"]]),
    }
