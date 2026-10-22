import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from neo4j import Driver
from pydantic import BaseModel, SecretStr
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.book.models import Book, ExtractedBook, Paragraph, Unit
from pov_retell.book.output import save_extraction
from pov_retell.config import Settings
from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.pipeline import ingest_book

T = TypeVar("T", bound=BaseModel)


def character(
    name: str,
    character_id: str = "new_1",
    relationships: dict[str, str] | None = None,
    merged_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "character_id": character_id,
        "merged_character_ids": merged_ids or [],
        "candidate_name": name,
        "aliases": [name],
        "attributes": {
            "gender": None,
            "species": "human",
            "age_description": None,
            "physical_description": None,
            "personality_traits": ["cautious"],
        },
        "relationships": relationships or {},
        "resolution_status": "candidate",
    }


def discovery(*characters: dict[str, Any]) -> dict[str, Any]:
    return {"characters": list(characters)}


class ScriptedLLM:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = copy.deepcopy(responses)
        self.prompts: list[str] = []

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        self.prompts.append(prompt)
        result = schema.model_validate(self.responses[len(self.prompts) - 1])
        if check is not None:
            check(result)
        return result


class RecordingWriter:
    def __init__(self) -> None:
        self.saved: tuple[str, str, list[dict[str, Any]]] | None = None

    def write_characters(self, book_id: str, run_id: str, rows: list[dict[str, Any]]) -> None:
        self.saved = (book_id, run_id, copy.deepcopy(rows))


def make_extraction(root: Path, texts: list[list[str]]) -> Path:
    units = []
    paragraphs = []
    position = 0
    for number, blocks in enumerate(texts, start=1):
        unit_id = f"u{number:02d}"
        start = position
        for index, text in enumerate(blocks, start=1):
            paragraphs.append(
                Paragraph(
                    id=f"{unit_id}_p{index:03d}",
                    unit_id=unit_id,
                    order=index,
                    text=text,
                    char_start=position,
                    char_end=position + len(text),
                )
            )
            position += len(text) + 2
        units.append(
            Unit(
                id=unit_id,
                order=number,
                kind="chapter",
                title=f"Chapter {number}",
                char_start=start,
                char_end=position,
            )
        )
    book = ExtractedBook(
        book=Book(
            id="sample",
            title="The Gate",
            author="Example",
            format="txt",
            sha256="a" * 64,
            source="sample.txt",
        ),
        map_method="llm",
        candidates=[],
        map_items=[],
        units=units,
        paragraphs=paragraphs,
    )
    return save_extraction(book, root / "extracted")


def run_ingest(
    root: Path, responses: list[dict[str, Any]]
) -> tuple[Any, ScriptedLLM, RecordingWriter]:
    llm = ScriptedLLM(responses)
    writer = RecordingWriter()
    result = ingest_book(
        "sample",
        llm,
        writer,
        extracted_dir=root / "extracted",
        ingest_dir=root / "ingest",
        run_id="run_test",
    )
    return result, llm, writer


def test_ingest_finishes_after_character_discovery_and_saves_character_nodes(
    tmp_path: Path,
) -> None:
    make_extraction(
        tmp_path,
        [["Jo befriended the captain. Mara watched."], ["Mara was the captain. Evan arrived."]],
    )
    merged = character("Mara", "char_001", merged_ids=["char_002"])
    merged["aliases"].append("the captain")
    llm = ScriptedLLM(
        [
            discovery(
                character("Mara"),
                character("the captain", "new_2"),
                character("Jo", "new_3", {"new_2": "friend of the captain"}),
            ),
            discovery(
                merged,
                character("Jo", "char_003", {"char_002": "friend of Mara"}),
                character("Evan"),
            ),
        ]
    )
    writer = RecordingWriter()
    steps: list[str] = []
    result = ingest_book(
        "sample",
        llm,
        writer,
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        run_id="run_test",
        on_step=steps.append,
    )
    final = json.loads(result.characters_file.read_text())
    assert len(llm.prompts) == 2
    assert [c["character_id"] for c in final] == ["char_001", "char_003", "char_004"]
    assert "the captain" in final[0]["aliases"]
    assert final[1]["relationships"] == {"char_001": "friend of Mara"}
    assert writer.saved is not None
    assert writer.saved[:2] == ("sample", "run_test")
    assert [row["canonical_name"] for row in writer.saved[2]] == ["Mara", "Jo", "Evan"]
    assert "relationships" not in writer.saved[2][0]
    assert steps.index("save_characters_json u02: 3 characters") < steps.index("save_neo4j")
    assert not (result.characters_file.parent / "relationships.json").exists()
    assert not (result.characters_file.parent / "relationship_batches").exists()


