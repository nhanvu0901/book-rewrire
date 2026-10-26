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
    summary_client,
)
from test_llm import make

from pov_retell.ingest.graph.extract_character.location import (
    extract_locations,
    validate_locations,
)
from pov_retell.ingest.graph.extract_character.model import (
    ExtractLocationResponse,
    LocationRecord,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_location import (
    PROMPT_EXTRACT_LOCATION,
)
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.pipeline import ingest_book


def loc_item(
    location_id: str,
    name: str,
    *,
    aliases: list[str] | None = None,
    kind: str | None = None,
    part_of: str | None = None,
) -> dict[str, Any]:
    return {
        "location_id": location_id,
        "name": name,
        "aliases": aliases or [],
        "kind": kind,
        "part_of": part_of,
    }


def loc_response(*locations: dict[str, Any]) -> dict[str, Any]:
    return {"locations": list(locations)}


def test_one_location_call_per_chapter_assigns_ids_reuses_existing_and_saves_files(
    tmp_path: Path,
) -> None:
    make_extraction(
        tmp_path,
        [
            ["Mara arrived at the old house and climbed to the spare room."],
            ["The old house was called Oak Manor. Mara entered the wardrobe hall."],
            ["Mara rested in Oak Manor."],
        ],
    )
    summaries = ScriptedLLM(
        [
            "SUMMARY_CH1",
            "Mara | - | traveler",
            "the old house | - | WHERE_CH1\nthe spare room | - | upstairs room in the old house",
            "SUMMARY_CH2",
            "Mara | - | traveler",
            "Oak Manor | the old house | WHERE_CH2\n"
            "the spare room | - | upstairs room in Oak Manor\n"
            "wardrobe hall | - | hall in Oak Manor",
            "SUMMARY_CH3",
            "Mara | - | traveler",
            "Oak Manor | the old house | WHERE_CH3\n"
            "the spare room | - | upstairs room in Oak Manor\n"
            "wardrobe hall | - | hall in Oak Manor",
            "CORE_MEMORY",
        ]
    )
    llm = ScriptedLLM(
        [
            extraction(character("Mara", "new_1")),
            loc_response(
                loc_item(
                    "new_1",
                    "the old house",
                    aliases=["the country house"],
                    kind="large stone country house",
                ),
                loc_item(
                    "new_2",
                    "the spare room",
                    kind="upstairs room",
                    part_of="new_1",
                ),
            ),
            extraction(character("Mara", "char_001")),
            loc_response(
                loc_item(
                    "loc_001",
                    "Oak Manor",
                    aliases=["the manor"],
                    kind=None,
                    part_of=None,
                ),
                loc_item(
                    "new_1",
                    "the wardrobe hall",
                    kind="long hall on the upper floor",
                    part_of="loc_001",
                ),
            ),
            extraction(character("Mara", "char_001")),
            loc_response(),
        ]
    )
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
        if schema_name in {"ExtractCharacterResponse", "ExtractLocationResponse"}
    ] == [
        "ExtractCharacterResponse",
        "ExtractLocationResponse",
        "ExtractCharacterResponse",
        "ExtractLocationResponse",
        "ExtractCharacterResponse",
        "ExtractLocationResponse",
    ]
    assert steps.index("validate_relationships u01") < steps.index("extract_locations u01")
    assert steps.index("validate_locations u01") < steps.index(
        "save_characters_json u01: 1 characters"
    )

    # Check Chapter 2 location prompt markers:
    ch2_loc_prompt = [p for s, p in llm.calls if s == "ExtractLocationResponse"][1]
    assert "Current chapter: u02" in ch2_loc_prompt
    assert "WHERE_CH1" in ch2_loc_prompt
    assert "WHERE_CH2" not in ch2_loc_prompt
    assert "[u01]\nSUMMARY_CH1" in ch2_loc_prompt
    assert "SUMMARY_CH2" not in ch2_loc_prompt
    existing_locs = json.loads(
        ch2_loc_prompt.split("<existing_locations_json>\n")[1].split(
            "\n</existing_locations_json>"
        )[0]
    )
    assert existing_locs == [
        {
            "location_id": "loc_001",
            "name": "the old house",
            "aliases": ["the country house"],
            "kind": "large stone country house",
            "part_of": None,
        },
        {
            "location_id": "loc_002",
            "name": "the spare room",
            "aliases": [],
            "kind": "upstairs room",
            "part_of": "loc_001",
        },
    ]

    run_dir = result.characters_file.parent
    final_locations = json.loads((run_dir / "locations.json").read_text())
    assert final_locations == [
        {
            "location_id": "loc_001",
            "name": "Oak Manor",
            "aliases": ["the country house", "the old house", "the manor"],
            "kind": "large stone country house",
            "part_of": None,
        },
        {
            "location_id": "loc_002",
            "name": "the spare room",
            "aliases": [],
            "kind": "upstairs room",
            "part_of": "loc_001",
        },
        {
            "location_id": "loc_003",
            "name": "the wardrobe hall",
            "aliases": [],
            "kind": "long hall on the upper floor",
            "part_of": "loc_001",
        },
    ]
    assert json.loads((run_dir / "chapters/u01.locations.json").read_text()) == existing_locs
    assert json.loads((run_dir / "chapters/u02.locations.json").read_text()) == final_locations
    assert json.loads((run_dir / "chapters/u03.locations.json").read_text()) == final_locations
    assert json.loads((run_dir / "chapters/u02.locations.proposed.json").read_text()) == {
        "locations": [
            {
                "location_id": "loc_001",
                "name": "Oak Manor",
                "aliases": ["the manor"],
                "kind": None,
                "part_of": None,
            },
            {
                "location_id": "new_1",
                "name": "the wardrobe hall",
                "aliases": [],
                "kind": "long hall on the upper floor",
                "part_of": "loc_001",
            },
        ]
    }


