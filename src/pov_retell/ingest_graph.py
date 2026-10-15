"""The ingest graph: `extracted/<book_id>/book.json` -> Neo4j, as a LangGraph StateGraph.

    START -> load_extracted -> validate --ok--> ensure_schema -> write_book -> write_units
                                  |                                               |
                                invalid -> END                                write_paragraphs
                                                                                  |
          END <--(no analysis)-- verify <---------------------------------------- '
                                  '--(analysis on)--> analysis_placeholder -> END

Deterministic, no LLM. Why a graph and not a plain function? Each node is one small, named,
testable step; the framework checkpoints the state after every node (so a crashed run resumes
at the node that failed instead of starting over) and streams an event per node. See
docs/INGEST_BASE.md for the LangGraph vocabulary explained on this very file.

The graph only knows the `GraphWriter` protocol, never the Neo4j driver: tests plug in a fake.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from pov_retell.models import NARRATIVE_KINDS, SCHEMA_VERSION, ExtractedBook

Pairs = list[tuple[str, str]]


class IngestState(TypedDict, total=False):
    """The state every node reads and updates. A node returns ONLY the keys it changes."""

    book_id: str  # input: which extraction to ingest
    replace: bool  # input: delete the book's old units/paragraphs first
    analysis: bool  # input: also run the (placeholder) analysis node after verify
    extracted: dict[str, Any]  # book.json as plain data (checkpoint-friendly, see load_extracted)
    errors: list[str]  # problems found; a non-empty list ends the run
    written: dict[str, int]  # how many rows each write node sent to Neo4j


class GraphWriter(Protocol):
    """What the graph needs from a database. `Neo4jWriter` is the real one; tests use a fake."""

    def ensure_schema(self) -> None: ...
    def book_sha256(self, book_id: str) -> str | None: ...
    def delete_book(self, book_id: str) -> None: ...
    def write_book(self, book: dict[str, Any]) -> None: ...
    def write_units(
        self, book_id: str, units: list[dict[str, Any]], next_pairs: Pairs, contains_pairs: Pairs
    ) -> None: ...
    def write_paragraphs(
        self, book_id: str, paragraphs: list[dict[str, Any]], next_pairs: Pairs
    ) -> None: ...
    def counts(self, book_id: str) -> dict[str, int]: ...


# ----------------------------------------------------------------- pure helpers (easy to test)


def unit_edges(units: list[dict[str, Any]]) -> tuple[Pairs, Pairs]:
    """(NEXT pairs, CONTAINS pairs). NEXT chains the narrative units (chapters, letters,
    sections) in reading order, because that is what the NEXT button follows; parts are skipped
    and linked to their chapters by CONTAINS instead."""
    narrative = [
        u["id"] for u in sorted(units, key=lambda u: u["order"]) if u["kind"] in NARRATIVE_KINDS
    ]
    contains = [(u["parent_id"], u["id"]) for u in units if u.get("parent_id")]
    return list(zip(narrative, narrative[1:], strict=False)), contains


def paragraph_edges(paragraphs: list[dict[str, Any]]) -> Pairs:
    """NEXT pairs between consecutive paragraphs of the same unit (the chain restarts per unit)."""
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for p in paragraphs:
        by_unit.setdefault(p["unit_id"], []).append(p)
    pairs: Pairs = []
    for group in by_unit.values():
        ordered = sorted(group, key=lambda p: p["order"])
        pairs += [(a["id"], b["id"]) for a, b in zip(ordered, ordered[1:], strict=False)]
    return pairs


def expected_counts(extracted: dict[str, Any]) -> dict[str, int]:
    """What Neo4j should hold after the ingest, computed from book.json alone."""
    units, paragraphs = extracted["units"], extracted["paragraphs"]
    unit_next, contains = unit_edges(units)
    return {
        "units": len(units),
        "paragraphs": len(paragraphs),
        "has_unit": len(units),
        "has_paragraph": len(paragraphs),
        "unit_next": len(unit_next),
        "contains": len(contains),
        "paragraph_next": len(paragraph_edges(paragraphs)),
    }


def validate_extracted(raw: dict[str, Any], book_id: str) -> list[str]:
    """Everything that must be true of book.json before we write a single node."""
    if raw.get("schema_version") != SCHEMA_VERSION:
        return [
            f"schema_version is {raw.get('schema_version')!r}, this code reads {SCHEMA_VERSION}"
        ]
    try:
        ExtractedBook.model_validate(raw)  # the phase A models are the contract of the file
    except ValidationError as exc:
        return [f"book.json does not match the phase A models: {exc.errors()[0]['msg']}"]

    errors: list[str] = []
    units, paragraphs = raw["units"], raw["paragraphs"]
    if raw["book"]["id"] != book_id:
        errors.append(f"book.json holds book {raw['book']['id']!r}, not {book_id!r}")
    if not units or not paragraphs:
        errors.append("book.json has no units or no paragraphs")
    if [u["order"] for u in units] != list(range(1, len(units) + 1)):
        errors.append("unit orders are not 1..n in sequence")
    for name, rows in (("unit", units), ("paragraph", paragraphs)):
        if len({r["id"] for r in rows}) != len(rows):
            errors.append(f"duplicate {name} ids")
    kind = {u["id"]: u["kind"] for u in units}
    for u in units:
        if u["parent_id"] is not None and kind.get(u["parent_id"]) != "part":
            errors.append(f"unit {u['id']} has parent {u['parent_id']!r}, which is not a part")
    for p in paragraphs:
        if kind.get(p["unit_id"]) not in NARRATIVE_KINDS or not p["id"].startswith(
            p["unit_id"] + "_"
        ):
            errors.append(f"paragraph {p['id']} does not belong to a chapter-like unit")
    return errors[:10]


# ----------------------------------------------------------------- the graph


def build_graph(
    writer: GraphWriter, extracted_dir: Path, checkpointer: BaseCheckpointSaver[Any] | None = None
) -> CompiledStateGraph[IngestState, Any, IngestState, IngestState]:
    """Wire the nodes. They are closures so each one can use `writer` without global state."""

    def load_extracted(state: IngestState) -> IngestState:
        """Read book.json as PLAIN data, not as a Pydantic model: the checkpointer must be able to
        save and reload the state, and plain dicts are always safe for that."""
        path = extracted_dir / state["book_id"] / "book.json"
        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist: run `pov extract` first")
        return {"extracted": json.loads(path.read_text(encoding="utf-8"))}

    def validate(state: IngestState) -> IngestState:
        return {"errors": validate_extracted(state["extracted"], state["book_id"])}

    def ensure_schema(state: IngestState) -> IngestState:
        writer.ensure_schema()
        return {}

    def write_book(state: IngestState) -> IngestState:
        book_id, raw = state["book_id"], state["extracted"]
        old_sha = writer.book_sha256(book_id)
        if old_sha is not None and old_sha != raw["book"]["sha256"] and not state.get("replace"):
            raise ValueError(
                f"Neo4j already holds book {book_id!r} from a different file; "
                "re-run with --replace to overwrite it"
            )
        if state.get("replace"):
            writer.delete_book(book_id)
        writer.write_book(
            {**raw["book"], "map_method": raw["map_method"], "schema_version": SCHEMA_VERSION}
        )
        return {"written": {"books": 1}}

    def write_units(state: IngestState) -> IngestState:
        units = state["extracted"]["units"]
        next_pairs, contains_pairs = unit_edges(units)
        writer.write_units(state["book_id"], units, next_pairs, contains_pairs)
        return {"written": {**state["written"], "units": len(units)}}

    def write_paragraphs(state: IngestState) -> IngestState:
        paragraphs = state["extracted"]["paragraphs"]
        writer.write_paragraphs(state["book_id"], paragraphs, paragraph_edges(paragraphs))
        return {"written": {**state["written"], "paragraphs": len(paragraphs)}}

    def verify(state: IngestState) -> IngestState:
        """Count what Neo4j really holds and compare with what book.json says it should."""
        expected, actual = expected_counts(state["extracted"]), writer.counts(state["book_id"])
        wrong = [
            f"{k}: book.json {expected[k]}, Neo4j {actual.get(k)}"
            for k in expected
            if actual.get(k) != expected[k]
        ]
        hint = ["(old rows of an earlier extraction? re-run with --replace)"] if wrong else []
        return {"errors": wrong + hint}

    # ============================ EXTENSION POINT ============================
    # Analysis steps (B1 mentions, B2 roster, ...) are added HERE: one function per step, then
    # `graph.add_node` and the edges below. docs/INGEST_BASE.md shows it step by step.
    def analysis_placeholder(state: IngestState) -> IngestState:
        """Does nothing. Off by default: only `pov ingest --analysis` routes here."""
        return {}

    def after_validate(state: IngestState) -> Literal["ok", "invalid"]:
        return "invalid" if state.get("errors") else "ok"

    def after_verify(state: IngestState) -> Literal["analysis", "done"]:
        return "analysis" if state.get("analysis") and not state.get("errors") else "done"

    graph = StateGraph(IngestState)
    nodes = [load_extracted, validate, ensure_schema, write_book, write_units]
    for node in [*nodes, write_paragraphs, verify, analysis_placeholder]:
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "load_extracted")
    graph.add_edge("load_extracted", "validate")
    graph.add_conditional_edges("validate", after_validate, {"ok": "ensure_schema", "invalid": END})
    graph.add_edge("ensure_schema", "write_book")
    graph.add_edge("write_book", "write_units")
    graph.add_edge("write_units", "write_paragraphs")
    graph.add_edge("write_paragraphs", "verify")
    graph.add_conditional_edges(
        "verify", after_verify, {"analysis": "analysis_placeholder", "done": END}
    )
    graph.add_edge("analysis_placeholder", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


# ----------------------------------------------------------------- running it


def thread_config(book_id: str) -> RunnableConfig:
    """A `thread_id` names one run's saved state. Same id = same checkpoints = resumable."""
    return {"configurable": {"thread_id": f"ingest-{book_id}"}}


