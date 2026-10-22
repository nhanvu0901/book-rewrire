from typing import Any

from neo4j import Driver, GraphDatabase, NotificationMinimumSeverity
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from pov_retell.config import Settings


class Neo4jUnavailable(RuntimeError):
    """Neo4j cannot be reached or refused the credentials. The message says what to do."""


def connect(settings: Settings) -> Driver:
    """Open a driver from the settings. The password is read here and never printed."""
    password = settings.NEO4J_PASSWORD.get_secret_value()
    if not password:
        raise Neo4jUnavailable(
            "NEO4J_PASSWORD is not set: put it in .env, then run `make neo4j-up`"
        )
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.NEO4J_USER, password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )


def check_health(driver: Driver) -> dict[str, str]:
    """Return the server version and edition, or raise Neo4jUnavailable."""
    try:
        driver.verify_connectivity()
        record, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        )
    except (ServiceUnavailable, OSError) as exc:
        raise Neo4jUnavailable("cannot reach Neo4j: is it up? run `make neo4j-up`") from exc
    except Neo4jError as exc:
        raise Neo4jUnavailable(f"Neo4j refused the request: {exc.message}") from exc
    return dict(record[0])


class Neo4jCharacterWriter:
    def __init__(self, driver: Driver) -> None:
        self.driver = driver

    def write_characters(self, book_id: str, run_id: str, rows: list[dict[str, Any]]) -> None:
        self.driver.execute_query(
            "CREATE CONSTRAINT character_key IF NOT EXISTS FOR (c:Character) "
            "REQUIRE (c.book_id, c.run_id, c.character_id) IS UNIQUE"
        )
        self.driver.execute_query(
            "UNWIND $rows AS row "
            "MERGE (c:Character {book_id: $book_id, run_id: $run_id, "
            "character_id: row.character_id}) "
            "SET c.canonical_name = row.canonical_name, c.aliases = row.aliases, "
            "c.gender = row.gender, c.species = row.species, "
            "c.age_description = row.age_description, "
            "c.physical_description = row.physical_description, "
            "c.personality = row.personality, "
            "c.resolution_status = row.resolution_status "
            "REMOVE c.first_mention_id, c.relationships",
            book_id=book_id,
            run_id=run_id,
            rows=rows,
        )