def test_character_graph_runs_independently_without_relationship_verification(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.character_discovery import build_character_graph

    make_extraction(tmp_path, [["Mara is Susan's sister."], ["Mara returned."]])
    llm = ScriptedLLM(
        [
            discovery(
                character("Mara", relationships={"new_2": "sister of Susan"}),
                character("Susan", "new_2"),
            ),
            discovery(
                character("Mara", "char_001", {"char_002": "sister of Susan"}),
                character("Susan", "char_002"),
            ),
        ]
    )
    graph = build_character_graph(llm, tmp_path / "extracted", tmp_path / "ingest")
    final = graph.invoke({"book_id": "sample", "run_id": "discovery_only"})
    assert final["chapter_index"] == 2
    assert len(llm.prompts) == 2
    assert final["characters"][0].relationships == {"char_002": "sister of Susan"}
    assert (final["output_dir"] / "chapters/u02.characters.json").exists()
    assert not (final["output_dir"] / "relationships.json").exists()


def test_discovery_preserves_prior_relationship_proposals(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara is Susan's sister."], ["Mara waited."]])
    result, llm, _ = run_ingest(
        tmp_path,
        [
            discovery(
                character("Mara", relationships={"new_2": "sister of Susan"}),
                character("Susan", "new_2"),
            ),
            discovery(character("Mara", "char_001"), character("Susan", "char_002")),
        ],
    )
    assert len(llm.prompts) == 2
    assert json.loads(result.characters_file.read_text())[0]["relationships"] == {
        "char_002": "sister of Susan"
    }


@pytest.mark.parametrize("target", ["new_1", "new_999", "char_999"])
def test_invalid_relationship_targets_stop_before_saving(tmp_path: Path, target: str) -> None:
    make_extraction(tmp_path, [["Mara waited."]])
    llm = ScriptedLLM([discovery(character("Mara", relationships={target: "friend"}))])
    writer = RecordingWriter()
    with pytest.raises(ValueError):
        ingest_book(
            "sample",
            llm,
            writer,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
        )
    assert len(llm.prompts) == 1
    assert writer.saved is None


@pytest.mark.parametrize(
    "failure",
    [
        "missing_character",
        "unknown_id",
        "duplicate_id",
        "verified",
        "null_attribute",
        "invalid_merge",
    ],
)
def test_invalid_character_updates_preserve_previous_json(tmp_path: Path, failure: str) -> None:
    make_extraction(tmp_path, [["Mara waited."], ["Mara returned."]])
    bad = character("Mara", "char_001")
    characters = [bad]
    if failure == "missing_character":
        characters = []
    elif failure == "unknown_id":
        bad["character_id"] = "char_999"
    elif failure == "duplicate_id":
        characters.append(copy.deepcopy(bad))
    elif failure == "verified":
        bad["resolution_status"] = "verified"
    elif failure == "null_attribute":
        bad["attributes"]["species"] = None
    else:
        bad["merged_character_ids"] = ["char_999"]
    writer = RecordingWriter()
    with pytest.raises(ValueError):
        ingest_book(
            "sample",
            ScriptedLLM([discovery(character("Mara")), discovery(*characters)]),
            writer,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="bad",
        )
    assert (
        json.loads((tmp_path / "ingest/sample/bad/characters.json").read_text())[0][
            "candidate_name"
        ]
        == "Mara"
    )
    assert writer.saved is None


def test_same_names_stay_separate_and_name_changes_keep_ids(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Two Alexes arrived."], ["One was Alex Vale."]])
    renamed = character("Alex Vale", "char_001")
    renamed["aliases"].append("Alex")
    result, _, _ = run_ingest(
        tmp_path,
        [
            discovery(character("Alex"), character("Alex", "new_2")),
            discovery(character("Alex", "char_002"), renamed),
        ],
    )
    assert [
        (c["character_id"], c["candidate_name"])
        for c in json.loads(result.characters_file.read_text())
    ] == [("char_001", "Alex Vale"), ("char_002", "Alex")]


def test_many_chapters_complete_in_numeric_order_without_checkpoints(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[f"Mara waited on day {day}."] for day in range(1, 13)])
    result, llm, _ = run_ingest(
        tmp_path,
        [discovery(character("Mara", "new_1" if day == 1 else "char_001")) for day in range(1, 13)],
    )
    assert "Current chapter: u10" in llm.prompts[9]
    assert len(list(result.characters_file.parent.rglob("*.json"))) == 13


def test_empty_character_discovery_is_saved(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["The wind blew."]])
    result, llm, writer = run_ingest(tmp_path, [discovery()])
    assert json.loads(result.characters_file.read_text()) == []
    assert len(llm.prompts) == 1
    assert writer.saved == ("sample", "run_test", [])


def test_existing_run_is_not_overwritten_or_reprocessed(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara waited."]])
    result, _, _ = run_ingest(tmp_path, [discovery(character("Mara"))])
    before = result.characters_file.read_bytes()
    llm, writer = ScriptedLLM([]), RecordingWriter()
    with pytest.raises(FileExistsError):
        ingest_book(
            "sample",
            llm,
            writer,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="run_test",
        )
    assert result.characters_file.read_bytes() == before
    assert llm.prompts == [] and writer.saved is None


@pytest.mark.parametrize("failure", ["missing_file", "edited_text", "empty_units"])
def test_invalid_source_files_stop_before_any_llm_call(tmp_path: Path, failure: str) -> None:
    directory = make_extraction(tmp_path, [] if failure == "empty_units" else [["Mara waited."]])
    if failure != "empty_units":
        path = next((directory / "units").glob("*.txt"))
        if failure == "missing_file":
            path.unlink()
        else:
            path.write_text(path.read_text().replace("Mara waited.", "Different text."))
    llm, writer = ScriptedLLM([]), RecordingWriter()
    with pytest.raises((OSError, ValueError)):
        ingest_book(
            "sample",
            llm,
            writer,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="invalid",
        )
    assert llm.prompts == [] and writer.saved is None


class RecordingDriver:
    def __init__(self) -> None:
        self.closed = False
        self.rows: list[dict[str, Any]] = []
        self.book_id = ""
        self.run_id = ""

    def __enter__(self) -> "RecordingDriver":
        return self

    def __exit__(self, *args: Any) -> None:
        self.closed = True

    def verify_connectivity(self) -> None:
        assert not self.closed

    def execute_query(self, query: str, **parameters: Any) -> tuple[list[Any], None, None]:
        assert not self.closed
        if "dbms.components" in query:
            return [{"version": "5", "edition": "community"}], None, None
        if "UNWIND" in query:
            self.rows = parameters["rows"]
            self.book_id = parameters["book_id"]
            self.run_id = parameters["run_id"]
        return [], None, None


@pytest.mark.parametrize("api_error", [False, True])
def test_cli_keeps_driver_open_until_ingest_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_error: bool
) -> None:
    make_extraction(tmp_path, [["Mara waited."]])
    llm = ScriptedLLM([discovery(character("Mara"))])
    if api_error:

        def unavailable(
            prompt: str, schema: type[T], check: Callable[[T], None] | None = None
        ) -> T:
            raise LLMError("Provider unavailable")

        monkeypatch.setattr(llm, "complete_json", unavailable)
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        OPENROUTER_API_KEY=SecretStr("test-key"),
        OPENROUTER_BASE_URL="https://example.invalid",
        OPENROUTER_MODEL="example",
        OPENROUTER_MAX_TOKENS=8192,
        BOOK_CLONE_DATA_DIR=tmp_path,
        NEO4J_HTTP_PORT=7475,
        NEO4J_BOLT_PORT=7688,
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD=SecretStr("test-password"),
    )
    driver = RecordingDriver()
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "connect", lambda settings: cast(Driver, driver))
    monkeypatch.setattr(cli, "OpenRouterClient", lambda settings: llm)
    result = CliRunner().invoke(cli.app, ["ingest", "sample"])
    assert driver.closed
    if api_error:
        assert result.exit_code == 1
        assert "Provider unavailable" in result.output
        assert driver.rows == []
    else:
        assert result.exit_code == 0, result.output
        assert driver.book_id == "sample"
        assert driver.run_id.startswith("run_")
        assert driver.rows[0]["canonical_name"] == "Mara"
        assert "mentions" not in driver.rows[0]
        assert "first_mention_id" not in driver.rows[0]
        assert "relationships" not in driver.rows[0]
        assert "1 characters" in result.output
    assert "test-key" not in result.output
    assert "test-password" not in result.output
