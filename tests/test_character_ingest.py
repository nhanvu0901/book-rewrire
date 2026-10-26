import copy
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from neo4j import Driver
from pydantic import BaseModel
from test_llm import settings
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.book.models import Book, ExtractedBook, Paragraph, Unit
from pov_retell.book.output import save_extraction
from pov_retell.config import Settings
from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.pipeline import ingest_book

T = TypeVar("T", bound=BaseModel)


class ScriptedLLM:
    def __init__(self, responses: Sequence[str | dict[str, Any] | Exception]) -> None:
        self.responses = copy.deepcopy(list(responses))
        self._cursor = 0
        self.prompts: list[str] = []
        self.all_prompts: list[str] = []
        self.calls: list[tuple[str, str]] = []
        self.system_prompts: list[str] = []

    def complete_text(self, text: str, *, system_prompt: str) -> str:
        self.prompts.append(text)
        self.all_prompts.append(text)
        self.calls.append(("text", text))
        self.system_prompts.append(system_prompt)
        result = self.responses[self._cursor]
        self._cursor += 1
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, str)
        return result

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        self.all_prompts.append(prompt)
        self.calls.append((schema.__name__, prompt))
        schema_keys = set(schema.model_fields)
        has_schema_dicts = any(
            isinstance(item, dict) and bool(schema_keys.intersection(item))
            for item in self.responses
        )
        if self._cursor < len(self.responses):
            candidate = self.responses[self._cursor]
            if schema.__name__ == "ExtractCharacterResponse" or (
                has_schema_dicts
                and (
                    isinstance(candidate, Exception)
                    or (isinstance(candidate, dict) and bool(schema_keys.intersection(candidate)))
                )
            ):
                self.prompts.append(prompt)
                self._cursor += 1
                if isinstance(candidate, Exception):
                    raise candidate
                result = schema.model_validate(candidate)
                if check is not None:
                    check(result)
                return result
        if schema.__name__ == "SceneMapResponse":
            import re

            pids = re.findall(r"\[(u\d+_p\d+)\]", prompt)
            empty_payload: dict[str, Any] = {
                "segments": [
                    {
                        "start": pids[0],
                        "end": pids[-1],
                        "location_id": None,
                        "present_ids": [],
                        "mentioned_ids": [],
                        "viewpoint_ids": [],
                        "time": {"relation": "continues", "anchor": None, "note": None},
                        "label": "Chapter scene",
                    }
                ]
                if pids
                else []
            }
        else:
            empty_payload = {key: [] for key in schema_keys}
        result = schema.model_validate(empty_payload)
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


def character(
    name: str,
    character_id: str = "new_1",
    *,
    aliases: list[str] | None = None,
    merges: list[str] | None = None,
    **attributes: Any,
) -> dict[str, Any]:
    return {
        "character_id": character_id,
        "candidate_name": name,
        "aliases": aliases or [],
        "attributes": attributes,
        "merged_character_ids": merges or [],
        "resolution_status": "candidate",
    }


def extraction(*characters: dict[str, Any]) -> dict[str, Any]:
    return {"characters": list(characters)}


def summary_client(chapter_count: int) -> ScriptedLLM:
    responses: list[str | dict[str, Any] | Exception] = []
    for index in range(1, chapter_count + 1):
        responses.append(f"Summary of chapter {index}.")
        responses.append(f"Mara | - | traveler in chapter {index}")
        responses.append(f"The Gate | - | stone gate in chapter {index}")
    responses.append("Core memory of the book.")
    return ScriptedLLM(responses)


def run_ingest(
    root: Path,
    responses: list[dict[str, Any] | Exception],
    *,
    run_id: str = "run_test",
) -> tuple[Any, ScriptedLLM, ScriptedLLM, RecordingWriter]:
    llm = ScriptedLLM(responses)
    summaries = summary_client(len(responses))
    writer = RecordingWriter()
    result = ingest_book(
        "sample",
        llm,
        writer,
        summary_llm=summaries,
        extracted_dir=root / "extracted",
        ingest_dir=root / "ingest",
        run_id=run_id,
    )
    return result, llm, summaries, writer


