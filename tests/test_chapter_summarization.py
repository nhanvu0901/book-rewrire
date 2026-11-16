import json
from pathlib import Path
from typing import Any

import pytest
from test_character_ingest import ScriptedLLM, make_extraction
from test_llm import make

from pov_retell.infrastructure.llm import LLMError
from pov_retell.ingest.graph.summarize_chapter.logic import (
    changes_to_update,
    check_changes,
    name_key,
    render_cards,
)
from pov_retell.ingest.graph.summarize_chapter.model import (
    Card,
    CardChanges,
    CardUpdate,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_where_is_where import (
    PROMPT_UPDATE_WHERE_IS_WHERE,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_who_is_who import (
    PROMPT_UPDATE_WHO_IS_WHO,
)
from pov_retell.ingest.source import load_chapters


def card(name: str, card_text: str, *other_names: str) -> dict[str, object]:
    return {"name": name, "other_names": list(other_names), "card": card_text}


def card_update(card_id: str, name: str, card_text: str, *other_names: str) -> dict[str, object]:
    return {"id": card_id, "name": name, "other_names": list(other_names), "card": card_text}


def changes(
    add: list[dict[str, object]] | None = None,
    update: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps({"add": add or [], "update": update or []})


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
            # Chapter 1: summary, who (add Mara), where (add The Gate)
            "CHAPTER_ONE_SUMMARY",
            changes(add=[card("Mara", "WHO_AFTER_ONE")]),
            changes(add=[card("The Gate", "WHERE_AFTER_ONE")]),
            # Chapter 2: who (update Mara, add Susan), where (update The Gate, add Great Hall)
            "CHAPTER_TWO_SUMMARY",
            changes(
                add=[card("Susan", "companion")],
                update=[card_update("C001", "Mara", "WHO_AFTER_TWO")],
            ),
            changes(
                add=[card("Great Hall", "hall inside the gate")],
                update=[card_update("P001", "The Gate", "WHERE_AFTER_TWO")],
            ),
            # Chapter 3: who (update Mara, add Evan), where (update The Gate, add Watchtower)
            "CHAPTER_THREE_SUMMARY",
            changes(
                add=[card("Evan", "scout")],
                update=[card_update("C001", "Mara", "WHO_AFTER_THREE")],
            ),
            changes(
                add=[card("Watchtower", "stone tower above the gate")],
                update=[card_update("P001", "The Gate", "WHERE_AFTER_THREE")],
            ),
            # Core memory
            "FINAL_CORE_MEMORY",
        ]
    )
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert final["chapter_index"] == 3
    assert final["who_is_who"] == (
        "Mara | - | WHO_AFTER_THREE\nSusan | - | companion\nEvan | - | scout"
    )
    assert final["where_is_where"] == (
        "The Gate | - | WHERE_AFTER_THREE\n"
        "Great Hall | - | hall inside the gate\n"
        "Watchtower | - | stone tower above the gate"
    )
    assert final["book_memory"].core_memory == "FINAL_CORE_MEMORY"
    assert final["book_memory"].where_is_where == final["where_is_where"]
    assert [s.chapter_id for s in final["summaries"]] == ["u01", "u02", "u03"]
    assert len(transport.requests) == 10
    prompts = [request["messages"][-1]["content"] for request in transport.requests]

    # u01 Call 1, 2, 3 receive empty previous context
    assert "<previous_book_summary>\n\n</previous_book_summary>" in prompts[0]
    assert "[u01_p001] Mara arrived." in prompts[0]
    assert "<previous_list>\n(empty)\n</previous_list>" in prompts[1]
    assert "[u01_p001] Mara arrived." in prompts[1]
    assert "<previous_list>\n(empty)\n</previous_list>" in prompts[2]

    # u02 Call 1 receives WHO IS WHO and WHERE IS WHERE without IDs and u01's summary
    assert "WHO_AFTER_ONE" in prompts[3]
    assert "WHERE_AFTER_ONE" in prompts[3]
    assert "C001" not in prompts[3]
    assert "P001" not in prompts[3]
    assert prompts[3].index("WHO IS WHO") < prompts[3].index("WHERE IS WHERE")
    assert prompts[3].index("WHERE IS WHERE") < prompts[3].index("CHAPTER SUMMARIES")
    assert "[u01]\nCHAPTER_ONE_SUMMARY" in prompts[3]

    # u02 Call 2 receives previous WHO IS WHO with ID C001
    assert "C001 | Mara | - | WHO_AFTER_ONE" in prompts[4]
    assert "WHERE_AFTER_ONE" not in prompts[4]
    assert "[u02_p001] Susan arrived later." in prompts[4]

    # u02 Call 3 receives previous WHERE IS WHERE with ID P001
    assert "P001 | The Gate | - | WHERE_AFTER_ONE" in prompts[5]
    assert "WHO_AFTER_ONE" not in prompts[5]
    assert "[u02_p001] Susan arrived later." in prompts[5]

    # u03 Call 1 receives WHO IS WHO and WHERE IS WHERE after u02 (without IDs)
    assert "WHO_AFTER_TWO" in prompts[6]
    assert "WHERE_AFTER_TWO" in prompts[6]
    assert "C001" not in prompts[6]
    assert "[u01]\nCHAPTER_ONE_SUMMARY" in prompts[6]
    assert "[u02]\nCHAPTER_TWO_SUMMARY" in prompts[6]

    # Final core-memory call receives all chapter summaries in order with chapter IDs
    assert "Book title: The Gate" in prompts[9]
    assert (
        prompts[9].index("[u01]\nCHAPTER_ONE_SUMMARY")
        < prompts[9].index("[u02]\nCHAPTER_TWO_SUMMARY")
        < prompts[9].index("[u03]\nCHAPTER_THREE_SUMMARY")
    )

    # Saved files verify no IDs are leaked into uNN.summary.json or book_memory.json
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
            "The Gate | - | WHERE_AFTER_THREE\n"
            "Great Hall | - | hall inside the gate\n"
            "Watchtower | - | stone tower above the gate"
        ),
        "core_memory": "FINAL_CORE_MEMORY",
    }
    assert len(list((output_dir / "summaries").glob("*.summary.json"))) == 3


