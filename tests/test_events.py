"""Events, utterances and claims per chapter (T-0016)."""

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
    summary_cards,
    summary_client,
)
from test_llm import make

from pov_retell.ingest.graph.extract_story.steps.characters.model import CharacterRecord
from pov_retell.ingest.graph.extract_story.steps.events.logic import extract_events, validate_events
from pov_retell.ingest.graph.extract_story.steps.events.model import (
    ClaimRecord,
    ExtractEventResponse,
)
from pov_retell.ingest.graph.extract_story.steps.events.prompt import PROMPT_EXTRACT_EVENTS
from pov_retell.ingest.graph.extract_story.steps.scenes.model import SceneSegmentRecord, SceneTime
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.pipeline import ingest_book

DOOR = "Mara found the tower door forced open."
ACCUSE = '"Jo took the key, I am sure of it," Mara told Jo.'


def segment(start: str, end: str, present: list[str], location_id: str | None = None) -> Any:
    return {
        "start": start,
        "end": end,
        "location_id": location_id,
        "present_ids": present,
        "mentioned_ids": [],
        "viewpoint_ids": [],
        "time": {"relation": "continues", "anchor": None, "note": None},
        "label": "At the tower",
    }


def claim(key: str, statement: str, about: list[str], truth: str = "unknown") -> Any:
    return {"key": key, "statement": statement, "about_ids": about, "truth": truth}


def event(segment_id: str, summary: str, who: list[str], pids: list[str], claims: list[str]) -> Any:
    return {
        "segment_id": segment_id,
        "summary": summary,
        "participant_ids": who,
        "paragraph_ids": pids,
        "claim_ids": claims,
    }


def utterance(
    segment_id: str,
    speaker: str | None,
    to: list[str],
    quote: str,
    pids: list[str],
    claims: list[str],
    mode: str = "spoken",
) -> Any:
    return {
        "segment_id": segment_id,
        "mode": mode,
        "speaker_id": speaker,
        "addressee_ids": to,
        "quote": quote,
        "paragraph_ids": pids,
        "claim_ids": claims,
    }


def answer(
    claims: list[Any] | None = None,
    events: list[Any] | None = None,
    utterances: list[Any] | None = None,
    truth_changes: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "claims": claims or [],
        "events": events or [],
        "utterances": utterances or [],
        "truth_changes": truth_changes or [],
    }


CHAPTER_ONE_EVENTS = answer(
    claims=[
        claim("new_1", "Jo stole the key from the tower", ["char_002"]),
        claim("new_2", "The tower door was forced open", [], "true"),
    ],
    events=[
        event(
            "u01_s1", "Mara finds the tower door forced open", ["char_001"], ["u01_p001"], ["new_2"]
        )
    ],
    utterances=[
        utterance(
            "u01_s1",
            "char_001",
            ["char_002"],
            "Jo took the key, I am sure of it",
            ["u01_p002"],
            ["new_1"],
        )
    ],
)


def run(tmp_path: Path, responses: list[Any], chapters: int = 2) -> tuple[Any, Any, Any]:
    llm = ScriptedLLM(responses, cards=summary_cards(chapters))
    writer = RecordingWriter()
    result = ingest_book(
        "sample",
        llm,
        writer,
        summary_llm=summary_client(chapters),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        run_id="run_events",
    )
    return result, llm, writer


def test_events_run_after_the_scene_map_and_claims_resolve_later(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[DOOR, ACCUSE], ["The guard admitted he had taken the key."]])
    result, llm, writer = run(
        tmp_path,
        [
            extraction(character("Mara"), character("Jo", "new_2")),
            {"segments": [segment("u01_p001", "u01_p002", ["char_001", "char_002"])]},
            CHAPTER_ONE_EVENTS,
            extraction(),
            answer(
                truth_changes=[
                    {"claim_id": "claim_001", "truth": "false", "paragraph_ids": ["u02_p001"]}
                ]
            ),
        ],
    )
    names = [name for name, _ in llm.calls]
    assert names.count("ExtractEventResponse") == 2
    assert names.index("ExtractEventResponse") == names.index("SceneMapResponse") + 1
    first_prompt = next(p for n, p in llm.calls if n == "ExtractEventResponse")
    assert '"segment_id": "u01_s1"' in first_prompt and "[u01_p002]" in first_prompt
    second_prompt = [p for n, p in llm.calls if n == "ExtractEventResponse"][1]
    assert (
        "claim_001 | unknown | Jo stole the key from the tower (about: char_002)" in second_prompt
    )

    run_dir = result.characters_file.parent
    claims = json.loads((run_dir / "claims.json").read_text())
    assert [(c["claim_id"], c["truth"]) for c in claims] == [
        ("claim_001", "false"),
        ("claim_002", "true"),
    ]
    assert claims[0]["truth_chapter_id"] == "u02"
    assert claims[0]["truth_paragraph_ids"] == ["u02_p001"]
    events = json.loads((run_dir / "events.json").read_text())
    assert events == [
        {
            "event_id": "u01_e1",
            "segment_id": "u01_s1",
            "location_id": None,
            "summary": "Mara finds the tower door forced open",
            "participant_ids": ["char_001"],
            "paragraph_ids": ["u01_p001"],
            "claim_ids": ["claim_002"],
        }
    ]
    utterances = json.loads((run_dir / "utterances.json").read_text())
    assert utterances[0]["utterance_id"] == "u01_q1"
    assert utterances[0]["claim_ids"] == ["claim_001"]
    u02 = json.loads((run_dir / "chapters/u02.events.json").read_text())
    assert [c["claim_id"] for c in u02["claims"]] == ["claim_001"]
    assert (run_dir / "chapters/u01.events.proposed.json").exists()

    last = writer.snapshots[-1]
    assert [c["claim_id"] for c in last["claims"]] == ["claim_001", "claim_002"]
    assert last["events"][0]["chapter_id"] == "u01" and last["events"][0]["order"] == 1
    assert last["utterances"][0]["speaker_id"] == "char_001"


