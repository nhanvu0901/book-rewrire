"""Events, utterances and claims of one chapter (T-0016)."""

import json
import re
from collections.abc import Sequence

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character.model import (
    ChapterEvents,
    CharacterRecord,
    ClaimProposal,
    ClaimRecord,
    EventRecord,
    ExtractEventResponse,
    SceneSegmentRecord,
    UtteranceRecord,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_events import PROMPT_EXTRACT_EVENTS
from pov_retell.ingest.graph.summarize_chapter.logic import name_key
from pov_retell.ingest.model import Chapter

MAX_CLAIM_WORDS = 25
MAX_EVENT_WORDS = 20
MAX_QUOTE_WORDS = 40
QUOTE_EDGES = " \t\n\"'“”‘’"


def format_existing_claims(claims: Sequence[ClaimRecord]) -> str:
    return "\n".join(
        f"{c.claim_id} | {c.truth} | {c.statement}"
        + (f" (about: {', '.join(c.about_ids)})" if c.about_ids else "")
        for c in claims
    )


def _scene_map_json(segments: Sequence[SceneSegmentRecord]) -> str:
    return json.dumps(
        [
            {
                "segment_id": s.segment_id,
                "start": s.start,
                "end": s.end,
                "location_id": s.location_id,
                "present_ids": s.present_ids,
                "viewpoint_ids": s.viewpoint_ids,
                "label": s.label,
            }
            for s in segments
        ],
        ensure_ascii=False,
    )


def extract_events(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    segments: list[SceneSegmentRecord],
    characters: list[CharacterRecord],
    claims: list[ClaimRecord],
    next_claim_number: int,
    redirects: dict[str, str],
    previous_book_summary: str,
) -> ExtractEventResponse:
    roster = [
        {"character_id": c.character_id, "candidate_name": c.candidate_name, "aliases": c.aliases}
        for c in characters
    ]
    prompt = PROMPT_EXTRACT_EVENTS.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=previous_book_summary,
        character_roster_json=json.dumps(roster, ensure_ascii=False),
        scene_map_json=_scene_map_json(segments),
        existing_claims=format_existing_claims(claims),
        chapter_text=chapter.text,
    )

    def check(response: ExtractEventResponse) -> None:
        validate_events(
            response, chapter, segments, characters, redirects, claims, next_claim_number
        )

    return llm.complete_json(prompt, ExtractEventResponse, check=check)


def _words(text: str) -> int:
    return len(text.split())


class ChapterChecks:
    """Shared checks for answers about one chapter: characters, segments, paragraphs, claims."""

    def __init__(
        self,
        chapter: Chapter,
        segments: Sequence[SceneSegmentRecord],
        characters: Sequence[CharacterRecord],
        redirects: dict[str, str],
    ) -> None:
        self.chapter_id = chapter.unit_id
        self.order = {pid: i for i, pid in enumerate(chapter.paragraphs)}
        self.segment_by_id = {s.segment_id: s for s in segments}
        self.known = {c.character_id for c in characters}
        self.redirects = redirects

    def character_ids(self, ids: Sequence[str], what: str) -> list[str]:
        resolved = list(dict.fromkeys(self.redirects.get(cid, cid) for cid in ids))
        unknown = [cid for cid in resolved if cid not in self.known]
        if unknown:
            raise ValueError(f"Unknown character ID in {what}: {unknown[0]}")
        return resolved

    def segment(self, segment_id: str, what: str) -> SceneSegmentRecord:
        if segment_id not in self.segment_by_id:
            raise ValueError(
                f"{what} segment_id is not a segment of {self.chapter_id}: {segment_id}"
            )
        return self.segment_by_id[segment_id]

    def paragraphs(
        self, pids: Sequence[str], seg: SceneSegmentRecord | None, what: str
    ) -> list[str]:
        if not pids:
            raise ValueError(f"{what} paragraph_ids must not be empty")
        for pid in pids:
            if pid not in self.order:
                raise ValueError(f"{what} paragraph ID does not belong to {self.chapter_id}: {pid}")
            if (
                seg is not None
                and not self.order[seg.start] <= self.order[pid] <= self.order[seg.end]
            ):
                raise ValueError(
                    f"{what} paragraph {pid} is outside segment {seg.segment_id} "
                    f"({seg.start}..{seg.end})"
                )
        return list(dict.fromkeys(pids))

    def new_claims(
        self,
        proposals: Sequence[ClaimProposal],
        claims: Sequence[ClaimRecord],
        next_claim_number: int,
    ) -> tuple[dict[str, str], list[ClaimRecord], int]:
        """Give new claims permanent IDs in answer order: key -> ID, records, next number."""
        statement_keys = {name_key(c.statement): c.claim_id for c in claims}
        new_ids: dict[str, str] = {}
        records: list[ClaimRecord] = []
        for claim in proposals:
            if not re.fullmatch(r"new_[1-9]\d*", claim.key):
                raise ValueError(f"New claim keys must look like new_1, got {claim.key!r}")
            if claim.key in new_ids:
                raise ValueError(f"Claim key used twice: {claim.key}")
            if _words(claim.statement) > MAX_CLAIM_WORDS:
                raise ValueError(
                    f"Claim statement must have at most {MAX_CLAIM_WORDS} words: "
                    f"{claim.statement!r}"
                )
            duplicate = statement_keys.get(name_key(claim.statement))
            if duplicate is not None:
                raise ValueError(f"Claim {claim.statement!r} already exists: use {duplicate}")
            claim_id = f"claim_{next_claim_number:03d}"
            next_claim_number += 1
            new_ids[claim.key] = claim_id
            statement_keys[name_key(claim.statement)] = claim_id
            records.append(
                ClaimRecord(
                    claim_id=claim_id,
                    statement=claim.statement,
                    about_ids=self.character_ids(claim.about_ids, f"claim {claim.key}"),
                    truth=claim.truth,
                    first_chapter_id=self.chapter_id,
                    truth_chapter_id=self.chapter_id if claim.truth != "unknown" else None,
                    truth_paragraph_ids=[],
                )
            )
        return new_ids, records, next_claim_number


