"""Wiring of the extract_story graph: a book loop around a per-chapter subgraph.

Node logic lives in nodes.py, output.py and steps/*; this module only connects them.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.ingest.graph.extract_story import nodes, output
from pov_retell.ingest.graph.extract_story.context import StoryContext
from pov_retell.ingest.graph.extract_story.state import StoryInput, StoryState
from pov_retell.ingest.graph.extract_story.steps.registry import STEPS

# Two nodes (extract, validate) per step, plus save_json and save_graph, plus initialize.
EXTRACT_NODES_PER_CHAPTER = len(STEPS) * 2 + 2


def extract_story_recursion_limit(chapter_count: int) -> int:
    return max(25, chapter_count * (EXTRACT_NODES_PER_CHAPTER + 1) + 10)


def build_chapter_graph() -> CompiledStateGraph[StoryState, StoryContext, StoryState, StoryState]:
    """Extract, validate and save one chapter. Steps run in the order of STEPS."""
    graph = StateGraph(StoryState, context_schema=StoryContext)
    previous = START
    for step in STEPS:
        graph.add_node(f"extract_{step.name}", step.extract)
        graph.add_node(f"validate_{step.name}", step.validate)
        graph.add_edge(previous, f"extract_{step.name}")
        graph.add_edge(f"extract_{step.name}", f"validate_{step.name}")
        previous = f"validate_{step.name}"
    graph.add_node("save_json", output.save_json)
    graph.add_node("save_graph", output.save_graph)
    graph.add_edge(previous, "save_json")
    graph.add_edge("save_json", "save_graph")
    graph.add_edge("save_graph", END)
    return graph.compile()


def build_extract_story_graph() -> CompiledStateGraph[
    StoryState, StoryContext, StoryInput, StoryState
]:
    graph = StateGraph(StoryState, context_schema=StoryContext, input_schema=StoryInput)
    graph.add_node("initialize", nodes.initialize)
    graph.add_node("chapter", build_chapter_graph())
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "chapter")
    graph.add_conditional_edges(
        "chapter", nodes.next_step, {"next_chapter": "chapter", "done": END}
    )
    return graph.compile()
