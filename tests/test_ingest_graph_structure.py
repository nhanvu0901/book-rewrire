"""Structure of the ingestion graphs: step order, wiring, runtime context and import rules."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from test_character_ingest import RecordingWriter, ScriptedLLM, make_extraction
from test_events import ACCUSE, DOOR
from test_knowledge import STORY

from pov_retell.ingest.graph.extract_story.context import StoryContext
from pov_retell.ingest.graph.extract_story.graph import (
    build_chapter_graph,
    build_extract_story_graph,
)
from pov_retell.ingest.graph.extract_story.steps.registry import STEPS
from pov_retell.ingest.graph.summarize_chapter import ChapterSummary
from pov_retell.ingest.graph.summarize_chapter.context import SummaryContext
from pov_retell.ingest.graph.summarize_chapter.graph import build_summarize_chapter_graph
from pov_retell.ingest.source import load_chapters

GRAPH_DIR = Path(__file__).parents[1] / "src/pov_retell/ingest/graph"
STORY_DIR = GRAPH_DIR / "extract_story"
STEP_NAMES = ["characters", "relationships", "locations", "scenes", "events", "knowledge"]
IMPORT_ROOT = "pov_retell.ingest.graph"


def test_steps_run_in_dependency_order() -> None:
    assert [step.name for step in STEPS] == STEP_NAMES


def test_chapter_subgraph_has_one_extract_and_validate_node_per_step() -> None:
    expected = [node for name in STEP_NAMES for node in (f"extract_{name}", f"validate_{name}")] + [
        "save_json",
        "save_graph",
    ]
    nodes = [n for n in build_chapter_graph().get_graph().nodes if not n.startswith("__")]
    assert nodes == expected


def test_parent_graph_only_wires_the_chapter_loop() -> None:
    nodes = [n for n in build_extract_story_graph().get_graph().nodes if not n.startswith("__")]
    assert nodes == ["initialize", "chapter"]
    summary = [n for n in build_summarize_chapter_graph().get_graph().nodes if n[:2] != "__"]
    assert summary == [
        "initialize",
        "summarize_chapter",
        "update_who_is_who",
        "update_where_is_where",
        "validate_summary",
        "save_summary",
        "summarize_book",
    ]


def test_context_reaches_nodes_of_a_subgraph_used_as_a_node() -> None:
    """The design relies on this LangGraph behavior: the parent's context flows into a subgraph."""

    @dataclass
    class Ctx:
        tag: str

    class State(TypedDict, total=False):
        seen: list[str]

    def inner(state: State, runtime: Runtime[Ctx]) -> State:
        return {"seen": [*state["seen"], runtime.context.tag]}

    sub = StateGraph(State, context_schema=Ctx)
    sub.add_node("inner", inner)
    sub.add_edge(START, "inner")
    sub.add_edge("inner", END)
    parent = StateGraph(State, context_schema=Ctx)
    parent.add_node("start", lambda state: {"seen": []})
    parent.add_node("chapter", sub.compile())
    parent.add_edge(START, "start")
    parent.add_edge("start", "chapter")
    parent.add_edge("chapter", END)
    assert parent.compile().invoke({}, context=Ctx("hello")) == {"seen": ["hello"]}


def test_story_context_reaches_every_node(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[DOOR, ACCUSE], ["The guard admitted he had taken the key."]])
    _, chapters = load_chapters(tmp_path / "extracted", "sample")
    summaries = [
        ChapterSummary(chapter_id=c.unit_id, chapter_summary="s", who_is_who="", where_is_where="")
        for c in chapters
    ]
    llm = ScriptedLLM(STORY)
    writer = RecordingWriter()
    writer.start_run("sample", "run_a", "Title", [c.unit_id for c in chapters])
    messages: list[str] = []
    final = build_extract_story_graph().invoke(
        {
            "book_id": "sample",
            "run_id": "run_a",
            "title": "Title",
            "chapters": chapters,
            "summaries": summaries,
            "output_dir": tmp_path / "out",
        },
        {"recursion_limit": 100},
        context=StoryContext(llm, writer, messages.append),
    )
    assert final["chapter_index"] == 2
    for chapter_id in ("u01", "u02"):
        for name in STEP_NAMES:
            assert f"extract_{name} {chapter_id}" in messages
            assert f"validate_{name} {chapter_id}" in messages
        assert any(m.startswith(f"save_characters_json {chapter_id}") for m in messages)
        assert f"save_graph {chapter_id}" in messages
    assert len(llm.calls) == 12  # one call per step and chapter, all via the context's client
    assert [s["chapter_id"] for s in writer.snapshots] == ["u01", "u02"]


