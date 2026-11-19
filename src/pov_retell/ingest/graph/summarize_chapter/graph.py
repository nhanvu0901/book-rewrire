"""Wiring of the summarize_chapter graph. Node logic lives in nodes.py and logic.py."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.ingest.graph.summarize_chapter import nodes
from pov_retell.ingest.graph.summarize_chapter.context import SummaryContext
from pov_retell.ingest.graph.summarize_chapter.state import (
    SummarizeChapterInput,
    SummarizeChapterState,
)

SUMMARY_NODES_PER_CHAPTER = 5


def summarize_chapter_recursion_limit(chapter_count: int) -> int:
    return max(25, chapter_count * (SUMMARY_NODES_PER_CHAPTER + 1) + 10)


def build_summarize_chapter_graph() -> CompiledStateGraph[
    SummarizeChapterState, SummaryContext, SummarizeChapterInput, SummarizeChapterState
]:
    graph = StateGraph(
        SummarizeChapterState,
        context_schema=SummaryContext,
        input_schema=SummarizeChapterInput,
    )
    for node in (
        nodes.initialize,
        nodes.summarize_chapter,
        nodes.update_who_is_who,
        nodes.update_where_is_where,
        nodes.validate_summary,
        nodes.save_summary,
        nodes.summarize_book,
    ):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "summarize_chapter")
    graph.add_edge("summarize_chapter", "update_who_is_who")
    graph.add_edge("update_who_is_who", "update_where_is_where")
    graph.add_edge("update_where_is_where", "validate_summary")
    graph.add_edge("validate_summary", "save_summary")
    graph.add_conditional_edges(
        "save_summary",
        nodes.next_step,
        {"next_chapter": "summarize_chapter", "done": "summarize_book"},
    )
    graph.add_edge("summarize_book", END)
    return graph.compile()
