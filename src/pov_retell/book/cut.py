"""Step A2c: cut the canonical text into units exactly where the structure map says, and VALIDATE.

Code cuts and checks; the LLM map only chooses which candidates are boundaries.
The units form ONE contiguous partition of the story body, in reading order:

    PART ONE | CHAPTER I | CHAPTER II | PART TWO | CHAPTER III

Part units hold only their heading; chapters point at their part through `parent_id`.
Front matter (before the first boundary) and back matter / licence (after the story) are not
units at all, so they can never leak into a retelling.

A bad map is REJECTED with a clear error, never silently repaired: a wrong cut makes every
later step wrong, so it is better to stop here.
"""

from pov_retell.book.models import NARRATIVE_KINDS, Candidate, MapItem, Unit, UnitKind


class StructureMapError(ValueError):
    """The structure map cannot be turned into valid units."""


def cut_units(
    canonical_text: str, candidates: list[Candidate], items: list[MapItem]
) -> tuple[list[Unit], list[str]]:
    """Return the validated units and warnings; raise StructureMapError if the cut is invalid."""
    warnings: list[str] = []
    pos = {c.cand_id: c.char_pos for c in candidates}
    text_of = {c.cand_id: c.text for c in candidates}
    # The boundaries: every candidate the map calls a chapter-like unit or a part heading.
    chosen = sorted(
        (i for i in items if i.role in ("body_unit", "part_heading")), key=lambda i: pos[i.cand_id]
    )
    if not any(i.role == "body_unit" for i in chosen):
        raise StructureMapError("the structure map has no body units to cut")

    # The story ends where the first back-matter or licence candidate after the last unit starts.
    after = [pos[i.cand_id] for i in items if i.role in ("back", "license")]
    body_end = min((p for p in after if p > pos[chosen[-1].cand_id]), default=len(canonical_text))

    unit_id = {i.cand_id: f"u{order:02d}" for order, i in enumerate(chosen, start=1)}
    parts = {i.cand_id for i in chosen if i.role == "part_heading"}
    units: list[Unit] = []
    last_part: MapItem | None = None
    for order, item in enumerate(chosen, start=1):
        parent = item.parent_cand_id
        parent_id: str | None = None
        if item.role == "part_heading":
            last_part = item
        elif parent is not None and parent in parts:
            parent_id = unit_id[parent]
        elif last_part is not None:  # the map forgot (or invented) the parent: go on, but say so
            warnings.append(f"cut: {item.title!r} follows part {last_part.title!r} without parent")
        kind: UnitKind = "part" if item.role == "part_heading" else item.unit_kind
        if kind not in (*NARRATIVE_KINDS, "part"):
            kind = "chapter"  # a body unit is always narrative, whatever the map said
        units.append(
            Unit(
                id=unit_id[item.cand_id],
                order=order,
                kind=kind,
                title=" ".join((item.title or text_of[item.cand_id]).split()),
                parent_id=parent_id,
                char_start=pos[item.cand_id],
                char_end=pos[chosen[order].cand_id] if order < len(chosen) else body_end,
            )
        )

    errors = validate_units(units, canonical_text, units[0].char_start, body_end)
    if errors:
        raise StructureMapError("unit validation failed: " + "; ".join(errors))
    return units, warnings


def validate_units(units: list[Unit], text: str, body_start: int, body_end: int) -> list[str]:
    """Return the problems found (an empty list means valid).

    Checks: ordered, non-empty, contiguous (no gap, no overlap), covering the whole story body
    [body_start, body_end), and every part followed by a chapter. That last check catches
    table-of-contents lines ("PART ONE ... PART SIX") mistaken for part headings.
    """
    if not units:
        return ["no units generated"]
    errors: list[str] = []
    for index, unit in enumerate(units):
        if unit.order != index + 1:
            errors.append(f"unit {unit.id} has order {unit.order}, expected {index + 1}")
        if unit.char_start >= unit.char_end:
            errors.append(f"unit {unit.id} has invalid range [{unit.char_start}, {unit.char_end})")
        elif not text[unit.char_start : unit.char_end].strip():
            errors.append(f"unit {unit.id} ({unit.title!r}) is empty")
        following = units[index + 1] if index + 1 < len(units) else None
        if unit.kind == "part" and (following is None or following.kind == "part"):
            errors.append(f"part {unit.id} ({unit.title!r}) has no chapters")
    for before, after in zip(units, units[1:], strict=False):
        if before.char_end != after.char_start:
            problem = "gap" if before.char_end < after.char_start else "overlap"
            errors.append(f"{problem} between {before.id} and {after.id}")
    if units[0].char_start != body_start:
        errors.append(f"first unit starts at {units[0].char_start}, body starts at {body_start}")
    if units[-1].char_end != body_end:
        errors.append(f"last unit ends at {units[-1].char_end}, body ends at {body_end}")
    return errors