def test_fake_chapter_update_only_preserves_earlier_cards(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara and Jo arrived."], ["Mara explored alone."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, _ = make(
        [
            "Summary one.",
            changes(add=[card("Mara", "traveler"), card("Jo", "friend")]),
            changes(add=[card("The Gate", "stone gate")]),
            "Summary two.",
            # Only update C001, add nothing: Jo (C002) must be preserved
            changes(update=[card_update("C001", "Mara", "lone traveler")]),
            changes(),
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert final["who_is_who"] == "Mara | - | lone traveler\nJo | - | friend"
    assert "C001" in final["who_cards"]
    assert "C002" in final["who_cards"]
    assert final["who_cards"]["C001"].card == "lone traveler"
    assert final["who_cards"]["C002"].card == "friend"


def test_unknown_update_id_retries_and_raises_after_max_retries(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara arrived."], ["Unknown update."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    bad_update = changes(update=[card_update("C999", "Ghost", "unknown person")])
    llm, transport = make(
        [
            "Summary one.",
            changes(add=[card("Mara", "traveler")]),
            changes(add=[card("The Gate", "stone gate")]),
            "Summary two.",
            bad_update,
            bad_update,
            bad_update,
        ]
    )
    with pytest.raises(LLMError, match=r"update uses unknown id\(s\): C999"):
        build_summarize_chapter_graph(llm, llm).invoke(
            {"title": title, "chapters": chapters, "output_dir": output_dir}
        )
    assert len(transport.requests) == 7
    retry_prompt = transport.requests[5]["messages"][-1]["content"]
    assert "Rejected: update uses unknown id(s): C999" in retry_prompt
    assert (output_dir / "summaries/u01.summary.json").exists()
    assert not (output_dir / "summaries/u02.summary.json").exists()


def test_duplicate_name_add_retries_and_raises_after_max_retries(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara arrived."], ["Mara re-added."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    bad_add = changes(add=[card("Mara", "duplicate traveler")])
    llm, transport = make(
        [
            "Summary one.",
            changes(add=[card("Mara", "traveler")]),
            changes(add=[card("The Gate", "stone gate")]),
            "Summary two.",
            bad_add,
            bad_add,
            bad_add,
        ]
    )
    with pytest.raises(LLMError, match=r"'Mara' is already listed as C001; use update"):
        build_summarize_chapter_graph(llm, llm).invoke(
            {"title": title, "chapters": chapters, "output_dir": output_dir}
        )
    assert len(transport.requests) == 7
    retry_prompt = transport.requests[5]["messages"][-1]["content"]
    assert "Rejected: 'Mara' is already listed as C001; use update" in retry_prompt


def test_unknown_update_id_retries_and_recovers(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Mara arrived."], ["Mara returned."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "Summary one.",
            changes(add=[card("Mara", "traveler")]),
            changes(add=[card("The Gate", "stone gate")]),
            "Summary two.",
            # Call 2: WHO IS WHO - first attempt uses unknown id C005, then corrects to C001
            changes(update=[card_update("C005", "Mara", "returned traveler")]),
            changes(update=[card_update("C001", "Mara", "returned traveler")]),
            changes(),
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert len(transport.requests) == 8
    retry_prompt = transport.requests[5]["messages"][-1]["content"]
    assert "Rejected: update uses unknown id(s): C005" in retry_prompt
    assert final["who_cards"]["C001"].card == "returned traveler"


def test_quote_normalized_duplicate_name_add_retries_and_recovers(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [["Madam Malkin’s Robes opened."], ["Malkin's Robes visited."]])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, transport = make(
        [
            "Summary one.",
            changes(add=[card("Mara", "traveler")]),
            changes(add=[card("Madam Malkin’s Robes", "robe shop", "Madam Malkin's")]),
            "Summary two.",
            changes(),
            # Call 3: WHERE IS WHERE - first attempt re-adds with straight quote
            changes(add=[card("Madam Malkin's Robes", "robe shop in Diagon Alley")]),
            # Second attempt uses valid new place
            changes(add=[card("Gringotts", "wizard bank")]),
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert len(transport.requests) == 8
    retry_prompt = transport.requests[6]["messages"][-1]["content"]
    rejection = 'Rejected: "Madam Malkin\'s Robes" is already listed as P001; use update'
    assert rejection in retry_prompt
    assert "Gringotts" in final["where_is_where"]
    assert "P001" in final["where_cards"]
    assert "P002" in final["where_cards"]


def test_ids_are_stable_across_chapters_and_continue_sequence(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(
        tmp_path,
        [["First chapter."], ["Second chapter."], ["Third chapter."]],
    )
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    llm, _ = make(
        [
            # Chapter 1: add C001, C002
            "Summary one.",
            changes(add=[card("Mara", "traveler"), card("Jo", "friend")]),
            changes(add=[card("The Gate", "stone gate")]),
            # Chapter 2: update only, no adds -> IDs C001, C002 remain stable
            "Summary two.",
            changes(update=[card_update("C001", "Mara", "lone traveler")]),
            changes(),
            # Chapter 3: add new card -> continues from max ID (C002) to C003
            "Summary three.",
            changes(add=[card("Evan", "scout")]),
            changes(add=[card("The Forest", "deep woods")]),
            "Core memory.",
        ]
    )
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    assert list(final["who_cards"].keys()) == ["C001", "C002", "C003"]
    assert list(final["where_cards"].keys()) == ["P001", "P002"]
    assert final["who_cards"]["C001"].name == "Mara"
    assert final["who_cards"]["C002"].name == "Jo"
    assert final["who_cards"]["C003"].name == "Evan"


def test_check_changes_validation_rules() -> None:
    existing = {
        "C001": Card(name="Mara", other_names=["Lady Mara"], card="traveler"),
        "C002": Card(name="Jo", other_names=[], card="friend"),
    }

    # Unknown ID in update
    bad_id = CardChanges(
        add=[],
        update=[CardUpdate(id="C999", name="Ghost", other_names=[], card="unknown")],
    )
    with pytest.raises(ValueError, match=r"update uses unknown id\(s\): C999"):
        check_changes(bad_id, existing)

    # Duplicate ID in update
    dup_id = CardChanges(
        add=[],
        update=[
            CardUpdate(id="C001", name="Mara", other_names=[], card="one"),
            CardUpdate(id="C001", name="Mara", other_names=[], card="two"),
        ],
    )
    with pytest.raises(ValueError, match="update lists the same id more than once"):
        check_changes(dup_id, existing)

    # Add name that already exists
    dup_add_name = CardChanges(
        add=[Card(name="Mara", other_names=[], card="new")],
        update=[],
    )
    with pytest.raises(ValueError, match=r"'Mara' is already listed as C001; use update"):
        check_changes(dup_add_name, existing)

    # Add other_name that already exists
    dup_add_other = CardChanges(
        add=[Card(name="Newcomer", other_names=["Lady Mara"], card="new")],
        update=[],
    )
    with pytest.raises(ValueError, match=r"'Lady Mara' is already listed as C001; use update"):
        check_changes(dup_add_other, existing)

    # Add duplicate within same payload
    dup_within_add = CardChanges(
        add=[
            Card(name="Evan", other_names=[], card="scout"),
            Card(name="Evan", other_names=[], card="scout duplicate"),
        ],
        update=[],
    )
    with pytest.raises(ValueError, match=r"'Evan' is added twice"):
        check_changes(dup_within_add, existing)

    # Curly quote normalization in add
    existing_quotes = {
        "C001": Card(name="“Mad-Eye” Moody", other_names=[], card="auror"),
    }
    quote_add = CardChanges(
        add=[Card(name='"Mad-Eye" Moody', other_names=[], card="noble")],
        update=[],
    )
    with pytest.raises(
        ValueError, match=r"'\"Mad-Eye\" Moody' is already listed as C001; use update"
    ):
        check_changes(quote_add, existing_quotes)


def test_render_cards_output_formatting() -> None:
    cards = {
        "C001": Card(name="Mara", other_names=["Lady Mara", "M"], card="traveler"),
        "C002": Card(name="Jo", other_names=[], card="friend"),
    }
    with_ids = render_cards(cards, with_ids=True)
    assert with_ids == "C001 | Mara | Lady Mara, M | traveler\nC002 | Jo | - | friend"

    without_ids = render_cards(cards, with_ids=False)
    assert without_ids == "Mara | Lady Mara, M | traveler\nJo | - | friend"

    assert render_cards({}, with_ids=True) == ""
    assert render_cards({}, with_ids=False) == ""


def test_changes_to_update_assigns_sequential_ids() -> None:
    # Starting from empty dict
    c = CardChanges(
        add=[
            Card(name="Mara", other_names=[], card="traveler"),
            Card(name="Jo", other_names=[], card="friend"),
        ],
        update=[],
    )
    result = changes_to_update(c, {}, "C")
    assert list(result.keys()) == ["C001", "C002"]

    # Continuing from existing dict
    c2 = CardChanges(
        add=[Card(name="Evan", other_names=[], card="scout")],
        update=[CardUpdate(id="C001", name="Mara", other_names=[], card="hero")],
    )
    result2 = changes_to_update(c2, result, "C")
    assert "C001" in result2
    assert "C003" in result2
    assert result2["C001"].card == "hero"
    assert result2["C003"].name == "Evan"


def test_who_is_who_and_where_is_where_prompts_are_book_agnostic(forbidden_term: str) -> None:
    import re

    who_combined = PROMPT_UPDATE_WHO_IS_WHO.casefold()
    where_combined = PROMPT_UPDATE_WHERE_IS_WHERE.casefold()
    assert re.search(rf"\b{re.escape(forbidden_term)}\b", who_combined, re.IGNORECASE) is None
    assert re.search(rf"\b{re.escape(forbidden_term)}\b", where_combined, re.IGNORECASE) is None
    assert "about 40" not in who_combined
    assert "at most 40 words" in PROMPT_UPDATE_WHO_IS_WHO
    assert "references to chapters" in PROMPT_UPDATE_WHO_IS_WHO
    assert "lists of actions or events" in PROMPT_UPDATE_WHO_IS_WHO
    assert "at most 30 words" in PROMPT_UPDATE_WHERE_IS_WHERE
    assert "references to chapters" in PROMPT_UPDATE_WHERE_IS_WHERE
    assert "lists of actions or events" in PROMPT_UPDATE_WHERE_IS_WHERE


@pytest.fixture(
    params=[
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
        "fawn",
        "faun's cave",
        "Paravel",
    ]
)
def forbidden_term(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def test_summary_graph_completes_seventeen_chapters_in_source_order(tmp_path: Path) -> None:
    from pov_retell.ingest.graph.summarize_chapter.graph import (
        build_summarize_chapter_graph,
        summarize_chapter_recursion_limit,
    )

    make_extraction(tmp_path, [[f"Day {i}."] for i in range(1, 18)])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    replies: list[str | dict[str, Any] | Exception] = []
    for i in range(1, 18):
        replies.append(f"Summary of day {i}.")
        if i == 1:
            replies.append({"add": [card("Mara", f"traveler on day {i}")], "update": []})
            replies.append({"add": [card("The Gate", f"stone gate on day {i}")], "update": []})
        else:
            replies.append(
                {
                    "add": [],
                    "update": [card_update("C001", "Mara", f"traveler on day {i}")],
                }
            )
            replies.append(
                {
                    "add": [],
                    "update": [card_update("P001", "The Gate", f"stone gate on day {i}")],
                }
            )
    replies.append("Core memory of all seventeen days.")
    llm = ScriptedLLM(replies)
    final = build_summarize_chapter_graph(llm, llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir},
        {"recursion_limit": summarize_chapter_recursion_limit(len(chapters))},
    )
    assert final["chapter_index"] == 17
    assert len(llm.prompts) == 18  # 17 chapter summaries + 1 book memory
    assert len(llm.card_prompts) == 34  # 17 WHO IS WHO + 17 WHERE IS WHERE
    assert "Current chapter: u10" in llm.prompts[9]  # u10 text call
    assert "Mara | - | traveler on day 9" in llm.prompts[9]
    assert "[u09]\nSummary of day 9." in llm.prompts[9]
    assert "Summary of day 10." not in llm.prompts[9]
    assert "Current chapter: u10" in llm.card_prompts[18]  # u10 who call
    assert "C001 | Mara | - | traveler on day 9" in llm.card_prompts[18]
    assert len(list((output_dir / "summaries").glob("*.summary.json"))) == 17
    assert json.loads((output_dir / "summaries/book_memory.json").read_text()) == {
        "who_is_who": "Mara | - | traveler on day 17",
        "where_is_where": "The Gate | - | stone gate on day 17",
        "core_memory": "Core memory of all seventeen days.",
    }


def test_quote_style_does_not_change_the_name_comparison_key() -> None:
    assert name_key("Madam Malkin’s Robes") == name_key("Madam Malkin's Robes")


class TextOnlyLLM(ScriptedLLM):
    def complete_json(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the summary client must not receive card updates")


class CardOnlyLLM(ScriptedLLM):
    def complete_text(self, text: str, *, system_prompt: str) -> str:
        raise AssertionError("the card client must not receive summary calls")


def run_summary_graph(
    tmp_path: Path, summary_llm: ScriptedLLM, card_llm: ScriptedLLM, chapter_count: int
) -> tuple[dict[str, Any], Path]:
    from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph

    make_extraction(tmp_path, [[f"Mara arrived on day {i}."] for i in range(1, chapter_count + 1)])
    title, chapters = load_chapters(tmp_path / "extracted", "sample")
    output_dir = tmp_path / "ingest/sample/summary"
    output_dir.mkdir(parents=True)
    final = build_summarize_chapter_graph(summary_llm, card_llm).invoke(
        {"title": title, "chapters": chapters, "output_dir": output_dir}
    )
    return final, output_dir


def test_card_updates_go_to_the_card_client_and_summaries_to_the_summary_client(
    tmp_path: Path,
) -> None:
    summaries = TextOnlyLLM(["Summary one.", "Summary two.", "Core memory."])
    cards = CardOnlyLLM(
        [],
        cards=[
            {"add": [card("Mara", "traveler")], "update": []},
            {"add": [card("The Gate", "stone gate")], "update": []},
            {"add": [], "update": [card_update("C001", "Mara", "tired traveler")]},
            {"add": [], "update": []},
        ],
    )
    final, _ = run_summary_graph(tmp_path, summaries, cards, 2)
    assert len(summaries.prompts) == 3 and summaries.card_prompts == []
    assert len(cards.card_prompts) == 4 and cards.prompts == []
    assert final["book_memory"].who_is_who == "Mara | - | tired traveler"
    assert final["book_memory"].where_is_where == "The Gate | - | stone gate"


@pytest.mark.parametrize("failing_call", [2, 3], ids=["who_is_who", "where_is_where"])
def test_card_update_failure_in_chapter_two_keeps_chapter_one_saved(
    tmp_path: Path, failing_call: int
) -> None:
    # Card calls in order: u01 who, u01 where, u02 who, u02 where.
    card_answers: list[dict[str, Any] | Exception] = [{"add": [], "update": []} for _ in range(4)]
    card_answers[failing_call] = LLMError("cards down")
    card_llm = ScriptedLLM([], cards=card_answers)
    summaries = ScriptedLLM(["Summary one.", "Summary two.", "Core memory."])
    with pytest.raises(LLMError, match="cards down"):
        run_summary_graph(tmp_path, summaries, card_llm, 2)
    assert len(card_llm.card_prompts) == failing_call + 1
    saved = tmp_path / "ingest/sample/summary/summaries"
    assert (saved / "u01.summary.json").exists()
    assert not (saved / "u02.summary.json").exists()
    assert not (saved / "book_memory.json").exists()


def test_summary_failure_in_chapter_two_keeps_chapter_one_saved(tmp_path: Path) -> None:
    summaries = ScriptedLLM(["Summary one.", LLMError("empty text response")])
    with pytest.raises(LLMError, match="empty text response"):
        run_summary_graph(tmp_path, summaries, ScriptedLLM([]), 2)
    saved = tmp_path / "ingest/sample/summary/summaries"
    assert (saved / "u01.summary.json").exists()
    assert not (saved / "u02.summary.json").exists()


def test_chapter_without_characters_or_places_saves_empty_lists(tmp_path: Path) -> None:
    final, output_dir = run_summary_graph(
        tmp_path, ScriptedLLM(["Summary one.", "Core memory."]), ScriptedLLM([]), 1
    )
    saved = json.loads((output_dir / "summaries/u01.summary.json").read_text())
    assert saved["who_is_who"] == "" and saved["where_is_where"] == ""
    assert final["book_memory"].who_is_who == ""


def test_card_changes_schema_has_no_regex_pattern_and_is_strict() -> None:
    from pov_retell.infrastructure.llm import strict_json_schema

    schema = strict_json_schema(CardChanges)
    assert '"pattern"' not in json.dumps(schema)

    def objects(node: Any) -> list[dict[str, Any]]:
        if isinstance(node, dict):
            found = [node] if node.get("type") == "object" else []
            return found + [item for value in node.values() for item in objects(value)]
        if isinstance(node, list):
            return [item for value in node for item in objects(value)]
        return []

    assert objects(schema) and all(o["additionalProperties"] is False for o in objects(schema))


def test_update_prompts_ask_for_json_entries_not_pipe_lines() -> None:
    for prompt in (PROMPT_UPDATE_WHO_IS_WHO, PROMPT_UPDATE_WHERE_IS_WHERE):
        assert 'separated by " | "' not in prompt
        assert "exactly three fields separated" not in prompt
        assert '"add"' in prompt and '"update"' in prompt and '"other_names"' in prompt