def test_merged_characters_are_rewritten_in_events_utterances_and_claims(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[DOOR, ACCUSE], ["Mara was Jo all along."]])
    _, _, writer = run(
        tmp_path,
        [
            extraction(character("Mara"), character("Jo", "new_2")),
            {"segments": [segment("u01_p001", "u01_p002", ["char_001", "char_002"])]},
            CHAPTER_ONE_EVENTS,
            extraction(character("Mara", "char_001", merges=["char_002"])),
        ],
    )
    last = writer.snapshots[-1]
    assert last["claims"][0]["about_ids"] == ["char_001"]
    assert last["utterances"][0]["speaker_id"] == "char_001"
    assert last["utterances"][0]["addressee_ids"] == []


CHAPTER = Chapter(
    unit_id="u03",
    text="",
    paragraphs={
        "u03_p001": DOOR,
        "u03_p002": ACCUSE,
        "u03_p003": "Later, alone, Jo wrote: the key is safe.",
    },
)
SEGMENTS = [
    SceneSegmentRecord(
        segment_id="u03_s1",
        start="u03_p001",
        end="u03_p002",
        location_id="loc_001",
        present_ids=["char_001", "char_002"],
        time=SceneTime(relation="continues"),
        label="At the tower",
    ),
    SceneSegmentRecord(
        segment_id="u03_s2",
        start="u03_p003",
        end="u03_p003",
        present_ids=["char_002"],
        time=SceneTime(relation="later"),
        label="Jo alone",
    ),
]
CHARACTERS = [
    CharacterRecord(character_id="char_001", candidate_name="Mara"),
    CharacterRecord(character_id="char_002", candidate_name="Jo"),
    CharacterRecord(character_id="char_003", candidate_name="Evan"),
]
EXISTING = [
    ClaimRecord(
        claim_id="claim_001",
        statement="The key is in the tower",
        truth="unknown",
        first_chapter_id="u01",
    )
]
GOOD_UTTERANCE = utterance(
    "u03_s1", "char_001", ["char_002"], "Jo took the key", ["u03_p002"], ["new_1"]
)
NEW_CLAIM = claim("new_1", "Jo took the key", ["char_002"])


def check(response: dict[str, Any]) -> Any:
    return validate_events(
        ExtractEventResponse.model_validate(response),
        CHAPTER,
        SEGMENTS,
        CHARACTERS,
        {"char_009": "char_002"},
        EXISTING,
        2,
    )


