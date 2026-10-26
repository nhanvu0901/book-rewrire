import re
from pathlib import Path

from pov_retell.book.models import NARRATIVE_KINDS
from pov_retell.book.output import load_extraction
from pov_retell.book.text import iter_blocks
from pov_retell.ingest.model import Chapter

_PARAGRAPH = re.compile(r"\[(u\d+_p\d+)(?: [^\]]*)?\]\s+(.+)")


def validate_directory_name(value: str) -> None:
    if not value or value in {".", ".."} or any(c in value for c in "/\\\x00"):
        raise ValueError(f"Invalid book or run ID: {value!r}")


def load_chapters(extracted_dir: Path, book_id: str) -> tuple[str, list[Chapter]]:
    validate_directory_name(book_id)
    extracted = load_extraction(extracted_dir, book_id)
    if extracted.book.id != book_id:
        raise ValueError("The extraction's book ID does not match the requested book")
    units = sorted((u for u in extracted.units if u.kind in NARRATIVE_KINDS), key=lambda u: u.order)
    if not units:
        raise ValueError("The extraction has no narrative chapters")
    paths: dict[int, Path] = {}
    for path in (extracted_dir / book_id / "units").glob("*.txt"):
        prefix = path.name.split("_", 1)[0]
        if not prefix.isdecimal() or int(prefix) in paths:
            raise ValueError(f"Invalid or duplicate chapter filename: {path.name}")
        paths[int(prefix)] = path
    if set(paths) != {unit.order for unit in units}:
        raise ValueError("Chapter files do not match the extraction's narrative units")

    chapters = []
    for unit in units:
        text = paths[unit.order].read_text(encoding="utf-8")
        expected = {
            p.id: p.text
            for p in sorted(extracted.paragraphs, key=lambda p: p.order)
            if p.unit_id == unit.id
        }
        blocks = list(iter_blocks(text))
        actual: dict[str, str] = {}
        for block in blocks[1:]:
            match = _PARAGRAPH.fullmatch(block.text)
            if match is None or match[1] in actual:
                raise ValueError(f"Invalid paragraph label in chapter {unit.id}")
            actual[match[1]] = match[2]
        if not expected or list(actual) != list(expected) or actual != expected:
            raise ValueError(f"Chapter {unit.id} text or paragraph IDs differ from book.json")
        chapters.append(Chapter(unit.id, text, actual))
    return extracted.book.title, chapters
