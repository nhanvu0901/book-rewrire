import json
from pathlib import Path

import pytest
from test_character_ingest import (
    RecordingWriter,
    character,
    extraction,
    make_extraction,
    run_ingest,
    summary_client,
)
from test_llm import make

from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.pipeline import ingest_book


def _default_scene(unit_id: str) -> dict[str, object]:
    return {
        "segments": [
            {
                "start": f"{unit_id}_p001",
                "end": f"{unit_id}_p001",
                "location_id": None,
                "present_ids": [],
                "mentioned_ids": [],
                "viewpoint_ids": [],
                "time": {"relation": "continues", "anchor": None, "note": None},
                "label": "Chapter scene",
            }
        ]
    }


def test_unknown_character_id_retries_before_saving(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara returned."]])
    client, transport = make(
        [
            json.dumps(value)
            for value in [
                extraction(character("Mara")),
                {"relationships": []},
                {"locations": []},
                _default_scene("u01"),
                extraction(character("Mara", "char_999")),
                extraction(character("Mara", "char_001")),
                {"relationships": []},
                {"locations": []},
                _default_scene("u02"),
            ]
        ]
    )
    result = ingest_book(
        "sample",
        client,
        RecordingWriter(),
        summary_llm=summary_client(2),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    assert result.character_count == 1 and len(transport.requests) == 9
    assert "unknown character ID" in transport.requests[5]["messages"][-1]["content"]


def test_repeated_invalid_ids_preserve_last_completed_chapter(tmp_path: Path) -> None:
    make_extraction(tmp_path, [["Mara arrived."], ["Mara returned."]])
    bad = extraction(character("Mara", "char_999"))
    client, _ = make(
        [
            json.dumps(value)
            for value in [
                extraction(character("Mara")),
                {"relationships": []},
                {"locations": []},
                _default_scene("u01"),
                bad,
                bad,
                bad,
            ]
        ]
    )
    writer = RecordingWriter()
    with pytest.raises(LLMError, match="unknown character ID"):
        ingest_book(
            "sample",
            client,
            writer,
            summary_llm=summary_client(2),
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="failed",
        )
    directory = tmp_path / "ingest/sample/failed"
    assert json.loads((directory / "characters.json").read_text())[0]["candidate_name"] == "Mara"
    assert not (directory / "chapters/u02.characters.json").exists()
    assert writer.saved is None


def test_response_with_relationships_key_is_rejected_and_triggers_repair_retry(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara arrived."]])
    with_relationships = {
        **character("Mara"),
        "relationships": {"new_2": "friend"},
    }
    client, transport = make(
        [
            json.dumps(extraction(with_relationships)),
            json.dumps(extraction(character("Mara"))),
            json.dumps({"relationships": []}),
            json.dumps({"locations": []}),
            json.dumps(_default_scene("u01")),
        ]
    )
    result = ingest_book(
        "sample",
        client,
        RecordingWriter(),
        summary_llm=summary_client(1),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    assert result.character_count == 1 and len(transport.requests) == 5
    retry_message = transport.requests[1]["messages"][-1]["content"]
    assert "Rejected:" in retry_message and "relationships" in retry_message


def test_successive_merges_flatten_redirects_and_combine_profiles(tmp_path: Path) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara, the captain, the stranger and Jo arrived."],
            ["The captain was the stranger."],
            ["Mara was the captain."],
        ],
    )
    result, _, _, _ = run_ingest(
        tmp_path,
        [
            extraction(
                character("Mara"),
                character("the captain", "new_2"),
                character("the stranger", "new_3"),
                character("Jo", "new_4"),
            ),
            extraction(character("the captain", "char_002", merges=["char_003"])),
            extraction(character("Mara", "char_001", merges=["char_002"])),
        ],
    )
    records = json.loads(result.characters_file.read_text())
    assert set(records[0]["aliases"]) == {"the captain", "the stranger"}
    assert json.loads((result.characters_file.parent / "identity_redirects.json").read_text()) == {
        "char_002": "char_001",
        "char_003": "char_001",
    }


@pytest.mark.parametrize(
    "case", ["duplicate", "unknown", "new_merge", "reverse_merge", "reuse_retired", "verify"]
)
def test_invalid_profile_updates_do_not_replace_saved_records(tmp_path: Path, case: str) -> None:
    make_extraction(tmp_path, [["Mara and the captain arrived."], ["Mara returned."]])
    proposals = {
        "duplicate": [character("Mara", "char_001"), character("Mara", "char_001")],
        "unknown": [character("Mara", "char_999")],
        "new_merge": [character("Mara", merges=["char_002"])],
        "reverse_merge": [character("the captain", "char_002", merges=["char_001"])],
        "reuse_retired": [
            character("Mara", "char_001", merges=["char_002"]),
            character("the captain", "char_002"),
        ],
        "verify": [{**character("Mara", "char_001"), "resolution_status": "verified"}],
    }
    with pytest.raises(ValueError):
        run_ingest(
            tmp_path,
            [
                extraction(character("Mara"), character("the captain", "new_2")),
                extraction(*proposals[case]),
            ],
        )
    records = json.loads((tmp_path / "ingest/sample/run_test/characters.json").read_text())
    assert [(c["character_id"], c["candidate_name"]) for c in records] == [
        ("char_001", "Mara"),
        ("char_002", "the captain"),
    ]
