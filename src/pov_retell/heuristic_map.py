"""Step A2b, default way: classify candidates with generic typographic rules (no LLM, no cost).

The rules look at HOW a heading is written ("CHAPTER IV", "PART ONE", a lone roman numeral,
"Prologue"), never at WHICH book it is: there is no book-specific code anywhere in this project.
The result is only a proposal; the same cut and validation (cut.py) run on it, exactly as they
run on the LLM's map.
"""

import re

from pov_retell.models import Candidate, CandidateRole, MapItem, UnitKind
from pov_retell.text import NUMBER, ROMAN, iter_blocks, merge_titles

_LICENSE = re.compile(r"gutenberg|licen[sc]e|transcriber", re.I)
_PART = re.compile(rf"^(?:part|book|volume)\s*{NUMBER}\b(?:\W.*)?$", re.I)
_CHAPTER = re.compile(rf"^(?:chapter|chap\.|letter|stave|canto)\s*{NUMBER}\b(?:\W.*)?$", re.I)
_NUMERAL_LEAD = re.compile(rf"^(?:\d+|{ROMAN})(?:[.:\s]|$)")  # capitals only: "XXXIV And Last"
_BODY_KEYWORD = re.compile(r"^(?:prologue|epilogue|interlude|prelude)\b", re.I)
_FRONT_KEYWORD = re.compile(
    r"^(?:table of contents|contents|preface|foreword|introduction|dedication|epigraph|"
    r"list of illustrations|illustrations)\b",
    re.I,
)
_TOC_KEYWORD = re.compile(r"^(?:table of )?contents\b", re.I)
# "He rode a black horse. CHAPTER III." : an illustration caption inside the heading
_CAPTION_THEN_HEADING = re.compile(
    rf"^.+?\s+((?:chapter|chap\.|letter|stave|canto)\s*{NUMBER}\b\W*)$", re.I
)
_TOC_MAX_GAP = 1200  # a TOC entry is followed by its sub-entries only, never by chapter prose


def heuristic_map(candidates: list[Candidate], canonical_text: str) -> list[MapItem]:
    """Give every candidate a role; the first matching rule wins."""
    toc_entries = _toc_entry_ids(candidates)
    items: list[MapItem] = []
    seen_body = False  # after the first chapter, unrecognised headings are back matter
    open_part: str | None = None

    for index, cand in enumerate(candidates):
        text = cand.text.strip()
        role: CandidateRole
        kind: UnitKind
        parent: str | None = None
        previous = items[-1] if items else None

        if cand.kind == "license_marker" or _LICENSE.search(text):
            role, kind = "license", ("back" if seen_body else "front")
        elif cand.cand_id in toc_entries or _TOC_KEYWORD.match(text):
            role, kind = "toc", "front"
        elif _PART.match(text):
            role, kind, seen_body, open_part = "part_heading", "part", True, cand.cand_id
        elif _CHAPTER.match(text):
            role, kind, seen_body, parent = "body_unit", _chapter_kind(text), True, open_part
        elif caption_match := _CAPTION_THEN_HEADING.match(text):
            text = caption_match.group(1).strip()
            role, kind, seen_body, parent = "body_unit", _chapter_kind(text), True, open_part
        elif _FRONT_KEYWORD.match(text):
            role, kind = "front", "front"
        elif _BODY_KEYWORD.match(text):
            role, kind, seen_body, parent = "body_unit", "section", True, open_part
        elif _NUMERAL_LEAD.match(text):
            role, kind, seen_body, parent = "body_unit", "chapter", True, open_part
        elif (
            previous is not None
            and previous.role in ("body_unit", "part_heading")
            and _only_heading_between(canonical_text, candidates[index - 1], cand)
        ):
            # a subtitle right under the previous heading: it belongs to that title
            previous.title = merge_titles(previous.title, text)
            role, kind = "front", "front"
        else:
            role, kind = ("back", "back") if seen_body else ("front", "front")

        items.append(
            MapItem(
                cand_id=cand.cand_id, role=role, unit_kind=kind, title=text, parent_cand_id=parent
            )
        )
    return items


def _chapter_kind(text: str) -> UnitKind:
    return "letter" if text.lower().startswith("letter") else "chapter"


def _only_heading_between(text: str, earlier: Candidate, later: Candidate) -> bool:
    """True when nothing but `earlier`'s own heading block lies before `later`."""
    return sum(1 for _ in iter_blocks(text, earlier.char_pos, later.char_pos)) <= 1


def _toc_entry_ids(candidates: list[Candidate]) -> set[str]:
    """Headings listed again further down, right before the next heading, are TOC lines.

    A real chapter heading is followed by pages of prose (a big gap to the next candidate); a
    TOC line is followed immediately by the next TOC line.
    """
    tokens = [re.findall(r"\w+", c.text.casefold()) for c in candidates]
    entries: set[str] = set()
    for index, mine in enumerate(tokens):
        if not mine or index + 1 >= len(candidates):
            continue
        if candidates[index + 1].char_pos - candidates[index].char_pos > _TOC_MAX_GAP:
            continue
        for later in tokens[index + 1 :]:
            if later and (mine[: len(later)] == later or later[: len(mine)] == mine):
                entries.add(candidates[index].cand_id)
                break
    return entries
