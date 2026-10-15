"""The ingest graph, run against an in-memory fake writer (no Neo4j, no network)."""

import json
from pathlib import Path
from typing import Any

import pytest
import samples
from fake_writer import FakeWriter

from pov_retell.ingest_graph import (
    GraphWriter,
    IngestState,
    NodeEvent,
    build_graph,
    expected_counts,
    open_checkpointer,
    paragraph_edges,
    stream_events,
    thread_config,
    unit_edges,
    validate_extracted,
)
from pov_retell.load import Source
from pov_retell.models import SCHEMA_VERSION
from pov_retell.output import save_extraction
from pov_retell.pipeline import extract_book

BOOK = "the-lantern-keeper"
NODES = ["load_extracted", "validate", "ensure_schema", "write_book", "write_units",
         "write_paragraphs", "verify"]  # fmt: skip


@pytest.fixture
def extracted_dir(tmp_path: Path) -> Path:
    """Phase A's real output for the invented story: 2 parts, 3 chapters, 7 paragraphs."""
    result = extract_book(Source(samples.render_txt(), "lantern.txt", "/tmp/lantern.txt"))
    save_extraction(result, tmp_path)
    return tmp_path


def run(
    writer: GraphWriter, extracted_dir: Path, replace: bool = False, analysis: bool = False
) -> tuple[list[NodeEvent], dict[str, Any]]:
    graph = build_graph(writer, extracted_dir)
    config = thread_config(BOOK)
    graph_input: IngestState = {"book_id": BOOK, "replace": replace, "analysis": analysis}
    events = list(stream_events(graph, graph_input, config))
    return events, dict(graph.get_state(config).values)


def finished(events: list[NodeEvent]) -> list[str]:
    return [e.node for e in events if e.status == "ok"]


def test_the_whole_book_is_written_and_verified(extracted_dir: Path) -> None:
    writer = FakeWriter()
    events, state = run(writer, extracted_dir)

    assert finished(events) == NODES
    assert state["errors"] == []
    assert writer.counts(BOOK) == {
        "units": 5, "paragraphs": 7, "has_unit": 5, "has_paragraph": 7,
        "unit_next": 2,  # 3 chapters -> 2 links; the 2 parts are not chained
        "contains": 3,  # each chapter hangs under its part
        "paragraph_next": 4,  # (3 + 2 + 2 paragraphs) minus one per chapter
    }  # fmt: skip
    assert state["written"] == {"books": 1, "units": 5, "paragraphs": 7}


def test_what_is_stored_on_the_nodes(extracted_dir: Path) -> None:
    writer = FakeWriter()
    run(writer, extracted_dir)
    book = writer.books[BOOK]
    assert (book["title"], book["format"], book["map_method"]) == (
        "The Lantern Keeper",
        "txt",
        "heuristic",
    )
    assert book["schema_version"] == SCHEMA_VERSION and len(book["sha256"]) == 64
    paragraph = writer.paragraphs[(BOOK, "u02_p001")]
    assert paragraph["text"].startswith(
        "One evening the keeper climbed"
    )  # the text lives on the node
    assert paragraph["unit_id"] == "u02" and paragraph["flags"] == []
    assert writer.units[(BOOK, "u02")]["parent_id"] == "u01"


def test_unit_and_paragraph_edges() -> None:
    units = [
        {"id": "u01", "order": 1, "kind": "part", "parent_id": None},
        {"id": "u02", "order": 2, "kind": "chapter", "parent_id": "u01"},
        {"id": "u03", "order": 3, "kind": "chapter", "parent_id": "u01"},
    ]
    assert unit_edges(units) == ([("u02", "u03")], [("u01", "u02"), ("u01", "u03")])
    paragraphs = [
        {"id": "u03_p002", "unit_id": "u03", "order": 2},  # deliberately out of order
        {"id": "u03_p001", "unit_id": "u03", "order": 1},
        {"id": "u02_p001", "unit_id": "u02", "order": 1},
    ]
    assert paragraph_edges(paragraphs) == [("u03_p001", "u03_p002")]  # the chain restarts per unit


def test_running_twice_creates_no_duplicates(extracted_dir: Path) -> None:
    writer = FakeWriter()
    run(writer, extracted_dir)
    first = writer.counts(BOOK)
    _, state = run(writer, extracted_dir)
    assert writer.counts(BOOK) == first and state["errors"] == []


def test_a_wrong_schema_version_stops_before_anything_is_written(extracted_dir: Path) -> None:
    path = extracted_dir / BOOK / "book.json"
    data = json.loads(path.read_text())
    data["schema_version"] = 99
    path.write_text(json.dumps(data))

    writer = FakeWriter()
    events, state = run(writer, extracted_dir)
    assert finished(events) == ["load_extracted", "validate"]  # the conditional edge went to END
    assert "schema_version" in state["errors"][0]
    assert writer.calls == []


def test_a_missing_extraction_is_a_clear_error(tmp_path: Path) -> None:
    events: list[NodeEvent] = []
    with pytest.raises(FileNotFoundError, match="pov extract"):
        for event in stream_events(
            build_graph(FakeWriter(), tmp_path), {"book_id": "nope"}, thread_config("nope")
        ):
            events.append(event)
    assert (events[-1].node, events[-1].status) == ("load_extracted", "error")


