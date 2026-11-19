"""Validation helpers shared by the events and knowledge steps."""

import re
from collections.abc import Sequence

from pov_retell.ingest.graph.extract_story.steps.characters.identity import resolve_ids
from pov_retell.ingest.graph.extract_story.steps.characters.model import CharacterRecord
from pov_retell.ingest.graph.extract_story.steps.events.model import ClaimProposal, ClaimRecord
from pov_retell.ingest.graph.extract_story.steps.scenes.model import SceneSegmentRecord
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.text import name_key

MAX_CLAIM_WORDS = 25


def word_count(text: str) -> int:
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
        resolved = resolve_ids(ids, self.redirects)
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
            if word_count(claim.statement) > MAX_CLAIM_WORDS:
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
