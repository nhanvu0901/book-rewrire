"""Knowledge acquisition and the knowledge timeline (T-0017)."""

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
from test_events import ACCUSE, DOOR, answer, claim, event, segment, utterance
from test_llm import make, settings
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.ingest.graph.extract_character.knowledge import (
    extract_knowledge,
    validate_knowledge,
)
from pov_retell.ingest.graph.extract_character.model import (
    ChapterEvents,
    CharacterRecord,
    ClaimRecord,
    EventRecord,
    ExtractKnowledgeResponse,
    KnowledgeRecord,
    SceneSegmentRecord,
    SceneTime,
    UtteranceRecord,
)
from pov_retell.ingest.graph.extract_character.prompt.extract_knowledge import (
    PROMPT_EXTRACT_KNOWLEDGE,
)
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.pipeline import ingest_book
from pov_retell.ingest.timeline import format_knowledge, knowledge_at, latest_run


def acquire(
    who: str,
    claim_id: str,
    channel: str,
    stance: str,
    segment_id: str,
    source: str | None,
    pids: list[str],
) -> dict[str, Any]:
    return {
        "character_id": who,
        "claim_id": claim_id,
        "channel": channel,
        "stance": stance,
        "segment_id": segment_id,
        "source_id": source,
        "paragraph_ids": pids,
    }


def knows(claims: list[Any] | None = None, acquisitions: list[Any] | None = None) -> Any:
    return {"claims": claims or [], "acquisitions": acquisitions or []}


