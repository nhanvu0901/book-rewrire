"""OPT-IN: the three real books in BOOK_CLONE_DATA_DIR/books (never in git).

    POV_LOCAL_BOOKS=1 uv run pytest -m local_books      (or: make test-books)

Same code, heuristic map, no LLM, no book-specific rule. The expected counts are the ones PRINTED
in the books. Treasure Island has six PARTS; they are represented as 6 units of kind `part`
(heading only, no paragraphs) and each of the 34 chapters points at its part with `parent_id`.
The Lion, the Witch and the Wardrobe is still in copyright: it only ever lives on this machine.
"""

from collections import Counter

import pytest

from pov_retell.config import Settings
from pov_retell.cut import validate_units
from pov_retell.models import ExtractedBook
from pov_retell.pipeline import extract_book

pytestmark = pytest.mark.local_books

# file name -> units by kind
EXPECTED: dict[str, dict[str, int]] = {
    "lww.html": {"chapter": 17},
    "treasure_island.html": {"part": 6, "chapter": 34},
    "treasure_island.epub": {"part": 6, "chapter": 34},
    "treasure_island.txt": {"part": 6, "chapter": 34},
    "pride_and_prejudice.html": {"chapter": 61},
    "pride_and_prejudice.epub": {"chapter": 61},
    "pride_and_prejudice.txt": {"chapter": 61},
}


def extract_local(name: str) -> ExtractedBook:
    path = Settings(_env_file=None).books_dir / name  # type: ignore[call-arg]
    if not path.exists():
        pytest.skip(f"{path} is not on this machine")
    return extract_book(str(path))


@pytest.mark.parametrize("name", EXPECTED)
def test_unit_counts_match_the_printed_book(name: str) -> None:
    result = extract_local(name)
    assert dict(Counter(u.kind for u in result.units)) == EXPECTED[name]


@pytest.mark.parametrize("name", EXPECTED)
def test_units_and_paragraphs_are_consistent(name: str) -> None:
    result = extract_local(name)
    text, units = result.canonical_text, result.units

    # one contiguous partition of the story body, in order
    assert validate_units(units, text, units[0].char_start, units[-1].char_end) == []
    assert [u.order for u in units] == list(range(1, len(units) + 1))
    parts = {u.id for u in units if u.kind == "part"}
    assert all(u.parent_id in parts for u in units if u.parent_id)
    if parts:  # Treasure Island: every chapter belongs to one of the 6 parts
        assert all(u.parent_id in parts for u in units if u.kind == "chapter")

    # paragraphs: unique ids, inside their unit, text equals the source slice
    assert len({p.id for p in result.paragraphs}) == len(result.paragraphs)
    by_id = {u.id: u for u in units}
    for p in result.paragraphs:
        unit = by_id[p.unit_id]
        assert unit.char_start <= p.char_start < p.char_end <= unit.char_end
        assert " ".join(text[p.char_start : p.char_end].split()) == p.text

    # every chapter has story text, and none of it is the Gutenberg licence
    assert {u.id for u in units if u.kind == "chapter"} == {p.unit_id for p in result.paragraphs}
    assert not [p for p in result.paragraphs if "license_leak" in p.flags]
    assert result.warnings == []
