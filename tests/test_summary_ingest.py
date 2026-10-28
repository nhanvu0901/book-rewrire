import json
from pathlib import Path

import pytest
from test_character_ingest import (
    RecordingWriter,
    ScriptedLLM,
    character,
    extraction,
    make_extraction,
)

from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.pipeline import ingest_book


def test_ingest_passes_only_preceding_who_is_who_where_is_where_and_chapter_summaries(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara met Jo."], ["FUTURE_PERSON arrived."]])
    summaries = ScriptedLLM(
        [
            "PAST_CHAPTER_ONE",
            {"add": [{"name": "Mara", "other_names": [], "card": "WHO_AFTER_ONE"}], "update": []},
            {
                "add": [{"name": "The Gate", "other_names": [], "card": "WHERE_AFTER_ONE"}],
                "update": [],
            },
            "CURRENT_CHAPTER_TWO",
            {
                "add": [{"name": "Jo", "other_names": [], "card": "companion"}],
                "update": [
                    {
                        "id": "C001",
                        "name": "Mara",
                        "other_names": [],
                        "card": "WHO_AFTER_TWO",
                    }
                ],
            },
            {
                "add": [
                    {
                        "name": "Great Hall",
                        "other_names": [],
                        "card": "hall inside the gate",
                    }
                ],
                "update": [
                    {
                        "id": "P001",
                        "name": "The Gate",
                        "other_names": [],
                        "card": "WHERE_AFTER_TWO",
                    }
                ],
            },
            "FUTURE_CHAPTER_THREE",
            {
                "add": [
                    {
                        "name": "FUTURE_PERSON",
                        "other_names": [],
                        "card": "stranger",
                    }
                ],
                "update": [
                    {
                        "id": "C001",
                        "name": "Mara",
                        "other_names": [],
                        "card": "WHO_AFTER_THREE",
                    }
                ],
            },
            {
                "add": [
                    {
                        "name": "FUTURE_PLACE",
                        "other_names": [],
                        "card": "tower",
                    }
                ],
                "update": [
                    {
                        "id": "P001",
                        "name": "The Gate",
                        "other_names": [],
                        "card": "WHERE_AFTER_THREE",
                    }
                ],
            },
            "FUTURE_CORE_MEMORY",
        ]
    )
    llm = ScriptedLLM(
        [
            extraction(character("Mara", species="human")),
            extraction(character("Jo")),
            extraction(),
        ]
    )
    writer = RecordingWriter()
    steps: list[str] = []
    result = ingest_book(
        "sample",
        llm,
        writer,
        summary_llm=summaries,
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        on_step=steps.append,
    )
    assert "<previous_book_summary>\n\n</previous_book_summary>" in llm.prompts[0]
    assert "WHO_AFTER_ONE" in llm.prompts[1]
    assert "WHERE_AFTER_ONE" in llm.prompts[1]
    assert "[u01]\nPAST_CHAPTER_ONE" in llm.prompts[1]
    assert "CURRENT_CHAPTER_TWO" not in llm.prompts[1]
    assert "WHO_AFTER_TWO" not in llm.prompts[1]
    assert "WHERE_AFTER_TWO" not in llm.prompts[1]
    assert "WHO_AFTER_TWO" in llm.prompts[2]
    assert "WHERE_AFTER_TWO" in llm.prompts[2]
    assert "WHO_AFTER_ONE" not in llm.prompts[2]
    assert "WHERE_AFTER_ONE" not in llm.prompts[2]
    assert llm.prompts[2].index("[u01]\nPAST_CHAPTER_ONE") < llm.prompts[2].index(
        "[u02]\nCURRENT_CHAPTER_TWO"
    )
    assert all("FUTURE_" not in prompt for prompt in llm.prompts[:2])
    assert "FUTURE_CHAPTER_THREE" not in llm.prompts[2]
    assert "WHO_AFTER_THREE" not in llm.prompts[2]
    assert "WHERE_AFTER_THREE" not in llm.prompts[2]
    assert "FUTURE_CORE_MEMORY" not in llm.prompts[2]
    assert "[u01_p001] Mara arrived." not in llm.prompts[1]
    assert '"species": "human"' in llm.prompts[1]
    saved = json.loads((result.characters_file.parent / "summaries/u02.summary.json").read_text())
    assert saved == {
        "chapter_id": "u02",
        "chapter_summary": "CURRENT_CHAPTER_TWO",
        "who_is_who": "Mara | - | WHO_AFTER_TWO\nJo | - | companion",
        "where_is_where": "The Gate | - | WHERE_AFTER_TWO\nGreat Hall | - | hall inside the gate",
    }
    book_memory = json.loads(
        (result.characters_file.parent / "summaries/book_memory.json").read_text()
    )
    assert book_memory == {
        "who_is_who": (
            "Mara | - | WHO_AFTER_THREE\nJo | - | companion\nFUTURE_PERSON | - | stranger"
        ),
        "where_is_where": (
            "The Gate | - | WHERE_AFTER_THREE\nGreat Hall | - | hall inside the gate\n"
            "FUTURE_PLACE | - | tower"
        ),
        "core_memory": "FUTURE_CORE_MEMORY",
    }
    assert steps.index("save_summary u03") < steps.index("save_book_memory")
    assert steps.index("save_book_memory") < steps.index("extract_characters u01")
    assert steps.index("save_characters_json u03: 2 characters") < steps.index("save_neo4j")


def test_summary_failure_keeps_saved_summaries_and_prevents_extraction(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara returned."]])
    summaries = ScriptedLLM(
        [
            "First summary",
            {"add": [{"name": "Mara", "other_names": [], "card": "traveler"}], "update": []},
            {"add": [{"name": "The Gate", "other_names": [], "card": "stone gate"}], "update": []},
            LLMError("Summary unavailable"),
        ]
    )
    llm, writer = ScriptedLLM([]), RecordingWriter()
    with pytest.raises(LLMError, match="Summary unavailable"):
        ingest_book(
            "sample",
            llm,
            writer,
            summary_llm=summaries,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="failed",
        )
    directory = tmp_path / "ingest/sample/failed"
    assert (directory / "summaries/u01.summary.json").exists()
    assert not (directory / "summaries/book_memory.json").exists()
    assert not (directory / "characters.json").exists()
    assert llm.prompts == [] and writer.saved is None
