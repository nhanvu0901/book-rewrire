from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.infrastructure.llm import TextLLM
from pov_retell.ingest.graph.summarize_chapter import logic
from pov_retell.ingest.graph.summarize_chapter.model import (
    ChapterSummary,
    SummarizeChapterState,
)

SUMMARY_NODES_PER_CHAPTER = 3


def summarize_chapter_recursion_limit(chapter_count: int) -> int:
    return max(25, chapter_count * (SUMMARY_NODES_PER_CHAPTER + 1) + 10)


def build_summarize_chapter_graph(
    llm: TextLLM,
    on_step: Callable[[str], None] | None = None,
) -> CompiledStateGraph[SummarizeChapterState, Any, SummarizeChapterState, SummarizeChapterState]:
    def report(message: str) -> None:
        if on_step is not None:
            on_step(message)

    def initialize(state: SummarizeChapterState) -> SummarizeChapterState:
        if not state["chapters"]:
            raise ValueError("Chapter summarization requires chapters")
        return {"chapter_index": 0, "who_is_who": "", "where_is_where": "", "summaries": []}

    def summarize_chapter(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"summarize_chapter {chapter.unit_id}")
        return {
            "proposed": logic.summarize_chapter(llm, state["title"], chapter, state["summaries"])
        }

    def validate_summary(state: SummarizeChapterState) -> SummarizeChapterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_summary {chapter.unit_id}")
        return {
            "summary": ChapterSummary(
                chapter_id=chapter.unit_id,
                **state["proposed"].model_dump(),
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
    for node in (initialize, summarize_chapter, validate_summary, save_summary, summarize_book):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "summarize_chapter")
    graph.add_edge("summarize_chapter", "validate_summary")
    graph.add_edge("validate_summary", "save_summary")
    graph.add_conditional_edges(
        "save_summary", next_step, {"next_chapter": "summarize_chapter", "done": "summarize_book"}
    )
    graph.add_edge("summarize_book", END)
    return graph.compile()
