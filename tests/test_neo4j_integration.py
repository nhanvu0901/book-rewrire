"""OPT-IN: the real ingest against the dev Neo4j from docker/compose.yml.

    make neo4j-up          # once
    make test-neo4j        # POV_NEO4J=1 uv run pytest -m neo4j

Skipped unless POV_NEO4J=1, and skipped again when Neo4j is not reachable. It writes ONE throwaway
book (a random id, the invented story) and deletes it afterwards, so your own books stay untouched.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import samples
from neo4j import Driver
from neo4j.exceptions import ConstraintError

from pov_retell.config import Settings
from pov_retell.ingest_graph import build_graph, expected_counts, stream_events, thread_config
from pov_retell.load import Source
from pov_retell.neo4j_store import Neo4jUnavailable, Neo4jWriter, check_health, connect
from pov_retell.output import save_extraction
from pov_retell.pipeline import extract_book

pytestmark = pytest.mark.neo4j


@pytest.fixture(scope="module")
def driver() -> Iterator[Driver]:
    try:
        driver = connect(Settings())
        check_health(driver)
    except Neo4jUnavailable as exc:
        pytest.skip(f"Neo4j is not available: {exc}")
    yield driver
    driver.close()


@pytest.fixture
def book_id(driver: Driver) -> Iterator[str]:
    name = f"test-lantern-{uuid.uuid4().hex[:8]}"
    yield name
    driver.execute_query("MATCH (n {book_id: $id}) DETACH DELETE n", id=name)
    driver.execute_query("MATCH (b:Book {id: $id}) DETACH DELETE b", id=name)


def ingest(driver: Driver, tmp_path: Path, book_id: str, replace: bool = False) -> list[str]:
    result = extract_book(Source(samples.render_txt(), "lantern.txt", "/tmp/x"), book_id=book_id)
    save_extraction(result, tmp_path)
    graph = build_graph(Neo4jWriter(driver), tmp_path)
    config = thread_config(f"{book_id}-{uuid.uuid4().hex[:4]}")
    list(stream_events(graph, {"book_id": book_id, "replace": replace}, config))
    return list(graph.get_state(config).values["errors"])


def query(driver: Driver, cypher: str, **params: str) -> list[dict[str, object]]:
    records, _, _ = driver.execute_query(cypher, parameters_=dict(params))
    return [dict(r) for r in records]


def test_the_book_lands_in_neo4j_with_the_expected_shape(
    driver: Driver, tmp_path: Path, book_id: str
) -> None:
    assert ingest(driver, tmp_path, book_id) == []

    expected = expected_counts(
        extract_book(Source(samples.render_txt(), "x.txt", "x")).model_dump()
    )
    assert Neo4jWriter(driver).counts(book_id) == expected

    # the text lives on the Paragraph nodes, and NEXT walks them in reading order
    rows = query(
        driver,
        "MATCH (:Unit {book_id: $id, id: 'u02'})-[:HAS_PARAGRAPH]->(p:Paragraph) "
        "WHERE NOT ()-[:NEXT]->(p) "
        "MATCH path = (p)-[:NEXT*0..]->(last) WHERE NOT (last)-[:NEXT]->() "
        "RETURN [n IN nodes(path) | n.text] AS texts",
        id=book_id,
    )
    assert rows[0]["texts"] == [" ".join(t.split()) for t in samples.CHAPTERS[0].paragraphs]

    # chapters are chained by NEXT (parts are not), and hang under their part by CONTAINS
    chain = query(
        driver,
        "MATCH (a:Unit {book_id: $id})-[:NEXT]->(b:Unit) RETURN a.id AS a, b.id AS b ORDER BY a",
        id=book_id,
    )
    assert chain == [{"a": "u02", "b": "u03"}, {"a": "u03", "b": "u05"}]
    parts = query(
        driver,
        "MATCH (p:Unit {book_id: $id})-[:CONTAINS]->(c) RETURN p.id AS p, c.id AS c ORDER BY c",
        id=book_id,
    )
    assert parts == [{"p": "u01", "c": "u02"}, {"p": "u01", "c": "u03"}, {"p": "u04", "c": "u05"}]


def test_running_it_again_changes_nothing_and_replace_rewrites(
    driver: Driver, tmp_path: Path, book_id: str
) -> None:
    ingest(driver, tmp_path, book_id)
    before = Neo4jWriter(driver).counts(book_id)
    assert ingest(driver, tmp_path, book_id) == []
    assert Neo4jWriter(driver).counts(book_id) == before

    query(driver, "CREATE (:Unit {book_id: $id, id: 'u99'})", id=book_id)  # a stale leftover
    assert any("units" in e for e in ingest(driver, tmp_path, book_id))  # verify notices it
    assert ingest(driver, tmp_path, book_id, replace=True) == []
    assert Neo4jWriter(driver).counts(book_id) == before


def test_uniqueness_constraints_reject_duplicates(driver: Driver, book_id: str) -> None:
    Neo4jWriter(driver).ensure_schema()
    query(driver, "CREATE (:Unit {book_id: $id, id: 'u01'})", id=book_id)
    with pytest.raises(ConstraintError):
        query(driver, "CREATE (:Unit {book_id: $id, id: 'u01'})", id=book_id)
    # the same unit id in ANOTHER book is fine: that is why the key is (book_id, id)
    query(driver, "CREATE (:Unit {book_id: $id, id: 'u01'})", id=f"{book_id}-2")
    query(driver, "MATCH (n:Unit {book_id: $id}) DELETE n", id=f"{book_id}-2")
