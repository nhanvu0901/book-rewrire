"""Nodes of the summarize_chapter graph: read state, call pure logic, return an update."""

from typing import Literal

from langgraph.runtime import Runtime

from pov_retell.ingest import storage
from pov_retell.ingest.graph.summarize_chapter import logic
from pov_retell.ingest.graph.summarize_chapter.context import SummaryContext
from pov_retell.ingest.graph.summarize_chapter.model import ChapterSummary
from pov_retell.ingest.graph.summarize_chapter.prompt.update_where_is_where import (
    PROMPT_UPDATE_WHERE_IS_WHERE,
    WHERE_IS_WHERE_INPUT,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_who_is_who import (
    PROMPT_UPDATE_WHO_IS_WHO,
    WHO_IS_WHO_INPUT,
)
from pov_retell.ingest.graph.summarize_chapter.state import SummarizeChapterState

State = SummarizeChapterState
SummaryRuntime = Runtime[SummaryContext]


def initialize(state: State, runtime: SummaryRuntime) -> State:
    if not state["chapters"]:
        raise ValueError("Chapter summarization requires chapters")
    return {
        "chapter_index": 0,
        "who_cards": {},
        "where_cards": {},
        "who_is_who": "",
        "where_is_where": "",
        "summaries": [],
    }


def summarize_chapter(state: State, runtime: SummaryRuntime) -> State:
    chapter = state["chapters"][state["chapter_index"]]
    runtime.context.report(f"summarize_chapter {chapter.unit_id}")
    return {
        "chapter_summary": logic.summarize_chapter(
            runtime.context.text_llm, state["title"], chapter, state["summaries"]
        )
    }


def update_who_is_who(state: State, runtime: SummaryRuntime) -> State:
    chapter = state["chapters"][state["chapter_index"]]
    runtime.context.report(f"update_who_is_who {chapter.unit_id}")
    update = logic.update_cards(
        runtime.context.card_llm,
        PROMPT_UPDATE_WHO_IS_WHO,
        WHO_IS_WHO_INPUT,
        state["title"],
        chapter.unit_id,
        chapter.text,
        state.get("who_cards", {}),
        "C",
    )
    return {"who_cards": update}


def update_where_is_where(state: State, runtime: SummaryRuntime) -> State:
    chapter = state["chapters"][state["chapter_index"]]
    runtime.context.report(f"update_where_is_where {chapter.unit_id}")
    update = logic.update_cards(
        runtime.context.card_llm,
        PROMPT_UPDATE_WHERE_IS_WHERE,
        WHERE_IS_WHERE_INPUT,
        state["title"],
        chapter.unit_id,
        chapter.text,
        state.get("where_cards", {}),
        "P",
    )
    return {"where_cards": update}


def validate_summary(state: State, runtime: SummaryRuntime) -> State:
    chapter = state["chapters"][state["chapter_index"]]
    runtime.context.report(f"validate_summary {chapter.unit_id}")
    return {
        "summary": ChapterSummary(
            chapter_id=chapter.unit_id,
            chapter_summary=state["chapter_summary"],
            who_is_who=logic.render_cards(state.get("who_cards", {}), with_ids=False),
            where_is_where=logic.render_cards(state.get("where_cards", {}), with_ids=False),
        )
    }


def save_summary(state: State, runtime: SummaryRuntime) -> State:
    summary = state["summary"]
    storage.save_model(
        state["output_dir"] / "summaries" / f"{summary.chapter_id}.summary.json", summary
    )
    runtime.context.report(f"save_summary {summary.chapter_id}")
    return {
        "chapter_index": state["chapter_index"] + 1,
        "who_is_who": summary.who_is_who,
        "where_is_where": summary.where_is_where,
        "summaries": [*state["summaries"], summary],
    }


def summarize_book(state: State, runtime: SummaryRuntime) -> State:
    runtime.context.report("summarize_book")
    memory = logic.summarize_book(
        runtime.context.text_llm,
        state["title"],
        state["summaries"],
        state["who_is_who"],
        state["where_is_where"],
    )
    storage.save_model(state["output_dir"] / "summaries" / "book_memory.json", memory)
    runtime.context.report("save_book_memory")
    return {"book_memory": memory}


def next_step(state: State) -> Literal["next_chapter", "done"]:
    return "next_chapter" if state["chapter_index"] < len(state["chapters"]) else "done"