def test_ingest_extracts_full_profiles_once_per_chapter_and_preserves_absent_records(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara and Jo arrived. Mara was cautious."], ["Mara returned."]])
    result, llm, summaries, writer = run_ingest(
        tmp_path,
        [
            extraction(
                character("Mara", gender="female", personality_traits=["cautious"]),
                character("Jo", "new_2", species="human"),
            ),
            extraction(character("Mara", "char_001", physical_description="dark hair")),
        ],
    )
    records = json.loads(result.characters_file.read_text())
    assert len(records) == 2 and len(llm.prompts) == 2
    assert records[0]["attributes"]["gender"] == "female"
    assert records[0]["attributes"]["physical_description"] == "dark hair"
    assert records[0]["attributes"]["personality_traits"] == ["cautious"]
    assert records[1]["candidate_name"] == "Jo"
    roster = json.loads(llm.prompts[1].split("<existing_characters_json>\n")[1].split("\n</")[0])
    assert roster[0]["attributes"]["gender"] == "female"
    assert roster[0]["character_id"] == "char_001"
    assert len(summaries.prompts) == 7
    assert writer.saved is not None and len(writer.saved[2]) == 2
    assert "relationships" not in writer.saved[2][0]
    assert all("relationships" not in record for record in records)
    for snapshot in (result.characters_file.parent / "chapters").glob("*.characters.json"):
        assert all("relationships" not in record for record in json.loads(snapshot.read_text()))
    run_files = {p.name for p in result.characters_file.parent.iterdir()}
    assert run_files == {
        "characters.json",
        "relationships.json",
        "locations.json",
        "identity_redirects.json",
        "chapters",
        "summaries",
    }
    assert ("pending_" + "relationships.json") not in run_files
    assert (result.characters_file.parent / "summaries/u02.summary.json").exists()
    assert not (result.characters_file.parent / "chapters/u01.attributes.json").exists()
    proposed = json.loads(
        (result.characters_file.parent / "chapters/u01.proposed.json").read_text()
    )
    assert proposed["characters"][0]["attributes"]["gender"] == "female"
    assert "relationships" not in proposed["characters"][0]


def test_chapter_updates_only_change_the_returned_fields(tmp_path: Path) -> None:
    make_extraction(
        tmp_path,
        [["Mara and Jo arrived. Mara was cautious."], ["Rain fell."], ["Jo wore a blue cloak."]],
    )
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(
                character(
                    "Mara",
                    gender="female",
                    physical_description="dark hair",
                    personality_traits=["cautious"],
                ),
                character("Jo", "new_2", physical_description="tall"),
            ),
            extraction(),
            extraction(
                character(
                    "Jo",
                    "char_002",
                    aliases=["Captain Jo"],
                    physical_description="a blue cloak",
                )
            ),
        ],
    )
    mara, jo = json.loads(result.characters_file.read_text())
    assert mara["attributes"] == {
        "gender": "female",
        "species": None,
        "age_description": None,
        "physical_description": "dark hair",
        "personality_traits": ["cautious"],
    }
    assert jo["aliases"] == ["Captain Jo"]
    assert jo["attributes"]["physical_description"] == "tall; a blue cloak"


def test_merge_preserves_profiles_and_redirects(tmp_path: Path) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara and the captain arrived. The captain was stern. Jo greeted the captain."],
            ["Mara was the captain."],
            ["Mara arrived with Evan."],
        ],
    )
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(
                character("Mara", gender="female", physical_description="dark hair"),
                character(
                    "the captain",
                    "new_2",
                    physical_description="a scar",
                    personality_traits=["stern"],
                ),
                character("Jo", "new_3"),
            ),
            extraction(character("Mara", "char_001", merges=["char_002"])),
            extraction(character("Evan")),
        ],
    )
    records = json.loads(result.characters_file.read_text())
    assert [c["character_id"] for c in records] == ["char_001", "char_003", "char_004"]
    assert "the captain" in records[0]["aliases"]
    assert records[0]["attributes"]["gender"] == "female"
    assert records[0]["attributes"]["physical_description"] == "dark hair; a scar"
    assert records[0]["attributes"]["personality_traits"] == ["stern"]
    assert json.loads((result.characters_file.parent / "identity_redirects.json").read_text()) == {
        "char_002": "char_001"
    }


