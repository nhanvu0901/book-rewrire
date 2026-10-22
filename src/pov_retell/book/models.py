"""Every data shape phase A produces, in one file.

Read this first: the models are the vocabulary of the whole pipeline. They follow the table
design in section 5.1 of the system design (books, structure_candidates, structure maps, units,
paragraphs), so the next step can load them into Postgres without renaming anything.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Bump when the layout of book.json changes, so readers can tell which layout they hold.
SCHEMA_VERSION = 1

BookFormat = Literal["html", "epub", "txt"]
MapMethod = Literal["heuristic", "llm"]  # legacy heuristic files remain readable
UnitKind = Literal["chapter", "letter", "part", "section", "front", "back"]

# How code found a candidate (A2a).
CandidateKind = Literal[
    "heading",  # html/epub h1-h4
    "toc_link",  # html/epub: target of an internal link (a table-of-contents entry)
    "anchor",  # html/epub: unlinked anchor whose id looks structural ("chap3")
    "spine_item",  # epub: a document of the reading order
    "section_header",  # txt: "CHAPTER 3", "PART ONE"
    "section_keyword",  # txt: "CONTENTS", "PREFACE"
    "numeral_header",  # txt: a line holding only a roman or arabic numeral
    "caps_line",  # txt: a short ALL-CAPS line set apart by blank lines
    "license_marker",  # txt/html: "*** START/END OF THE PROJECT GUTENBERG ..."
]

# What the structure map says a candidate is (A2b).
CandidateRole = Literal["front", "toc", "license", "body_unit", "part_heading", "back"]

# Kinds a narrative unit (one that gets retold) can have. Parts only group chapters.
NARRATIVE_KINDS: tuple[UnitKind, ...] = ("chapter", "letter", "section")


class Book(BaseModel):
    """A1: what we know about the file."""

    id: str  # slug of the title, e.g. "pride-and-prejudice"; names the output directory
    title: str
    author: str
    format: BookFormat
    sha256: str  # fingerprint of the file bytes: a different edition gives a different hash
    source: str  # the path or URL the file came from


class Candidate(BaseModel):
    """A2a: a place in the text that MIGHT start a unit. Code finds them; it does not decide."""

    cand_id: str  # "cand_001", numbered in reading order
    kind: CandidateKind
    text: str
    char_pos: int  # offset into the canonical text
    preview: str = ""  # the first words at that position, to help whoever classifies it


class MapItem(BaseModel):
    """A2b: the LLM's classification of one candidate (or a stored legacy map)."""

    cand_id: str
    role: CandidateRole
    unit_kind: UnitKind
    title: str  # the clean title the unit will carry
    parent_cand_id: str | None = None  # a chapter points at its part_heading


class MapResponse(BaseModel):
    """The JSON the LLM must answer with (see llm_map.py)."""

    items: list[MapItem] = Field(default_factory=list)


class Unit(BaseModel):
    """A2c: a slice of the canonical text: one chapter, letter, section or part heading."""

    id: str  # "u04": u + order
    order: int
    kind: UnitKind
    title: str
    parent_id: str | None = None  # a chapter's part, when the book has parts
    char_start: int
    char_end: int


class Paragraph(BaseModel):
    """A3: one paragraph with an id that never changes (everything later points at it)."""

    id: str  # "u04_p041": unit 4, paragraph 41
    unit_id: str
    order: int
    text: str  # whitespace collapsed to single spaces
    char_start: int
    char_end: int
    flags: list[str] = Field(default_factory=list)  # anomaly flags, see paragraphs.py


class ExtractedBook(BaseModel):
    """Everything phase A produces for one book: this is what book.json holds."""

    schema_version: int = SCHEMA_VERSION
    book: Book
    map_method: MapMethod
    candidates: list[Candidate]
    map_items: list[MapItem]
    units: list[Unit]
    paragraphs: list[Paragraph]
    warnings: list[str] = Field(default_factory=list)
    # The cleaned text every char_start/char_end points into. It is saved as canonical.txt,
    # not inside book.json, to keep book.json readable.
    canonical_text: str = Field(default="", exclude=True)
