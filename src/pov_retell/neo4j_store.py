"""Everything that talks to Neo4j: connection, health check, schema, and idempotent writes.

Why MERGE: every write is `MERGE` on the node's key, then `SET` its properties. Running the same
ingest twice therefore changes nothing (no duplicate nodes, no duplicate edges), which is what
makes a crashed run safe to resume or to repeat.

Why UNWIND: one query per batch of rows instead of one query per row. 2,000 paragraphs take a
handful of round trips instead of 2,000.

The rest of the code never imports `neo4j`: the ingest graph only knows the `GraphWriter`
protocol (see ingest_graph.py). That is what lets the tests run with an in-memory fake.
"""

from collections.abc import Iterator
from typing import Any

from neo4j import Driver, GraphDatabase, NotificationMinimumSeverity
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from pov_retell.config import Settings

BATCH = 500  # rows per transaction: big enough to be fast, small enough to stay light

# `IF NOT EXISTS` makes this safe to run on every ingest. A uniqueness constraint also creates
# the index that makes MERGE and MATCH on those keys fast. The key of a Unit or Paragraph includes
# book_id because "u02" exists in every book.
SCHEMA = [
    "CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.id IS UNIQUE",
    "CREATE CONSTRAINT unit_key IF NOT EXISTS FOR (u:Unit) REQUIRE (u.book_id, u.id) IS UNIQUE",
    "CREATE CONSTRAINT paragraph_key IF NOT EXISTS "
    "FOR (p:Paragraph) REQUIRE (p.book_id, p.id) IS UNIQUE",
]


class Neo4jUnavailable(RuntimeError):
    """Neo4j cannot be reached or refused the credentials. The message says what to do."""


def connect(settings: Settings) -> Driver:
    """Open a driver from the settings. The password is read here and never printed."""
    password = settings.NEO4J_PASSWORD.get_secret_value()
    if not password:
        raise Neo4jUnavailable(
            "NEO4J_PASSWORD is not set: put it in ~/.config/book-clone/secrets.env, "
            "then run `make neo4j-up`"
        )
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.NEO4J_USER, password),
        # Neo4j warns about every label or property it has not seen yet ("does not exist"). On a
        # fresh database that is just noise, and it would bury the node events in the console.
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )


def check_health(driver: Driver) -> dict[str, str]:
    """Return the server name, version and edition, or raise Neo4jUnavailable."""
    try:
        driver.verify_connectivity()
        record, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        )
    except (ServiceUnavailable, OSError) as exc:
        raise Neo4jUnavailable("cannot reach Neo4j: is it up? run `make neo4j-up`") from exc
    except Neo4jError as exc:  # wrong password, for example
        raise Neo4jUnavailable(f"Neo4j refused the request: {exc.message}") from exc
    return dict(record[0])


def _batches(rows: list[Any]) -> Iterator[list[Any]]:
    for start in range(0, len(rows), BATCH):
        yield rows[start : start + BATCH]


