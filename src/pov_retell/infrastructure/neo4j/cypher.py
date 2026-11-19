"""Cypher for the per-chapter story-graph snapshot, grouped by entity.

Each chapter snapshot replaces the run's graph: nodes are upserted, nodes that left the
snapshot are removed, and every edge of the run is rebuilt from the snapshot.
"""

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

RUN_STATEMENTS: tuple[str, ...] = (
    "MERGE (r:IngestRun {book_id: $book_id, run_id: $run_id}) "
    "SET r.status = 'running', r.chapters_done = $chapters_done, "
    "r.last_chapter_id = $chapter_id, r.updated_at = datetime()",
)

CHARACTER_STATEMENTS: tuple[str, ...] = (
    "UNWIND $characters AS row "
    "MERGE (c:Character {book_id: $book_id, run_id: $run_id, character_id: row.character_id}) "
    + "SET "
    + ", ".join(f"c.{name} = row.{name}" for name in CHARACTER_PROPERTIES)
    + " REMOVE c.first_mention_id, c.relationships",
    "MATCH (c:Character {book_id: $book_id, run_id: $run_id}) "
    "WHERE NOT c.character_id IN [row IN $characters | row.character_id] "
    "DETACH DELETE c",
)

LOCATION_STATEMENTS: tuple[str, ...] = (
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
)

RELATIONSHIP_STATEMENTS: tuple[str, ...] = (
    "MATCH (:Character {book_id: $book_id, run_id: $run_id})-[e:RELATES_TO]->() DELETE e",
    "UNWIND $relationships AS row "
    "MATCH (a:Character {book_id: $book_id, run_id: $run_id, character_id: row.source_id}), "
    "(b:Character {book_id: $book_id, run_id: $run_id, character_id: row.target_id}) "
    "CREATE (a)-[:RELATES_TO {relationship_id: row.relationship_id, kind: row.kind, "
    "valid_from_chapter_id: row.valid_from_chapter_id, "
    "valid_from_paragraph_ids: row.valid_from_paragraph_ids, "
    "valid_to_chapter_id: row.valid_to_chapter_id, "
    "valid_to_paragraph_ids: row.valid_to_paragraph_ids}]->(b)",
)

SCENE_STATEMENTS: tuple[str, ...] = (
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
)

CLAIM_STATEMENTS: tuple[str, ...] = (
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
)

EVENT_STATEMENTS: tuple[str, ...] = (
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
)

UTTERANCE_STATEMENTS: tuple[str, ...] = (
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
)

KNOWLEDGE_STATEMENTS: tuple[str, ...] = (
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

CHAPTER_STATEMENTS: tuple[str, ...] = (
    *RUN_STATEMENTS,
    *CHARACTER_STATEMENTS,
    *LOCATION_STATEMENTS,
    *RELATIONSHIP_STATEMENTS,
    *SCENE_STATEMENTS,
    *CLAIM_STATEMENTS,
    *EVENT_STATEMENTS,
    *UTTERANCE_STATEMENTS,
    *KNOWLEDGE_STATEMENTS,
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
