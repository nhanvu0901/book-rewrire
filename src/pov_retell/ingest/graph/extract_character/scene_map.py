import json
from collections.abc import Sequence

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character.model import (
    CharacterRecord,
    LocationRecord,
    SceneMapResponse,
    SceneSegmentRecord,
    SceneTime,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_scene_map import (
    PROMPT_EXTRACT_SCENE_MAP,
)
from pov_retell.ingest.model import Chapter

VALID_TIME_RELATIONS = {"continues", "later", "parallel", "flashback", "time_jump"}
ANCHOR_REQUIRED_RELATIONS = {"parallel", "flashback"}


def _dedupe_ids(ids: Sequence[str], redirects: dict[str, str]) -> list[str]:
    resolved = [redirects.get(cid, cid) for cid in ids]
    return list(dict.fromkeys(resolved))


def extract_scene_map(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    chapters_up_to_current: Sequence[Chapter],
    characters: list[CharacterRecord],
    locations: list[LocationRecord],
    redirects: dict[str, str],
    previous_book_summary: str,
) -> SceneMapResponse:
    roster = [
        {
            "character_id": c.character_id,
            "candidate_name": c.candidate_name,
            "aliases": c.aliases,
        }
        for c in characters
    ]
    compact_locations = [
        {
            "location_id": loc.location_id,
            "name": loc.name,
            "aliases": loc.aliases,
            "part_of": loc.part_of,
        }
        for loc in locations
    ]
    prompt = PROMPT_EXTRACT_SCENE_MAP.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=previous_book_summary,
        character_roster_json=json.dumps(roster, ensure_ascii=False),
        locations_json=json.dumps(compact_locations, ensure_ascii=False),
        chapter_text=chapter.text,
    )

    def check(response: SceneMapResponse) -> None:
        validate_scene_map(
            response,
            chapter,
            chapters_up_to_current,
            characters,
            locations,
            redirects,
        )

    return llm.complete_json(prompt, SceneMapResponse, check=check)


def validate_scene_map(
    response: SceneMapResponse,
    chapter: Chapter,
    chapters_up_to_current: Sequence[Chapter],
    characters: list[CharacterRecord],
    locations: list[LocationRecord],
    redirects: dict[str, str],
) -> list[SceneSegmentRecord]:
    ordered_pids = list(chapter.paragraphs.keys())
    if not ordered_pids:
        return []
    if not response.segments:
        raise ValueError(f"Scene map must cover all paragraphs of chapter {chapter.unit_id}")

    pid_index = {pid: idx for idx, pid in enumerate(ordered_pids)}
    global_pid_index: dict[str, int] = {}
    cursor = 0
    for ch in chapters_up_to_current:
        for pid in ch.paragraphs:
            global_pid_index[pid] = cursor
            cursor += 1

    known_character_ids = {c.character_id for c in characters}
    known_location_ids = {loc.location_id for loc in locations}

    expected_idx = 0
    records: list[SceneSegmentRecord] = []

    for seg_number, seg in enumerate(response.segments, start=1):
        if seg.start not in pid_index:
            raise ValueError(
                f"Segment paragraph ID does not belong to chapter {chapter.unit_id}: {seg.start}"
            )
        if seg.end not in pid_index:
            raise ValueError(
                f"Segment paragraph ID does not belong to chapter {chapter.unit_id}: {seg.end}"
            )

        start_idx = pid_index[seg.start]
        end_idx = pid_index[seg.end]
        if start_idx > end_idx:
            raise ValueError(f"Segment start must not come after end: {seg.start} > {seg.end}")
        if start_idx < expected_idx:
            raise ValueError(
                f"Segment overlap at paragraph {seg.start} (expected {ordered_pids[expected_idx]})"
            )
        if start_idx > expected_idx:
            raise ValueError(
                f"Segment gap before paragraph {seg.start} (expected {ordered_pids[expected_idx]})"
            )
        expected_idx = end_idx + 1

        if seg.location_id is not None and seg.location_id not in known_location_ids:
            raise ValueError(f"Unknown location_id in scene segment: {seg.location_id}")

        present_ids = _dedupe_ids(seg.present_ids, redirects)
        mentioned_ids = _dedupe_ids(seg.mentioned_ids, redirects)
        viewpoint_ids = _dedupe_ids(seg.viewpoint_ids, redirects)

        for cid in (*present_ids, *mentioned_ids, *viewpoint_ids):
            if cid not in known_character_ids:
                raise ValueError(f"Unknown character_id in scene segment: {cid}")

        present_set = set(present_ids)
        not_present = [cid for cid in viewpoint_ids if cid not in present_set]
        if not_present:
            raise ValueError(
                f"viewpoint_ids must be a subset of present_ids; not present: {not_present[0]}"
            )

        overlap = [cid for cid in mentioned_ids if cid in present_set]
        if overlap:
            raise ValueError(f"present_ids and mentioned_ids must not overlap: {overlap[0]}")

        relation = seg.time.relation
        if relation not in VALID_TIME_RELATIONS:
            raise ValueError(f"Invalid time relation: {relation!r}")

        anchor = seg.time.anchor
        if relation in ANCHOR_REQUIRED_RELATIONS:
            if anchor is None:
                raise ValueError(f"Time relation {relation!r} requires an anchor paragraph ID")
            if anchor not in global_pid_index:
                raise ValueError(
                    f"Time anchor paragraph ID does not exist at or before chapter "
                    f"{chapter.unit_id}: {anchor}"
                )
            if global_pid_index[anchor] >= global_pid_index[seg.start]:
                raise ValueError(f"Time anchor {anchor} must come before segment start {seg.start}")
        elif anchor is not None:
            raise ValueError(f"Time relation {relation!r} must have anchor=null, got {anchor!r}")

        note = seg.time.note
        if note is not None and len(note.split()) > 8:
            raise ValueError(
                f"Segment time note must have at most 8 words, got {len(note.split())}: {note!r}"
            )

        if len(seg.label.split()) > 15:
            raise ValueError(
                f"Segment label must have at most 15 words, got {len(seg.label.split())}: "
                f"{seg.label!r}"
            )

        records.append(
            SceneSegmentRecord(
                segment_id=f"{chapter.unit_id}_s{seg_number}",
                start=seg.start,
                end=seg.end,
                location_id=seg.location_id,
                present_ids=present_ids,
                mentioned_ids=mentioned_ids,
                viewpoint_ids=viewpoint_ids,
                time=SceneTime(relation=relation, anchor=anchor, note=note),
                label=seg.label,
            )
        )

    if expected_idx != len(ordered_pids):
        raise ValueError(
            f"Segment gap at end of chapter {chapter.unit_id}: "
            f"missing {ordered_pids[expected_idx]}..{ordered_pids[-1]}"
        )

    return records
