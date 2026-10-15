"""Step A1: get the file (path or URL), detect its format, fingerprint it, read title and author.

The format is decided by the CONTENT (EPUB is a ZIP with container.xml; HTML has an <html> tag),
because file names lie: a URL often ends in `/pg1342` with no extension at all.
"""

import hashlib
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from pov_retell.models import Book, BookFormat

MAX_BYTES = 100 * 1024 * 1024
HEAD_BYTES = 256 * 1024  # Gutenberg HTML carries a long inline <style> before its <meta> tags


@dataclass(frozen=True)
class Source:
    content: bytes
    filename: str | None
    origin: str  # absolute path or URL


def load_source(location: str, client: httpx.Client | None = None) -> Source:
    """Read a local file, or download an http(s) URL (pass `client` to test without network)."""
    if not location.startswith(("http://", "https://")):
        path = Path(location).expanduser()
        return Source(path.read_bytes(), path.name, str(path.resolve()))

    http = client or httpx.Client(follow_redirects=True, timeout=60.0)
    try:
        response = http.get(location)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(f"could not download {location}: {exc}") from exc
    finally:
        if client is None:
            http.close()
    if len(response.content) > MAX_BYTES:
        raise ValueError(f"{location} is larger than {MAX_BYTES} bytes")
    name = Path(unquote(urlparse(str(response.url)).path)).name
    return Source(response.content, name or None, location)


def sha256_of(content: bytes) -> str:
    """The book's fingerprint. If the file changes (another edition), the hash changes."""
    return hashlib.sha256(content).hexdigest()


def detect_format(content: bytes, filename: str | None = None) -> BookFormat:
    """Return "epub", "html" or "txt"; the extension only breaks ties."""
    if content.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "META-INF/container.xml" in archive.namelist():
                    return "epub"
        except zipfile.BadZipFile:
            pass
        raise ValueError("unsupported format: a ZIP file that is not an EPUB")
    sample = content[:4096].lower()
    if b"\x00" in sample:
        raise ValueError("unsupported format: binary content (use html, epub or txt)")
    if b"<!doctype html" in sample or b"<html" in sample:
        return "html"
    return "html" if filename and filename.lower().endswith((".html", ".htm", ".xhtml")) else "txt"


def slugify(text: str) -> str:
    """'Pride and Prejudice' -> 'pride-and-prejudice' (used as the book id and directory name)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "book"


def make_book(source: Source, book_id: str | None = None) -> Book:
    """A1 in one call: format + hash + best-effort title and author."""
    fmt = detect_format(source.content, source.filename)
    title, author = _read_metadata(source.content, fmt)
    if not title:
        stem = Path(source.filename).stem if source.filename else ""
        title = stem.replace("_", " ").replace("-", " ").title() or "Untitled Book"
    return Book(
        id=book_id or slugify(title),
        title=title,
        author=author or "Unknown Author",
        format=fmt,
        sha256=sha256_of(source.content),
        source=source.origin,
    )


def _read_metadata(content: bytes, fmt: BookFormat) -> tuple[str, str]:
    if fmt == "epub":
        return _epub_metadata(content)
    if fmt == "html":
        return _html_metadata(content)
    return _txt_metadata(content)


def _clean_title(raw: str) -> str:
    """Drop Gutenberg's decoration: 'Treasure Island | Project Gutenberg' -> 'Treasure Island'."""
    title = " ".join(raw.split())
    title = re.sub(r"\s*[|\-–—]\s*Project Gutenberg\s*$", "", title, flags=re.I)
    return re.sub(r"^(?:The\s+)?Project Gutenberg(?:'s)?\s+e?books?\s+of\s+", "", title, flags=re.I)


def _split_title_author(raw: str) -> tuple[str, str]:
    """'The Lion, the Witch and the Wardrobe, by C. S. Lewis' -> (title, 'C. S. Lewis')."""
    title = _clean_title(raw)
    head, found, tail = title.partition(", by ")
    return (head.strip(), tail.strip()) if found and head and tail else (title, "")


def _natural_name(name: str) -> str:
    """'Austen, Jane, 1775-1817' -> 'Jane Austen'."""
    name = re.sub(r",?\s*\(?\d{3,4}\??\s*-\s*(?:\d{3,4}\??)?\)?\s*$", "", name).strip()
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and all(parts):
        return f"{parts[1]} {parts[0]}"
    return " ".join(name.split())


def _epub_metadata(content: bytes) -> tuple[str, str]:
    from ebooklib import epub

    book = epub.read_epub(io.BytesIO(content), options={"ignore_ncx": True})
    titles = book.get_metadata("DC", "title")
    creators = book.get_metadata("DC", "creator")
    return (
        str(titles[0][0]).strip() if titles else "",
        _natural_name(str(creators[0][0])) if creators else "",
    )


def _html_metadata(content: bytes) -> tuple[str, str]:
    soup = BeautifulSoup(content[:HEAD_BYTES], "html.parser")
    meta_title = soup.find("meta", attrs={"name": re.compile(r"^dc\.title$", re.I)})
    meta_author = soup.find("meta", attrs={"name": re.compile(r"^dc\.creator$", re.I)})
    title = _clean_title(str(meta_title.get("content", ""))) if meta_title else ""
    author = _natural_name(str(meta_author.get("content", ""))) if meta_author else ""
    if not title and soup.title:
        title, title_author = _split_title_author(soup.title.get_text())
        author = author or title_author
    return title, author


def _txt_metadata(content: bytes) -> tuple[str, str]:
    head = content[:32768].decode("utf-8", errors="ignore").lstrip("\ufeff")
    title_line = re.search(r"^Title:\s*(.+)$", head, re.M | re.I)
    author_line = re.search(r"^Author:\s*(.+)$", head, re.M | re.I)
    title = _clean_title(title_line.group(1)) if title_line else ""
    author = _natural_name(author_line.group(1).strip()) if author_line else ""
    if not title:  # older files only have the banner "The Project Gutenberg EBook of X, by Y"
        banner = re.search(
            r"^(?:The\s+)?Project Gutenberg(?:'s)?\s+e?books?\s+of\s+(.+)$", head, re.M | re.I
        )
        if banner:
            title, banner_author = _split_title_author(banner.group(1))
            author = author or banner_author
    return title, author