@contextmanager
def open_checkpointer(
    kind: Literal["memory", "sqlite"], sqlite_path: Path
) -> Iterator[BaseCheckpointSaver[Any]]:
    """Memory (default): lost when the process ends. SQLite: a file, so a crashed run can resume."""
    if kind == "memory":
        yield InMemorySaver()
        return
    from langgraph.checkpoint.sqlite import SqliteSaver

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path, check_same_thread=False)
    try:
        yield SqliteSaver(connection)
    finally:
        connection.close()


@dataclass(frozen=True)
class NodeEvent:
    node: str
    status: Literal["start", "ok", "error"]
    seconds: float = 0.0
    detail: str = ""


def stream_events(
    graph: CompiledStateGraph[IngestState, Any, IngestState, IngestState],
    graph_input: IngestState | None,
    config: RunnableConfig,
) -> Iterator[NodeEvent]:
    """Run the graph and yield one event when a node starts and one when it ends.

    `graph_input=None` means "continue from the last checkpoint" (that is how `--resume` works).
    stream_mode="debug" reports every task with a timestamp, which gives us the duration.
    """
    started: dict[str, datetime] = {}
    running = ""
    try:
        for event in graph.stream(graph_input, config, stream_mode="debug"):
            payload, when = event["payload"], datetime.fromisoformat(event["timestamp"])
            if event["type"] == "task":
                running = payload["name"]
                started[running] = when
                yield NodeEvent(running, "start")
            elif event["type"] == "task_result":
                result = payload.get("result") or {}
                seconds = (when - started[payload["name"]]).total_seconds()
                yield NodeEvent(payload["name"], "ok", seconds, _detail(result))
                running = ""
    except Exception as exc:
        if running:
            elapsed = (datetime.now(tz=started[running].tzinfo) - started[running]).total_seconds()
            yield NodeEvent(running, "error", elapsed, f"{type(exc).__name__}: {exc}")
        raise


def _detail(result: dict[str, Any]) -> str:
    if result.get("errors"):
        return f"{len(result['errors'])} problem(s)"
    if "errors" in result:
        return "ok"
    written = result.get("written")
    return "{}={}".format(*list(written.items())[-1]) if written else ""
