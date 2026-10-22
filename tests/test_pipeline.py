"""A1-A3 end to end, the files written, and the command line."""

import json
from pathlib import Path

import pytest
import samples
from fakes import sample_llm
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.book.load import Source
from pov_retell.book.models import SCHEMA_VERSION, BookFormat, ExtractedBook
from pov_retell.book.output import BookIdConflictError, load_extraction, save_extraction
from pov_retell.book.pipeline import extract_book

app = cli.app


def extract(fmt: BookFormat, content: bytes, book_id: str | None = None) -> ExtractedBook:
    return extract_book(
        Source(content, f"lantern.{fmt}", f"/tmp/lantern.{fmt}"),
        sample_llm(content, fmt),
        book_id=book_id,
    )


@pytest.mark.parametrize("fmt", ["html", "epub", "txt"])
def test_each_format_ends_with_the_same_units_and_paragraphs(
    fmt: BookFormat, sample_bytes: dict[BookFormat, bytes]
) -> None:
    result = extract(fmt, sample_bytes[fmt])
    assert result.map_method == "llm"
    assert result.book.format == fmt and result.book.id == "the-lantern-keeper"
    assert [(u.kind, u.parent_id) for u in result.units] == samples.EXPECTED_UNITS
    assert [p.text for p in result.paragraphs] == [
        " ".join(p.split()) for p in samples.STORY_PARAGRAPHS
    ]
    assert result.warnings == []


def test_the_llm_map_is_used_for_extraction(sample_bytes: dict[BookFormat, bytes]) -> None:
    content = sample_bytes["txt"]
    llm = sample_llm(content, "txt")
    result = extract_book(Source(content, "lantern.txt", "x"), llm)
    assert result.map_method == "llm"
    assert [(u.kind, u.parent_id) for u in result.units] == samples.EXPECTED_UNITS
    assert len(llm.prompts) == 1


def test_book_id_can_be_chosen(sample_bytes: dict[BookFormat, bytes]) -> None:
    assert extract("txt", sample_bytes["txt"], book_id="my-copy").book.id == "my-copy"


# ----------------------------------------------------------------- the files


def test_book_json_and_readable_unit_files(
    tmp_path: Path, sample_bytes: dict[BookFormat, bytes]
) -> None:
    result = extract("html", sample_bytes["html"])
    book_dir = save_extraction(result, tmp_path)

    assert book_dir == tmp_path / "the-lantern-keeper"
    data = json.loads((book_dir / "book.json").read_text())
    assert data["schema_version"] == SCHEMA_VERSION
    assert set(data) == {
        "schema_version", "book", "map_method", "candidates", "map_items", "units", "paragraphs",
        "warnings",
    }  # fmt: skip
    assert data["book"]["title"] == "The Lantern Keeper"
    assert data["units"][1] == {
        "id": "u02", "order": 2, "kind": "chapter", "title": data["units"][1]["title"],
        "parent_id": "u01", "char_start": data["units"][1]["char_start"],
        "char_end": data["units"][1]["char_end"],
    }  # fmt: skip
    assert data["paragraphs"][0]["id"] == "u02_p001"

    canonical = (book_dir / "canonical.txt").read_text()
    for p in data["paragraphs"]:  # offsets point into canonical.txt
        assert " ".join(canonical[p["char_start"] : p["char_end"]].split()) == p["text"]

    files = sorted(f.name for f in (book_dir / "units").iterdir())
    assert [f[:2] for f in files] == ["02", "03", "05"]  # parts (01, 04) hold no paragraphs
    first = (book_dir / "units" / files[0]).read_text()
    assert first.startswith("CHAPTER I The Lamp") or first.startswith("CHAPTER I: The Lamp")
    assert "[u02_p001] One evening the keeper" in first


def test_saved_book_loads_back_and_unit_files_do_not_go_stale(
    tmp_path: Path, sample_bytes: dict[BookFormat, bytes]
) -> None:
    result = extract("txt", sample_bytes["txt"])
    book_dir = save_extraction(result, tmp_path)
    (book_dir / "units" / "99_stale.txt").write_text("left over")
    save_extraction(result, tmp_path)  # same file again: allowed, replaces everything
    assert not (book_dir / "units" / "99_stale.txt").exists()
    loaded = load_extraction(tmp_path, "the-lantern-keeper")
    assert loaded.units == result.units and loaded.paragraphs == result.paragraphs


def test_an_existing_heuristic_extraction_remains_readable(
    tmp_path: Path, sample_bytes: dict[BookFormat, bytes]
) -> None:
    legacy = extract("txt", sample_bytes["txt"]).model_copy(update={"map_method": "heuristic"})
    save_extraction(legacy, tmp_path)
    assert load_extraction(tmp_path, "the-lantern-keeper").map_method == "heuristic"


def test_a_different_file_under_the_same_id_is_refused(
    tmp_path: Path, sample_bytes: dict[BookFormat, bytes]
) -> None:
    save_extraction(extract("html", sample_bytes["html"]), tmp_path)
    with pytest.raises(BookIdConflictError, match="--id"):
        save_extraction(extract("txt", sample_bytes["txt"]), tmp_path)


def test_an_unknown_schema_version_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "book.json").write_text('{"schema_version": 99}')
    with pytest.raises(ValueError):
        load_extraction(tmp_path, "x")


# ----------------------------------------------------------------- the command line


def test_cli_extract_then_show(
    tmp_path: Path, sample_bytes: dict[BookFormat, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOK_CLONE_DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "lantern.epub"
    source.write_bytes(sample_bytes["epub"])
    monkeypatch.setattr(
        cli, "OpenRouterClient", lambda settings: sample_llm(sample_bytes["epub"], "epub")
    )
    runner = CliRunner()

    done = runner.invoke(app, ["extract", str(source)])
    assert done.exit_code == 0, done.output
    assert "Units:      5 (2 part, 3 chapter)" in done.output
    assert "Paragraphs: 7 (0 flagged)" in done.output
    assert (tmp_path / "data" / "extracted" / "the-lantern-keeper" / "book.json").exists()

    shown = runner.invoke(app, ["show", "the-lantern-keeper"])
    assert shown.exit_code == 0, shown.output
    assert "The Light Goes Out" in shown.output

    paragraphs = runner.invoke(app, ["show", "the-lantern-keeper", "u03"])
    assert "[u03_p001] At dawn a stranger knocked" in paragraphs.output


def test_cli_errors_are_short_messages_not_tracebacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOK_CLONE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(cli, "OpenRouterClient", lambda settings: sample_llm(b"x", "txt"))
    runner = CliRunner()
    assert "Error:" in runner.invoke(app, ["extract", str(tmp_path / "missing.txt")]).output
    assert "run `pov extract` first" in runner.invoke(app, ["show", "nope"]).output
    monkeypatch.undo()
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    no_key = runner.invoke(app, ["extract", str(tmp_path)])
    assert no_key.exit_code == 1 and "OPENROUTER_API_KEY" in no_key.output