@pytest.mark.parametrize(
    ("bad_payload", "expected_error"),
    [
        (
            loc_response(loc_item("new_0", "the gate", kind="stone gate")),
            "Invalid new location_id format: new_0",
        ),
        (
            loc_response(loc_item("loc_999", "the gate", kind="stone gate")),
            "Unknown location_id: loc_999",
        ),
        (
            loc_response(
                loc_item("loc_001", "the gate", kind="stone gate"),
                loc_item("loc_001", "the gate", aliases=["north gate"]),
            ),
            "Duplicate location_id in response: loc_001",
        ),
        (
            loc_response(
                loc_item("new_1", "the hall", kind="great hall", part_of="loc_999"),
            ),
            "Unknown part_of location_id: loc_999",
        ),
        (
            loc_response(
                loc_item("new_1", "the hall", kind="great hall", part_of="new_2"),
            ),
            "Unknown part_of location_id: new_2",
        ),
        (
            loc_response(
                loc_item("new_1", "the hall", kind="great hall", part_of="new_1"),
            ),
            "Location cannot be part_of itself: new_1",
        ),
        (
            loc_response(
                loc_item("loc_001", "the castle", part_of="loc_002"),
            ),
            "Location part_of cycle detected involving loc_001",
        ),
        (
            loc_response(
                loc_item("new_1", "outer ward", part_of="new_2"),
                loc_item("new_2", "inner ward", part_of="new_1"),
            ),
            "Location part_of cycle detected involving loc_003",
        ),
    ],
)
def test_location_validation_rules_reject_and_retry_with_reason(
    bad_payload: dict[str, Any],
    expected_error: str,
) -> None:
    chapter = Chapter(
        unit_id="u02",
        text="[u02_p001] Mara entered the great hall inside the castle.",
        paragraphs={"u02_p001": "Mara entered the great hall inside the castle."},
    )
    existing = [
        LocationRecord(
            location_id="loc_001",
            name="the castle",
            aliases=[],
            kind="stone fortress",
            part_of=None,
        ),
        LocationRecord(
            location_id="loc_002",
            name="the courtyard",
            aliases=[],
            kind="walled courtyard",
            part_of="loc_001",
        ),
    ]
    valid_payload = loc_response(
        loc_item("new_1", "the great hall", kind="vaulted stone hall", part_of="loc_001")
    )
    llm, transport = make([json.dumps(bad_payload), json.dumps(valid_payload)])
    response = extract_locations(
        llm,
        "The Gate",
        chapter,
        existing,
        3,
        "WHERE IS WHERE\nthe castle | - | stone fortress",
    )
    assert len(transport.requests) == 2
    retry_prompt = transport.requests[1]["messages"][-1]["content"]
    assert f"Rejected: {expected_error}" in retry_prompt
    records, next_num = validate_locations(response, existing, 3)
    assert next_num == 4
    assert records[-1].location_id == "loc_003"
    assert records[-1].part_of == "loc_001"


@pytest.mark.parametrize("reverse", [False, True])
def test_new_location_cannot_reference_an_unseen_permanent_id(reverse: bool) -> None:
    locations = [
        loc_item("new_1", "Harbor Depot"),
        loc_item("new_2", "Loading Bay", part_of="loc_001"),
    ]
    if reverse:
        locations.reverse()

    response = ExtractLocationResponse.model_validate(loc_response(*locations))

    with pytest.raises(ValueError, match="Unknown part_of location_id: loc_001"):
        validate_locations(response, [], 1)


def test_new_location_can_forward_reference_a_local_new_id() -> None:
    response = ExtractLocationResponse.model_validate(
        loc_response(
            loc_item("new_1", "Loading Bay", part_of="new_2"),
            loc_item("new_2", "Harbor Depot"),
        )
    )

    records, next_number = validate_locations(response, [], 1)

    assert next_number == 3
    assert records[0].part_of == "loc_002"
    assert records[1].part_of is None


def test_seventeen_chapters_complete_with_location_step(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[f"Mara waited at the gate on day {day}."] for day in range(1, 18)])
    result = ingest_book(
        "sample",
        ScriptedLLM(
            [
                extraction(character("Mara", "new_1" if day == 1 else "char_001"))
                for day in range(1, 18)
            ]
        ),
        RecordingWriter(),
        summary_llm=summary_client(17),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
    )
    assert (result.characters_file.parent / "chapters/u17.locations.json").exists()
    assert (result.characters_file.parent / "locations.json").exists()


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
        "satyr",
        "centaur",
        "Eve",
        "Adam",
        "Silenus",
        "wardrobe",
        "lamp",
        "spare room",
        "hilltop",
        "Stone Table",
        "pavilion",
        "Professor",
        "Cair",
        "Paravel",
    ],
)
def test_extract_location_prompt_is_book_agnostic(forbidden_word: str) -> None:
    assert (
        re.search(rf"\b{re.escape(forbidden_word)}\b", PROMPT_EXTRACT_LOCATION, re.IGNORECASE)
        is None
    )