def test_summary_context_reaches_every_node(tmp_path: Path) -> None:
    make_extraction(tmp_path, [[DOOR], ["The guard admitted he had taken the key."]])
    _, chapters = load_chapters(tmp_path / "extracted", "sample")
    llm = ScriptedLLM(["Summary one.", "Summary two.", "Core memory."])
    messages: list[str] = []
    final = build_summarize_chapter_graph().invoke(
        {"title": "Title", "chapters": chapters, "output_dir": tmp_path / "out"},
        context=SummaryContext(llm, llm, messages.append),
    )
    assert len(final["summaries"]) == 2
    for chapter_id in ("u01", "u02"):
        for node in (
            "summarize_chapter",
            "update_who_is_who",
            "update_where_is_where",
            "validate_summary",
            "save_summary",
        ):
            assert f"{node} {chapter_id}" in messages
    assert messages[-2:] == ["summarize_book", "save_book_memory"]


def _functions(path: Path) -> list[ast.FunctionDef]:
    return [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef)]


@pytest.mark.parametrize(
    "graph_file", sorted(GRAPH_DIR.glob("*/graph.py")), ids=lambda p: p.parent.name
)
def test_graph_modules_only_wire(graph_file: Path) -> None:
    for function in _functions(graph_file):
        assert function.name.startswith("build_") or function.name.endswith("_recursion_limit")


def test_node_functions_stay_short() -> None:
    files = [*GRAPH_DIR.glob("*/nodes.py"), *STORY_DIR.glob("steps/*/nodes.py")]
    files.append(STORY_DIR / "output.py")
    assert len(files) == 9
    for path in files:
        for function in _functions(path):
            length = (function.end_lineno or 0) - function.lineno + 1
            assert length <= 25, f"{path.name}:{function.name} has {length} lines"


def _imported_modules(path: Path) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


@pytest.mark.parametrize("step", STEP_NAMES)
def test_steps_import_only_earlier_steps_and_shared_modules(step: str) -> None:
    later = STEP_NAMES[STEP_NAMES.index(step) + 1 :]
    forbidden = [f"{IMPORT_ROOT}.extract_story.steps.{name}" for name in [*later, "registry"]]
    forbidden.append(f"{IMPORT_ROOT}.extract_story.graph")
    for path in sorted((STORY_DIR / "steps" / step).glob("*.py")):
        for module in _imported_modules(path):
            assert not any(module == f or module.startswith(f + ".") for f in forbidden), (
                f"{path.relative_to(GRAPH_DIR)} imports {module}"
            )
            if module.startswith(f"{IMPORT_ROOT}.summarize_chapter"):
                assert module == f"{IMPORT_ROOT}.summarize_chapter", (
                    f"{path.relative_to(GRAPH_DIR)} imports {module}"
                )


def test_shared_step_helpers_do_not_import_the_knowledge_step_or_graph() -> None:
    forbidden = (
        f"{IMPORT_ROOT}.extract_story.steps.knowledge",
        f"{IMPORT_ROOT}.extract_story.steps.registry",
        f"{IMPORT_ROOT}.extract_story.graph",
    )
    modules = _imported_modules(STORY_DIR / "steps" / "checks.py")
    assert not [m for m in modules if m.startswith(forbidden)]
