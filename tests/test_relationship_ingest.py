import json
import re
from pathlib import Path
from typing import Any

import pytest
from test_character_ingest import (
    RecordingWriter,
    ScriptedLLM,
    character,
    extraction,
    make_extraction,
    split_card_answers,
    summary_client,
)
from test_llm import make

from pov_retell.infrastructure.llm import strict_json_schema
from pov_retell.ingest.graph.extract_character.graph import (
    EXTRACT_NODES_PER_CHAPTER,
    extract_character_recursion_limit,
)
from pov_retell.ingest.graph.extract_character.model import ExtractRelationshipResponse
from pov_retell.ingest.graph.extract_character.prompt.extract_relationship import (
    PROMPT_EXTRACT_RELATIONSHIP,
)
from pov_retell.ingest.graph.summarize_chapter.graph import (
    SUMMARY_NODES_PER_CHAPTER,
    summarize_chapter_recursion_limit,
)
from pov_retell.ingest.pipeline import ingest_book


def rel_change(
    op: str,
    source_id: str,
    target_id: str,
    kind: str,
    paragraph_ids: list[str],
) -> dict[str, Any]:
    return {
        "op": op,
        "source_id": source_id,
        "target_id": target_id,
        "kind": kind,
        "paragraph_ids": paragraph_ids,
    }


def rel_response(*changes: dict[str, Any]) -> dict[str, Any]:
    return {"relationships": list(changes)}


def test_one_relationship_call_per_chapter_after_character_step_and_prompt_markers(
    tmp_path: Path,
) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara and Jo were sisters. Eli served Rafe."],
            ["Mara met Eli at the gate."],
            ["Rafe waited alone."],
        ],
    )
    texts, cards = split_card_answers(
        [
            "SUMMARY_CH1",
            {"add": [{"name": "Mara", "other_names": [], "card": "WHO_CH1"}], "update": []},
            {"add": [{"name": "The Gate", "other_names": [], "card": "WHERE_CH1"}], "update": []},
            "SUMMARY_CH2",
            {
                "add": [],
                "update": [{"id": "C001", "name": "Mara", "other_names": [], "card": "WHO_CH2"}],
            },
            {
                "add": [],
                "update": [
                    {"id": "P001", "name": "The Gate", "other_names": [], "card": "WHERE_CH2"}
                ],
            },
            "SUMMARY_CH3",
            {
                "add": [],
                "update": [{"id": "C001", "name": "Mara", "other_names": [], "card": "WHO_CH3"}],
            },
            {
                "add": [],
                "update": [
                    {"id": "P001", "name": "The Gate", "other_names": [], "card": "WHERE_CH3"}
                ],
            },
            "CORE_MEMORY",
        ]
    )
    llm = ScriptedLLM(
        [
            extraction(
                character("Mara", "new_1", aliases=["Lady Mara"]),
                character("Jo", "new_2"),
                character("Eli", "new_3"),
                character("Rafe", "new_4"),
            ),
            rel_response(
                rel_change("start", "char_001", "char_002", "Sister Of", ["u01_p001"]),
                rel_change("start", "char_003", "char_004", "servant of", ["u01_p001"]),
            ),
            extraction(
                character("Mara", "char_001"),
            ),
            rel_response(),
            extraction(
                character("Rafe", "char_004"),
            ),
            rel_response(
                rel_change("end", "char_003", "char_004", "servant of", ["u03_p001"]),
            ),
        ],
        cards=cards,
    )
    summaries = ScriptedLLM(texts)
    steps: list[str] = []
    result = ingest_book(
        "sample",
        llm,
        RecordingWriter(),
        summary_llm=summaries,
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        on_step=steps.append,
    )
    assert [
        schema_name
        for schema_name, _ in llm.calls
        if schema_name in {"ExtractCharacterResponse", "ExtractRelationshipResponse"}
    ] == [
        "ExtractCharacterResponse",
        "ExtractRelationshipResponse",
        "ExtractCharacterResponse",
        "ExtractRelationshipResponse",
        "ExtractCharacterResponse",
        "ExtractRelationshipResponse",
    ]
    assert steps.index("validate_characters u01") < steps.index("extract_relationships u01")
    assert steps.index("extract_relationships u02") < steps.index("extract_characters u03")

    # Check Chapter 2 relationship prompt markers:
    # Active in u02 is only char_001 (Mara). Open rels are rel_001 (char_001->char_002) and
    # rel_002 (char_003->char_004). Only rel_001 involves active char_001!
    ch2_rel_prompt = [p for s, p in llm.calls if s == "ExtractRelationshipResponse"][1]
    assert "Current chapter: u02" in ch2_rel_prompt
    assert "WHO_CH1" in ch2_rel_prompt and "[u01]\nSUMMARY_CH1" in ch2_rel_prompt
    assert "SUMMARY_CH2" not in ch2_rel_prompt
    assert "[u02_p001] Mara met Eli at the gate." in ch2_rel_prompt

    roster_block = ch2_rel_prompt.split("<character_roster_json>\n")[1].split(
        "\n</character_roster_json>"
    )[0]
    roster = json.loads(roster_block)
    assert roster[0] == {
        "character_id": "char_001",
        "candidate_name": "Mara",
        "aliases": ["Lady Mara"],
    }
    assert len(roster) == 4

    active_block = ch2_rel_prompt.split("<active_character_ids_json>\n")[1].split(
        "\n</active_character_ids_json>"
    )[0]
    assert json.loads(active_block) == ["char_001"]

    open_block = ch2_rel_prompt.split("<open_relationships>\n")[1].split("\n</open_relationships>")[
        0
    ]
    assert "rel_001: char_001 -> char_002 | sister of" in open_block
    assert "rel_002" not in open_block

    run_dir = result.characters_file.parent
    saved_rels = json.loads((run_dir / "relationships.json").read_text())
    assert saved_rels == [
        {
            "relationship_id": "rel_001",
            "source_id": "char_001",
            "target_id": "char_002",
            "kind": "sister of",
            "valid_from": {"chapter_id": "u01", "paragraph_ids": ["u01_p001"]},
            "valid_to": None,
        },
        {
            "relationship_id": "rel_002",
            "source_id": "char_003",
            "target_id": "char_004",
            "kind": "servant of",
            "valid_from": {"chapter_id": "u01", "paragraph_ids": ["u01_p001"]},
            "valid_to": {"chapter_id": "u03", "paragraph_ids": ["u03_p001"]},
        },
    ]
    assert (run_dir / "chapters/u01.relationships.proposed.json").exists()
    assert (run_dir / "chapters/u01.relationships.json").exists()


