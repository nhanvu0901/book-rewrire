"""Step A3: split each unit into paragraphs with stable ids, and flag the odd ones.

A paragraph id like `u04_p041` (unit 4, paragraph 41) never changes. Every later fact points
back at it, so a human can check any claim against the source, and the LLM can answer with an
id instead of copying text.

Flags do not remove anything: they tell the human where the extraction may have gone wrong.
"""

import re

from pov_retell.book.models import NARRATIVE_KINDS, Candidate, Paragraph, Unit
from pov_retell.book.text import iter_blocks

TOO_SHORT_CHARS = 10
TOO_LONG_CHARS = 3000
TOO_LONG_WORDS = 500
_SHORT_OK_CHARS = frozenset("\"“”'‘’—*")  # dialogue, dashes and scene breaks may be short
_GLUED_HEADER = re.compile(r"^(?i:chapter|chap\.|part|book|volume)\s+(?:\d+|[IVXLCDM]+)\b")
_GLUED_HEADER_MIN_CHARS = 120
_LICENSE = re.compile(r"project gutenberg|gutenberg-tm|gutenberg literary|full license", re.I)
_HEADING_TITLE_MAX_CHARS = 120


def paragraph_flags(text: str) -> list[str]:
    """`too_short`, `too_long` (a missed break), `suspicious_header` (a heading glued to prose),
    `license_leak` (Gutenberg boilerplate inside the story)."""
    flags: list[str] = []
    if len(text) < TOO_SHORT_CHARS and not _SHORT_OK_CHARS.intersection(text):
        flags.append("too_short")
    if len(text) > TOO_LONG_CHARS or len(text.split()) > TOO_LONG_WORDS:
        flags.append("too_long")
    if len(text) > _GLUED_HEADER_MIN_CHARS and _GLUED_HEADER.search(text):
        flags.append("suspicious_header")
    if _LICENSE.search(text):
        flags.append("license_leak")
    return flags


def split_paragraphs(
    units: list[Unit], canonical_text: str, candidates: list[Candidate]
) -> list[Paragraph]:
    """Paragraphs of every narrative unit (parts only hold their heading).

    Heading blocks at the top of a unit (blocks that start at a candidate position, or that just
    repeat the unit's title) belong to the title, not to the story text, so they are skipped.
    """
    heading_positions = {c.char_pos for c in candidates}
    paragraphs: list[Paragraph] = []
    for unit in units:
        if unit.kind not in NARRATIVE_KINDS:
            continue
        title = _normalise(unit.title)
        in_heading = True
        count = 0
        for block in iter_blocks(canonical_text, unit.char_start, unit.char_end):
            if in_heading and (
                block.start in heading_positions or _repeats_title(block.text, title)
            ):
                continue
            in_heading = False
            count += 1
            paragraphs.append(
                Paragraph(
                    id=f"{unit.id}_p{count:03d}",
                    unit_id=unit.id,
                    order=count,
                    text=block.text,
                    char_start=block.start,
                    char_end=block.end,
                    flags=paragraph_flags(block.text),
                )
            )
    return paragraphs


def _repeats_title(text: str, normalised_title: str) -> bool:
    normalised = _normalise(text)
    return (
        bool(normalised)
        and len(text) <= _HEADING_TITLE_MAX_CHARS
        and normalised in normalised_title
    )


def _normalise(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())
