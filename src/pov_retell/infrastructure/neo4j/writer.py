from typing import Any

from neo4j import Driver, ManagedTransaction

from pov_retell.infrastructure.neo4j.cypher import CHAPTER_STATEMENTS, KEYS, SNAPSHOT_LISTS


class Neo4jGraphWriter:
    """Writes a run's story graph after every chapter. Nodes are keyed by book and run."""

    def __init__(self, driver: Driver) -> None:
        self.driver = driver
        self._schema_ready = False

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        for label, key in KEYS.items():
            properties = ", ".join(f"n.{name}" for name in ("book_id", "run_id", *key))
            self.driver.execute_query(
                f"CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS FOR (n:{label}) "
                f"REQUIRE ({properties}) IS UNIQUE"
            )
        self._schema_ready = True

    def start_run(self, book_id: str, run_id: str, title: str, chapter_ids: list[str]) -> None:
        self.ensure_schema()
        self.driver.execute_query(
            "MERGE (r:IngestRun {book_id: $book_id, run_id: $run_id}) "
            "SET r.title = $title, r.chapter_count = $chapter_count, r.status = 'running', "
            "r.chapters_done = 0, r.last_chapter_id = null, r.error = null, "
            "r.started_at = datetime()",
            book_id=book_id,
            run_id=run_id,
            title=title,
            chapter_count=len(chapter_ids),
        )

    def write_chapter(self, book_id: str, run_id: str, snapshot: dict[str, Any]) -> None:
        self.ensure_schema()
        parameters = {
            "book_id": book_id,
            "run_id": run_id,
            "chapter_id": snapshot["chapter_id"],
            "chapters_done": snapshot["chapters_done"],
            **{name: snapshot.get(name, []) for name in SNAPSHOT_LISTS},
        }

        def write(tx: ManagedTransaction) -> None:
            for statement in CHAPTER_STATEMENTS:
                tx.run(statement, parameters).consume()

        with self.driver.session() as session:
            session.execute_write(write)

    def finish_run(self, book_id: str, run_id: str) -> None:
        self.driver.execute_query(
            "MATCH (r:IngestRun {book_id: $book_id, run_id: $run_id}) "
            "SET r.status = 'complete', r.finished_at = datetime()",
            book_id=book_id,
            run_id=run_id,
        )

    def fail_run(self, book_id: str, run_id: str, error: str) -> None:
        self.driver.execute_query(
            "MERGE (r:IngestRun {book_id: $book_id, run_id: $run_id}) "
            "SET r.status = 'failed', r.error = $error, r.finished_at = datetime()",
            book_id=book_id,
            run_id=run_id,
            error=error,
        )
