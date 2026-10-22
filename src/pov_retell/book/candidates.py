"""Step A2a: build the canonical text and find structure candidates (code only, no LLM).

The *canonical text* is the single source of truth for everything after this step: units and
paragraphs are slices of it, and the LLM only ever points at it by candidate id. A *candidate*
is any place that COULD start a unit (an HTML heading, a table-of-contents link, an
all-caps line...). This step finds them all, generously; step A2b decides which ones are real.
"""

import io
import posixpath
import re
from dataclasses import dataclass
from urllib.parse import unquote

from pov_retell.book.html_text import HtmlBlock, Link, html_to_blocks
from pov_retell.book.models import BookFormat, Candidate, CandidateKind
from pov_retell.book.text import NUMBER, ROMAN, contains_words, merge_titles, words

PREVIEW_CHARS = 160
LICENSE_MARKER = re.compile(r"^\*{3}\s*(?:START|END) OF (?:THE|THIS) PROJECT GUTENBERG", re.I)

# When several candidates sit at the same position, keep the most informative one.
_KIND_PRIORITY: tuple[CandidateKind, ...] = (
    "spine_item", "heading", "license_marker", "section_header", "section_keyword",
    "numeral_header", "caps_line", "toc_link", "anchor",
)  # fmt: skip
_STRUCTURAL_ANCHOR = re.compile(r"chap|part|book|vol|sect|prolog|epilog", re.I)
_FOOTNOTE_LINK_TEXT = re.compile(r"^[\[(]?\s*(?:\d+|[*†‡§¶]+)\s*[\])]?$")


def find_candidates(content: bytes, book_format: BookFormat) -> tuple[str, list[Candidate]]:
    """Return `(canonical_text, candidates)`; candidates are in reading order."""
    if book_format == "html":
        return _from_html(content)
    if book_format == "epub":
        return _from_epub(content)
    return _from_txt(content)


@dataclass
class _Raw:
    kind: CandidateKind
    text: str
    pos: int


def _finalize(raw: list[_Raw], canonical: str) -> list[Candidate]:
    """One candidate per position (the best kind wins), numbered in reading order."""
    rank = {kind: i for i, kind in enumerate(_KIND_PRIORITY)}
    best: dict[int, _Raw] = {}
    for cand in raw:
        if cand.pos not in best or rank[cand.kind] < rank[best[cand.pos].kind]:
            best[cand.pos] = cand
    return [
        Candidate(
            cand_id=f"cand_{index:03d}",
            kind=best[pos].kind,
            text=best[pos].text,
            char_pos=pos,
            preview=" ".join(canonical[pos : pos + PREVIEW_CHARS].split()),
        )
        for index, pos in enumerate(sorted(best), start=1)
    ]


# ------------------------------------------------------------------ html and epub


class _Builder:
    """Joins documents' blocks into the canonical text, remembering where each id and doc starts.

    That memory is what turns a link like `href="ch2.xhtml#top"` into a position in the text.
    """

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.length = 0
        self.id_pos: dict[tuple[str, str], int] = {}
        self.doc_start: dict[str, int] = {}

    def add_document(self, doc: str, blocks: list[HtmlBlock]) -> list[int]:
        """Append a document's blocks; return where each block starts."""
        positions: list[int] = []
        for index, block in enumerate(blocks):
            positions.append(self.length)
            if index == 0:
                self.doc_start[doc] = self.length
            for anchor_id in block.ids:
                self.id_pos.setdefault((doc, anchor_id), self.length)
            self.parts.append(block.text + "\n\n")
            self.length += len(block.text) + 2
        return positions

    def resolve(self, href: str, current_doc: str) -> int | None:
        """The text position an href points at, or None when it points outside the book."""
        path, _, fragment = href.partition("#")
        doc: str | None = current_doc
        if path:
            target = posixpath.normpath(
                posixpath.join(posixpath.dirname(current_doc), unquote(path))
            )
            doc = self._match_document(target)
        if doc is None:
            return None
        if fragment:
            return self.id_pos.get((doc, unquote(fragment)))
        return self.doc_start.get(doc)

    def _match_document(self, name: str) -> str | None:
        if name in self.doc_start:
            return name
        same_name = [d for d in self.doc_start if posixpath.basename(d) == posixpath.basename(name)]
        return same_name[0] if len(same_name) == 1 else None


