import re

from pov_retell.ingest.graph.extract_character.model import CharacterRecord, IdentityResponse
from pov_retell.ingest.model import Chapter


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def appears_in_source(value: str, source: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(normalized(value)) + r"(?!\w)", source) is not None


def unique_names(names: list[str]) -> list[str]:
    result: dict[str, str] = {}
    for name in names:
        result.setdefault(normalized(name), name)
    return list(result.values())


def combine_descriptions(first: str | None, second: str | None) -> str | None:
    parts = [part for value in (first, second) if value for part in value.split("; ")]
    return "; ".join(unique_names(parts)) or None


def focus_is_ambiguous(
    character: CharacterRecord,
    records: list[CharacterRecord],
    current_names: list[str],
    current_context: str | None,
) -> bool:
    names = {normalized(n) for n in current_names}
    others = [record for record in records if record.character_id != character.character_id]
    other_names = {
        normalized(name) for record in others for name in [record.candidate_name, *record.aliases]
    }
    if names - other_names:
        return False
    context = normalized(current_context or "")
    return (
        not context
        or context in names
        or any(context == normalized(record.identity_context or "") for record in others)
    )


def apply_identities(
    response: IdentityResponse,
    previous: list[CharacterRecord],
    next_number: int,
    redirects: dict[str, str],
    chapter: Chapter,
) -> tuple[list[CharacterRecord], list[str], int, dict[str, str]]:
    records = {c.character_id: c.model_copy(deep=True) for c in previous}
    order = {c.character_id: i for i, c in enumerate(previous)}
    used: set[str] = set()
    local_ids: set[str] = set()
    active: list[str] = []
    redirects = dict(redirects)
    source = normalized(" ".join(chapter.paragraphs.values()))

    for proposal in response.characters:
        cid = proposal.character_id
        if cid in local_ids:
            raise ValueError("A character ID cannot appear more than once")
        local_ids.add(cid)
        if proposal.identity_context and not appears_in_source(proposal.identity_context, source):
            raise ValueError("The identifying context was not found in the chapter")
        is_new = cid not in order
        if is_new and not re.fullmatch(r"new_[1-9]\d*", cid):
            raise ValueError("The LLM returned an unknown character ID")
        if is_new and proposal.merged_character_ids:
            raise ValueError("A merge must retain an existing character ID")
        ids = ([] if is_new else [cid]) + proposal.merged_character_ids
        if len(ids) != len(set(ids)) or used.intersection(ids):
            raise ValueError("A character ID cannot be updated or merged more than once")
        if any(old_id not in order for old_id in ids):
            raise ValueError("A merge contains an unknown character ID")
        if ids and ids[0] != min(ids, key=order.__getitem__):
            raise ValueError("A merge must retain the earliest character ID")
        used.update(ids)
        known_names = list(proposal.names_in_chapter)
        for old_id in ids:
            known_names.extend([records[old_id].candidate_name, *records[old_id].aliases])
        if is_new:
            cid = f"char_{next_number:03d}"
            next_number += 1
            record = CharacterRecord(character_id=cid, candidate_name=proposal.candidate_name)
            records[cid] = record
        else:
            record = records[cid]
        for retired_id in proposal.merged_character_ids:
            retired = records.pop(retired_id)
            for field in ("gender", "species", "age_description", "physical_description"):
                setattr(
                    record.attributes,
                    field,
                    combine_descriptions(
                        getattr(record.attributes, field), getattr(retired.attributes, field)
                    ),
                )
            record.attributes.personality_traits = unique_names(
                record.attributes.personality_traits + retired.attributes.personality_traits
            )
            redirects[retired_id] = cid
            record.resolution_status = "candidate"
        if proposal.identity_context:
            record.identity_context = proposal.identity_context
        record.candidate_name = proposal.candidate_name
        record.aliases = [
            n
            for n in unique_names(known_names)
            if normalized(n) != normalized(record.candidate_name)
        ]
        active.append(cid)

    for retired_id, target in list(redirects.items()):
        while target in redirects:
            target = redirects[target]
        redirects[retired_id] = target
    return list(records.values()), active, next_number, redirects