def validate_events(
    response: ExtractEventResponse,
    chapter: Chapter,
    segments: list[SceneSegmentRecord],
    characters: list[CharacterRecord],
    redirects: dict[str, str],
    claims: list[ClaimRecord],
    next_claim_number: int,
) -> tuple[ChapterEvents, list[ClaimRecord], int]:
    """Check one chapter's answer and return its records, all claims, and the next claim number."""
    chapter_id = chapter.unit_id
    checks = ChapterChecks(chapter, segments, characters, redirects)
    character_ids, segment, paragraphs = checks.character_ids, checks.segment, checks.paragraphs
    existing = {c.claim_id: c for c in claims}
    new_ids, new_claims, next_claim_number = checks.new_claims(
        response.claims, claims, next_claim_number
    )

    referenced: set[str] = set()

    def claim_refs(ids: Sequence[str], what: str) -> list[str]:
        result = []
        for ref in ids:
            if ref in new_ids:
                referenced.add(ref)
                result.append(new_ids[ref])
            elif ref in existing:
                result.append(ref)
            else:
                raise ValueError(f"Unknown claim ID in {what}: {ref}")
        return list(dict.fromkeys(result))

    events: list[EventRecord] = []
    for number, event in enumerate(response.events, start=1):
        what = f"event {number}"
        seg = segment(event.segment_id, what)
        if _words(event.summary) > MAX_EVENT_WORDS:
            raise ValueError(
                f"Event summary must have at most {MAX_EVENT_WORDS} words: {event.summary!r}"
            )
        participants = character_ids(event.participant_ids, what)
        absent = [cid for cid in participants if cid not in seg.present_ids]
        if absent:
            raise ValueError(
                f"Event participant {absent[0]} is not present in segment {seg.segment_id}"
            )
        events.append(
            EventRecord(
                event_id=f"{chapter_id}_e{number}",
                segment_id=seg.segment_id,
                location_id=seg.location_id,
                summary=event.summary,
                participant_ids=participants,
                paragraph_ids=paragraphs(event.paragraph_ids, seg, what),
                claim_ids=claim_refs(event.claim_ids, what),
            )
        )

    utterances: list[UtteranceRecord] = []
    for number, said in enumerate(response.utterances, start=1):
        what = f"utterance {number}"
        seg = segment(said.segment_id, what)
        pids = paragraphs(said.paragraph_ids, seg, what)
        speaker = character_ids([said.speaker_id], what)[0] if said.speaker_id is not None else None
        addressees = character_ids(said.addressee_ids, what)
        if said.mode == "spoken":
            if speaker is None:
                raise ValueError(f"A spoken utterance needs a speaker_id ({what})")
            missing = [cid for cid in [speaker, *addressees] if cid not in seg.present_ids]
            if missing:
                raise ValueError(
                    f"Spoken {what}: {missing[0]} is not present in segment {seg.segment_id}"
                )
        if speaker is not None and speaker in addressees:
            raise ValueError(f"The speaker cannot also be an addressee ({what})")
        quote = said.quote.strip(QUOTE_EDGES)
        if not quote:
            raise ValueError(f"Quote must not be empty ({what})")
        if _words(quote) > MAX_QUOTE_WORDS:
            raise ValueError(f"Quote must have at most {MAX_QUOTE_WORDS} words ({what})")
        cited = name_key(" ".join(chapter.paragraphs[pid] for pid in pids))
        if name_key(quote) not in cited:
            raise ValueError(
                f"Quote of {what} was not found in its paragraphs {', '.join(pids)}: {quote!r}"
            )
        if not said.claim_ids:
            raise ValueError(f"Every utterance must state at least one claim ({what})")
        utterances.append(
            UtteranceRecord(
                utterance_id=f"{chapter_id}_q{number}",
                segment_id=seg.segment_id,
                mode=said.mode,
                speaker_id=speaker,
                addressee_ids=addressees,
                quote=quote,
                paragraph_ids=pids,
                claim_ids=claim_refs(said.claim_ids, what),
            )
        )

    orphans = [key for key in new_ids if key not in referenced]
    if orphans:
        raise ValueError(f"New claim {orphans[0]} is not linked from any event or utterance")

    updated = {c.claim_id: c.model_copy(deep=True) for c in claims}
    changed: list[str] = []
    for change in response.truth_changes:
        what = f"truth change of {change.claim_id}"
        if change.claim_id in new_ids:
            raise ValueError(f"Set the truth of new claim {change.claim_id} directly")
        if change.claim_id not in updated:
            raise ValueError(f"Unknown claim ID in truth_changes: {change.claim_id}")
        if change.claim_id in changed:
            raise ValueError(f"Claim truth changed twice: {change.claim_id}")
        record = updated[change.claim_id]
        if record.truth == change.truth:
            raise ValueError(f"{change.claim_id} is already {change.truth}; list real changes only")
        record.truth = change.truth
        record.truth_chapter_id = chapter_id
        record.truth_paragraph_ids = paragraphs(change.paragraph_ids, None, what)
        changed.append(change.claim_id)

    all_claims = [*updated.values(), *new_claims]
    chapter_claims = [updated[cid] for cid in changed] + new_claims
    return (
        ChapterEvents(
            chapter_id=chapter_id,
            events=events,
            utterances=utterances,
            claims=chapter_claims,
        ),
        all_claims,
        next_claim_number,
    )