STORY = [
    extraction(character("Mara"), character("Jo", "new_2"), character("Evan", "new_3")),
    {"segments": [segment("u01_p001", "u01_p002", ["char_001", "char_002", "char_003"])]},
    answer(
        claims=[
            claim("new_1", "Jo stole the key from the tower", ["char_002"]),
            claim("new_2", "The tower door was forced open", [], "true"),
        ],
        events=[
            event("u01_s1", "Mara finds the door forced", ["char_001"], ["u01_p001"], ["new_2"])
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
    ),
    knows(
        claims=[claim("new_1", "Jo wants the key for herself", ["char_002"])],
        acquisitions=[
            acquire(
                "char_001", "claim_002", "witnessed", "believes", "u01_s1", "u01_e1", ["u01_p001"]
            ),
            acquire(
                "char_002", "claim_001", "told", "disbelieves", "u01_s1", "u01_q1", ["u01_p002"]
            ),
            acquire(
                "char_003", "claim_001", "overheard", "believes", "u01_s1", "u01_q1", ["u01_p002"]
            ),
            acquire("char_001", "new_1", "inferred", "believes", "u01_s1", None, ["u01_p002"]),
            # Evan already believes it: a repeat adds nothing and is dropped.
            acquire("char_003", "claim_001", "inferred", "believes", "u01_s1", None, ["u01_p002"]),
        ],
    ),
    extraction(),
    {"segments": [segment("u02_p001", "u02_p001", ["char_001", "char_003"])]},
    answer(
        truth_changes=[{"claim_id": "claim_001", "truth": "false", "paragraph_ids": ["u02_p001"]}]
    ),
    knows(
        claims=[claim("new_1", "The guard took the key", [])],
        acquisitions=[
            acquire(
                "char_003", "claim_001", "learns_truth", "disbelieves", "u02_s1", None, ["u02_p001"]
            ),
            acquire("char_002", "new_1", "prior", "believes", "u02_s1", None, ["u02_p001"]),
        ],
    ),
]


def run_story(tmp_path: Path) -> tuple[Path, ScriptedLLM, RecordingWriter]:
    make_extraction(tmp_path, [[DOOR, ACCUSE], ["The guard admitted he had taken the key."]])
    llm = ScriptedLLM(STORY, cards=summary_cards(2))
    writer = RecordingWriter()
    result = ingest_book(
        "sample",
        llm,
        writer,
        summary_llm=summary_client(2),
        extracted_dir=tmp_path / "extracted",
        ingest_dir=tmp_path / "ingest",
        run_id="run_knowledge",
    )
    return result.characters_file.parent, llm, writer


def test_knowledge_runs_after_events_and_is_saved(tmp_path: Path) -> None:
    run_dir, llm, writer = run_story(tmp_path)
    names = [name for name, _ in llm.calls]
    assert names.count("ExtractKnowledgeResponse") == 2
    assert names.index("ExtractKnowledgeResponse") == names.index("ExtractEventResponse") + 1
    second = [p for n, p in llm.calls if n == "ExtractKnowledgeResponse"][1]
    assert "char_003 | claim_001 | believes | Jo stole the key from the tower" in second
    assert "claim_001 | false | Jo stole the key from the tower" in second

    knowledge = json.loads((run_dir / "knowledge.json").read_text())
    assert [k["acquisition_id"] for k in knowledge] == [
        "u01_k1",
        "u01_k2",
        "u01_k3",
        "u01_k4",
        "u02_k1",
        "u02_k2",
    ]
    assert knowledge[3]["claim_id"] == "claim_003"
    claims = json.loads((run_dir / "claims.json").read_text())
    assert [c["claim_id"] for c in claims] == ["claim_001", "claim_002", "claim_003", "claim_004"]
    u02 = json.loads((run_dir / "chapters/u02.knowledge.json").read_text())
    assert [c["claim_id"] for c in u02["claims"]] == ["claim_004"]
    assert (run_dir / "chapters/u01.knowledge.proposed.json").exists()
    last = writer.snapshots[-1]
    assert [k["chapter_id"] for k in last["knowledge"]] == ["u01"] * 4 + ["u02"] * 2


def test_timeline_keeps_the_belief_before_the_reveal_and_the_truth_after(tmp_path: Path) -> None:
    run_dir, _, _ = run_story(tmp_path)
    before = knowledge_at(run_dir, "Evan", until="u01")
    (accused,) = before.claims
    assert (accused.claim_id, accused.stance, accused.known_truth) == (
        "claim_001",
        "believes",
        None,
    )
    assert accused.truth is None  # the real truth stays hidden
    after = knowledge_at(run_dir, "char_003")
    assert after.claims[0].stance == "disbelieves"
    assert after.claims[0].known_truth == "false"
    assert [step.channel for step in after.claims[0].history] == ["overheard", "learns_truth"]
    assert knowledge_at(run_dir, "Evan", reveal=True).claims[0].truth == "false"
    assert knowledge_at(run_dir, "Evan", until="u02_s1").claims[0].known_truth == "false"


def test_prior_knowledge_counts_from_the_start(tmp_path: Path) -> None:
    run_dir, _, _ = run_story(tmp_path)
    jo = knowledge_at(run_dir, "jo", until="u01")
    assert [(c.claim_id, c.stance) for c in jo.claims] == [
        ("claim_004", "believes"),
        ("claim_001", "disbelieves"),
    ]
    mara = knowledge_at(run_dir, "Mara", until="u01_s1")
    assert [c.claim_id for c in mara.claims] == ["claim_002", "claim_003"]
    assert "truth not known" in format_knowledge(mara)


def test_timeline_follows_merges(tmp_path: Path) -> None:
    run_dir, _, _ = run_story(tmp_path)
    (run_dir / "identity_redirects.json").write_text(json.dumps({"char_009": "char_003"}))
    assert knowledge_at(run_dir, "char_009").character_id == "char_003"
    with pytest.raises(ValueError, match="no character"):
        knowledge_at(run_dir, "Nobody")
    with pytest.raises(ValueError, match="expected a chapter"):
        knowledge_at(run_dir, "Evan", until="chapter 1")


def test_cli_prints_the_timeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir, _, _ = run_story(tmp_path)
    assert latest_run(tmp_path / "ingest", "sample") == run_dir
    monkeypatch.setattr(cli, "Settings", lambda: settings(BOOK_CLONE_DATA_DIR=tmp_path))
    text = CliRunner().invoke(cli.app, ["knowledge", "sample", "Evan", "--until", "u01"])
    assert text.exit_code == 0, text.output
    assert "Jo stole the key from the tower" in text.output
    assert "truth not known" in text.output and "book:" not in text.output
    data = CliRunner().invoke(cli.app, ["knowledge", "sample", "Evan", "--json", "--reveal"])
    assert json.loads(data.output)["claims"][0]["truth"] == "false"
    missing = CliRunner().invoke(cli.app, ["knowledge", "sample", "Nobody"])
    assert missing.exit_code == 1 and "no character" in missing.output


CHAPTER = Chapter(
    unit_id="u03",
    text="",
    paragraphs={"u03_p001": DOOR, "u03_p002": ACCUSE, "u03_p003": "Jo read the note."},
)
SEGMENTS = [
    SceneSegmentRecord(
        segment_id="u03_s1",
        start="u03_p001",
        end="u03_p002",
        present_ids=["char_001", "char_002", "char_003"],
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
    CharacterRecord(character_id=f"char_00{n}", candidate_name=name)
    for n, name in [(1, "Mara"), (2, "Jo"), (3, "Evan")]
]
CLAIMS = [
    ClaimRecord(
        claim_id="claim_001", statement="Jo took the key", truth="unknown", first_chapter_id="u01"
    ),
    ClaimRecord(
        claim_id="claim_002", statement="The key is safe", truth="true", first_chapter_id="u01"
    ),
    ClaimRecord(
        claim_id="claim_003", statement="The door is old", truth="unknown", first_chapter_id="u01"
    ),
]
EVENTS = ChapterEvents(
    chapter_id="u03",
    events=[
        EventRecord(
            event_id="u03_e1",
            segment_id="u03_s1",
            summary="Mara finds the door",
            participant_ids=["char_001"],
            paragraph_ids=["u03_p001"],
            claim_ids=["claim_001"],
        )
    ],
    utterances=[
        UtteranceRecord(
            utterance_id="u03_q1",
            segment_id="u03_s1",
            mode="spoken",
            speaker_id="char_001",
            addressee_ids=["char_002"],
            quote="Jo took the key",
            paragraph_ids=["u03_p002"],
            claim_ids=["claim_001"],
        ),
        UtteranceRecord(
            utterance_id="u03_q2",
            segment_id="u03_s2",
            mode="written",
            speaker_id=None,
            quote="note",
            paragraph_ids=["u03_p003"],
            claim_ids=["claim_002"],
        ),
    ],
    claims=[],
)
EARLIER = [
    KnowledgeRecord(
        acquisition_id="u02_k1",
        character_id="char_009",
        claim_id="claim_003",
        channel="inferred",
        stance="believes",
        segment_id="u02_s1",
        paragraph_ids=["u02_p001"],
    )
]


def check(*items: dict[str, Any], claims: list[Any] | None = None) -> Any:
    return validate_knowledge(
        ExtractKnowledgeResponse.model_validate(knows(claims, list(items))),
        CHAPTER,
        SEGMENTS,
        CHARACTERS,
        {"char_009": "char_003"},
        EVENTS,
        CLAIMS,
        4,
        EARLIER,
    )


def test_valid_acquisitions_get_ids_and_repeats_are_dropped() -> None:
    chapter_knowledge, claims, next_number = check(
        acquire("char_001", "claim_001", "witnessed", "believes", "u03_s1", "u03_e1", ["u03_p001"]),
        acquire("char_002", "claim_002", "read", "believes", "u03_s2", "u03_q2", ["u03_p003"]),
        acquire("char_002", "claim_002", "learns_truth", "believes", "u03_s2", None, ["u03_p003"]),
        # char_009 was merged into char_003, who already believes claim_003.
        acquire("char_009", "claim_003", "inferred", "believes", "u03_s1", None, ["u03_p002"]),
        acquire("char_003", "new_1", "prior", "believes", "u03_s2", None, ["u03_p003"]),
        claims=[claim("new_1", "Evan grew up near the tower", ["char_003"])],
    )
    assert [k.acquisition_id for k in chapter_knowledge.acquisitions] == [
        "u03_k1",
        "u03_k2",
        "u03_k3",
        "u03_k4",
    ]
    assert chapter_knowledge.acquisitions[3].claim_id == "claim_004"
    assert [c.claim_id for c in claims][-1] == "claim_004" and next_number == 5


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (
            acquire("char_001", "claim_001", "witnessed", "believes", "u03_s1", None, ["u03_p001"]),
            "needs a source_id",
        ),
        (
            acquire(
                "char_002", "claim_001", "witnessed", "believes", "u03_s1", "u03_q1", ["u03_p002"]
            ),
            "needs an event source",
        ),
        (
            acquire("char_003", "claim_001", "told", "believes", "u03_s1", "u03_q1", ["u03_p002"]),
            "is not an addressee",
        ),
        (
            acquire(
                "char_002", "claim_001", "overheard", "believes", "u03_s1", "u03_q1", ["u03_p002"]
            ),
            "use told",
        ),
        (
            acquire("char_003", "claim_001", "read", "believes", "u03_s1", "u03_q1", ["u03_p002"]),
            "needs a written utterance",
        ),
        (
            acquire("char_002", "claim_002", "told", "believes", "u03_s2", "u03_q2", ["u03_p003"]),
            "needs a spoken utterance",
        ),
        (
            acquire(
                "char_001", "claim_001", "inferred", "believes", "u03_s1", "u03_e1", ["u03_p001"]
            ),
            "source_id=null",
        ),
        (
            acquire("char_001", "claim_003", "inferred", "believes", "u03_s2", None, ["u03_p003"]),
            "is not present",
        ),
        (
            acquire(
                "char_001", "claim_001", "learns_truth", "believes", "u03_s1", None, ["u03_p001"]
            ),
            "not resolved yet",
        ),
        (
            acquire(
                "char_002", "claim_002", "learns_truth", "disbelieves", "u03_s2", None, ["u03_p003"]
            ),
            "means stance 'believes'",
        ),
        (
            acquire(
                "char_002", "claim_001", "witnessed", "believes", "u03_s2", "u03_e1", ["u03_p003"]
            ),
            "is not in segment",
        ),
        (
            acquire(
                "char_001", "claim_003", "witnessed", "believes", "u03_s1", "u03_e1", ["u03_p001"]
            ),
            "is not linked to claim",
        ),
        (
            acquire(
                "char_001", "claim_001", "witnessed", "believes", "u03_s1", "u03_e9", ["u03_p001"]
            ),
            "is not an event or utterance",
        ),
        (
            acquire("char_001", "claim_404", "inferred", "believes", "u03_s1", None, ["u03_p001"]),
            "Unknown claim ID",
        ),
        (
            acquire("char_001", "claim_001", "inferred", "believes", "u03_s1", None, ["u03_p003"]),
            "outside segment",
        ),
        (
            acquire("char_404", "claim_001", "inferred", "believes", "u03_s1", None, ["u03_p001"]),
            "Unknown character",
        ),
    ],
)
def test_channel_rules_reject_with_a_reason(bad: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValueError, match=re.escape(reason)):
        check(bad)