def test_start_then_repeated_start_is_noop_and_end_sets_valid_to(tmp_path: Path) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara served Jo."],
            ["Mara still served Jo."],
            ["Mara left Jo's service."],
        ],
    )
    llm = ScriptedLLM(
        [
            extraction(character("Mara", "new_1"), character("Jo", "new_2")),
            rel_response(
                rel_change("start", "char_001", "char_002", "  Servant   Of ", ["u01_p001"])
            ),
            extraction(character("Mara", "char_001"), character("Jo", "char_002")),
            rel_response(rel_change("start", "char_001", "char_002", "servant of", ["u02_p001"])),
            extraction(character("Mara", "char_001"), character("Jo", "char_002")),
            rel_response(rel_change("end", "char_001", "char_002", "servant of", ["u03_p001"])),
        ]
    )
    result = ingest_book(
        "sample",
        llm,
        RecordingWriter(),
        summary_llm=summary_client(3),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    run_dir = result.characters_file.parent
    u02_snapshot = json.loads((run_dir / "chapters/u02.relationships.json").read_text())
    assert u02_snapshot == [
        {
            "relationship_id": "rel_001",
            "source_id": "char_001",
            "target_id": "char_002",
            "kind": "servant of",
            "valid_from": {"chapter_id": "u01", "paragraph_ids": ["u01_p001"]},
            "valid_to": None,
        }
    ]
    final_rels = json.loads((run_dir / "relationships.json").read_text())
    assert final_rels == [
        {
            "relationship_id": "rel_001",
            "source_id": "char_001",
            "target_id": "char_002",
            "kind": "servant of",
            "valid_from": {"chapter_id": "u01", "paragraph_ids": ["u01_p001"]},
            "valid_to": {"chapter_id": "u03", "paragraph_ids": ["u03_p001"]},
        }
    ]


@pytest.mark.parametrize(
    ("bad_change", "expected_reason"),
    [
        (
            rel_change("start", "char_001", "char_999", "friend of", ["u01_p001"]),
            "Unknown character ID",
        ),
        (
            rel_change("start", "char_001", "char_001", "friend of", ["u01_p001"]),
            "source_id and target_id must differ",
        ),
        (
            rel_change("start", "char_001", "char_002", "friend of", ["u02_p001"]),
            "Paragraph ID does not belong to chapter u01",
        ),
        (
            rel_change("end", "char_001", "char_002", "servant of", ["u01_p001"]),
            "Cannot end relationship that is not open",
        ),
        (
            rel_change(
                "start",
                "char_001",
                "char_002",
                "very loyal trusted old friend of",
                ["u01_p001"],
            ),
            "Relationship kind must have 1 to 5 words",
        ),
    ],
)
def test_relationship_validation_rejects_and_retries_with_reason(
    tmp_path: Path,
    bad_change: dict[str, Any],
    expected_reason: str,
) -> None:
    make_extraction(tmp_path, [["Mara and Jo met."]])
    client, transport = make(
        [
            *[json.dumps({"add": [], "update": []})] * 2,  # WHO/WHERE card updates for u01
            json.dumps(extraction(character("Mara", "new_1"), character("Jo", "new_2"))),
            json.dumps(rel_response(bad_change)),
            json.dumps(
                rel_response(rel_change("start", "char_001", "char_002", "friend of", ["u01_p001"]))
            ),
            json.dumps({"locations": []}),
            json.dumps(
                {
                    "segments": [
                        {
                            "start": "u01_p001",
                            "end": "u01_p001",
                            "location_id": None,
                            "present_ids": ["char_001", "char_002"],
                            "mentioned_ids": [],
                            "viewpoint_ids": [],
                            "time": {"relation": "continues", "anchor": None, "note": None},
                            "label": "Mara and Jo meet",
                        }
                    ]
                }
            ),
        ]
    )
    ingest_book(
        "sample",
        client,
        RecordingWriter(),
        summary_llm=summary_client(1),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    assert len(transport.requests) == 7
    retry_msg = transport.requests[4]["messages"][-1]["content"]
    assert "Rejected:" in retry_msg and expected_reason in retry_msg


def test_character_merge_rewrites_relationship_ids_and_merges_duplicate_open_records(
    tmp_path: Path,
) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara was an enemy of Rafe."],
            ["The masked captain was an enemy of Rafe and friend of Jo."],
            ["The masked captain revealed she was Mara."],
        ],
    )
    llm = ScriptedLLM(
        [
            extraction(
                character("Mara", "new_1"),
                character("the masked captain", "new_2"),
                character("Rafe", "new_3"),
                character("Jo", "new_4"),
            ),
            rel_response(
                rel_change("start", "char_001", "char_003", "enemy of", ["u01_p001"]),
            ),
            extraction(
                character("the masked captain", "char_002"),
                character("Rafe", "char_003"),
                character("Jo", "char_004"),
            ),
            rel_response(
                rel_change("start", "char_002", "char_003", "enemy of", ["u02_p001"]),
                rel_change("start", "char_002", "char_004", "friend of", ["u02_p001"]),
            ),
            extraction(
                character("Mara", "char_001", merges=["char_002"]),
            ),
            rel_response(),
        ]
    )
    result = ingest_book(
        "sample",
        llm,
        RecordingWriter(),
        summary_llm=summary_client(3),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    run_dir = result.characters_file.parent
    final_rels = json.loads((run_dir / "relationships.json").read_text())
    assert final_rels == [
        {
            "relationship_id": "rel_001",
            "source_id": "char_001",
            "target_id": "char_003",
            "kind": "enemy of",
            "valid_from": {"chapter_id": "u01", "paragraph_ids": ["u01_p001"]},
            "valid_to": None,
        },
        {
            "relationship_id": "rel_003",
            "source_id": "char_001",
            "target_id": "char_004",
            "kind": "friend of",
            "valid_from": {"chapter_id": "u02", "paragraph_ids": ["u02_p001"]},
            "valid_to": None,
        },
    ]


def test_recursion_limit_helpers_count_nodes_per_chapter() -> None:
    assert SUMMARY_NODES_PER_CHAPTER == 5
    assert EXTRACT_NODES_PER_CHAPTER >= 5
    assert summarize_chapter_recursion_limit(17) == max(
        25, 17 * (SUMMARY_NODES_PER_CHAPTER + 1) + 10
    )
    assert extract_character_recursion_limit(17) == max(
        25, 17 * (EXTRACT_NODES_PER_CHAPTER + 1) + 10
    )


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
def test_extract_relationship_prompt_is_book_agnostic(forbidden_word: str) -> None:
    assert (
        re.search(rf"\b{re.escape(forbidden_word)}\b", PROMPT_EXTRACT_RELATIONSHIP, re.IGNORECASE)
        is None
    )


def test_extract_relationship_response_strict_schema_matches_prompt_example() -> None:
    schema = strict_json_schema(ExtractRelationshipResponse)
    match = re.search(
        r"OUTPUT\n.*?\n(\{\{.*?\}\})\n\nIf no relationship", PROMPT_EXTRACT_RELATIONSHIP, re.S
    )
    assert match is not None
    example = json.loads(match.group(1).replace("{{", "{").replace("}}", "}"))
    assert set(schema["properties"].keys()) == set(example.keys())
    change_schema = schema["$defs"]["RelationshipChange"]
    assert change_schema["additionalProperties"] is False
    for item in example["relationships"]:
        assert set(change_schema["properties"].keys()) == set(item.keys())
        assert set(change_schema["required"]) == set(item.keys())
