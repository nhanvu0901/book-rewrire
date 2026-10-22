import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pov_retell.book.models import NARRATIVE_KINDS
from pov_retell.book.output import load_extraction
from pov_retell.book.text import iter_blocks
from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.models.chapter import Chapter
from pov_retell.ingest.models.character_discovery import CharacterDiscoveryResponse, CharacterRecord
from prompt.extract_character import PROMPT_EXTRACT_CHAR

_PARAGRAPH = re.compile(r"\[(u\d+_p\d+)(?: [^\]]*)?\]\s+(.+)")


def validate_directory_name(value: str) -> None:
    if not value or value in {".", ".."} or any(c in value for c in "/\\\x00"):
        raise ValueError(f"Invalid book or run ID: {value!r}")


def load_chapters(extracted_dir: Path, book_id: str) -> tuple[str, list[Chapter]]:
    validate_directory_name(book_id)
    extracted = load_extraction(extracted_dir, book_id)
    if extracted.book.id != book_id:
        raise ValueError("The extraction's book ID does not match the requested book")
    units = sorted((u for u in extracted.units if u.kind in NARRATIVE_KINDS), key=lambda u: u.order)
    if not units:
        raise ValueError("The extraction has no narrative chapters")
    paths: dict[int, Path] = {}
    for path in (extracted_dir / book_id / "units").glob("*.txt"):
        prefix = path.name.split("_", 1)[0]
        if not prefix.isdecimal() or int(prefix) in paths:
            raise ValueError(f"Invalid or duplicate chapter filename: {path.name}")
        paths[int(prefix)] = path
    if set(paths) != {unit.order for unit in units}:
        raise ValueError("Chapter files do not match the extraction's narrative units")

    chapters = []
    for unit in units:
        text = paths[unit.order].read_text(encoding="utf-8")
        expected = {
            p.id: p.text
            for p in sorted(extracted.paragraphs, key=lambda p: p.order)
            if p.unit_id == unit.id
        }
        blocks = list(iter_blocks(text))
        actual: dict[str, str] = {}
        for block in blocks[1:]:
            match = _PARAGRAPH.fullmatch(block.text)
            if match is None or match[1] in actual:
                raise ValueError(f"Invalid paragraph label in chapter {unit.id}")
            actual[match[1]] = match[2]
        if not expected or list(actual) != list(expected) or actual != expected:
            raise ValueError(f"Chapter {unit.id} text or paragraph IDs differ from book.json")
        chapters.append(Chapter(unit.id, text, actual))
    return extracted.book.title, chapters


def extract_characters(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    characters: list[CharacterRecord],
    next_number: int,
) -> CharacterDiscoveryResponse:
    existing = [c.model_dump() for c in characters]
    prompt = PROMPT_EXTRACT_CHAR.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        existing_characters_json=json.dumps(existing, ensure_ascii=False),
        chapter_text=chapter.text,
    )

    def check(response: CharacterDiscoveryResponse) -> None:
        validate_characters(response, characters, next_number)

    return llm.complete_json(prompt, CharacterDiscoveryResponse, check=check)


def validate_characters(
    response: CharacterDiscoveryResponse,
    previous: list[CharacterRecord],
    next_number: int,
) -> tuple[list[CharacterRecord], int]:
    previous_by_id = {c.character_id: c for c in previous}
    previous_order = {c.character_id: index for index, c in enumerate(previous)}
    consumed: set[str] = set()
    returned_ids: set[str] = set()
    updates = []

    for index, character in enumerate(response.characters):
        character = character.model_copy(deep=True)
        if character.character_id in returned_ids:
            raise ValueError("A character ID cannot appear more than once")
        returned_ids.add(character.character_id)
        ids = []
        if character.character_id in previous_by_id:
            ids.append(character.character_id)
        elif not re.fullmatch(r"new_[1-9]\d*", character.character_id):
            raise ValueError("A new character must use a chapter-local new_N ID")
        if not ids and character.merged_character_ids:
            raise ValueError("A merge must retain an existing character ID")
        ids.extend(character.merged_character_ids)
        if len(ids) != len(set(ids)) or consumed.intersection(ids):
            raise ValueError("A character ID cannot be updated or merged more than once")
        if any(cid not in previous_by_id for cid in ids):
            raise ValueError("The LLM returned an unknown character ID")
        consumed.update(ids)
        old_records = [previous_by_id[cid] for cid in ids]
        if old_records and ids[0] != min(ids, key=previous_order.__getitem__):
            raise ValueError("A merge must retain the earliest character ID")
        expected_status = old_records[0].resolution_status if len(old_records) == 1 else "candidate"
        if character.resolution_status != expected_status:
            raise ValueError("The LLM cannot verify a new or merged character")
        for old_record in old_records:
            aliases = character.aliases + old_record.aliases
            if old_record.candidate_name != character.candidate_name:
                aliases.append(old_record.candidate_name)
            character.aliases = list(dict.fromkeys(aliases))
            for field in ("gender", "species", "age_description", "physical_description"):
                if (
                    getattr(old_record.attributes, field) is not None
                    and getattr(character.attributes, field) is None
                ):
                    raise ValueError(f"Lost known {field} of {old_record.candidate_name}")
            if (
                old_record.attributes.personality_traits
                and not character.attributes.personality_traits
            ):
                raise ValueError(f"Lost personality traits of {old_record.candidate_name}")
        order = previous_order[ids[0]] if ids else len(previous) + index
        updates.append((order, character))

    if consumed != set(previous_by_id):
        raise ValueError(f"Lost existing characters: {sorted(set(previous_by_id) - consumed)}")

    redirects = {cid: cid for cid in previous_by_id}
    assigned = []
    for _, character in sorted(updates, key=lambda update: update[0]):
        character_id = character.character_id
        if character_id not in previous_by_id:
            character_id = f"char_{next_number:03d}"
            next_number += 1
        redirects[character.character_id] = character_id
        for retired_id in character.merged_character_ids:
            redirects[retired_id] = character_id
        assigned.append((character_id, character))

    records = []
    for character_id, character in assigned:
        relationships: dict[str, str] = {}
        for target, description in character.relationships.items():
            if target not in redirects:
                raise ValueError(f"Unknown relationship target: {target}")
            if target == character.character_id:
                raise ValueError("A character cannot relate to itself")
            resolved = redirects[target]
            if resolved == character_id:
                continue  # A merge invalidates relationships between the merged identities.
            if resolved in relationships and relationships[resolved] != description:
                relationships[resolved] += "; " + description
            else:
                relationships[resolved] = description
        records.append(
            CharacterRecord.model_validate(
                {
                    **character.model_dump(exclude={"merged_character_ids"}),
                    "character_id": character_id,
                    "relationships": relationships,
                }
            )
        )
    by_id = {record.character_id: record for record in records}
    for old in previous:
        source = redirects[old.character_id]
        for target, description in old.relationships.items():
            resolved = redirects[target]
            if resolved != source:
                by_id[source].relationships.setdefault(resolved, description)
    return records, next_number


def save_records(path: Path, records: Sequence[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    try:
        temporary.write_text(
            json.dumps([record.model_dump() for record in records], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


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
