"""Opt-in tests against Neo4j. Graph data uses a temporary book ID and is removed."""

from typing import Any
from uuid import uuid4

import pytest

from pov_retell.config import Settings
from pov_retell.infrastructure.neo4j_store import Neo4jGraphWriter, check_health, connect


def character_row(character_id: str, name: str, personality: str | None) -> dict[str, Any]:
    return {
        "character_id": character_id,
        "canonical_name": name,
        "aliases": [name],
        "gender": None,
        "species": "human",
        "age_description": None,
        "physical_description": None,
        "personality": personality,
        "resolution_status": "candidate",
    }


def scene_row(
    segment_id: str, order: int, present: list[str], viewpoint: list[str]
) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "chapter_id": segment_id.split("_")[0],
        "order": order,
        "start": f"{segment_id.split('_')[0]}_p001",
        "end": f"{segment_id.split('_')[0]}_p001",
        "location_id": "loc_001",
        "present_ids": present,
        "mentioned_ids": [],
        "viewpoint_ids": viewpoint,
        "time_relation": "continues",
        "time_anchor": None,
        "time_note": None,
        "label": "At the gate",
    }


def snapshot(chapter: int, characters: list[dict[str, Any]], scenes: list[dict[str, Any]]) -> Any:
    ids = [row["character_id"] for row in characters]
    return {
        "chapter_id": f"u{chapter:02d}",
        "chapters_done": chapter,
        "characters": characters,
        "retired_character_ids": [],
        "locations": [
            {
                "location_id": "loc_001",
                "name": "the gate",
                "aliases": [],
                "kind": "gate",
                "part_of": None,
            }
        ],
        "relationships": [
            {
                "relationship_id": "rel_001",
                "source_id": ids[0],
                "target_id": ids[-1],
                "kind": "friend of",
                "valid_from_chapter_id": "u01",
                "valid_from_paragraph_ids": ["u01_p001"],
                "valid_to_chapter_id": None,
                "valid_to_paragraph_ids": [],
            }
        ]
        if len(ids) > 1
        else [],
        "scenes": scenes,
    }


def counts(driver: Any, book_id: str) -> dict[str, int]:
    records, _, _ = driver.execute_query(
        "MATCH (n {book_id: $book_id}) "
        "OPTIONAL MATCH (n)-[e]->() "
        "RETURN labels(n)[0] AS label, count(DISTINCT n) AS nodes, count(e) AS edges",
        book_id=book_id,
    )
    return {f"{r['label']}": r["nodes"] for r in records} | {
        f"{r['label']}->": r["edges"] for r in records
    }


@pytest.mark.neo4j
def test_neo4j_connection() -> None:
    with connect(Settings()) as driver:  # type: ignore[call-arg]
        info = check_health(driver)
    assert info["version"]
    assert info["edition"]


@pytest.mark.neo4j
def test_chapter_writes_are_idempotent_scoped_by_run_and_follow_merges() -> None:
    book_id = f"test_graph_{uuid4().hex}"
    mara = character_row("char_001", "Mara", "cautious")
    jo = character_row("char_002", "Jo", None)
    first = snapshot(
        1,
        [mara, jo],
        [scene_row("u01_s1", 1, ["char_001", "char_002"], ["char_002"])],
    )
    with connect(Settings()) as driver:  # type: ignore[call-arg]
        writer = Neo4jGraphWriter(driver)
        try:
            writer.start_run(book_id, "run_a", "The Gate", ["u01", "u02"])
            writer.write_chapter(book_id, "run_a", first)
            once = counts(driver, book_id)
            writer.write_chapter(book_id, "run_a", first)
            assert counts(driver, book_id) == once
            assert once["Character"] == 2
            assert once["Scene"] == 1

            # Chapter 2: Jo was merged into Mara, so char_002 leaves the graph.
            second = snapshot(
                2,
                [{**mara, "personality": "cautious; brave"}],
                [
                    scene_row("u01_s1", 1, ["char_001"], ["char_001"]),
                    scene_row("u02_s1", 2, ["char_001"], []),
                ],
            )
            writer.write_chapter(book_id, "run_a", second)
            writer.start_run(book_id, "run_b", "The Gate", ["u01"])
            writer.write_chapter(book_id, "run_b", first)
            writer.finish_run(book_id, "run_a")

            records, _, _ = driver.execute_query(
                "MATCH (c:Character {book_id: $book_id}) "
                "RETURN c.run_id AS run_id, c.character_id AS id, c.personality AS personality "
                "ORDER BY run_id, id",
                book_id=book_id,
            )
            assert [dict(r) for r in records] == [
                {"run_id": "run_a", "id": "char_001", "personality": "cautious; brave"},
                {"run_id": "run_b", "id": "char_001", "personality": "cautious"},
                {"run_id": "run_b", "id": "char_002", "personality": None},
            ]
            records, _, _ = driver.execute_query(
                "MATCH (a:Scene {book_id: $book_id, run_id: 'run_a'})-[:NEXT]->"
                "(b:Scene)-[:OCCURRED_AT]->(l:Location) "
                "MATCH (r:IngestRun {book_id: $book_id, run_id: 'run_a'}) "
                "RETURN a.segment_id AS a, b.segment_id AS b, l.name AS place, "
                "r.status AS status, r.chapters_done AS done",
                book_id=book_id,
            )
            assert [dict(r) for r in records] == [
                {"a": "u01_s1", "b": "u02_s1", "place": "the gate", "status": "complete", "done": 2}
            ]
        finally:
            driver.execute_query("MATCH (n {book_id: $book_id}) DETACH DELETE n", book_id=book_id)