class Neo4jWriter:
    """The real `GraphWriter`: Cypher over a driver."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _run(self, query: str, **params: Any) -> list[Any]:
        """One query in its own transaction (execute_query retries transient errors for us)."""
        records, _, _ = self._driver.execute_query(query, **params)
        return list(records)

    def ensure_schema(self) -> None:
        for statement in SCHEMA:
            self._run(statement)

    def book_sha256(self, book_id: str) -> str | None:
        records = self._run("MATCH (b:Book {id: $id}) RETURN b.sha256 AS sha256", id=book_id)
        return records[0]["sha256"] if records else None

    def delete_book(self, book_id: str) -> None:
        """Remove a book's units and paragraphs (not the Book node) so it can be rewritten."""
        for label in ("Paragraph", "Unit"):
            deleted = BATCH
            while deleted:  # in chunks, so a big book does not become one huge transaction
                deleted = self._run(
                    f"MATCH (n:{label} {{book_id: $id}}) WITH n LIMIT $n "
                    "DETACH DELETE n RETURN count(*) AS deleted",
                    id=book_id,
                    n=BATCH,
                )[0]["deleted"]

    def write_book(self, book: dict[str, Any]) -> None:
        self._run("MERGE (b:Book {id: $book.id}) SET b += $book", book=book)

    def write_units(
        self,
        book_id: str,
        units: list[dict[str, Any]],
        next_pairs: list[tuple[str, str]],
        contains_pairs: list[tuple[str, str]],
    ) -> None:
        for rows in _batches(units):
            self._run(
                "MATCH (b:Book {id: $book_id}) UNWIND $rows AS row "
                "MERGE (u:Unit {book_id: $book_id, id: row.id}) SET u += row "
                "MERGE (b)-[:HAS_UNIT]->(u)",
                book_id=book_id,
                rows=rows,
            )
        for rel, pairs in (("NEXT", next_pairs), ("CONTAINS", contains_pairs)):
            for batch in _batches(pairs):
                self._run(
                    "UNWIND $pairs AS pair "
                    "MATCH (a:Unit {book_id: $book_id, id: pair[0]}), "
                    "(c:Unit {book_id: $book_id, id: pair[1]}) "
                    f"MERGE (a)-[:{rel}]->(c)",
                    book_id=book_id,
                    pairs=batch,
                )

    def write_paragraphs(
        self, book_id: str, paragraphs: list[dict[str, Any]], next_pairs: list[tuple[str, str]]
    ) -> None:
        for rows in _batches(paragraphs):
            self._run(
                "UNWIND $rows AS row "
                "MATCH (u:Unit {book_id: $book_id, id: row.unit_id}) "
                "MERGE (p:Paragraph {book_id: $book_id, id: row.id}) SET p += row "
                "MERGE (u)-[:HAS_PARAGRAPH]->(p)",
                book_id=book_id,
                rows=rows,
            )
        for batch in _batches(next_pairs):
            self._run(
                "UNWIND $pairs AS pair "
                "MATCH (a:Paragraph {book_id: $book_id, id: pair[0]}), "
                "(c:Paragraph {book_id: $book_id, id: pair[1]}) "
                "MERGE (a)-[:NEXT]->(c)",
                book_id=book_id,
                pairs=batch,
            )

    def counts(self, book_id: str) -> dict[str, int]:
        """What Neo4j holds for this book, under the same keys as ingest_graph.expected_counts."""
        queries = {
            "units": "MATCH (n:Unit {book_id: $id}) RETURN count(n) AS n",
            "paragraphs": "MATCH (n:Paragraph {book_id: $id}) RETURN count(n) AS n",
            "has_unit": "MATCH (:Book {id: $id})-[r:HAS_UNIT]->(:Unit) RETURN count(r) AS n",
            "has_paragraph": (
                "MATCH (:Unit {book_id: $id})-[r:HAS_PARAGRAPH]->(:Paragraph) RETURN count(r) AS n"
            ),
            "unit_next": "MATCH (:Unit {book_id: $id})-[r:NEXT]->(:Unit) RETURN count(r) AS n",
            "contains": "MATCH (:Unit {book_id: $id})-[r:CONTAINS]->(:Unit) RETURN count(r) AS n",
            "paragraph_next": (
                "MATCH (:Paragraph {book_id: $id})-[r:NEXT]->(:Paragraph) RETURN count(r) AS n"
            ),
        }
        return {name: self._run(query, id=book_id)[0]["n"] for name, query in queries.items()}


def books_overview(driver: Driver) -> list[dict[str, Any]]:
    """One row per book: how much of it is in Neo4j. For `pov neo4j-status`."""
    records, _, _ = driver.execute_query(
        "MATCH (b:Book) "
        "OPTIONAL MATCH (b)-[:HAS_UNIT]->(u:Unit) "
        "WITH b, count(u) AS units "
        "OPTIONAL MATCH (p:Paragraph {book_id: b.id}) "
        "RETURN b.id AS id, b.title AS title, units, count(p) AS paragraphs ORDER BY id"
    )
    return [dict(r) for r in records]