def test_new_claims_must_be_inferred_or_prior_and_used() -> None:
    new = [claim("new_1", "Jo hid the note", ["char_002"])]
    told = acquire("char_002", "new_1", "told", "believes", "u03_s1", "u03_q1", ["u03_p002"])
    with pytest.raises(ValueError, match="can only be inferred or prior"):
        check(told, claims=new)
    with pytest.raises(ValueError, match="not used by any acquisition"):
        check(claims=new)
    twice = acquire("char_001", "claim_001", "inferred", "doubts", "u03_s1", None, ["u03_p001"])
    with pytest.raises(ValueError, match="Duplicate acquisition"):
        check(twice, twice)


def test_a_rejected_answer_is_retried_with_the_reason() -> None:
    bad = knows(
        acquisitions=[
            acquire("char_003", "claim_001", "told", "believes", "u03_s1", "u03_q1", ["u03_p002"])
        ]
    )
    good = knows(
        acquisitions=[
            acquire(
                "char_003", "claim_001", "overheard", "believes", "u03_s1", "u03_q1", ["u03_p002"]
            )
        ]
    )
    client, transport = make([json.dumps(bad), json.dumps(good)])
    response = extract_knowledge(
        client,
        "The Gate",
        CHAPTER,
        SEGMENTS,
        CHARACTERS,
        EVENTS,
        CLAIMS,
        4,
        EARLIER,
        {"char_009": "char_003"},
        "",
    )
    assert response.acquisitions[0].channel == "overheard"
    prompt = transport.requests[0]["messages"][0]["content"]
    assert "char_003 | claim_003 | believes | The door is old" in prompt
    retry = transport.requests[1]["messages"][-1]["content"]
    assert "Rejected:" in retry and "is not an addressee" in retry


@pytest.mark.parametrize(
    "forbidden_word",
    ["Narnia", "Aslan", "Edmund", "Lucy", "Witch", "Harry", "Hogwarts", "Snape", "Quirrell"],
)
def test_extract_knowledge_prompt_is_book_agnostic(forbidden_word: str) -> None:
    assert re.search(rf"\b{forbidden_word}\b", PROMPT_EXTRACT_KNOWLEDGE, re.IGNORECASE) is None