@pytest.mark.neo4j
def test_events_utterances_and_claims_are_linked() -> None:
    book_id = f"test_events_{uuid4().hex}"
    mara = character_row("char_001", "Mara", None)
    jo = character_row("char_002", "Jo", None)
    data = snapshot(
        1,
        [mara, jo],
        [scene_row("u01_s1", 1, ["char_001", "char_002"], [])],
    )
    data["claims"] = [
        {
            "claim_id": "claim_001",
            "statement": "Jo stole the key",
            "about_ids": ["char_002"],
            "truth": "unknown",
            "first_chapter_id": "u01",
            "truth_chapter_id": None,
            "truth_paragraph_ids": [],
        }
    ]
    data["events"] = [
        {
            "event_id": "u01_e1",
            "chapter_id": "u01",
            "order": 1,
            "segment_id": "u01_s1",
            "location_id": "loc_001",
            "summary": "Mara finds the door open",
            "participant_ids": ["char_001"],
            "paragraph_ids": ["u01_p001"],
            "claim_ids": ["claim_001"],
        }
    ]
    data["utterances"] = [
        {
            "utterance_id": "u01_q1",
            "chapter_id": "u01",
            "order": 1,
            "segment_id": "u01_s1",
            "mode": "spoken",
            "speaker_id": "char_001",
            "addressee_ids": ["char_002"],
            "quote": "Jo took the key",
            "paragraph_ids": ["u01_p001"],
            "claim_ids": ["claim_001"],
        }
    ]
    data["knowledge"] = [
        {
            "acquisition_id": f"u01_k{n}",
            "chapter_id": "u01",
            "order": n,
            "character_id": who,
            "claim_id": "claim_001",
            "channel": channel,
            "stance": "believes",
            "segment_id": "u01_s1",
            "source_id": source,
            "paragraph_ids": ["u01_p001"],
        }
        for n, (who, channel, source) in enumerate(
            [("char_001", "witnessed", "u01_e1"), ("char_002", "told", "u01_q1")], start=1
        )
    ]
    with connect(Settings()) as driver:  # type: ignore[call-arg]
        writer = Neo4jGraphWriter(driver)
        try:
            writer.start_run(book_id, "run_a", "The Gate", ["u01"])
            writer.write_chapter(book_id, "run_a", data)
            writer.write_chapter(book_id, "run_a", data)
            records, _, _ = driver.execute_query(
                "MATCH (c:Character {book_id: $book_id})-[:ACQUIRED]->(k:KnowledgeAcquisition)"
                "-[:ABOUT]->(:Claim {claim_id: 'claim_001'}), (k)-[:IN_SCENE]->(:Scene), "
                "(k)-[:VIA]->(source) "
                "OPTIONAL MATCH (c)-[x:EXPERIENCED]->(:Event) "
                "RETURN c.character_id AS who, k.channel AS channel, labels(source)[0] AS via, "
                "count(x) AS experienced ORDER BY who",
                book_id=book_id,
            )
            assert [dict(r) for r in records] == [
                {"who": "char_001", "channel": "witnessed", "via": "Event", "experienced": 1},
                {"who": "char_002", "channel": "told", "via": "Utterance", "experienced": 0},
            ]
            records, _, _ = driver.execute_query(
                "MATCH (m:Character {book_id: $book_id, character_id: 'char_001'})"
                "-[:SAID]->(u:Utterance)-[:ASSERTS]->(c:Claim)-[:CONCERNS]->(j:Character), "
                "(u)-[:ADDRESSED_TO]->(j), (u)-[:IN_SCENE]->(s:Scene), "
                "(m)-[:PARTICIPATED_IN]->(e:Event)-[:HAS_CLAIM]->(c), "
                "(e)-[:OCCURRED_AT]->(l:Location), (e)-[:IN_SCENE]->(s) "
                "RETURN j.canonical_name AS about, c.truth AS truth, l.name AS place, "
                "count(*) AS paths",
                book_id=book_id,
            )
            assert [dict(r) for r in records] == [
                {"about": "Jo", "truth": "unknown", "place": "the gate", "paths": 1}
            ]
        finally:
            driver.execute_query("MATCH (n {book_id: $book_id}) DETACH DELETE n", book_id=book_id)
