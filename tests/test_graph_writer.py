"""The story graph is written after every chapter (T-0015)."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from neo4j import Driver
from test_character_ingest import (
    RecordingDriver,
    RecordingWriter,
    ScriptedLLM,
    character,
    extraction,
    make_extraction,
    summary_cards,
    summary_client,
)

from pov_retell.infrastructure.llm import LLMError
from pov_retell.infrastructure.neo4j import Neo4jGraphWriter
from pov_retell.infrastructure.neo4j.cypher import CHAPTER_STATEMENTS, KEYS
from pov_retell.ingest.pipeline import ingest_book


def segment(
    start: str,
    end: str,
    location_id: str | None,
    present: list[str],
    viewpoint: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "location_id": location_id,
        "present_ids": present,
        "mentioned_ids": [],
        "viewpoint_ids": viewpoint or [],
        "time": {"relation": "continues", "anchor": None, "note": None},
        "label": "At the gate",
    }


def run(
    root: Path, chapters: int, responses: list[Any], writer: RecordingWriter
) -> tuple[Any, ScriptedLLM]:
    llm = ScriptedLLM(responses, cards=summary_cards(chapters))
    result = ingest_book(
        "sample",
        llm,
        writer,
        summary_llm=summary_client(chapters),
        extracted_dir=root / "extracted",
        ingest_dir=root / "ingest",
        run_id="run_graph",
    )
    return result, llm


def two_chapter_story(tmp_path: Path) -> list[Any]:
    make_extraction(
        tmp_path,
        [
            ["Mara and the captain met at the gate.", "The captain stayed."],
            ["Mara was the captain.", "They walked into the hall."],
        ],
    )
    return [
        extraction(character("Mara"), character("the captain", "new_2")),
        {
            "relationships": [
                {
                    "op": "start",
                    "source_id": "char_001",
                    "target_id": "char_002",
                    "kind": "friend of",
                    "paragraph_ids": ["u01_p001"],
                }
            ]
        },
        {
            "locations": [
                {
                    "location_id": "new_1",
                    "name": "the gate",
                    "aliases": [],
                    "kind": "gate",
                    "part_of": None,
                }
            ]
        },
        {
            "segments": [
                segment("u01_p001", "u01_p001", "loc_001", ["char_001", "char_002"], ["char_001"]),
                segment("u01_p002", "u01_p002", "loc_001", ["char_002"]),
            ]
        },
        extraction(character("Mara", "char_001", merges=["char_002"])),
        {
            "locations": [
                {
                    "location_id": "new_1",
                    "name": "the hall",
                    "aliases": [],
                    "kind": "hall",
                    "part_of": "loc_001",
                }
            ]
        },
        {"segments": [segment("u02_p001", "u02_p002", "loc_002", ["char_001"])]},
    ]


def test_each_chapter_writes_the_cumulative_graph_after_its_json(tmp_path: Path) -> None:
    writer = RecordingWriter()
    result, _ = run(tmp_path, 2, two_chapter_story(tmp_path), writer)
    assert writer.events == [
        ("start", "The Gate"),
        ("chapter", "u01"),
        ("chapter", "u02"),
        ("finish", "run_graph"),
    ]
    first, second = writer.snapshots
    assert first["chapters_done"] == 1 and second["chapters_done"] == 2
    assert [c["character_id"] for c in first["characters"]] == ["char_001", "char_002"]
    assert [r["kind"] for r in first["relationships"]] == ["friend of"]
    assert [loc["location_id"] for loc in second["locations"]] == ["loc_001", "loc_002"]
    assert second["locations"][1]["part_of"] == "loc_001"
    assert [s["segment_id"] for s in second["scenes"]] == ["u01_s1", "u01_s2", "u02_s1"]
    assert [s["order"] for s in second["scenes"]] == [1, 2, 3]
    assert second["scenes"][2]["chapter_id"] == "u02"
    scenes_file = json.loads((result.characters_file.parent / "scenes.json").read_text())
    assert [s["segment_id"] for s in scenes_file] == ["u01_s1", "u01_s2", "u02_s1"]


def test_a_merge_retires_the_old_id_and_rewrites_scenes(tmp_path: Path) -> None:
    writer = RecordingWriter()
    result, _ = run(tmp_path, 2, two_chapter_story(tmp_path), writer)
    second = writer.snapshots[-1]
    assert second["retired_character_ids"] == ["char_002"]
    assert [c["character_id"] for c in second["characters"]] == ["char_001"]
    # The friendship pointed at the merged character, so it collapses to a self-loop and goes.
    assert second["relationships"] == []
    first_scene, lone_scene, _ = second["scenes"]
    assert first_scene["present_ids"] == ["char_001"]
    assert first_scene["viewpoint_ids"] == ["char_001"]
    assert lone_scene["present_ids"] == ["char_001"]
    scenes_file = json.loads((result.characters_file.parent / "scenes.json").read_text())
    assert scenes_file[1]["present_ids"] == ["char_001"]
    # The per-chapter file keeps what the model answered for that chapter.
    chapter_file = result.characters_file.parent / "chapters/u01.scenes.json"
    assert json.loads(chapter_file.read_text())[1]["present_ids"] == ["char_002"]


def test_a_failure_marks_the_run_failed_after_the_written_chapters(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara and Evan arrived."]])
    writer = RecordingWriter()
    with pytest.raises(LLMError, match="Unavailable"):
        run(tmp_path, 2, [extraction(character("Mara")), LLMError("Unavailable")], writer)
    assert writer.events == [
        ("start", "The Gate"),
        ("chapter", "u01"),
        ("fail", "run_graph"),
    ]
    assert writer.status == "failed"
    assert writer.error is not None and "LLMError: Unavailable" in writer.error


def test_neo4j_writes_one_chapter_in_a_single_transaction() -> None:
    driver = RecordingDriver()
    writer = Neo4jGraphWriter(cast(Driver, driver))
    snapshot: dict[str, Any] = {
        "chapter_id": "u01",
        "chapters_done": 1,
        "characters": [{"character_id": "char_001", "canonical_name": "Mara"}],
        "retired_character_ids": [],
        "locations": [],
        "relationships": [],
        "scenes": [],
    }
    writer.start_run("sample", "run_a", "The Gate", ["u01"])
    writer.write_chapter("sample", "run_a", snapshot)
    writer.write_chapter("sample", "run_a", snapshot)
    assert driver.transactions == 2
    assert driver.statements == list(CHAPTER_STATEMENTS) * 2
    assert driver.rows == snapshot["characters"]
    assert (driver.book_id, driver.run_id) == ("sample", "run_a")
    constraints = [q for q in driver.queries if q.startswith("CREATE CONSTRAINT")]
    assert len(constraints) == len(KEYS)  # created once per writer, not per chapter
