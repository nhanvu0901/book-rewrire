import json
from pathlib import Path
from typing import Any

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character.identity import (
    appears_in_source,
    apply_identities,
    combine_descriptions,
    normalized,
    unique_names,
)
from pov_retell.ingest.graph.extract_character.model import (
    CharacterIdentity,
    CharacterRecord,
    ExtractCharacterResponse,
    IdentityResponse,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_character import PROMPT_EXTRACT_CHAR
from pov_retell.ingest.model import Chapter


def extract_characters(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    characters: list[CharacterRecord],
    next_number: int,
    redirects: dict[str, str],
    previous_book_summary: str,
) -> ExtractCharacterResponse:
    prompt = PROMPT_EXTRACT_CHAR.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        existing_characters_json=json.dumps(
            [c.model_dump() for c in characters], ensure_ascii=False
        ),
        previous_book_summary=previous_book_summary,
        chapter_text=chapter.text,
    )

    def check(response: ExtractCharacterResponse) -> None:
        validate_characters(response, characters, next_number, redirects, chapter)

    return llm.complete_json(prompt, ExtractCharacterResponse, check=check)


def validate_characters(
    response: ExtractCharacterResponse,
    previous: list[CharacterRecord],
    next_number: int,
    redirects: dict[str, str],
    chapter: Chapter,
) -> tuple[list[CharacterRecord], list[str], int, dict[str, str]]:
    previous_by_id = {c.character_id: c for c in previous}
    for proposal in response.characters:
        old = previous_by_id.get(proposal.character_id)
        status = old.resolution_status if old and not proposal.merged_character_ids else "candidate"
        if proposal.resolution_status != status:
            raise ValueError("The LLM cannot verify a new or merged character")
    identities = IdentityResponse(
        characters=[
            CharacterIdentity(
                character_id=p.character_id,
                candidate_name=p.candidate_name,
                names_in_chapter=[p.candidate_name, *p.aliases],
                merged_character_ids=p.merged_character_ids,
            )
            for p in response.characters
        ]
    )
    records, active, next_number, redirects = apply_identities(
        identities, previous, next_number, redirects, chapter
    )
    by_id = {record.character_id: record for record in records}
    source = normalized(" ".join(chapter.paragraphs.values()))
    for proposal, cid in zip(response.characters, active, strict=True):
        record = by_id[cid]
        for field in ("gender", "species", "age_description", "physical_description"):
            value = getattr(proposal.attributes, field)
            if value is not None:
                if field in ("age_description", "physical_description"):
                    value = combine_descriptions(getattr(record.attributes, field), value)
                setattr(record.attributes, field, value)
        record.attributes.personality_traits = unique_names(
            record.attributes.personality_traits
            + [
                trait
                for trait in proposal.attributes.personality_traits
                if appears_in_source(trait, source)
            ]
        )
    return records, active, next_number, redirects


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
