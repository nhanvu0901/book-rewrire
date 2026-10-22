"""Save and load the extraction as plain files a human can open.

<BOOK_CLONE_DATA_DIR>/extracted/<book_id>/
    book.json            metadata + units + paragraphs (the file the next step ingests)
    canonical.txt        the cleaned text; every char_start/char_end points into it
    units/NN_title.txt   one readable file per chapter, NN = the unit's order
"""

import shutil
from pathlib import Path

from pov_retell.book.load import slugify
from pov_retell.book.models import SCHEMA_VERSION, ExtractedBook


class BookIdConflictError(ValueError):
    """The directory already holds an extraction of a DIFFERENT file."""


def save_extraction(extracted: ExtractedBook, extracted_dir: Path) -> Path:
    """Write the files; returns the book's directory.

    Re-extracting the same file replaces the old files. A different file under the same book id
    (say the epub of a book whose html is already there) is refused: pass another `--id`.
    """
    book_dir = extracted_dir / extracted.book.id
    existing = book_dir / "book.json"
    if existing.exists():
        old = load_extraction(extracted_dir, extracted.book.id).book
        if old.sha256 != extracted.book.sha256:
            raise BookIdConflictError(
                f"{book_dir} already holds a different file ({old.format}, sha256 "
                f"{old.sha256[:8]}); this one is {extracted.book.format}. Use --id to name it"
            )
    units_dir = book_dir / "units"
    if units_dir.exists():
        shutil.rmtree(units_dir)  # no stale chapter files from an earlier, different cut
    units_dir.mkdir(parents=True)

    (book_dir / "book.json").write_text(extracted.model_dump_json(indent=2), encoding="utf-8")
    (book_dir / "canonical.txt").write_text(extracted.canonical_text, encoding="utf-8")

    for unit in extracted.units:
        paragraphs = [p for p in extracted.paragraphs if p.unit_id == unit.id]
        if not paragraphs:  # a part holds only its heading
            continue
        blocks = [f"{unit.title}\n{'=' * len(unit.title)}"]
        for p in paragraphs:
            tag = " ".join([p.id, *(f"!{flag}" for flag in p.flags)])
            blocks.append(f"[{tag}] {p.text}")
        name = f"{unit.order:02d}_{slugify(unit.title)[:50]}.txt"
        (units_dir / name).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return book_dir


def load_extraction(extracted_dir: Path, book_id: str) -> ExtractedBook:
    """Read book.json back (without canonical_text: read canonical.txt if you need it)."""
    path = extracted_dir / book_id / "book.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist: run `pov extract` first")
    extracted = ExtractedBook.model_validate_json(path.read_text(encoding="utf-8"))
    if extracted.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"{path} has schema_version {extracted.schema_version}, expected {SCHEMA_VERSION}"
        )
    return extracted
