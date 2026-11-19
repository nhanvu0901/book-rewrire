"""Knowledge acquisition: who gets which claim, how, and what they believe (T-0017)."""

import json
from collections.abc import Sequence

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_story.steps.characters.model import CharacterRecord
from pov_retell.ingest.graph.extract_story.steps.checks import ChapterChecks
from pov_retell.ingest.graph.extract_story.steps.events.logic import format_existing_claims
from pov_retell.ingest.graph.extract_story.steps.events.model import ChapterEvents, ClaimRecord
from pov_retell.ingest.graph.extract_story.steps.knowledge.model import (
    ChapterKnowledge,
    ExtractKnowledgeResponse,
    KnowledgeRecord,
)
from pov_retell.ingest.graph.extract_story.steps.knowledge.prompt import PROMPT_EXTRACT_KNOWLEDGE
from pov_retell.ingest.graph.extract_story.steps.scenes.model import SceneSegmentRecord
from pov_retell.ingest.model import Chapter

SOURCE_CHANNELS = {"witnessed", "told", "overheard", "read"}
NO_SOURCE_CHANNELS = {"inferred", "prior"}
TRUTH_STANCE = {"true": "believes", "false": "disbelieves"}


def latest_beliefs(
    knowledge: Sequence[KnowledgeRecord], redirects: dict[str, str]
) -> dict[tuple[str, str], str]:
    """(character_id, claim_id) -> the latest stance, with merged IDs resolved."""
    beliefs: dict[tuple[str, str], str] = {}
    for record in knowledge:
        beliefs[(redirects.get(record.character_id, record.character_id), record.claim_id)] = (
            record.stance
        )
    return beliefs


def format_current_beliefs(
    knowledge: Sequence[KnowledgeRecord],
    claims: Sequence[ClaimRecord],
    character_ids: set[str],
    redirects: dict[str, str],
) -> str:
    statements = {c.claim_id: c.statement for c in claims}
    return "\n".join(
        f"{cid} | {claim_id} | {stance} | {statements.get(claim_id, '')}"
        for (cid, claim_id), stance in latest_beliefs(knowledge, redirects).items()
        if cid in character_ids
    )


def extract_knowledge(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    segments: list[SceneSegmentRecord],
    characters: list[CharacterRecord],
    chapter_events: ChapterEvents,
    claims: list[ClaimRecord],
    next_claim_number: int,
    knowledge: list[KnowledgeRecord],
    redirects: dict[str, str],
    previous_book_summary: str,
) -> ExtractKnowledgeResponse:
    roster = [
        {"character_id": c.character_id, "candidate_name": c.candidate_name, "aliases": c.aliases}
        for c in characters
    ]
    present = {cid for s in segments for cid in s.present_ids}
    prompt = PROMPT_EXTRACT_KNOWLEDGE.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=previous_book_summary,
        character_roster_json=json.dumps(roster, ensure_ascii=False),
        scene_map_json=json.dumps(
            [
                {
                    "segment_id": s.segment_id,
                    "start": s.start,
                    "end": s.end,
                    "present_ids": s.present_ids,
                    "viewpoint_ids": s.viewpoint_ids,
                    "label": s.label,
                }
                for s in segments
            ],
            ensure_ascii=False,
        ),
        claims=format_existing_claims(claims),
        events_json=json.dumps(
            [e.model_dump(exclude={"location_id"}) for e in chapter_events.events],
            ensure_ascii=False,
        ),
        utterances_json=json.dumps(
            [u.model_dump() for u in chapter_events.utterances], ensure_ascii=False
        ),
        current_beliefs=format_current_beliefs(knowledge, claims, present, redirects),
        chapter_text=chapter.text,
    )

    def check(response: ExtractKnowledgeResponse) -> None:
        validate_knowledge(
            response,
            chapter,
            segments,
            characters,
            redirects,
            chapter_events,
            claims,
            next_claim_number,
            knowledge,
        )

    return llm.complete_json(prompt, ExtractKnowledgeResponse, check=check)


