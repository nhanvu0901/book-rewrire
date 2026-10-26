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
from test_location_ingest import loc_item, loc_response

from pov_retell.ingest.graph.extract_character.model import (
    CharacterRecord,
    LocationRecord,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_scene_map import (
    PROMPT_EXTRACT_SCENE_MAP,
)
from pov_retell.ingest.graph.extract_character.scene_map import (
    extract_scene_map,
    validate_scene_map,
)
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.pipeline import ingest_book


def seg_item(
    start: str,
    end: str,
    *,
    location_id: str | None = "loc_001",
    present_ids: list[str] | None = None,
    mentioned_ids: list[str] | None = None,
    viewpoint_ids: list[str] | None = None,
    relation: str = "continues",
    anchor: str | None = None,
    note: str | None = None,
    label: str = "Scene segment",
) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "location_id": location_id,
        "present_ids": present_ids if present_ids is not None else ["char_001"],
        "mentioned_ids": mentioned_ids or [],
        "viewpoint_ids": viewpoint_ids if viewpoint_ids is not None else ["char_001"],
        "time": {
            "relation": relation,
            "anchor": anchor,
            "note": note,
        },
        "label": label,
    }


def scene_response(*segments: dict[str, Any]) -> dict[str, Any]:
    return {"segments": list(segments)}


def test_one_scene_map_call_per_chapter_after_location_step_and_saves_segments(
    tmp_path: Path,
) -> None:
    make_extraction(
        tmp_path,
        [
            [
                "Mara and Jo waited at the stone gate.",
                "Rafe marched toward the eastern ridge.",
            ],
            [
                "While Rafe marched, Mara and Jo entered the hilltop camp.",
                "Jo went into the tent while Mara spoke with Eli on the ridge.",
            ],
        ],
    )
    llm = ScriptedLLM(
        [
            extraction(
                character("Mara", "new_1"),
                character("Jo", "new_2"),
                character("Rafe", "new_3"),
            ),
            loc_response(
                loc_item("new_1", "the stone gate", kind="stone gate"),
                loc_item("new_2", "the eastern ridge", kind="rocky ridge"),
            ),
            scene_response(
                seg_item(
                    "u01_p001",
                    "u01_p001",
                    location_id="loc_001",
                    present_ids=["char_001", "char_002"],
                    viewpoint_ids=["char_001"],
                    relation="continues",
                    label="Mara and Jo wait at the stone gate",
                ),
                seg_item(
                    "u01_p002",
                    "u01_p002",
                    location_id="loc_002",
                    present_ids=["char_003"],
                    viewpoint_ids=["char_003"],
                    relation="later",
                    label="Rafe marches toward the eastern ridge",
                ),
            ),
            extraction(
                character("Mara", "char_001"),
                character("Jo", "char_002"),
                character("Eli", "new_1"),
            ),
            loc_response(
                loc_item("new_1", "the hilltop camp", kind="walled camp"),
                loc_item("new_2", "the tent", kind="canvas tent", part_of="new_1"),
            ),
            scene_response(
                seg_item(
                    "u02_p001",
                    "u02_p001",
                    location_id="loc_003",
                    present_ids=["char_001", "char_002"],
                    mentioned_ids=["char_003"],
                    viewpoint_ids=["char_001", "char_002"],
                    relation="parallel",
                    anchor="u01_p002",
                    note="while Rafe marched",
                    label="Mara and Jo enter the hilltop camp",
                ),
                seg_item(
                    "u02_p002",
                    "u02_p002",
                    location_id="loc_002",
                    present_ids=["char_001", "char_004"],
                    mentioned_ids=["char_002"],
                    viewpoint_ids=["char_001"],
                    relation="continues",
                    label="Mara speaks privately with Eli on the ridge",
                ),
            ),
        ]
    )
    steps: list[str] = []
    result = ingest_book(
        "sample",
        llm,
        RecordingWriter(),
        summary_llm=summary_client(2),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        on_step=steps.append,
    )
    assert [s for s, _ in llm.calls] == [
        "ExtractCharacterResponse",
        "ExtractRelationshipResponse",
        "ExtractLocationResponse",
        "SceneMapResponse",
        "ExtractCharacterResponse",
        "ExtractRelationshipResponse",
        "ExtractLocationResponse",
        "SceneMapResponse",
    ]
    assert steps.index("validate_locations u01") < steps.index("extract_scenes u01")
    assert steps.index("validate_scenes u01") < steps.index(
        "save_characters_json u01: 3 characters"
    )

    ch2_scene_prompt = [p for s, p in llm.calls if s == "SceneMapResponse"][1]
    assert "Current chapter: u02" in ch2_scene_prompt
    locs_in_prompt = json.loads(
        ch2_scene_prompt.split("<locations_json>\n")[1].split("\n</locations_json>")[0]
    )
    assert [loc["location_id"] for loc in locs_in_prompt] == [
        "loc_001",
        "loc_002",
        "loc_003",
        "loc_004",
    ]

    run_dir = result.characters_file.parent
    u02_scenes = json.loads((run_dir / "chapters/u02.scenes.json").read_text())
    assert u02_scenes == [
        {
            "segment_id": "u02_s1",
            "start": "u02_p001",
            "end": "u02_p001",
            "location_id": "loc_003",
            "present_ids": ["char_001", "char_002"],
            "mentioned_ids": ["char_003"],
            "viewpoint_ids": ["char_001", "char_002"],
            "time": {
                "relation": "parallel",
                "anchor": "u01_p002",
                "note": "while Rafe marched",
            },
            "label": "Mara and Jo enter the hilltop camp",
        },
        {
            "segment_id": "u02_s2",
            "start": "u02_p002",
            "end": "u02_p002",
            "location_id": "loc_002",
            "present_ids": ["char_001", "char_004"],
            "mentioned_ids": ["char_002"],
            "viewpoint_ids": ["char_001"],
            "time": {
                "relation": "continues",
                "anchor": None,
                "note": None,
            },
            "label": "Mara speaks privately with Eli on the ridge",
        },
    ]
    u02_proposed = json.loads((run_dir / "chapters/u02.scenes.proposed.json").read_text())
    assert "segment_id" not in u02_proposed["segments"][0]


