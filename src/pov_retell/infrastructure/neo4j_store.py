from typing import Any

from neo4j import Driver, GraphDatabase, ManagedTransaction, NotificationMinimumSeverity
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


KEYS = {
    "IngestRun": (),
    "Character": ("character_id",),
    "Location": ("location_id",),
    "Scene": ("segment_id",),
    "Claim": ("claim_id",),
    "Event": ("event_id",),
    "Utterance": ("utterance_id",),
    "KnowledgeAcquisition": ("acquisition_id",),
}

CHARACTER_PROPERTIES = (
    "canonical_name",
    "aliases",
    "gender",
    "species",
    "age_description",
    "physical_description",
    "personality",
    "resolution_status",
)

# Each chapter snapshot replaces the run's graph: nodes are upserted, nodes that left the
# snapshot are removed, and every edge of the run is rebuilt from the snapshot.
CHAPTER_STATEMENTS: tuple[str, ...] = (
    "MERGE (r:IngestRun {book_id: $book_id, run_id: $run_id}) "
    "SET r.status = 'running', r.chapters_done = $chapters_done, "
    "r.last_chapter_id = $chapter_id, r.updated_at = datetime()",
    # Characters
    "UNWIND $characters AS row "
    "MERGE (c:Character {book_id: $book_id, run_id: $run_id, character_id: row.character_id}) "
    + "SET "
    + ", ".join(f"c.{name} = row.{name}" for name in CHARACTER_PROPERTIES)
    + " REMOVE c.first_mention_id, c.relationships",
    "MATCH (c:Character {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT c.character_id IN [row IN $characters | row.character_id] "
    "DETACH DELETE c",
    # Locations
    "UNWIND $locations AS row "
    "MERGE (l:Location {book_id: $book_id, run_id: $run_id, location_id: row.location_id}) "
    "SET l.name = row.name, l.aliases = row.aliases, l.kind = row.kind",
    "MATCH (l:Location {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT l.location_id IN [row IN $locations | row.location_id] "
    "DETACH DELETE l",
    "MATCH (:Location {book_id: $book_id, run_id: $run_id})-[e:PART_OF]->() DELETE e",
    "UNWIND $locations AS row WITH row WHERE row.part_of IS NOT NULL "
    "MATCH (a:Location {book_id: $book_id, run_id: $run_id, location_id: row.location_id}), "
    "(b:Location {book_id: $book_id, run_id: $run_id, location_id: row.part_of}) "
    "MERGE (a)-[:PART_OF]->(b)",
    # Relationships
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:RELATES_TO]->() DELETE e",
    "UNWIND $relationships AS row "
    "MATCH (a:Character {book_id: $book_id, run_id: $run_id, character_id: row.source_id}), "
    "(b:Character {book_id: $book_id, run_id: $run_id, character_id: row.target_id}) "
    "CREATE (a)-[:RELATES_TO {relationship_id: row.relationship_id, kind: row.kind, "
    "valid_from_chapter_id: row.valid_from_chapter_id, "
    "valid_from_paragraph_ids: row.valid_from_paragraph_ids, "
    "valid_to_chapter_id: row.valid_to_chapter_id, "
    "valid_to_paragraph_ids: row.valid_to_paragraph_ids}]->(b)",
    # Scenes
    "UNWIND $scenes AS row "
    "MERGE (s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}) "
    "SET s.chapter_id = row.chapter_id, s.order = row.order, s.start = row.start, "
    "s.end = row.end, s.label = row.label, s.time_relation = row.time_relation, "
    "s.time_anchor = row.time_anchor, s.time_note = row.time_note",
    "MATCH (s:Scene {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT s.segment_id IN [row IN $scenes | row.segment_id] "
    "DETACH DELETE s",
    "MATCH (:Scene {book_id: $book_id, run_id: $run_id})-[e:OCCURRED_AT|NEXT]->() DELETE e",
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:PRESENT_IN|MENTIONED_IN]->() "
    "DELETE e",
    "UNWIND $scenes AS row WITH row WHERE row.location_id IS NOT NULL "
    "MATCH (s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}), "
    "(l:Location {book_id: $book_id, run_id: $run_id, location_id: row.location_id}) "
    "MERGE (s)-[:OCCURRED_AT]->(l)",
    "UNWIND range(1, size($scenes) - 1) AS i "
    "MATCH (a:Scene {book_id: $book_id, run_id: $run_id, segment_id: $scenes[i - 1].segment_id}), "
    "(b:Scene {book_id: $book_id, run_id: $run_id, segment_id: $scenes[i].segment_id}) "
    "MERGE (a)-[:NEXT]->(b)",
    "UNWIND $scenes AS row UNWIND row.present_ids AS cid "
    "MATCH (s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: cid}) "
    "MERGE (c)-[:PRESENT_IN {viewpoint: cid IN row.viewpoint_ids}]->(s)",
    "UNWIND $scenes AS row UNWIND row.mentioned_ids AS cid "
    "MATCH (s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: cid}) "
    "MERGE (c)-[:MENTIONED_IN]->(s)",
    # Claims
    "UNWIND $claims AS row "
    "MERGE (c:Claim {book_id: $book_id, run_id: $run_id, claim_id: row.claim_id}) "
    "SET c.statement = row.statement, c.truth = row.truth, "
    "c.first_chapter_id = row.first_chapter_id, c.truth_chapter_id = row.truth_chapter_id, "
    "c.truth_paragraph_ids = row.truth_paragraph_ids",
    "MATCH (c:Claim {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT c.claim_id IN [row IN $claims | row.claim_id] "
    "DETACH DELETE c",
    "MATCH (:Claim {book_id: $book_id, run_id: $run_id})-[e:CONCERNS]->() DELETE e",
    "UNWIND $claims AS row UNWIND row.about_ids AS cid "
    "MATCH (c:Claim {book_id: $book_id, run_id: $run_id, claim_id: row.claim_id}), "
    "(p:Character {book_id: $book_id, run_id: $run_id, character_id: cid}) "
    "MERGE (c)-[:CONCERNS]->(p)",
    # Events
    "UNWIND $events AS row "
    "MERGE (e:Event {book_id: $book_id, run_id: $run_id, event_id: row.event_id}) "
    "SET e.chapter_id = row.chapter_id, e.segment_id = row.segment_id, e.order = row.order, "
    "e.summary = row.summary, e.paragraph_ids = row.paragraph_ids",
    "MATCH (e:Event {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT e.event_id IN [row IN $events | row.event_id] "
    "DETACH DELETE e",
    "MATCH (:Event {book_id: $book_id, run_id: $run_id})-[e:IN_SCENE|OCCURRED_AT|HAS_CLAIM]->() "
    "DELETE e",
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:PARTICIPATED_IN]->() DELETE e",
    "UNWIND $events AS row "
    "MATCH (e:Event {book_id: $book_id, run_id: $run_id, event_id: row.event_id}), "
    "(s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}) "
    "MERGE (e)-[:IN_SCENE]->(s)",
    "UNWIND $events AS row WITH row WHERE row.location_id IS NOT NULL "
    "MATCH (e:Event {book_id: $book_id, run_id: $run_id, event_id: row.event_id}), "
    "(l:Location {book_id: $book_id, run_id: $run_id, location_id: row.location_id}) "
    "MERGE (e)-[:OCCURRED_AT]->(l)",
    "UNWIND $events AS row UNWIND row.participant_ids AS cid "
    "MATCH (e:Event {book_id: $book_id, run_id: $run_id, event_id: row.event_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: cid}) "
    "MERGE (c)-[:PARTICIPATED_IN]->(e)",
    "UNWIND $events AS row UNWIND row.claim_ids AS claim_id "
    "MATCH (e:Event {book_id: $book_id, run_id: $run_id, event_id: row.event_id}), "
    "(c:Claim {book_id: $book_id, run_id: $run_id, claim_id: claim_id}) "
    "MERGE (e)-[:HAS_CLAIM]->(c)",
    # Utterances
    "UNWIND $utterances AS row "
    "MERGE (u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.utterance_id}) "
    "SET u.chapter_id = row.chapter_id, u.segment_id = row.segment_id, u.order = row.order, "
    "u.mode = row.mode, u.quote = row.quote, u.paragraph_ids = row.paragraph_ids",
    "MATCH (u:Utterance {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT u.utterance_id IN [row IN $utterances | row.utterance_id] "
    "DETACH DELETE u",
    "MATCH (:Utterance {book_id: $book_id, run_id: $run_id})-[e:IN_SCENE|ADDRESSED_TO|ASSERTS]->() "
    "DELETE e",
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:SAID]->() DELETE e",
    "UNWIND $utterances AS row "
    "MATCH (u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.utterance_id}), "
    "(s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}) "
    "MERGE (u)-[:IN_SCENE]->(s)",
    "UNWIND $utterances AS row WITH row WHERE row.speaker_id IS NOT NULL "
    "MATCH (u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.utterance_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: row.speaker_id}) "
    "MERGE (c)-[:SAID]->(u)",
    "UNWIND $utterances AS row UNWIND row.addressee_ids AS cid "
    "MATCH (u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.utterance_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: cid}) "
    "MERGE (u)-[:ADDRESSED_TO]->(c)",
    "UNWIND $utterances AS row UNWIND row.claim_ids AS claim_id "
    "MATCH (u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.utterance_id}), "
    "(c:Claim {book_id: $book_id, run_id: $run_id, claim_id: claim_id}) "
    "MERGE (u)-[:ASSERTS]->(c)",
    # Knowledge acquisitions
    "UNWIND $knowledge AS row "
    "MERGE (k:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id, "
    "acquisition_id: row.acquisition_id}) "
    "SET k.channel = row.channel, k.stance = row.stance, k.chapter_id = row.chapter_id, "
    "k.segment_id = row.segment_id, k.order = row.order, k.paragraph_ids = row.paragraph_ids",
    "MATCH (k:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT k.acquisition_id IN [row IN $knowledge | row.acquisition_id] "
    "DETACH DELETE k",
    "MATCH (:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id})"
    "-[e:ABOUT|VIA|IN_SCENE]->() DELETE e",
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:ACQUIRED|EXPERIENCED]->() DELETE e",
    "UNWIND $knowledge AS row "
    "MATCH (k:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id, "
    "acquisition_id: row.acquisition_id}), "
    "(c:Character {book_id: $book_id, run_id: $run_id, character_id: row.character_id}), "
    "(claim:Claim {book_id: $book_id, run_id: $run_id, claim_id: row.claim_id}), "
    "(s:Scene {book_id: $book_id, run_id: $run_id, segment_id: row.segment_id}) "
    "MERGE (c)-[:ACQUIRED]->(k) MERGE (k)-[:ABOUT]->(claim) MERGE (k)-[:IN_SCENE]->(s)",
    "UNWIND $knowledge AS row "
    "MATCH (k:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id, "
    "acquisition_id: row.acquisition_id}), "
    "(e:Event {book_id: $book_id, run_id: $run_id, event_id: row.source_id}) "
    "MERGE (k)-[:VIA]->(e)",
    "UNWIND $knowledge AS row "
    "MATCH (k:KnowledgeAcquisition {book_id: $book_id, run_id: $run_id, "
    "acquisition_id: row.acquisition_id}), "
    "(u:Utterance {book_id: $book_id, run_id: $run_id, utterance_id: row.source_id}) "
    "MERGE (k)-[:VIA]->(u)",
    "UNWIND $knowledge AS row WITH row WHERE row.channel = 'witnessed' "
    "MATCH (c:Character {book_id: $book_id, run_id: $run_id, character_id: row.character_id}), "
    "(e:Event {book_id: $book_id, run_id: $run_id, event_id: row.source_id}) "
    "MERGE (c)-[:EXPERIENCED]->(e)",
)

SNAPSHOT_LISTS = (
    "characters",
    "locations",
    "relationships",
    "scenes",
    "claims",
    "events",
    "utterances",
    "knowledge",
)


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