def test_a_valid_answer_gets_ids_location_and_redirects() -> None:
    chapter_events, claims, next_number = check(
        answer(
            claims=[NEW_CLAIM],
            events=[
                event(
                    "u03_s1",
                    "Mara sees the door",
                    ["char_001", "char_009"],
                    ["u03_p001"],
                    ["claim_001"],
                )
            ],
            utterances=[
                GOOD_UTTERANCE,
                utterance(
                    "u03_s2",
                    "char_002",
                    ["char_003"],
                    "the key is safe",
                    ["u03_p003"],
                    ["claim_001"],
                    "written",
                ),
            ],
        )
    )
    assert next_number == 3
    assert [c.claim_id for c in claims] == ["claim_001", "claim_002"]
    assert chapter_events.events[0].event_id == "u03_e1"
    assert chapter_events.events[0].location_id == "loc_001"
    assert chapter_events.events[0].participant_ids == ["char_001", "char_002"]
    assert [u.utterance_id for u in chapter_events.utterances] == ["u03_q1", "u03_q2"]
    assert chapter_events.utterances[0].claim_ids == ["claim_002"]


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (answer(events=[event("u03_s9", "x", [], ["u03_p001"], [])]), "is not a segment of u03"),
        (answer(events=[event("u03_s1", "x", [], ["u03_p003"], [])]), "outside segment u03_s1"),
        (answer(events=[event("u03_s1", "x", [], [], [])]), "paragraph_ids must not be empty"),
        (answer(events=[event("u03_s2", "x", ["char_001"], ["u03_p003"], [])]), "not present"),
        (
            answer(events=[event("u03_s1", "x", ["char_404"], ["u03_p001"], [])]),
            "Unknown character",
        ),
        (answer(events=[event("u03_s1", "word " * 21, [], ["u03_p001"], [])]), "at most 20 words"),
        (
            answer(events=[event("u03_s1", "x", [], ["u03_p001"], ["claim_404"])]),
            "Unknown claim ID",
        ),
        (
            answer(claims=[NEW_CLAIM], utterances=[{**GOOD_UTTERANCE, "speaker_id": None}]),
            "needs a speaker_id",
        ),
        (
            answer(
                claims=[NEW_CLAIM],
                utterances=[
                    {
                        **GOOD_UTTERANCE,
                        "segment_id": "u03_s2",
                        "paragraph_ids": ["u03_p003"],
                        "quote": "the key is safe",
                    }
                ],
            ),
            "char_001 is not present",
        ),
        (
            answer(
                claims=[NEW_CLAIM], utterances=[{**GOOD_UTTERANCE, "addressee_ids": ["char_001"]}]
            ),
            "cannot also be an addressee",
        ),
        (
            answer(claims=[NEW_CLAIM], utterances=[{**GOOD_UTTERANCE, "quote": "Jo hid the key"}]),
            "was not found in its paragraphs",
        ),
        (
            answer(claims=[NEW_CLAIM], utterances=[{**GOOD_UTTERANCE, "quote": "key " * 41}]),
            "at most 40 words",
        ),
        (answer(utterances=[{**GOOD_UTTERANCE, "claim_ids": []}]), "at least one claim"),
        (answer(claims=[{**NEW_CLAIM, "key": "c1"}]), "must look like new_1"),
        (answer(claims=[NEW_CLAIM, NEW_CLAIM]), "used twice"),
        (answer(claims=[{**NEW_CLAIM, "statement": "word " * 26}]), "at most 25 words"),
        (
            answer(claims=[{**NEW_CLAIM, "statement": "the KEY is in the tower"}]),
            "already exists: use claim_001",
        ),
        (answer(claims=[NEW_CLAIM]), "new_1 is not linked"),
        (
            answer(
                truth_changes=[
                    {"claim_id": "claim_404", "truth": "true", "paragraph_ids": ["u03_p001"]}
                ]
            ),
            "Unknown claim ID in truth_changes",
        ),
        (
            answer(
                claims=[NEW_CLAIM],
                utterances=[GOOD_UTTERANCE],
                truth_changes=[
                    {"claim_id": "new_1", "truth": "true", "paragraph_ids": ["u03_p001"]}
                ],
            ),
            "directly",
        ),
        (
            answer(
                truth_changes=[
                    {"claim_id": "claim_001", "truth": "true", "paragraph_ids": ["u03_p001"]},
                    {"claim_id": "claim_001", "truth": "false", "paragraph_ids": ["u03_p001"]},
                ]
            ),
            "changed twice",
        ),
        (
            answer(
                truth_changes=[
                    {"claim_id": "claim_001", "truth": "true", "paragraph_ids": ["u02_p001"]}
                ]
            ),
            "does not belong to u03",
        ),
    ],
)
def test_invalid_answers_are_rejected_with_a_reason(bad: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValueError, match=re.escape(reason)):
        check(bad)


def test_a_truth_change_that_changes_nothing_is_rejected() -> None:
    resolved = [EXISTING[0].model_copy(update={"truth": "true"})]
    with pytest.raises(ValueError, match="already true"):
        validate_events(
            ExtractEventResponse.model_validate(
                answer(
                    truth_changes=[
                        {"claim_id": "claim_001", "truth": "true", "paragraph_ids": ["u03_p001"]}
                    ]
                )
            ),
            CHAPTER,
            SEGMENTS,
            CHARACTERS,
            {},
            resolved,
            2,
        )


def test_a_rejected_answer_is_retried_with_the_reason() -> None:
    bad = answer(claims=[NEW_CLAIM], utterances=[{**GOOD_UTTERANCE, "quote": "Jo hid the key"}])
    good = answer(claims=[NEW_CLAIM], utterances=[GOOD_UTTERANCE])
    client, transport = make([json.dumps(bad), json.dumps(good)])
    response = extract_events(
        client, "The Gate", CHAPTER, SEGMENTS, CHARACTERS, EXISTING, 2, {}, ""
    )
    assert response.utterances[0].quote == "Jo took the key"
    retry = transport.requests[1]["messages"][-1]["content"]
    assert "Rejected:" in retry and "was not found in its paragraphs" in retry


@pytest.mark.parametrize(
    "forbidden_word",
    ["Narnia", "Aslan", "Edmund", "Lucy", "Witch", "Harry", "Hogwarts", "Snape", "Quirrell"],
)
def test_extract_events_prompt_is_book_agnostic(forbidden_word: str) -> None:
    assert re.search(rf"\b{forbidden_word}\b", PROMPT_EXTRACT_EVENTS, re.IGNORECASE) is None
