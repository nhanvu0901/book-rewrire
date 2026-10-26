"""Opt-in tests against Neo4j. Character data uses a temporary book ID and is removed."""

from uuid import uuid4

import pytest

from pov_retell.config import Settings
from pov_retell.infrastructure.neo4j_store import Neo4jCharacterWriter, check_health, connect


@pytest.mark.neo4j
def test_neo4j_connection() -> None:
    with connect(Settings()) as driver:  # type: ignore[call-arg]
        info = check_health(driver)
    assert info["version"]
    assert info["edition"]


@pytest.mark.neo4j
def test_character_writes_are_idempotent_and_scoped_by_run() -> None:
    book_id = f"test_characters_{uuid4().hex}"
    rows = [
        {
            "character_id": "char_001",
            "canonical_name": "Mara",
            "aliases": ["Mara"],
            "gender": None,
            "species": "human",
            "age_description": None,
            "physical_description": None,
            "personality": "cautious",
            "resolution_status": "candidate",
        }
    ]
    with connect(Settings()) as driver:  # type: ignore[call-arg]
        writer = Neo4jCharacterWriter(driver)
        try:
            writer.write_characters(book_id, "run_a", rows)
            writer.write_characters(book_id, "run_a", rows)
            writer.write_characters(
                book_id,
                "run_a",
                [{**rows[0], "personality": "cautious; brave"}],
            )
            writer.write_characters(book_id, "run_b", rows)
            records, _, _ = driver.execute_query(
                "MATCH (c:Character {book_id: $book_id}) "
                "RETURN c.run_id AS run_id, c.canonical_name AS name, "
                "c.relationships AS relationships, c.personality AS personality, "
                "c.resolution_status AS status, c.mentions AS mentions ORDER BY run_id",
                book_id=book_id,
            )
            assert [dict(record) for record in records] == [
                {
                    "run_id": run_id,
                    "name": "Mara",
                    "relationships": None,
                    "personality": "cautious; brave" if run_id == "run_a" else "cautious",
                    "status": "candidate",
                    "mentions": None,
                }
                for run_id in ("run_a", "run_b")
            ]
        finally:
            driver.execute_query(
                "MATCH (c:Character {book_id: $book_id}) DETACH DELETE c", book_id=book_id
            )