def _block_candidates(blocks: list[HtmlBlock], positions: list[int]) -> list[_Raw]:
    """Headings, structural-looking anchors and Gutenberg start/end markers."""
    found: list[_Raw] = []
    for block, pos in zip(blocks, positions, strict=True):
        if block.is_heading:
            found.append(_Raw("heading", block.text, pos))
        elif LICENSE_MARKER.match(block.text):
            found.append(_Raw("license_marker", block.text, pos))
        found += [
            _Raw("anchor", anchor_id, pos)
            for anchor_id in block.ids
            if _STRUCTURAL_ANCHOR.search(anchor_id)
        ]
    return found


def _link_candidates(links: list[Link], current_doc: str, builder: _Builder) -> list[_Raw]:
    """Targets of internal links are likely table-of-contents entries; the link text titles them."""
    seen: set[int] = set()
    found: list[_Raw] = []
    for link in links:
        if not _is_navigation_text(link.text):
            continue
        pos = builder.resolve(link.href, current_doc)
        if pos is not None and pos not in seen:
            seen.add(pos)
            found.append(_Raw("toc_link", link.text, pos))
    return found


def _is_navigation_text(text: str) -> bool:
    """A link text can be a TOC entry; footnote markers like '[1]' or '*' cannot."""
    return bool(re.search(r"\w", text)) and not _FOOTNOTE_LINK_TEXT.match(text)


def _from_html(content: bytes) -> tuple[str, list[Candidate]]:
    blocks, links = html_to_blocks(content)
    builder = _Builder()
    positions = builder.add_document("", blocks)
    raw = _block_candidates(blocks, positions) + _link_candidates(links, "", builder)
    canonical = "".join(builder.parts)
    return canonical, _finalize(raw, canonical)


def _from_epub(content: bytes) -> tuple[str, list[Candidate]]:
    """Walk the spine (the reading order) and use the book's own navigation as extra evidence."""
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(io.BytesIO(content))
    toc_titles, toc_targets = _flatten_toc(book.toc)
    builder = _Builder()
    raw: list[_Raw] = []
    documents: list[tuple[str, list[HtmlBlock], list[int]]] = []
    doc_links: list[tuple[str, list[Link]]] = []

    for entry in book.spine:
        item = book.get_item_with_id(entry[0] if isinstance(entry, tuple) else entry)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        if isinstance(item, epub.EpubNav):
            continue  # the generated table of contents is navigation, not book text
        doc = item.get_name()
        blocks, links = html_to_blocks(item.get_content())
        positions = builder.add_document(doc, blocks)
        if blocks:
            documents.append((doc, blocks, positions))
            doc_links.append((doc, links))
            raw += _block_candidates(blocks, positions)

    for doc, blocks, positions in documents:
        nav_title = _nav_title_for(doc, toc_titles)
        if not _headings_name_the_document(blocks, nav_title):
            title = nav_title or blocks[0].text[:50].rsplit(" ", 1)[0]
            raw.append(_Raw("spine_item", title, positions[0]))

    for href, title in toc_targets:  # navigation entries that point inside a document
        pos = builder.resolve(href, "")
        if pos is not None and _is_navigation_text(title):
            raw.append(_Raw("toc_link", title, pos))
    for doc, links in doc_links:
        raw += _link_candidates(links, doc, builder)

    canonical = "".join(builder.parts)
    return canonical, _finalize(raw, canonical)


