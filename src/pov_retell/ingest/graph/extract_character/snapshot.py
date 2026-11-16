"""Plain rows describing a run's graph after one chapter, ready for a graph writer."""

from typing import Any

from pov_retell.ingest.graph.extract_character import logic
from pov_retell.ingest.graph.extract_character.model import (
    ExtractCharacterState,
    LocationRecord,
    RelationshipRecord,
    SceneSegmentRecord,
)


def _resolve(ids: list[str], redirects: dict[str, str]) -> list[str]:
    return list(dict.fromkeys(redirects.get(cid, cid) for cid in ids))


def resolve_scene(scene: SceneSegmentRecord, redirects: dict[str, str]) -> SceneSegmentRecord:
    """Return the scene with retired character IDs replaced by their survivors."""
    if not redirects:
        return scene
    present = _resolve(scene.present_ids, redirects)
    present_set = set(present)
    return scene.model_copy(
        update={
            "present_ids": present,
            "mentioned_ids": [
                cid for cid in _resolve(scene.mentioned_ids, redirects) if cid not in present_set
            ],
            "viewpoint_ids": _resolve(scene.viewpoint_ids, redirects),
        }
    )


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
            "chapter_id": s.segment_id.rsplit("_s", 1)[0],
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


def chapter_snapshot(state: ExtractCharacterState) -> dict[str, Any]:
    """The cumulative graph of the run after the current chapter."""
    index = state["chapter_index"]
    redirects = state["identity_redirects"]
    scenes = [resolve_scene(s, redirects) for s in state["scene_history"]]
    return {
        "chapter_id": state["chapters"][index].unit_id,
        "chapters_done": index + 1,
        "characters": logic.character_rows(state["characters"]),
        "retired_character_ids": sorted(redirects),
        "locations": location_rows(state["locations"]),
        "relationships": relationship_rows(state["relationships"]),
        "scenes": scene_rows(scenes),
    }