def validate_knowledge(
    response: ExtractKnowledgeResponse,
    chapter: Chapter,
    segments: list[SceneSegmentRecord],
    characters: list[CharacterRecord],
    redirects: dict[str, str],
    chapter_events: ChapterEvents,
    claims: list[ClaimRecord],
    next_claim_number: int,
    knowledge: list[KnowledgeRecord],
) -> tuple[ChapterKnowledge, list[ClaimRecord], int]:
    """Check one chapter's acquisitions; return its records, all claims, and the next number."""
    chapter_id = chapter.unit_id
    checks = ChapterChecks(chapter, segments, characters, redirects)
    claim_by_id = {c.claim_id: c for c in claims}
    new_ids, new_claims, next_claim_number = checks.new_claims(
        response.claims, claims, next_claim_number
    )
    events = {e.event_id: e for e in chapter_events.events}
    utterances = {u.utterance_id: u for u in chapter_events.utterances}
    beliefs = latest_beliefs(knowledge, redirects)
    learned = {
        (redirects.get(k.character_id, k.character_id), k.claim_id)
        for k in knowledge
        if k.channel == "learns_truth"
    }
    used_keys: set[str] = set()
    seen: set[tuple[str, str, str, str | None]] = set()
    records: list[KnowledgeRecord] = []

    for number, item in enumerate(response.acquisitions, start=1):
        what = f"acquisition {number} ({item.channel})"
        cid = checks.character_ids([item.character_id], what)[0]
        seg = checks.segment(item.segment_id, what)
        pids = checks.paragraphs(item.paragraph_ids, seg, what)
        if item.claim_id in new_ids:
            if item.channel not in NO_SOURCE_CHANNELS:
                raise ValueError(
                    f"A new claim in the knowledge answer can only be inferred or prior ({what})"
                )
            used_keys.add(item.claim_id)
            claim_id = new_ids[item.claim_id]
        elif item.claim_id in claim_by_id:
            claim_id = item.claim_id
        else:
            raise ValueError(f"Unknown claim ID in {what}: {item.claim_id}")

        if item.channel != "prior" and cid not in seg.present_ids:
            raise ValueError(f"{cid} is not present in segment {seg.segment_id} ({what})")

        source = item.source_id
        if item.channel in NO_SOURCE_CHANNELS and source is not None:
            raise ValueError(f"{item.channel} knowledge must have source_id=null ({what})")
        if item.channel in SOURCE_CHANNELS and source is None:
            raise ValueError(f"{item.channel} knowledge needs a source_id ({what})")
        if source is not None:
            linked = events.get(source) or utterances.get(source)
            if linked is None:
                raise ValueError(
                    f"source_id is not an event or utterance of {chapter_id}: {source}"
                )
            if linked.segment_id != seg.segment_id:
                raise ValueError(f"Source {source} is not in segment {seg.segment_id} ({what})")
            if claim_id not in linked.claim_ids:
                raise ValueError(f"Source {source} is not linked to claim {claim_id} ({what})")

        if item.channel == "witnessed" and source not in events:
            raise ValueError(f"witnessed knowledge needs an event source ({what})")
        if item.channel in {"told", "overheard", "read"}:
            utterance = utterances.get(source or "")
            if utterance is None:
                raise ValueError(f"{item.channel} knowledge needs an utterance source ({what})")
            if item.channel == "read" and utterance.mode != "written":
                raise ValueError(f"read knowledge needs a written utterance ({what})")
            if item.channel in {"told", "overheard"} and utterance.mode != "spoken":
                raise ValueError(f"{item.channel} knowledge needs a spoken utterance ({what})")
            if item.channel == "told" and cid not in utterance.addressee_ids:
                raise ValueError(f"{cid} is not an addressee of {utterance.utterance_id} ({what})")
            if item.channel == "overheard" and (
                cid == utterance.speaker_id or cid in utterance.addressee_ids
            ):
                raise ValueError(
                    f"{cid} is the speaker or an addressee of {utterance.utterance_id}; "
                    f"use told ({what})"
                )
        if item.channel == "learns_truth":
            truth = claim_by_id[claim_id].truth
            if truth == "unknown":
                raise ValueError(f"Claim {claim_id} is not resolved yet; cannot learn its truth")
            if item.stance != TRUTH_STANCE[truth]:
                raise ValueError(
                    f"Learning that {claim_id} is {truth} means stance "
                    f"{TRUTH_STANCE[truth]!r} ({what})"
                )

        key = (cid, claim_id, item.channel, source)
        if key in seen:
            raise ValueError(f"Duplicate acquisition: {cid} {claim_id} {item.channel} ({what})")
        seen.add(key)
        # A belief the character already holds adds nothing to the timeline: keep the first.
        if item.channel == "learns_truth":
            if (cid, claim_id) in learned:
                continue
            learned.add((cid, claim_id))
        elif beliefs.get((cid, claim_id)) == item.stance:
            continue
        beliefs[(cid, claim_id)] = item.stance
        records.append(
            KnowledgeRecord(
                acquisition_id=f"{chapter_id}_k{len(records) + 1}",
                character_id=cid,
                claim_id=claim_id,
                channel=item.channel,
                stance=item.stance,
                segment_id=seg.segment_id,
                source_id=source,
                paragraph_ids=pids,
            )
        )

    unused = [key for key in new_ids if key not in used_keys]
    if unused:
        raise ValueError(f"New claim {unused[0]} is not used by any acquisition")
    return (
        ChapterKnowledge(chapter_id=chapter_id, acquisitions=records, claims=new_claims),
        [*claims, *new_claims],
        next_claim_number,
    )


def resolve_knowledge(record: KnowledgeRecord, redirects: dict[str, str]) -> KnowledgeRecord:
    if record.character_id not in redirects:
        return record
    return record.model_copy(update={"character_id": redirects[record.character_id]})
