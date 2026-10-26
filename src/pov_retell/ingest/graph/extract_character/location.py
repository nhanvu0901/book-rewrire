import json
import re

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character.identity import normalized, unique_names
from pov_retell.ingest.graph.extract_character.model import (
    ExtractLocationResponse,
    LocationRecord,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_location import (
    PROMPT_EXTRACT_LOCATION,
)
from pov_retell.ingest.model import Chapter

NEW_LOCATION_ID_RE = re.compile(r"^new_[1-9]\d*$")


def _merge_aliases(prior: list[str], added: list[str], *, exclude: str) -> list[str]:
    excl = normalized(exclude)
    return [name for name in unique_names(prior + added) if normalized(name) != excl]


def extract_locations(
    llm: JsonLLM,
    title: str,
    chapter: Chapter,
    locations: list[LocationRecord],
    next_number: int,
    previous_book_summary: str,
) -> ExtractLocationResponse:
    existing_json = json.dumps(
        [loc.model_dump() for loc in locations],
        ensure_ascii=False,
    )
    prompt = PROMPT_EXTRACT_LOCATION.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=previous_book_summary,
        existing_locations_json=existing_json,
        chapter_text=chapter.text,
    )

    def check(response: ExtractLocationResponse) -> None:
        validate_locations(response, locations, next_number)

    return llm.complete_json(prompt, ExtractLocationResponse, check=check)


def validate_locations(
    response: ExtractLocationResponse,
    previous: list[LocationRecord],
    next_number: int,
) -> tuple[list[LocationRecord], int]:
    records = [loc.model_copy(deep=True) for loc in previous]
    by_id: dict[str, LocationRecord] = {loc.location_id: loc for loc in records}
    original_ids = set(by_id)

    seen_ids: set[str] = set()
    new_id_map: dict[str, str] = {}

    for item in response.locations:
        loc_id = item.location_id
        if loc_id in seen_ids:
            raise ValueError(f"Duplicate location_id in response: {loc_id}")
        seen_ids.add(loc_id)

        if item.kind is not None and len(item.kind.split()) > 12:
            raise ValueError(f"Location kind must have at most 12 words: {item.kind!r}")

        if loc_id.startswith("new_"):
            if not NEW_LOCATION_ID_RE.fullmatch(loc_id):
                raise ValueError(f"Invalid new location_id format: {loc_id}")
            assigned_id = f"loc_{next_number:03d}"
            next_number += 1
            new_id_map[loc_id] = assigned_id
        elif loc_id not in by_id:
            raise ValueError(f"Unknown location_id: {loc_id}")

    for item in response.locations:
        resolved_id = new_id_map.get(item.location_id, item.location_id)
        resolved_part_of: str | None = None
        if item.part_of is not None:
            if item.part_of.startswith("new_"):
                if item.part_of not in new_id_map:
                    raise ValueError(f"Unknown part_of location_id: {item.part_of}")
                resolved_part_of = new_id_map[item.part_of]
            elif item.part_of in original_ids:
                resolved_part_of = item.part_of
            else:
                raise ValueError(f"Unknown part_of location_id: {item.part_of}")
            if resolved_part_of == resolved_id:
                raise ValueError(f"Location cannot be part_of itself: {item.location_id}")

        if item.location_id in new_id_map:
            aliases = _merge_aliases([], item.aliases, exclude=item.name)
            created = LocationRecord(
                location_id=resolved_id,
                name=item.name,
                aliases=aliases,
                kind=item.kind,
                part_of=resolved_part_of,
            )
            records.append(created)
            by_id[resolved_id] = created
        else:
            existing = by_id[resolved_id]
            prior_names = list(existing.aliases)
            if item.name.casefold() != existing.name.casefold():
                prior_names.append(existing.name)
            existing.name = item.name
            existing.aliases = _merge_aliases(prior_names, item.aliases, exclude=item.name)
            if item.kind is not None:
                existing.kind = item.kind
            if item.part_of is not None:
                existing.part_of = resolved_part_of

    parent_map = {loc.location_id: loc.part_of for loc in records}
    for loc in records:
        visited = {loc.location_id}
        curr = loc.part_of
        while curr is not None:
            if curr in visited:
                raise ValueError(f"Location part_of cycle detected involving {loc.location_id}")
            visited.add(curr)
            curr = parent_map.get(curr)

    return records, next_number