def _flatten_toc(toc: object) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Return ({document name: nav title}, [(href with #fragment, nav title)])."""
    titles: dict[str, str] = {}
    targets: list[tuple[str, str]] = []

    def visit(node: object) -> None:
        if isinstance(node, list | tuple):
            for child in node:
                visit(child)
            return
        href, title = getattr(node, "href", None), getattr(node, "title", None)
        if isinstance(href, str) and isinstance(title, str) and title.strip():
            path, _, fragment = href.partition("#")
            clean = " ".join(title.split())
            if fragment:
                targets.append((href, clean))
            else:
                titles.setdefault(posixpath.normpath(unquote(path)), clean)

    visit(toc)
    return titles, targets


def _nav_title_for(doc: str, toc_titles: dict[str, str]) -> str | None:
    if doc in toc_titles:
        return toc_titles[doc]
    same_name = [
        t for n, t in toc_titles.items() if posixpath.basename(n) == posixpath.basename(doc)
    ]
    return same_name[0] if len(same_name) == 1 else None


def _headings_name_the_document(blocks: list[HtmlBlock], nav_title: str | None) -> bool:
    """True when the document opens with a heading, or a heading in it repeats the nav title.

    A navigation title is only trusted as a boundary when no heading explains it: EPUB files are
    often split mid-chapter, and then the nav title points at a heading further down the file.
    """
    if blocks[0].is_heading:
        return True
    if nav_title is None:
        return False
    title_words = words(nav_title)
    return any(
        b.is_heading
        and (
            contains_words(title_words, words(b.text)) or contains_words(words(b.text), title_words)
        )
        for b in blocks
    )


# ------------------------------------------------------------------ txt

_SECTION_HEADER = re.compile(
    rf"^(?:PART|BOOK|VOLUME|SECTION|CHAPTER|CHAP\.|LETTER|STAVE|CANTO|ACT|SCENE)\s+{NUMBER}\b(?:\W.*)?$",
    re.I,
)
_SECTION_KEYWORD = re.compile(
    r"^(?:CONTENTS|TABLE OF CONTENTS|LIST OF ILLUSTRATIONS|ILLUSTRATIONS|PREFACE|FOREWORD|"
    r"INTRODUCTION|DEDICATION|PROLOGUE|EPILOGUE|AFTERWORD|APPENDIX|GLOSSARY|NOTES|INDEX|"
    r"THE END|FINIS)\.?$",
    re.I,
)
_NUMERAL_LINE = re.compile(rf"^(?:{ROMAN}|\d{{1,3}})[.:]?$")  # roman numerals only in capitals
_MAX_HEADING_LINE = 80
_MAX_SUBTITLE_LINE = 60


def _from_txt(content: bytes) -> tuple[str, list[Candidate]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = canonical.split("\n")
    raw: list[_Raw] = []
    offset = 0
    for index, line in enumerate(lines):
        before_blank = index == 0 or not lines[index - 1].strip()
        after_blank = index == len(lines) - 1 or not lines[index + 1].strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        found = _classify_line(line.strip(), before_blank, after_blank, next_line)
        if found is not None:
            raw.append(_Raw(found[0], found[1], offset + len(line) - len(line.lstrip())))
        offset += len(line) + 1
    return canonical, _finalize(raw, canonical)


def _classify_line(
    line: str, before_blank: bool, after_blank: bool, next_line: str
) -> tuple[CandidateKind, str] | None:
    """Headings are short and set apart by a blank line: a line glued to prose is prose."""
    if not line or len(line) > _MAX_HEADING_LINE:
        return None
    if LICENSE_MARKER.match(line):
        return "license_marker", line
    if not before_blank:
        return None
    if _SECTION_KEYWORD.match(line):
        return "section_keyword", line
    if _SECTION_HEADER.match(line):
        return "section_header", _with_subtitle(line, next_line)
    if _NUMERAL_LINE.match(line):
        return "numeral_header", _with_subtitle(line, next_line)
    letters = [ch for ch in line if ch.isalpha()]
    if (
        after_blank
        and len(letters) >= 3
        and line.isupper()
        and not line.endswith(("!", "?", '"', "”", "'"))
    ):
        return "caps_line", line
    return None


def _with_subtitle(heading: str, next_line: str) -> str:
    """'CHAPTER I' + a title-like line directly under it -> 'CHAPTER I: The Lamp'."""
    looks_like_title = (
        0 < len(next_line) <= _MAX_SUBTITLE_LINE
        and not next_line.endswith((".", ",", ";", ":", "!", "?", '"', "”"))
        and not _SECTION_HEADER.match(next_line)
        and not _NUMERAL_LINE.match(next_line)
    )
    return merge_titles(heading, next_line) if looks_like_title else heading
