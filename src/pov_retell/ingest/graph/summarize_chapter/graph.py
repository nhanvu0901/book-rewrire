from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.infrastructure.llm import SummarizeLLM
from pov_retell.ingest.graph.summarize_chapter import logic
from pov_retell.ingest.graph.summarize_chapter.model import (
    ChapterSummary,
    SummarizeChapterState,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_where_is_where import (
    PROMPT_UPDATE_WHERE_IS_WHERE,
    WHERE_IS_WHERE_INPUT,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_who_is_who import (
    PROMPT_UPDATE_WHO_IS_WHO,
    WHO_IS_WHO_INPUT,
)

SUMMARY_NODES_PER_CHAPTER = 5


def summarize_chapter_recursion_limit(chapter_count: int) -> int:
    return max(25, chapter_count * (SUMMARY_NODES_PER_CHAPTER + 1) + 10)


def build_summarize_chapter_graph(
    llm: SummarizeLLM,
    on_step: Callable[[str], None] | None = None,
) -> CompiledStateGraph[SummarizeChapterState, Any, SummarizeChapterState, SummarizeChapterState]:
    def report(message: str) -> None:
        if on_step is not None:
            on_step(message)

    def initialize(state: SummarizeChapterState) -> SummarizeChapterState:
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

    def summarize_chapter(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"summarize_chapter {chapter.unit_id}")
        return {
            "chapter_summary": logic.summarize_chapter(
                llm, state["title"], chapter, state["summaries"]
            )
        }

    def update_who_is_who(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"update_who_is_who {chapter.unit_id}")
        update = logic.update_cards(
            llm,
            PROMPT_UPDATE_WHO_IS_WHO,
            WHO_IS_WHO_INPUT,
            state["title"],
            chapter.unit_id,
            chapter.text,
            state.get("who_cards", {}),
            "C",
        )
        return {"who_cards": update}

    def update_where_is_where(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"update_where_is_where {chapter.unit_id}")
        update = logic.update_cards(
            llm,
            PROMPT_UPDATE_WHERE_IS_WHERE,
            WHERE_IS_WHERE_INPUT,
            state["title"],
            chapter.unit_id,
            chapter.text,
            state.get("where_cards", {}),
            "P",
        )
        return {"where_cards": update}

    def validate_summary(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_summary {chapter.unit_id}")
        return {
            "summary": ChapterSummary(
                chapter_id=chapter.unit_id,
                chapter_summary=state["chapter_summary"],
                who_is_who=logic.render_cards(state.get("who_cards", {}), with_ids=False),
                where_is_where=logic.render_cards(state.get("where_cards", {}), with_ids=False),
            )
        }

    def save_summary(state: SummarizeChapterState) -> SummarizeChapterState:
        summary = state["summary"]
        logic.save_summary(
            state["output_dir"] / "summaries" / f"{summary.chapter_id}.summary.json", summary
        )
        report(f"save_summary {summary.chapter_id}")
        return {
            "chapter_index": state["chapter_index"] + 1,
            "who_is_who": summary.who_is_who,
            "where_is_where": summary.where_is_where,
            "summaries": [*state["summaries"], summary],
        }

    def summarize_book(state: SummarizeChapterState) -> SummarizeChapterState:
        report("summarize_book")
        memory = logic.summarize_book(
            llm,
            state["title"],
            state["summaries"],
            state["who_is_who"],
            state["where_is_where"],
        )
        logic.save_summary(state["output_dir"] / "summaries" / "book_memory.json", memory)
        report("save_book_memory")
        return {"book_memory": memory}

    def next_step(state: SummarizeChapterState) -> Literal["next_chapter", "done"]:
        return "next_chapter" if state["chapter_index"] < len(state["chapters"]) else "done"

    graph = StateGraph(SummarizeChapterState)
    for node in (
        initialize,
        summarize_chapter,
        update_who_is_who,
        update_where_is_where,
        validate_summary,
        save_summary,
        summarize_book,
    ):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "summarize_chapter")
    graph.add_edge("summarize_chapter", "update_who_is_who")
    graph.add_edge("update_who_is_who", "update_where_is_where")
    graph.add_edge("update_where_is_where", "validate_summary")
    graph.add_edge("validate_summary", "save_summary")
    graph.add_conditional_edges(
        "save_summary", next_step, {"next_chapter": "summarize_chapter", "done": "summarize_book"}
    )
    graph.add_edge("summarize_book", END)
    return graph.compile()