def test_validate_extracted_catches_broken_books(extracted_dir: Path) -> None:
    good = json.loads((extracted_dir / BOOK / "book.json").read_text())
    assert validate_extracted(good, BOOK) == []
    assert "not 'other'" in validate_extracted(good, "other")[0]

    def problems(change: Any) -> str:
        data = json.loads(json.dumps(good))
        change(data)
        return " | ".join(validate_extracted(data, BOOK))

    assert "duplicate unit ids" in problems(lambda d: d["units"][1].update(id="u01"))
    assert "1..n" in problems(lambda d: d["units"][1].update(order=9))
    assert "duplicate paragraph ids" in problems(lambda d: d["paragraphs"][1].update(id="u02_p001"))
    assert "not a part" in problems(lambda d: d["units"][2].update(parent_id="u02"))
    assert "does not belong" in problems(lambda d: d["paragraphs"][0].update(unit_id="u01"))
    assert "phase A models" in problems(lambda d: d["units"][0].pop("title"))


def test_stale_rows_are_caught_by_verify_and_cleaned_by_replace(extracted_dir: Path) -> None:
    writer = FakeWriter()
    run(writer, extracted_dir)
    writer.units[(BOOK, "u99")] = {"id": "u99"}  # left over from an earlier, different extraction

    _, state = run(writer, extracted_dir)
    assert "units: book.json 5, Neo4j 6" in state["errors"][0]
    assert "--replace" in state["errors"][-1]

    _, state = run(writer, extracted_dir, replace=True)
    assert state["errors"] == [] and (BOOK, "u99") not in writer.units


def test_a_different_file_under_the_same_book_id_is_refused(extracted_dir: Path) -> None:
    writer = FakeWriter()
    run(writer, extracted_dir)
    writer.books[BOOK]["sha256"] = "0" * 64  # as if another edition had been ingested

    with pytest.raises(ValueError, match="different file"):
        run(writer, extracted_dir)
    _, state = run(writer, extracted_dir, replace=True)  # --replace overwrites it
    assert state["errors"] == [] and writer.books[BOOK]["sha256"] != "0" * 64


def test_the_analysis_placeholder_runs_only_when_asked(extracted_dir: Path) -> None:
    assert "analysis_placeholder" not in finished(run(FakeWriter(), extracted_dir)[0])
    assert (
        finished(run(FakeWriter(), extracted_dir, analysis=True)[0])[-1] == "analysis_placeholder"
    )


def test_events_carry_status_duration_and_detail(extracted_dir: Path) -> None:
    events, _ = run(FakeWriter(), extracted_dir)
    assert [(e.node, e.status) for e in events[:3]] == [
        ("load_extracted", "start"),
        ("load_extracted", "ok"),
        ("validate", "start"),
    ]
    done = {e.node: e for e in events if e.status == "ok"}
    assert all(e.seconds >= 0 for e in done.values())
    assert (done["validate"].detail, done["write_units"].detail) == ("ok", "units=5")


def test_a_crashed_run_resumes_at_the_failed_node(extracted_dir: Path, tmp_path: Path) -> None:
    writer = FakeWriter(fail_once_in="write_paragraphs")
    config = thread_config(BOOK)
    with open_checkpointer("sqlite", tmp_path / "cp" / "checkpoints.sqlite") as saver:
        graph = build_graph(writer, extracted_dir, saver)
        with pytest.raises(OSError, match="simulated crash"):
            list(stream_events(graph, {"book_id": BOOK}, config))
        assert graph.get_state(config).next == ("write_paragraphs",)
        assert writer.counts(BOOK)["paragraphs"] == 0 and writer.counts(BOOK)["units"] == 5

        resumed = list(stream_events(graph, None, config))  # None = continue from the checkpoint
        assert finished(resumed) == ["write_paragraphs", "verify"]  # nothing earlier runs again
        assert graph.get_state(config).values["errors"] == []
    assert writer.calls.count("write_book") == 1 and writer.counts(BOOK)["paragraphs"] == 7


def test_the_sqlite_checkpointer_keeps_state_in_a_file(extracted_dir: Path, tmp_path: Path) -> None:
    db = tmp_path / "checkpoints.sqlite"
    with open_checkpointer("sqlite", db) as saver:
        run_graph = build_graph(FakeWriter(), extracted_dir, saver)
        list(stream_events(run_graph, {"book_id": BOOK}, thread_config(BOOK)))
    with open_checkpointer("sqlite", db) as saver:  # a NEW connection (as in a new process)
        state = build_graph(FakeWriter(), extracted_dir, saver).get_state(thread_config(BOOK))
    assert state.values["written"]["paragraphs"] == 7 and state.next == ()


def test_the_mermaid_diagram_shows_nodes_and_conditional_edges() -> None:
    diagram = build_graph(FakeWriter(), Path(".")).get_graph().draw_mermaid()
    for name in [*NODES, "analysis_placeholder", "ok", "invalid", "done", "analysis"]:
        assert name in diagram


def test_expected_counts_come_from_book_json_alone(extracted_dir: Path) -> None:
    data = json.loads((extracted_dir / BOOK / "book.json").read_text())
    assert expected_counts(data)["paragraphs"] == len(data["paragraphs"]) == 7


def test_state_keys_are_documented() -> None:
    assert set(IngestState.__annotations__) == {
        "book_id", "replace", "analysis", "extracted", "errors", "written",
    }  # fmt: skip
