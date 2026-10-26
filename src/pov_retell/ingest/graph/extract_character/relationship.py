import json

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character.model import (
    CharacterRecord,
    ExtractRelationshipResponse,
    RelationshipRecord,
    RelationshipSpan,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_relationship import (
    PROMPT_EXTRACT_RELATIONSHIP,
)
from pov_retell.ingest.model import Chapter


def normalize_kind(raw: str) -> str:
    words = raw.split()
    if not (1 <= len(words) <= 5):
        raise ValueError(f"Relationship kind must have 1 to 5 words, got {len(words)}: {raw!r}")
    return " ".join(words).lower()


def format_open_relationships(
    relationships: list[RelationshipRecord], active_ids: list[str]
) -> str:
    active_set = set(active_ids)
    lines = [
        f"{r.relationship_id}: {r.source_id} -> {r.target_id} | {r.kind} "
        f"(since {r.valid_from.chapter_id}: {', '.join(r.valid_from.paragraph_ids)})"
        for r in relationships
        if r.valid_to is None and (r.source_id in active_set or r.target_id in active_set)
    ]
    return "\n".join(lines)


def _span_sort_key(span: RelationshipSpan, chapter_order: dict[str, int]) -> tuple[int, str]:
    first_para = min(span.paragraph_ids) if span.paragraph_ids else ""
    return (chapter_order.get(span.chapter_id, 0), first_para)


def rewrite_relationships_for_redirects(
    relationships: list[RelationshipRecord],
    redirects: dict[str, str],
    chapter_order: dict[str, int],
) -> list[RelationshipRecord]:
    if not redirects:
        return [r.model_copy(deep=True) for r in relationships]

    rewritten: list[RelationshipRecord] = []
    open_by_key: dict[tuple[str, str, str], int] = {}

    for original in relationships:
        record = original.model_copy(deep=True)
        record.source_id = redirects.get(record.source_id, record.source_id)
        record.target_id = redirects.get(record.target_id, record.target_id)
        if record.source_id == record.target_id:
            continue
        if record.valid_to is not None:
            rewritten.append(record)
            continue

        key = (record.source_id, record.target_id, record.kind)
        existing_idx = open_by_key.get(key)
        if existing_idx is None:
            open_by_key[key] = len(rewritten)
            rewritten.append(record)
        else:
            existing = rewritten[existing_idx]
            if _span_sort_key(record.valid_from, chapter_order) < _span_sort_key(
                existing.valid_from, chapter_order
            ):
                existing.valid_from = record.valid_from
            if record.relationship_id < existing.relationship_id:
                existing.relationship_id = record.relationship_id

    return rewritten


def extract_relationships(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    characters: list[CharacterRecord],
    active_ids: list[str],
    relationships: list[RelationshipRecord],
    next_number: int,
    redirects: dict[str, str],
    previous_book_summary: str,
) -> ExtractRelationshipResponse:
    roster = [
        {
            "character_id": c.character_id,
            "candidate_name": c.candidate_name,
            "aliases": c.aliases,
        }
        for c in characters
    ]
    prompt = PROMPT_EXTRACT_RELATIONSHIP.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=previous_book_summary,
        character_roster_json=json.dumps(roster, ensure_ascii=False),
        active_character_ids_json=json.dumps(active_ids, ensure_ascii=False),
        open_relationships=format_open_relationships(relationships, active_ids),
        chapter_text=chapter.text,
    )

    def check(response: ExtractRelationshipResponse) -> None:
        validate_relationships(
            response,
            relationships,
            next_number,
            characters,
            redirects,
            chapter,
        )

    return llm.complete_json(prompt, ExtractRelationshipResponse, check=check)


def validate_relationships(
    response: ExtractRelationshipResponse,
    previous: list[RelationshipRecord],
    next_number: int,
    characters: list[CharacterRecord],
    redirects: dict[str, str],
    chapter: Chapter,
) -> tuple[list[RelationshipRecord], int]:
    known_ids = {c.character_id for c in characters}
    records = [r.model_copy(deep=True) for r in previous]

    for change in response.relationships:
        source_id = redirects.get(change.source_id, change.source_id)
        target_id = redirects.get(change.target_id, change.target_id)
        if source_id not in known_ids or target_id not in known_ids:
            raise ValueError(
                f"Unknown character ID in relationship: {change.source_id} -> {change.target_id}"
            )
        if source_id == target_id:
            raise ValueError(f"Relationship source_id and target_id must differ: {source_id}")
        if not change.paragraph_ids:
            raise ValueError("Relationship paragraph_ids must not be empty")
        invalid_pids = [pid for pid in change.paragraph_ids if pid not in chapter.paragraphs]
        if invalid_pids:
            raise ValueError(
                f"Paragraph ID does not belong to chapter {chapter.unit_id}: {invalid_pids[0]}"
            )
        pids = list(dict.fromkeys(change.paragraph_ids))
        kind = normalize_kind(change.kind)

        open_match = next(
            (
                r
                for r in records
                if r.valid_to is None
                and r.source_id == source_id
                and r.target_id == target_id
                and r.kind == kind
            ),
            None,
        )
        if change.op == "end":
            if open_match is None:
                raise ValueError(
                    f"Cannot end relationship that is not open: {source_id} -> {target_id} ({kind})"
                )
            open_match.valid_to = RelationshipSpan(chapter_id=chapter.unit_id, paragraph_ids=pids)
        else:
            if open_match is not None:
                continue
            rel_id = f"rel_{next_number:03d}"
            next_number += 1
            records.append(
                RelationshipRecord(
                    relationship_id=rel_id,
                    source_id=source_id,
                    target_id=target_id,
                    kind=kind,
                    valid_from=RelationshipSpan(chapter_id=chapter.unit_id, paragraph_ids=pids),
                    valid_to=None,
                )
            )

    return records, next_number
