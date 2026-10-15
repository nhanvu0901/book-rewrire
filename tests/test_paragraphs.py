"""A3: paragraphs with stable ids and anomaly flags."""

import pytest
import samples

from pov_retell.candidates import find_candidates
from pov_retell.cut import cut_units
from pov_retell.heuristic_map import heuristic_map
from pov_retell.models import BookFormat
from pov_retell.paragraphs import paragraph_flags, split_paragraphs


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_paragraphs_have_stable_ids_and_the_story_text_only(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    text, candidates = find_candidates(sample_bytes[fmt], fmt)
    units, _ = cut_units(text, candidates, heuristic_map(candidates, text))
    paragraphs = split_paragraphs(units, text, candidates)

    # every format gives the same paragraphs; the headings and subtitles are not among them
    assert [p.text for p in paragraphs] == [" ".join(p.split()) for p in samples.STORY_PARAGRAPHS]
    assert [p.id for p in paragraphs] == [
        "u02_p001", "u02_p002", "u02_p003", "u03_p001", "u03_p002", "u05_p001", "u05_p002",
    ]  # fmt: skip
    assert all(p.flags == [] for p in paragraphs)


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_paragraph_offsets_point_into_the_canonical_text(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    text, candidates = find_candidates(sample_bytes[fmt], fmt)
    units, _ = cut_units(text, candidates, heuristic_map(candidates, text))
    by_id = {u.id: u for u in units}
    for p in split_paragraphs(units, text, candidates):
        assert " ".join(text[p.char_start : p.char_end].split()) == p.text
        assert by_id[p.unit_id].char_start <= p.char_start < p.char_end <= by_id[p.unit_id].char_end


def test_part_units_have_no_paragraphs(sample_bytes: dict[BookFormat, bytes]) -> None:
    text, candidates = find_candidates(sample_bytes["txt"], "txt")
    units, _ = cut_units(text, candidates, heuristic_map(candidates, text))
    owners = {p.unit_id for p in split_paragraphs(units, text, candidates)}
    assert owners == {u.id for u in units if u.kind == "chapter"}


def test_anomaly_flags() -> None:
    assert paragraph_flags("Dear Madam,") == []
    assert paragraph_flags("0033m") == ["too_short"]  # a page-number marker, as in a real epub
    assert paragraph_flags('"') == []  # a lone quotation mark is dialogue, not an anomaly
    assert paragraph_flags("word " * 600) == ["too_long"]  # a missed paragraph break
    assert "license_leak" in paragraph_flags("Please read the Project Gutenberg license.")
    glued = "CHAPTER IV The morning came grey and cold, and " + "the keeper rose slowly. " * 8
    assert paragraph_flags(glued) == ["suspicious_header"]
