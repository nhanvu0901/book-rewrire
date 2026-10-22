"""Turn an HTML/XHTML document into an ordered list of text blocks.

HTML and EPUB both go through here, so every format ends up with the same kind of canonical
text: one block per heading or paragraph-like element, whitespace collapsed, scripts and styles
dropped, and text inside `div`/`li`/`td` kept (nothing silently lost).
"""

import re
import warnings
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Comment, Tag, XMLParsedAsHTMLWarning
from bs4.element import NavigableString

HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4"})
_SKIPPED_TAGS = frozenset({"script", "style", "noscript", "head", "title", "meta", "link", "svg"})
_BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "body", "caption", "center", "dd", "details",
        "dir", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h5", "h6",
        "header", "hr", "html", "li", "main", "menu", "nav", "ol", "p", "pre", "section", "table",
        "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }
)  # fmt: skip


@dataclass
class HtmlBlock:
    text: str
    is_heading: bool
    ids: list[str] = field(default_factory=list)  # anchor ids that point at the start of it


@dataclass
class Link:
    """An in-book link such as <a href="#ch1">Chapter I</a>: likely a table-of-contents entry."""

    href: str
    text: str


def html_to_blocks(content: bytes) -> tuple[list[HtmlBlock], list[Link]]:
    """Walk the document body; return its blocks and every internal link found."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)  # XHTML from EPUBs is fine here
        soup = BeautifulSoup(content, "lxml")
    walker = _Walker()
    walker.walk(soup.body or soup)
    walker.flush()
    return walker.blocks, walker.links


class _Walker:
    def __init__(self) -> None:
        self.blocks: list[HtmlBlock] = []
        self.links: list[Link] = []
        self._buffer: list[str] = []
        self._pending_ids: list[str] = []

    def flush(self, *, heading: bool = False) -> None:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        if text:  # ids stay pending when the block is empty: they bind to the next real block
            self.blocks.append(HtmlBlock(text, heading, self._pending_ids))
            self._pending_ids = []

    def walk(self, parent: Tag) -> None:
        for child in parent.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                self._buffer.append(str(child))
            elif isinstance(child, Tag):
                self._visit(child)

    def _visit(self, tag: Tag) -> None:
        name = (tag.name or "").lower()
        if name in _SKIPPED_TAGS:
            return
        if name in HEADING_TAGS or name in _BLOCK_TAGS:
            self.flush()
            self._register_ids(tag)
            self.walk(tag)
            self.flush(heading=name in HEADING_TAGS)
        elif name == "br":
            self._buffer.append(" ")
        elif name == "img":
            alt = str(tag.get("alt") or "").strip()
            if len(alt) == 1 and alt.isalpha():  # a drop cap: the first letter lives in the alt
                self._buffer.append(alt)
        else:  # an inline element: its text joins the surrounding block
            self._register_ids(tag)
            if name == "a":
                self._record_link(tag)
            self.walk(tag)

    def _register_ids(self, tag: Tag) -> None:
        for attr in ("id", "name") if tag.name == "a" else ("id",):
            value = tag.get(attr)
            if isinstance(value, str) and value.strip():
                self._pending_ids.append(value.strip())

    def _record_link(self, tag: Tag) -> None:
        href = tag.get("href")
        if not isinstance(href, str) or not href.strip():
            return
        if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
            return  # http:, mailto:, ... point outside the book
        text = " ".join(tag.get_text().split())
        if text:
            self.links.append(Link(href.strip(), text))
