"""A2a: the canonical text and the structure candidates, for each format."""

import pytest
import samples

from pov_retell.book.candidates import find_candidates
from pov_retell.book.models import BookFormat


def texts(content: bytes, fmt: BookFormat) -> list[str]:
    return [c.text for c in find_candidates(content, fmt)[1]]


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_every_heading_of_the_story_is_a_candidate(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    found = " | ".join(texts(sample_bytes[fmt], fmt))
    for name in ("PART ONE", "PART TWO", "CHAPTER I", "CHAPTER II", "CHAPTER III"):
        assert name in found


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_candidates_are_in_reading_order_with_one_per_position(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    text, candidates = find_candidates(sample_bytes[fmt], fmt)
    positions = [c.char_pos for c in candidates]
    assert positions == sorted(set(positions))
    assert [c.cand_id for c in candidates] == [
        f"cand_{i:03d}" for i in range(1, len(candidates) + 1)
    ]
    for cand in candidates:  # the preview is the text found at that position
        assert text[cand.char_pos :].split()[0] == cand.preview.split()[0]


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_the_canonical_text_holds_the_story_paragraphs(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    text = " ".join(find_candidates(sample_bytes[fmt], fmt)[0].split())
    assert all(" ".join(p.split()) in text for p in samples.STORY_PARAGRAPHS)


def test_html_drop_cap_letters_are_kept() -> None:
    html = b'<html><body><h2>CHAPTER I</h2><p><img alt="O" src="x.png">ne evening</p></body></html>'
    assert "One evening" in find_candidates(html, "html")[0]


def test_html_toc_links_and_structural_anchors_are_candidates() -> None:
    html = (
        b'<html><body><p><a href="#c1">The First Day</a></p>'
        b'<p><a id="c1"></a>It began in May.</p>'
        b'<p><a name="chap2"></a>The second day.</p></body></html>'
    )
    found = {c.kind: c.text for c in find_candidates(html, "html")[1]}
    assert found["toc_link"] == "The First Day"  # a link target, titled by the link text
    assert found["anchor"] == "chap2"  # an anchor whose id looks structural


def test_html_footnote_links_are_not_toc_entries() -> None:
    html = (
        b'<html><body><p>Text<a href="#n1">[1]</a></p><p><a id="n1"></a>A note.</p></body></html>'
    )
    assert find_candidates(html, "html")[1] == []


def test_epub_document_without_a_heading_is_titled_by_the_navigation() -> None:
    import io

    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("x")
    book.set_title("T")
    doc = epub.EpubHtml(title="The Night Watch", file_name="a.xhtml")
    doc.content = "<html><body><p>No heading here at all.</p></body></html>"
    book.add_item(doc)
    book.toc = (epub.Link("a.xhtml", "The Night Watch", "a"),)
    book.add_item(epub.EpubNcx())
    book.spine = [doc]
    buffer = io.BytesIO()
    epub.write_epub(buffer, book, {})

    candidates = find_candidates(buffer.getvalue(), "epub")[1]
    assert [(c.kind, c.text) for c in candidates] == [("spine_item", "The Night Watch")]


def test_txt_headings_must_be_set_apart_from_prose() -> None:
    text = (
        b"CHAPTER I\nThe Lamp\n\nShe said CHAPTER II is next.\nTHE\n\nMORE PROSE HERE.\n"
        b"\nXIV\n\nThen came CHAPTER 3 in the middle of a line.\n"
    )
    found = [(c.kind, c.text) for c in find_candidates(text, "txt")[1]]
    assert ("section_header", "CHAPTER I: The Lamp") in found  # the subtitle joins its heading
    assert ("numeral_header", "XIV") in found
    assert not any("CHAPTER II" in t or "CHAPTER 3" in t for _, t in found)