def test_same_names_stay_distinct_and_renames_keep_prior_aliases(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Two Alexes arrived."], ["One was Alex Vale."]])
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(character("Alex", aliases=["Al"]), character("Alex", "new_2")),
            extraction(character("Alex Vale", "char_001", aliases=["Vale"])),
        ],
    )
    records = json.loads(result.characters_file.read_text())
    assert [(c["character_id"], c["candidate_name"]) for c in records] == [
        ("char_001", "Alex Vale"),
        ("char_002", "Alex"),
    ]
    assert set(records[0]["aliases"]) == {"Al", "Alex", "Vale"}


def test_canonical_name_does_not_have_to_match_returned_aliases_or_source_verbatim(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["A faun arrived."], ["He said his name was Tumnus."]])
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(character("Faun")),
            extraction(character("Mr. Tumnus", "char_001", aliases=["the faun"])),
        ],
    )
    record = json.loads(result.characters_file.read_text())[0]
    assert record["candidate_name"] == "Mr. Tumnus" and record["character_id"] == "char_001"
    assert set(record["aliases"]) == {"Faun", "the faun"}


def test_character_failure_preserves_last_completed_snapshot(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara and Evan arrived."]])
    writer = RecordingWriter()
    with pytest.raises(LLMError, match="Unavailable"):
        ingest_book(
            "sample",
            ScriptedLLM([extraction(character("Mara")), LLMError("Unavailable")]),
            writer,
            summary_llm=summary_client(2),
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="failed",
        )
    directory = tmp_path / "ingest/sample/failed"
    assert len(json.loads((directory / "characters.json").read_text())) == 1
    assert not (directory / "chapters/u02.characters.json").exists()
    assert writer.saved is None


def test_empty_response_preserves_existing_profiles(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["The wind blew."]])
    result, _, _, writer = run_ingest(tmp_path, [extraction(character("Mara")), extraction()])
    assert json.loads(result.characters_file.read_text())[0]["candidate_name"] == "Mara"
    assert writer.saved is not None and len(writer.saved[2]) == 1


@pytest.mark.parametrize("failure", ["missing_file", "edited_text", "empty_units"])
def test_invalid_source_stops_before_any_model_request(tmp_path: Path, failure: str) -> None:
    directory = make_extraction(tmp_path, [] if failure == "empty_units" else [["Mara arrived."]])
    if failure != "empty_units":
        path = next((directory / "units").glob("*.txt"))
        if failure == "missing_file":
            path.unlink()
        else:
            path.write_text("Edited source")
    llm, summaries, writer = ScriptedLLM([]), ScriptedLLM([]), RecordingWriter()
    with pytest.raises((OSError, ValueError)):
        ingest_book(
            "sample",
            llm,
            writer,
            summary_llm=summaries,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
        )
    assert llm.prompts == [] and summaries.prompts == [] and writer.saved is None


def test_ingest_without_a_writer_still_saves_json(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."]])
    steps: list[str] = []
    result = ingest_book(
        "sample",
        ScriptedLLM([extraction(character("Mara"))]),
        None,
        summary_llm=summary_client(1),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        on_step=steps.append,
    )
    assert json.loads(result.characters_file.read_text())[0]["candidate_name"] == "Mara"
    assert "skip_neo4j" in steps and "save_neo4j" not in steps


def test_existing_run_is_not_overwritten(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."]])
    result, _, _, _ = run_ingest(tmp_path, [extraction(character("Mara"))])
    before = result.characters_file.read_bytes()
    with pytest.raises(FileExistsError):
        run_ingest(tmp_path, [])
    assert result.characters_file.read_bytes() == before


@pytest.mark.parametrize("api_error", [False, True])
def test_cli_selects_summary_and_full_profile_models_and_closes_driver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    api_error: bool,
) -> None:
    make_extraction(tmp_path, [["Mara arrived."]])
    configured = settings(BOOK_CLONE_DATA_DIR=tmp_path)
    llm = ScriptedLLM(
        [LLMError("Unavailable") if api_error else extraction(character("Mara", gender="female"))]
    )
    summaries = summary_client(1)
    driver = RecordingDriver()
    selected: list[tuple[str, str]] = []

    def make_client(settings: Settings, *, model: str, max_tokens_setting: str, **_: Any) -> Any:
        selected.append((model, max_tokens_setting))
        client = llm if model == "example/characters" else summaries
        client.model = model
        return client

    monkeypatch.setattr(cli, "Settings", lambda: configured)
    monkeypatch.setattr(cli, "connect", lambda settings: cast(Driver, driver))
    monkeypatch.setattr(cli, "OpenRouterClient", make_client)
    result = CliRunner().invoke(cli.app, ["ingest", "sample"])
    assert driver.closed
    assert selected == [
        ("example/characters", "OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS"),
        ("example/summary", "OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS"),
    ]
    if api_error:
        assert result.exit_code == 1 and "Unavailable" in result.output
        assert driver.rows == []
    else:
        assert result.exit_code == 0, result.output
        assert driver.rows[0]["canonical_name"] == "Mara"
        assert driver.rows[0]["gender"] == "female"
        assert "Build summarize_chapter graph: model=example/summary" in result.output
        assert "Build extract_character graph: model=example/characters" in result.output
        assert "attributes_model=" not in result.output


def test_new_personality_traits_require_source_wording_but_old_traits_survive(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara was unkind and cautious."], ["Mara returned."]])
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(character("Mara", personality_traits=["kind", "curious", "cautious"])),
            extraction(character("Mara", "char_001")),
        ],
    )
    record = json.loads(result.characters_file.read_text())[0]
    assert record["attributes"]["personality_traits"] == ["cautious"]


