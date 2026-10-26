import json
from pathlib import Path

import pytest
from test_character_ingest import ScriptedLLM, make_extraction
from test_llm import make

from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.graph.summarize_chapter.logic import (
    validate_where_is_where,
    validate_who_is_who,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_where_is_where import (
    PROMPT_UPDATE_WHERE_IS_WHERE,
    UPDATE_WHERE_IS_WHERE_REMINDER,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_who_is_who import (
    PROMPT_UPDATE_WHO_IS_WHO,
    UPDATE_WHO_IS_WHO_REMINDER,
)
from pov_retell.ingest.source import load_chapters


def summary(
    chapter: str,
    who_is_who: str,
    where_is_where: str = "The Gate | - | stone gate",
) -> dict[str, str]:
    return {
        "chapter_summary": chapter,
        "who_is_who": who_is_who,
        "where_is_where": where_is_where,
    }


def test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(
        tmp_path,
        [["Mara arrived."], ["Susan arrived later."], ["Evan arrived last."]],
    )
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "CHAPTER_ONE_SUMMARY",
            "WHO IS WHO\nMara | - | WHO_AFTER_ONE",
            "WHERE IS WHERE\nThe Gate | - | WHERE_AFTER_ONE",
            "CHAPTER_TWO_SUMMARY",
            "Mara | - | WHO_AFTER_TWO\nSusan | - | companion",
            "The Gate | - | WHERE_AFTER_TWO\nGreat Hall | - | hall inside the gate",
            "CHAPTER_THREE_SUMMARY",
            "Mara | - | WHO_AFTER_THREE\nSusan | - | companion\nEvan | - | scout",
            "The Gate | - | WHERE_AFTER_THREE\nGreat Hall | - | hall inside the gate\n"
            "Watchtower | - | stone tower above the gate",
            "FINAL_CORE_MEMORY",
        ]
    )
    final = build_summarize_chapter_graph(llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert final["chapter_index"] == 3
    assert final["who_is_who"] == (
        "Mara | - | WHO_AFTER_THREE\nSusan | - | companion\nEvan | - | scout"
    )
    assert final["where_is_where"] == (
        "The Gate | - | WHERE_AFTER_THREE\nGreat Hall | - | hall inside the gate\n"
        "Watchtower | - | stone tower above the gate"
    )
    assert final["book_memory"].core_memory == "FINAL_CORE_MEMORY"
    assert final["book_memory"].where_is_where == final["where_is_where"]
    assert [s.chapter_id for s in final["summaries"]] == ["u01", "u02", "u03"]
    assert len(transport.requests) == 10
    prompts = [request["messages"][-1]["content"] for request in transport.requests]

    # u01 call 1, call 2, and call 3 receive empty previous context / lists.
    assert "<previous_book_summary>\n\n</previous_book_summary>" in prompts[0]
    assert "[u01_p001] Mara arrived." in prompts[0]
    assert "Susan arrived later." not in prompts[0]
    assert "<previous_who_is_who>\n\n</previous_who_is_who>" in prompts[1]
    assert "[u01_p001] Mara arrived." in prompts[1]
    assert "CHAPTER_ONE_SUMMARY" not in prompts[1]
    assert prompts[1].endswith(UPDATE_WHO_IS_WHO_REMINDER)
    assert "<previous_where_is_where>\n\n</previous_where_is_where>" in prompts[2]
    assert "[u01_p001] Mara arrived." in prompts[2]
    assert "CHAPTER_ONE_SUMMARY" not in prompts[2]
    assert "WHO_AFTER_ONE" not in prompts[2]
    assert prompts[2].endswith(UPDATE_WHERE_IS_WHERE_REMINDER)

    # u02 call 1 receives WHO IS WHO and WHERE IS WHERE after u01 and u01's summary.
    assert "WHO_AFTER_ONE" in prompts[3]
    assert "WHERE_AFTER_ONE" in prompts[3]
    assert prompts[3].index("WHO IS WHO") < prompts[3].index("WHERE IS WHERE")
    assert prompts[3].index("WHERE IS WHERE") < prompts[3].index("CHAPTER SUMMARIES")
    assert "[u01]\nCHAPTER_ONE_SUMMARY" in prompts[3]
    assert "CHAPTER_TWO_SUMMARY" not in prompts[3]
    assert "WHO_AFTER_TWO" not in prompts[3]
    assert "WHERE_AFTER_TWO" not in prompts[3]
    assert "[u02_p001] Susan arrived later." in prompts[3]
    assert UPDATE_WHO_IS_WHO_REMINDER not in prompts[0] + prompts[3] + prompts[6] + prompts[9]
    assert UPDATE_WHERE_IS_WHERE_REMINDER not in prompts[0] + prompts[3] + prompts[6] + prompts[9]

    # u02 call 2 receives previous WHO IS WHO and chapter text, without summaries or call-1 output.
    assert "WHO_AFTER_ONE" in prompts[4]
    assert "WHERE_AFTER_ONE" not in prompts[4]
    assert "[u02_p001] Susan arrived later." in prompts[4]
    assert "CHAPTER_ONE_SUMMARY" not in prompts[4]
    assert "CHAPTER_TWO_SUMMARY" not in prompts[4]
    assert prompts[4].endswith(UPDATE_WHO_IS_WHO_REMINDER)

    # u02 call 3 receives previous WHERE IS WHERE and chapter text, without summaries or WHO IS WHO.
    assert "WHERE_AFTER_ONE" in prompts[5]
    assert "WHO_AFTER_ONE" not in prompts[5]
    assert "[u02_p001] Susan arrived later." in prompts[5]
    assert "CHAPTER_ONE_SUMMARY" not in prompts[5]
    assert "CHAPTER_TWO_SUMMARY" not in prompts[5]
    assert prompts[5].endswith(UPDATE_WHERE_IS_WHERE_REMINDER)

    # u03 call 1 receives WHO IS WHO and WHERE IS WHERE after u02 and summaries 1..2 in order.
    assert "WHO_AFTER_TWO" in prompts[6]
    assert "WHERE_AFTER_TWO" in prompts[6]
    assert "WHO_AFTER_ONE" not in prompts[6]
    assert "WHERE_AFTER_ONE" not in prompts[6]
    assert prompts[6].index("[u01]\nCHAPTER_ONE_SUMMARY") < prompts[6].index(
        "[u02]\nCHAPTER_TWO_SUMMARY"
    )
    assert "CHAPTER_THREE_SUMMARY" not in prompts[6]
    assert "WHO_AFTER_THREE" not in prompts[6]
    assert "WHERE_AFTER_THREE" not in prompts[6]
    assert "[u03_p001] Evan arrived last." in prompts[6]

    # Final core-memory call receives all chapter summaries in order with chapter IDs.
    assert "Book title: The Gate" in prompts[9]
    assert (
        prompts[9].index("[u01]\nCHAPTER_ONE_SUMMARY")
        < prompts[9].index("[u02]\nCHAPTER_TWO_SUMMARY")
        < prompts[9].index("[u03]\nCHAPTER_THREE_SUMMARY")
    )
    assert all("response_format" not in request for request in transport.requests)

    assert json.loads((output_dir / "summaries/u01.summary.json").read_text()) == {
        "chapter_id": "u01",
        "chapter_summary": "CHAPTER_ONE_SUMMARY",
        "who_is_who": "Mara | - | WHO_AFTER_ONE",
        "where_is_where": "The Gate | - | WHERE_AFTER_ONE",
    }
    assert json.loads((output_dir / "summaries/u02.summary.json").read_text()) == {
        "chapter_id": "u02",
        "chapter_summary": "CHAPTER_TWO_SUMMARY",
        "who_is_who": "Mara | - | WHO_AFTER_TWO\nSusan | - | companion",
        "where_is_where": "The Gate | - | WHERE_AFTER_TWO\nGreat Hall | - | hall inside the gate",
    }
    assert json.loads((output_dir / "summaries/book_memory.json").read_text()) == {
        "who_is_who": "Mara | - | WHO_AFTER_THREE\nSusan | - | companion\nEvan | - | scout",
        "where_is_where": (
            "The Gate | - | WHERE_AFTER_THREE\nGreat Hall | - | hall inside the gate\n"
            "Watchtower | - | stone tower above the gate"
        ),
        "core_memory": "FINAL_CORE_MEMORY",
    }
    assert len(list((output_dir / "summaries").glob("*.summary.json"))) == 3
    assert not (output_dir / "characters.json").exists()


@pytest.mark.parametrize("bad_reply", ["", " \n\t"])
@pytest.mark.parametrize("stage", ["chapter", "who_is_who", "where_is_where"])
def test_empty_summary_stops_without_losing_previous_saved_chapter(
    tmp_path: Path, bad_reply: str, stage: str
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara arrived."], ["Mara left."], ["Susan arrived."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    first = summary("Only Mara is known.", "Mara | - | traveler", "The Gate | - | stone gate")
    replies = [
        "Only Mara is known.",
        "Mara | - | traveler",
        "The Gate | - | stone gate",
    ]
    if stage in {"who_is_who", "where_is_where"}:
        replies.append("Mara left.")
    if stage == "where_is_where":
        replies.append("Mara | - | traveler")
    replies.append(bad_reply)
    llm, transport = make(replies)
    with pytest.raises(LLMError, match="empty text"):
        build_summarize_chapter_graph(llm).invoke(
            {"title": title, "chapters": chapters, "output_dir": output_dir}
        )
    expected_calls = {"chapter": 4, "who_is_who": 5, "where_is_where": 6}[stage]
    assert len(transport.requests) == expected_calls
    assert json.loads((output_dir / "summaries/u01.summary.json").read_text()) == {
        "chapter_id": "u01",
        **first,
    }
    assert not (output_dir / "summaries/u02.summary.json").exists()
    assert not (output_dir / "summaries/u03.summary.json").exists()
    assert not (output_dir / "summaries/book_memory.json").exists()
    assert not list(output_dir.rglob("*.tmp"))


@pytest.mark.parametrize(
    "bad_line",
    [
        "WHO IS WHO",
        "Mara - traveler",
        "Mara | traveler",
        "Mara | - | human | traveler",
        "Mara | | traveler",
    ],
)
def test_who_is_who_rejects_blank_or_malformed_lines(bad_line: str) -> None:
    with pytest.raises(ValueError):
        validate_who_is_who(bad_line)


@pytest.mark.parametrize(
    "bad_line",
    [
        "WHERE IS WHERE",
        "The Gate - stone gate",
        "The Gate | stone gate",
        "The Gate | - | fortress | stone gate",
        "The Gate | | stone gate",
    ],
)
def test_where_is_where_rejects_blank_or_malformed_lines(bad_line: str) -> None:
    with pytest.raises(ValueError):
        validate_where_is_where(bad_line)


def test_who_is_who_accepts_case_insensitive_survival_in_first_or_second_field() -> None:
    previous = "Mara | - | traveler\nthe captain | - | masked woman"
    merged = "MARA | The Captain, Captain Mara | cautious human woman"
    assert validate_who_is_who(merged, previous) == merged


def test_where_is_where_accepts_case_insensitive_survival_in_first_or_second_field() -> None:
    previous = "Professor's house | - | country house\nthe spare room | - | upstairs room"
    merged = (
        "Professor's House | the old house | large country house\n"
        "Spare room | the spare room | upstairs room in Professor's House"
    )
    assert validate_where_is_where(merged, previous) == merged


@pytest.mark.parametrize(
    "forbidden_term",
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
def test_who_is_who_and_where_is_where_prompts_are_book_agnostic(forbidden_term: str) -> None:
    import re

    who_combined = (PROMPT_UPDATE_WHO_IS_WHO + "\n" + UPDATE_WHO_IS_WHO_REMINDER).casefold()
    where_combined = (
        PROMPT_UPDATE_WHERE_IS_WHERE + "\n" + UPDATE_WHERE_IS_WHERE_REMINDER
    ).casefold()
    assert re.search(rf"\b{re.escape(forbidden_term)}\b", who_combined, re.IGNORECASE) is None
    assert re.search(rf"\b{re.escape(forbidden_term)}\b", where_combined, re.IGNORECASE) is None
    assert "about 40" not in who_combined
    assert "at most 40 words" in PROMPT_UPDATE_WHO_IS_WHO
    assert "at most 40 words" in UPDATE_WHO_IS_WHO_REMINDER
    assert "no chapter references" in UPDATE_WHO_IS_WHO_REMINDER
    assert "no event lists" in UPDATE_WHO_IS_WHO_REMINDER
    assert "at most 30 words" in PROMPT_UPDATE_WHERE_IS_WHERE
    assert "at most 30 words" in UPDATE_WHERE_IS_WHERE_REMINDER
    assert "no chapter references" in UPDATE_WHERE_IS_WHERE_REMINDER
    assert "no event lists" in UPDATE_WHERE_IS_WHERE_REMINDER


def test_dropping_previous_character_retries_with_rejection_reason_and_recovers(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara and Jo arrived."], ["Susan arrived."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "Mara and Jo arrived.",
            "Mara | - | traveler\nJo | - | friend",
            "The Gate | - | stone gate",
            "Susan arrived.",
            "Mara | - | traveler\nSusan | - | newcomer",
            "Mara | - | traveler\nJo | - | friend\nSusan | - | newcomer",
            "The Gate | - | stone gate",
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert len(transport.requests) == 8
    retry_prompt = transport.requests[5]["messages"][-1]["content"]
    assert "Rejected: WHO IS WHO dropped earlier character(s): Jo" in retry_prompt
    assert "Jo | - | friend" in final["who_is_who"]


def test_dropping_previous_place_retries_with_rejection_reason_and_recovers(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara entered the hall."], ["Mara climbed the tower."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "Mara entered the hall.",
            "Mara | - | traveler",
            "The Gate | - | stone gate\nGreat Hall | - | hall inside the gate",
            "Mara climbed the tower.",
            "Mara | - | traveler",
            "The Gate | - | stone gate\nWatchtower | - | stone tower",
            "The Gate | - | stone gate\nGreat Hall | - | hall inside the gate\n"
            "Watchtower | - | stone tower",
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert len(transport.requests) == 8
    retry_prompt = transport.requests[6]["messages"][-1]["content"]
    assert "Rejected: WHERE IS WHERE dropped earlier place(s): Great Hall" in retry_prompt
    assert "Great Hall | - | hall inside the gate" in final["where_is_where"]


@pytest.mark.parametrize(
    ("previous_list", "dropped_reply", "recovered_reply", "missing_name"),
    [
        (
            "Lucy | Daughter of Eve | human girl\nEve | - | ancestor",
            "Lucy | Daughter of Eve | human girl",
            "Lucy | Daughter of Eve | human girl\nEve | - | ancestor",
            "Eve",
        ),
        (
            "Tumnus | - | faun\nTumnus's father | - | faun in a picture",
            "Tumnus's father | - | faun in a picture",
            "Tumnus | - | faun\nTumnus's father | - | faun in a picture",
            "Tumnus",
        ),
    ],
)
def test_substring_matches_do_not_hide_dropped_characters_and_trigger_retry(
    tmp_path: Path,
    previous_list: str,
    dropped_reply: str,
    recovered_reply: str,
    missing_name: str,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Chapter one."], ["Chapter two."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "Summary one.",
            previous_list,
            "The Gate | - | stone gate",
            "Summary two.",
            dropped_reply,
            recovered_reply,
            "The Gate | - | stone gate",
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert len(transport.requests) == 8
    retry_prompt = transport.requests[5]["messages"][-1]["content"]
    assert f"Rejected: WHO IS WHO dropped earlier character(s): {missing_name}" in retry_prompt
    assert final["who_is_who"] == recovered_reply


def test_three_invalid_who_is_who_answers_raise_and_preserve_saved_chapters(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara and Jo arrived."], ["Susan arrived."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    dropped = "Mara | - | traveler\nSusan | - | newcomer"
    llm, transport = make(
        [
            "Mara and Jo arrived.",
            "Mara | - | traveler\nJo | - | friend",
            "The Gate | - | stone gate",
            "Susan arrived.",
            dropped,
            "Mara | missing third field",
            dropped,
        ]
    )
    with pytest.raises(LLMError, match="Jo"):
        build_summarize_chapter_graph(llm).invoke(
            {"title": title, "chapters": chapters, "output_dir": output_dir}
        )
    assert len(transport.requests) == 7
    assert "Rejected:" in transport.requests[5]["messages"][-1]["content"]
    assert "Rejected:" in transport.requests[6]["messages"][-1]["content"]
    assert (output_dir / "summaries/u01.summary.json").exists()
    assert not (output_dir / "summaries/u02.summary.json").exists()
    assert not (output_dir / "summaries/book_memory.json").exists()


def test_three_invalid_where_is_where_answers_raise_and_preserve_saved_chapters(
    tmp_path: Path,
) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara entered the hall."], ["Mara climbed the tower."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    dropped = "The Gate | - | stone gate"
    llm, transport = make(
        [
            "Mara entered the hall.",
            "Mara | - | traveler",
            "The Gate | - | stone gate\nGreat Hall | - | hall inside the gate",
            "Mara climbed the tower.",
            "Mara | - | traveler",
            dropped,
            "The Gate | missing third field",
            dropped,
        ]
    )
    with pytest.raises(LLMError, match="Great Hall"):
        build_summarize_chapter_graph(llm).invoke(
            {"title": title, "chapters": chapters, "output_dir": output_dir}
        )
    assert len(transport.requests) == 8
    assert "Rejected:" in transport.requests[6]["messages"][-1]["content"]
    assert "Rejected:" in transport.requests[7]["messages"][-1]["content"]
    assert (output_dir / "summaries/u01.summary.json").exists()
    assert not (output_dir / "summaries/u02.summary.json").exists()
    assert not (output_dir / "summaries/book_memory.json").exists()


def test_summary_graph_completes_seventeen_chapters_in_source_order(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import (
        build_summarize_chapter_graph,
        summarize_chapter_recursion_limit,
    )

    make_extraction(tmp_path, [[f"Day {i}."] for i in range(1, 18)])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    replies: list[str] = []
    for i in range(1, 18):
        replies.extend(
            [
                f"Summary of day {i}.",
                f"Mara | - | traveler on day {i}",
                f"The Gate | - | stone gate on day {i}",
            ]
        )
    replies.append("Core memory of all seventeen days.")
    llm = ScriptedLLM(replies)
    final = build_summarize_chapter_graph(llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir},
        {"recursion_limit": summarize_chapter_recursion_limit(len(chapters))},
    )
    assert final["chapter_index"] == 17
    assert len(llm.prompts) == 52
    assert "Current chapter: u10" in llm.prompts[27]
    assert "Mara | - | traveler on day 9" in llm.prompts[27]
    assert "The Gate | - | stone gate on day 9" in llm.prompts[27]
    assert "[u09]\nSummary of day 9." in llm.prompts[27]
    assert "Summary of day 10." not in llm.prompts[27]
    assert len(list((output_dir / "summaries").glob("*.summary.json"))) == 17
    assert json.loads((output_dir / "summaries/book_memory.json").read_text()) == {
        "who_is_who": "Mara | - | traveler on day 17",
        "where_is_where": "The Gate | - | stone gate on day 17",
        "core_memory": "Core memory of all seventeen days.",
    }
