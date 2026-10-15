"""A2b and A2c: the structure map (heuristic and LLM) and the cut with its validation."""

from functools import partial

import pytest
import samples
from fakes import FakeLLM, classify_like_an_llm

from pov_retell.candidates import find_candidates
from pov_retell.cut import StructureMapError, cut_units, validate_units
from pov_retell.heuristic_map import heuristic_map
from pov_retell.llm_map import llm_map
from pov_retell.load import Source, make_book
from pov_retell.models import BookFormat, Candidate, MapItem, MapResponse, Unit, UnitKind


def cut_sample(fmt: BookFormat, content: bytes) -> tuple[str, list[Candidate], list[Unit]]:
    text, candidates = find_candidates(content, fmt)
    units, _ = cut_units(text, candidates, heuristic_map(candidates, text))
    return text, candidates, units


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_heuristic_map_cuts_parts_and_chapters(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    text, _, units = cut_sample(fmt, sample_bytes[fmt])
    assert [(u.kind, u.parent_id) for u in units] == samples.EXPECTED_UNITS
    assert [u.id for u in units] == ["u01", "u02", "u03", "u04", "u05"]
    assert units[1].title.startswith("CHAPTER I") and "The Lamp" in units[1].title
    # front matter and the licence are outside every unit
    covered = text[units[0].char_start : units[-1].char_end]
    assert "Project Gutenberg" not in covered and "CONTENTS" not in covered
    assert "PART ONE" in covered


@pytest.mark.parametrize("fmt", ["html", "txt"])
def test_the_llm_map_gives_the_same_cut_as_the_heuristic_map(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    content = sample_bytes[fmt]
    text, candidates, expected = cut_sample(fmt, content)
    llm = FakeLLM(lambda prompt: classify_like_an_llm(candidates))
    book = make_book(Source(content, f"x.{fmt}", "x"))

    items = llm_map(book, candidates, llm)
    units, _ = cut_units(text, candidates, items)

    assert [(u.kind, u.char_start, u.char_end) for u in units] == [
        (u.kind, u.char_start, u.char_end) for u in expected
    ]
    assert len(llm.prompts) == 1


def test_the_llm_sees_candidates_with_short_previews_not_the_book(
    sample_bytes: dict[BookFormat, bytes],
) -> None:
    _, candidates = find_candidates(sample_bytes["txt"], "txt")
    llm = FakeLLM(lambda prompt: classify_like_an_llm(candidates))
    llm_map(make_book(Source(sample_bytes["txt"], "x.txt", "x")), candidates, llm)
    assert all(c.cand_id in llm.prompts[0] for c in candidates)
    assert samples.STORY_PARAGRAPHS[-1] not in llm.prompts[0]  # only the first words of each


def test_llm_answers_that_skip_repeat_or_invent_ids_are_rejected(
    sample_bytes: dict[BookFormat, bytes],
) -> None:
    _, candidates = find_candidates(sample_bytes["txt"], "txt")
    good = classify_like_an_llm(candidates)["items"]
    book = make_book(Source(sample_bytes["txt"], "x.txt", "x"))
    broken = {
        "missing": good[1:],
        "repeated": [*good, good[0]],
        "unknown": [*good, {**good[0], "cand_id": "cand_999"}],
    }
    for problem, items in broken.items():
        fake = FakeLLM(partial(lambda _prompt, answer: {"items": answer}, answer=items))
        with pytest.raises(ValueError, match=f"{problem} ids"):
            llm_map(book, candidates, fake)


def test_many_candidates_are_sent_in_batches(sample_bytes: dict[BookFormat, bytes]) -> None:
    _, candidates = find_candidates(sample_bytes["txt"], "txt")
    many = [
        c.model_copy(update={"cand_id": f"cand_{i:03d}"}) for i, c in enumerate(candidates * 20)
    ]

    def answer(prompt: str) -> dict[str, object]:
        ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("- cand_")]
        return {
            "items": [
                {"cand_id": i, "role": "front", "unit_kind": "front", "title": i} for i in ids
            ]
        }

    llm = FakeLLM(answer)
    items = llm_map(make_book(Source(b"x", "x.txt", "x")), many, llm)
    assert len(llm.prompts) == 3  # 80 + 80 + the rest
    assert [i.cand_id for i in items] == [c.cand_id for c in many]


# ----------------------------------------------------------------- validation


def unit(order: int, start: int, end: int, kind: UnitKind = "chapter") -> Unit:
    return Unit(
        id=f"u{order:02d}",
        order=order,
        kind=kind,
        title=f"T{order}",
        char_start=start,
        char_end=end,
    )


TEXT = "x" * 100


def test_a_valid_cut_has_no_errors() -> None:
    assert validate_units([unit(1, 10, 50), unit(2, 50, 90)], TEXT, 10, 90) == []


def test_validation_catches_each_kind_of_bad_cut() -> None:
    problems = {
        "gap": validate_units([unit(1, 10, 40), unit(2, 50, 90)], TEXT, 10, 90),
        "overlap": validate_units([unit(1, 10, 60), unit(2, 50, 90)], TEXT, 10, 90),
        "invalid range": validate_units([unit(1, 10, 10)], TEXT, 10, 10),
        "empty": validate_units([unit(1, 10, 50)], " " * 100, 10, 50),
        "order": validate_units([unit(2, 10, 50)], TEXT, 10, 50),
        "body ends at": validate_units([unit(1, 10, 50)], TEXT, 10, 90),
        "no chapters": validate_units(
            [unit(1, 10, 50, "part"), unit(2, 50, 90, "part")], TEXT, 10, 90
        ),
    }
    for expected, errors in problems.items():
        assert any(expected in e for e in errors), (expected, errors)


def test_a_map_without_body_units_cannot_be_cut() -> None:
    cand = Candidate(cand_id="cand_001", kind="heading", text="Hello", char_pos=0)
    item = MapItem(cand_id="cand_001", role="front", unit_kind="front", title="Hello")
    with pytest.raises(StructureMapError, match="no body units"):
        cut_units("Hello world", [cand], [item])


TWO_HEADINGS = "PART ONE\n\nCHAPTER I\n\nStory text here.\n"
HEADING_CANDIDATES = [
    Candidate(cand_id="cand_001", kind="heading", text="PART ONE", char_pos=0),
    Candidate(cand_id="cand_002", kind="heading", text="CHAPTER I", char_pos=10),
]


def part(cand_id: str) -> MapItem:
    return MapItem(cand_id=cand_id, role="part_heading", unit_kind="part", title="PART ONE")


def chapter(cand_id: str, parent: str | None = None) -> MapItem:
    return MapItem(
        cand_id=cand_id,
        role="body_unit",
        unit_kind="chapter",
        title="CHAPTER I",
        parent_cand_id=parent,
    )


def test_a_chapter_that_forgets_its_part_is_kept_but_warned() -> None:
    items = [part("cand_001"), chapter("cand_002")]
    units, warnings = cut_units(TWO_HEADINGS, HEADING_CANDIDATES, items)
    assert [(u.kind, u.parent_id) for u in units] == [("part", None), ("chapter", None)]
    assert "without parent" in warnings[0]


def test_a_part_without_chapters_is_rejected() -> None:
    """A table of contents lists "PART ONE" too: a part that no chapter follows is not a part."""
    items = [chapter("cand_001"), part("cand_002")]
    with pytest.raises(StructureMapError, match="no chapters"):
        cut_units(TWO_HEADINGS, HEADING_CANDIDATES, items)


def test_map_response_schema_rejects_unknown_roles() -> None:
    with pytest.raises(ValueError):
        MapResponse.model_validate(
            {"items": [{"cand_id": "c", "role": "villain", "unit_kind": "front", "title": "x"}]}
        )
