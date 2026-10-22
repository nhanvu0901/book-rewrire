import copy
import json
from pathlib import Path

import pytest
from test_character_ingest import (
    RecordingWriter,
    character,
    discovery,
    make_extraction,
)
from test_llm import make

from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.extrac_character import validate_characters
from pov_retell.ingest.models.character_discovery import CharacterDiscoveryResponse, CharacterRecord
from pov_retell.ingest.pipeline import ingest_book


def test_renaming_keeps_known_names_and_aliases_without_mutating_llm_output() -> None:
    old = character("Faun", "char_001")
    old["aliases"] = ["the Faun"]
    renamed = character("Tumnus", "char_001")
    renamed["aliases"] = ["Mr. Tumnus"]
    response = CharacterDiscoveryResponse.model_validate(discovery(renamed))
    records, next_number = validate_characters(response, [CharacterRecord.model_validate(old)], 2)
    assert records[0].candidate_name == "Tumnus"
    assert set(records[0].aliases) == {"Mr. Tumnus", "the Faun", "Faun"}
    assert response.characters[0].aliases == ["Mr. Tumnus"]
    assert next_number == 2


def test_explicit_merge_keeps_names_from_both_old_records() -> None:
    previous = [
        CharacterRecord.model_validate(character(name, cid))
        for name, cid in [
            ("Mara", "char_001"),
            ("the captain", "char_002"),
        ]
    ]
    response = CharacterDiscoveryResponse.model_validate(
        discovery(
            character("Mara", "char_001", merged_ids=["char_002"]),
        )
    )
    records, next_number = validate_characters(response, previous, 3)
    assert records[0].character_id == "char_001"
    assert set(records[0].aliases) == {"Mara", "the captain"}
    assert next_number == 3


def test_correcting_a_wrong_target_preserves_prior_proposals() -> None:
    previous = [
        CharacterRecord.model_validate(value)
        for value in [
            character("Lucy", "char_004", {"char_009": "meets the Faun in the wood"}),
            character("Betty", "char_009"),
            character("the Faun", "char_010"),
        ]
    ]
    response = CharacterDiscoveryResponse.model_validate(
        discovery(
            character("Lucy", "char_004", {"char_010": "meets the Faun in the wood"}),
            character("Betty", "char_009"),
            character("the Faun", "char_010"),
        )
    )
    records, _ = validate_characters(response, previous, 11)
    assert set(records[0].relationships) == {"char_009", "char_010"}


def test_invalid_relationship_reference_is_sent_back_to_llm_before_graph_advances(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara met Susan."], ["Mara is Susan's older sister."]])
    bad = discovery(
        character("Mara", "char_001", {"char_2": "older sister of Susan"}),
        character("Susan", "char_002"),
    )
    corrected = copy.deepcopy(bad)
    corrected["characters"][0]["relationships"] = {"char_002": "older sister of Susan"}
    client, transport = make(
        [
            json.dumps(value)
            for value in [
                discovery(character("Mara"), character("Susan", "new_2")),
                bad,
                corrected,
            ]
        ]
    )
    result = ingest_book(
        "sample",
        client,
        RecordingWriter(),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        run_id="recovery",
    )
    assert result.character_count == 2
    assert len(transport.requests) == 3
    assert "Unknown relationship target: char_2" in transport.requests[2]["messages"][-1]["content"]


def test_repeated_semantic_errors_stop_without_overwriting_last_valid_chapter(
    tmp_path: Path,
) -> None:
    make_extraction(tmp_path, [["Mara met Susan."], ["Mara returned."]])
    bad = discovery(character("Mara", "char_001"))
    client, transport = make(
        [
            json.dumps(value)
            for value in [
                discovery(character("Mara"), character("Susan", "new_2")),
                bad,
                bad,
                bad,
            ]
        ]
    )
    writer = RecordingWriter()
    with pytest.raises(LLMError, match="Lost existing characters"):
        ingest_book(
            "sample",
            client,
            writer,
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            run_id="failed_recovery",
        )
    assert len(transport.requests) == 4
    directory = tmp_path / "ingest/sample/failed_recovery"
    assert len(json.loads((directory / "characters.json").read_text())) == 2
    assert not (directory / "chapters/u02.characters.json").exists()
    assert writer.saved is None