def test_many_chapters_complete_in_numeric_order(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[f"Mara waited on day {day}."] for day in range(1, 18)])
    result, llm, summaries, _ = run_ingest(
        tmp_path,
        [
            extraction(character("Mara", "new_1" if day == 1 else "char_001"))
            for day in range(1, 18)
        ],
    )
    assert "Current chapter: u10" in llm.prompts[9]
    assert len(summaries.prompts) == 52
    assert (result.characters_file.parent / "chapters/u17.characters.json").exists()


def test_later_profile_details_preserve_complementary_earlier_descriptions(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara had dark hair."], ["Mara also had a scar."]])
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(
                character("Mara", physical_description="dark hair", age_description="young woman")
            ),
            extraction(
                character(
                    "Mara",
                    "char_001",
                    physical_description="a scar",
                    age_description="older than Jo",
                )
            ),
        ],
    )
    profile = json.loads(result.characters_file.read_text())[0]["attributes"]
    assert profile["physical_description"] == "dark hair; a scar"
    assert profile["age_description"] == "young woman; older than Jo"


def test_extract_character_prompt_rules_and_example_have_no_relationships() -> None:
    from pov_retell.ingest.graph.extract_character.prompt.extract_character import (
        PROMPT_EXTRACT_CHAR,
    )

    assert "relationship" not in PROMPT_EXTRACT_CHAR.casefold()
    assert "lasting appearance only" in PROMPT_EXTRACT_CHAR
    assert "age, life stage, or birth order only" in PROMPT_EXTRACT_CHAR
    assert "Never infer species" in PROMPT_EXTRACT_CHAR
    assert "Titles or names gained in the story" in PROMPT_EXTRACT_CHAR
    assert (
        "Change\n   candidate_name only when this chapter gives a proper name for a character "
        "known so far\n   by a description, or clearly replaces the name"
    ) in PROMPT_EXTRACT_CHAR
    assert "Titles and epithets gained in the story go into aliases." in PROMPT_EXTRACT_CHAR
    assert "Create no record for any group" in PROMPT_EXTRACT_CHAR

    example_block = PROMPT_EXTRACT_CHAR.split("\n{{\n", maxsplit=1)[1].split("\n}}\n", maxsplit=1)[
        0
    ]
    example_json = "{\n" + example_block.replace("{{", "{").replace("}}", "}") + "\n}"
    parsed = json.loads(example_json)
    assert len(parsed["characters"]) == 2
    assert all("relationships" not in item for item in parsed["characters"])


@pytest.mark.parametrize(
    "forbidden_word",
    [
        "Narnia",
        "Aslan",
        "Tumnus",
        "Edmund",
        "Lucy",
        "Peter",
        "Susan",
        "Beaver",
        "Fenris",
        "Jadis",
        "Witch",
        "Eve",
        "Adam",
        "Silenus",
    ],
)
def test_extract_character_prompt_is_book_agnostic(forbidden_word: str) -> None:
    import re

    from pov_retell.ingest.graph.extract_character.prompt.extract_character import (
        PROMPT_EXTRACT_CHAR,
    )

    assert (
        re.search(rf"\b{re.escape(forbidden_word)}\b", PROMPT_EXTRACT_CHAR, re.IGNORECASE) is None
    )
