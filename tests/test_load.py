"""A1: format detection, fingerprint, metadata, loading from a path or a URL."""

import httpx
import pytest
import samples

from pov_retell.book.load import (
    Source,
    detect_format,
    load_source,
    make_book,
    sha256_of,
    slugify,
)
from pov_retell.book.models import BookFormat


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_format_is_detected_from_the_content(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    assert detect_format(sample_bytes[fmt]) == fmt


def test_the_content_wins_over_the_file_name() -> None:
    assert detect_format(b"<html><body>hi</body></html>", "book.txt") == "html"
    assert detect_format(b"just words", "book.html") == "html"  # extension only breaks ties
    assert detect_format(b"just words", "pg1342") == "txt"


def test_unsupported_content_is_refused() -> None:
    with pytest.raises(ValueError, match="binary"):
        detect_format(b"%PDF\x00\x01 binary")
    with pytest.raises(ValueError, match="not an EPUB"):
        detect_format(b"PK\x03\x04" + b"\x00" * 30)  # not even a valid zip: still refused


def test_sha256_changes_when_the_file_changes() -> None:
    assert sha256_of(b"abc") == sha256_of(b"abc")
    assert sha256_of(b"abc") != sha256_of(b"abd")
    assert len(sha256_of(b"abc")) == 64


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_title_author_and_id_are_read_from_each_format(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    book = make_book(Source(sample_bytes[fmt], f"x.{fmt}", "/tmp/x"))
    assert (book.title, book.author, book.id) == (
        samples.TITLE,
        samples.AUTHOR,
        "the-lantern-keeper",
    )
    assert book.format == fmt
    assert book.sha256 == sha256_of(sample_bytes[fmt])


def test_title_and_author_are_cleaned() -> None:
    page = b"<html><head><title>Emma, by Jane Austen | Project Gutenberg</title></head></html>"
    assert make_book(Source(page, None, "x")).title == "Emma"
    assert make_book(Source(page, None, "x")).author == "Jane Austen"
    txt = b"Title: Emma\nAuthor: Austen, Jane, 1775-1817\n"
    assert make_book(Source(txt, None, "x")).author == "Jane Austen"


def test_a_book_without_metadata_falls_back_to_the_file_name() -> None:
    book = make_book(Source(b"hello", "my_odd-book.txt", "x"))
    assert (book.title, book.author) == ("My Odd Book", "Unknown Author")


def test_slugify() -> None:
    assert slugify("Pride and Prejudice") == "pride-and-prejudice"
    assert slugify("Café: the Book!") == "cafe-the-book"
    assert slugify("???") == "book"


def test_load_from_a_local_file(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "story.txt"  # type: ignore[operator]
    path.write_bytes(b"hello")
    source = load_source(str(path))
    assert (source.content, source.filename) == (b"hello", "story.txt")
    assert source.origin == str(path.resolve())


def test_load_from_a_url_without_touching_the_network() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.org/files/story%20one.txt"
        return httpx.Response(200, content=b"downloaded")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = load_source("https://example.org/files/story%20one.txt", client=client)
    assert (source.content, source.filename) == (b"downloaded", "story one.txt")
    assert source.origin == "https://example.org/files/story%20one.txt"


def test_a_failed_download_is_a_clear_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(ValueError, match="could not download"):
        load_source("https://example.org/missing", client=client)
