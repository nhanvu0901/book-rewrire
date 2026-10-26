"""One INVENTED story rendered three ways: Gutenberg-style HTML, EPUB and TXT.

The text is made up for the tests (no real book is committed to git). Rendering the same story
in every format lets the tests assert that html, epub and txt all end with the same units and
paragraphs, which is the whole point of the "canonical text".
"""

import io
from dataclasses import dataclass
from html import escape

TITLE = "The Lantern Keeper"
AUTHOR = "Jane Doe"
LICENSE_HEAD = f"The Project Gutenberg eBook of {TITLE}"
LICENSE_TAIL = "End of the Project Gutenberg EBook. Section 1. General Terms of Use."


@dataclass(frozen=True)
class Chapter:
    numeral: str
    title: str
    paragraphs: list[str]


# (part name, part title, chapters): two parts, three chapters
STORY: list[tuple[str, str, list[Chapter]]] = [
    (
        "PART ONE",
        "The Cliff",
        [
            Chapter(
                "I",
                "The Lamp",
                [
                    "One evening the keeper climbed the long stair to light the great lamp, as "
                    "his father had done before him and his grandfather before that.",
                    '"The sea is quiet tonight," said the boy who followed him up the steps.',
                    "The keeper made no answer, for he was watching a small boat far below.",
                ],
            ),
            Chapter(
                "II",
                "The Stranger",
                [
                    "At dawn a stranger knocked on the heavy door of the lighthouse and asked "
                    "for bread and a place by the fire.",
                    '"Who sent you?" asked the keeper. "Nobody," said the stranger.',
                ],
            ),
        ],
    ),
    (
        "PART TWO",
        "The Storm",
        [
            Chapter(
                "III",
                "The Light Goes Out",
                [
                    "That night the wind rose and the waves climbed the rocks, and the great "
                    "lamp flickered and died while the boy slept in his small bed.",
                    "The stranger took the lantern and went out into the dark alone.",
                ],
            ),
        ],
    ),
]

CHAPTERS = [c for _, _, chapters in STORY for c in chapters]
STORY_PARAGRAPHS = [p for c in CHAPTERS for p in c.paragraphs]
# What the units should look like after extraction: (kind, parent unit id)
EXPECTED_UNITS = [
    ("part", None),
    ("chapter", "u01"),
    ("chapter", "u01"),
    ("part", None),
    ("chapter", "u04"),
]


def render_html() -> bytes:
    """Boilerplate, a linked table of contents, part and chapter headings, a drop cap."""
    toc = "".join(
        f'<li><a href="#part{pi}">{name}</a></li>'
        + "".join(
            f'<li><a href="#ch{c.numeral}">Chapter {c.numeral}. {escape(c.title)}</a></li>'
            for c in chapters
        )
        for pi, (name, _, chapters) in enumerate(STORY, start=1)
    )
    body = [
        f"<section><h2>{LICENSE_HEAD}</h2><p>This ebook is for anyone anywhere.</p></section>",
        f"<h1>{TITLE}</h1><p>by {AUTHOR}</p>",
        f"<h2>CONTENTS</h2><ul>{toc}</ul>",
    ]
    for pi, (name, title, chapters) in enumerate(STORY, start=1):
        body.append(f'<h2 id="part{pi}">{name}</h2><h3>{escape(title)}</h3>')
        for chapter in chapters:
            body.append(
                f'<h2><a id="ch{chapter.numeral}"></a>CHAPTER {chapter.numeral}.</h2>'
                f"<h3>{escape(chapter.title)}</h3>"
            )
            for i, para in enumerate(chapter.paragraphs):
                if i == 0:  # a Gutenberg drop cap: the first letter lives in an <img alt="X">
                    cap = f'<span class="cap"><img alt="{para[0]}" src="x.png"></span>'
                    body.append(f"<p>{cap}{escape(para[1:])}</p>")
                else:
                    body.append(f"<p>{escape(para)}</p>")
    body.append(
        f"<section><p>*** END OF THE PROJECT GUTENBERG EBOOK ***</p><p>{LICENSE_TAIL}</p></section>"
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{TITLE} | Project Gutenberg</title>"
        f'<meta name="dc.title" content="{TITLE}">'
        '<meta name="dc.creator" content="Doe, Jane"></head><body>'
        + "\n".join(body)
        + "</body></html>"
    ).encode()


def render_txt() -> bytes:
    """Hard-wrapped lines, START/END markers, a contents list."""
    lines = [LICENSE_HEAD, "", f"Title: {TITLE}", f"Author: {AUTHOR}", ""]
    lines += [f"*** START OF THE PROJECT GUTENBERG EBOOK {TITLE.upper()} ***", "", "CONTENTS", ""]
    for name, _, chapters in STORY:
        lines.append(name)
        lines += [f"Chapter {c.numeral}. {c.title}" for c in chapters]
    lines.append("")
    for name, title, chapters in STORY:
        lines += [name, "", title.upper(), ""]
        for chapter in chapters:
            lines += [f"CHAPTER {chapter.numeral}.", chapter.title, ""]
            for para in chapter.paragraphs:
                lines += [_hard_wrap(para), ""]
    lines += [f"*** END OF THE PROJECT GUTENBERG EBOOK {TITLE.upper()} ***", "", LICENSE_TAIL, ""]
    return "\n".join(lines).encode()


def render_epub() -> bytes:
    """One spine document per part page and per chapter, plus a navigation list."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("urn:test:lantern-keeper")
    book.set_title(TITLE)
    book.set_language("en")
    book.add_author(AUTHOR)
    docs: list[epub.EpubHtml] = []

    def add(file_name: str, title: str, html: str) -> None:
        doc = epub.EpubHtml(title=title, file_name=file_name, lang="en")
        doc.content = f"<html><body>{html}</body></html>"
        book.add_item(doc)
        docs.append(doc)

    add("license.xhtml", "Project Gutenberg", f"<h1>{LICENSE_HEAD}</h1><p>For anyone anywhere.</p>")
    for pi, (name, title, chapters) in enumerate(STORY, start=1):
        add(f"part{pi}.xhtml", name, f"<h1>{name}</h1><h2>{escape(title)}</h2>")
        for chapter in chapters:
            paras = "".join(f"<p>{escape(p)}</p>" for p in chapter.paragraphs)
            add(
                f"ch{chapter.numeral}.xhtml",
                f"Chapter {chapter.numeral}. {chapter.title}",
                f"<h1>CHAPTER {chapter.numeral}.</h1><h2>{escape(chapter.title)}</h2>{paras}",
            )
    add(
        "end.xhtml",
        "Licence",
        f"<h1>Licence</h1><p>*** END OF THE PROJECT GUTENBERG EBOOK ***</p><p>{LICENSE_TAIL}</p>",
    )
    book.toc = tuple(epub.Link(d.file_name, d.title, d.file_name) for d in docs)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *docs]
    buffer = io.BytesIO()
    epub.write_epub(buffer, book, {})
    return buffer.getvalue()


def _hard_wrap(text: str, width: int = 60) -> str:
    """Wrap like a Gutenberg .txt: one paragraph spread over several lines."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return "\n".join([*lines, current])