@pytest.mark.parametrize(
    ("bad_payload", "expected_error"),
    [
        (
            scene_response(
                seg_item("u02_p001", "u02_p001"),
                seg_item("u02_p003", "u02_p003"),
            ),
            "Segment gap before paragraph u02_p003 (expected u02_p002)",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p002"),
            ),
            "Segment gap at end of chapter u02: missing u02_p003..u02_p003",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p002"),
                seg_item("u02_p002", "u02_p003"),
            ),
            "Segment overlap at paragraph u02_p002 (expected u02_p003)",
        ),
        (
            scene_response(
                seg_item("u02_p002", "u02_p001"),
                seg_item("u02_p002", "u02_p003"),
            ),
            "Segment start must not come after end: u02_p002 > u02_p001",
        ),
        (
            scene_response(
                seg_item("u01_p001", "u02_p003"),
            ),
            "Segment paragraph ID does not belong to chapter u02: u01_p001",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", present_ids=["char_999"], viewpoint_ids=[]),
            ),
            "Unknown character_id in scene segment: char_999",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", location_id="loc_999"),
            ),
            "Unknown location_id in scene segment: loc_999",
        ),
        (
            scene_response(
                seg_item(
                    "u02_p001",
                    "u02_p003",
                    present_ids=["char_001"],
                    viewpoint_ids=["char_002"],
                ),
            ),
            "viewpoint_ids must be a subset of present_ids; not present: char_002",
        ),
        (
            scene_response(
                seg_item(
                    "u02_p001",
                    "u02_p003",
                    present_ids=["char_001"],
                    mentioned_ids=["char_001"],
                ),
            ),
            "present_ids and mentioned_ids must not overlap: char_001",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", relation="simultaneous"),
            ),
            "continues",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", relation="parallel", anchor=None),
            ),
            "Time relation 'parallel' requires an anchor paragraph ID",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", relation="continues", anchor="u01_p001"),
            ),
            "Time relation 'continues' must have anchor=null",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", relation="flashback", anchor="u02_p002"),
            ),
            "Time anchor u02_p002 must come before segment start u02_p001",
        ),
        (
            scene_response(
                seg_item("u02_p001", "u02_p003", relation="flashback", anchor="u99_p001"),
            ),
            "Time anchor paragraph ID does not exist at or before chapter u02: u99_p001",
        ),
        (
            scene_response(
                seg_item(
                    "u02_p001",
                    "u02_p003",
                    label=" ".join(["word"] * 16),
                ),
            ),
            "Segment label must have at most 15 words",
        ),
        (
            scene_response(
                seg_item(
                    "u02_p001",
                    "u02_p003",
                    note="one two three four five six seven eight nine",
                ),
            ),
            "Segment time note must have at most 8 words",
        ),
    ],
)
def test_scene_map_validation_rules_reject_and_retry_with_reason(
    bad_payload: dict[str, Any],
    expected_error: str,
) -> None:
    ch1 = Chapter(
        unit_id="u01",
        text="[u01_p001] Earlier chapter.",
        paragraphs={"u01_p001": "Earlier chapter."},
    )
    ch2 = Chapter(
        unit_id="u02",
        text="[u02_p001] First.\n\n[u02_p002] Second.\n\n[u02_p003] Third.",
        paragraphs={
            "u02_p001": "First.",
            "u02_p002": "Second.",
            "u02_p003": "Third.",
        },
    )
    characters = [
        CharacterRecord(character_id="char_001", candidate_name="Mara"),
        CharacterRecord(character_id="char_002", candidate_name="Jo"),
    ]
    locations = [
        LocationRecord(location_id="loc_001", name="the gate", kind="stone gate"),
    ]
    valid_payload = scene_response(
        seg_item(
            "u02_p001",
            "u02_p003",
            location_id="loc_001",
            present_ids=["char_001", "char_002"],
            viewpoint_ids=["char_001"],
            relation="parallel",
            anchor="u01_p001",
            note="earlier that morning",
            label="Mara and Jo wait at the gate",
        )
    )
    llm, transport = make([json.dumps(bad_payload), json.dumps(valid_payload)])
    response = extract_scene_map(
        llm,
        "The Gate",
        ch2,
        [ch1, ch2],
        characters,
        locations,
        {},
        "WHO IS WHO\nMara | - | traveler",
    )
    assert len(transport.requests) == 2
    retry_prompt = transport.requests[1]["messages"][-1]["content"]
    assert "Rejected:" in retry_prompt and expected_error in retry_prompt
    records = validate_scene_map(response, ch2, [ch1, ch2], characters, locations, {})
    assert len(records) == 1
    assert records[0].segment_id == "u02_s1"
    assert records[0].time.anchor == "u01_p001"


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
        "Cair",
        "Paravel",
    ],
)
def test_extract_scene_map_prompt_is_book_agnostic(forbidden_word: str) -> None:
    assert (
        re.search(rf"\b{re.escape(forbidden_word)}\b", PROMPT_EXTRACT_SCENE_MAP, re.IGNORECASE)
        is None
    )
