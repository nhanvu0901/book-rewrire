---
id: T-0015
title: Write the story graph to Neo4j after each chapter
status: done
owner: Claude (at the user's request)
branch: ticket/T-0015-neo4j-graph-per-chapter
priority: high
created: 2026-11-16
updated: 2026-11-16
depends_on: [T-0014]
---

# T-0015: Write the story graph to Neo4j after each chapter

## Background

`pov ingest` already extracts characters, relationships, locations and scene maps per chapter
(T-0003 to T-0008), but Neo4j only receives selected `Character` properties after the last
chapter (`Neo4jCharacterWriter.write_characters`). Relationships, locations and scenes exist
only as JSON. The POV graph design in the README and slide deck needs them in Neo4j.

## User decisions

- 2026-11-16: "finish rest of the project". The user chose: Claude codes this directly
  (exception to the PM-only rule), and tickets cover (a) graph write, (b) events and claims,
  (c) knowledge timeline. This ticket is (a).
- 2026-11-16: write to Neo4j **after each chapter**, not only at the end of the run.

## PM recommendations

- Each chapter write makes the run's graph equal to the cumulative JSON state after that
  chapter (a full sync for the run, in one transaction). Merges and redirects can change
  earlier data, so appending only the new chapter would leave stale nodes and edges.
- Track run status on an `IngestRun` node (`running`, `complete`, `failed`) so a partial run
  is visible and distinguishable in Neo4j.
- Branch is stacked on `ticket/T-0014-transient-retry` (T-0013 Revision 2 and T-0014, both
  `done` and unmerged) plus current `main`, because both touch the same pipeline and tests.
  Merge order: T-0013 → T-0014 → T-0015.

## Requirements

1. Replace `Neo4jCharacterWriter` with `Neo4jGraphWriter` (`start_run`, `write_chapter`,
   `finish_run`, `fail_run`). All nodes keep the `(book_id, run_id, <id>)` key.
2. Schema written per chapter:
   - `(:Character)` with today's properties; characters retired by a merge are deleted.
   - `(:Location {location_id, name, aliases, kind})`, `(:Location)-[:PART_OF]->(:Location)`.
   - `(:Character)-[:RELATES_TO {relationship_id, kind, valid_from_chapter_id,
     valid_from_paragraph_ids, valid_to_chapter_id, valid_to_paragraph_ids}]->(:Character)`.
   - `(:Scene {segment_id, chapter_id, order, start, end, label, time_relation, time_anchor,
     time_note})`, `(:Scene)-[:OCCURRED_AT]->(:Location)`, `(:Scene)-[:NEXT]->(:Scene)` in
     reading order, `(:Character)-[:PRESENT_IN {viewpoint}]->(:Scene)`,
     `(:Character)-[:MENTIONED_IN]->(:Scene)`.
   - `(:IngestRun {status, chapters_done, last_chapter_id, chapter_count, title})`.
3. The extraction graph gets a `save_graph` node after `save_json`. With a writer it writes
   the chapter snapshot; without one (`--no-neo4j`) it does nothing.
4. The pipeline calls `start_run` before the summary graph, `finish_run` after the last
   chapter, and `fail_run` (then re-raises) when ingestion raises after `start_run`.
5. Scene records accumulate across chapters in state (`scene_history`); redirects are applied
   to their character IDs when the snapshot is built. A cumulative `scenes.json` is saved.
6. The audit runner (`run_api_audit.py`) passes the card client to the summary graph
   (left over from T-0013 Revision 2) and keeps working with the new node count.

## Acceptance criteria

- [x] Offline: with a recording writer, `write_chapter` is called once per chapter in order,
      after that chapter's JSON is saved, with cumulative characters, locations,
      relationships and scenes.
- [x] Offline: a merge in chapter 2 removes the retired ID from the snapshot
      (`retired_character_ids`) and rewrites scene and relationship IDs to the survivor.
- [x] Offline: `--no-neo4j` makes no writer calls and still saves JSON, including `scenes.json`.
- [x] Offline: a failure in chapter 2 calls `fail_run` with the error, after chapter 1 was
      written, and the error still reaches the caller.
- [x] Offline: the Cypher for one chapter runs inside a single write transaction.
- [x] Opt-in Neo4j test (`POV_NEO4J=1`): writing the same snapshot twice gives the same node
      and edge counts; a later snapshot with a merge deletes the retired character.
- [x] The full offline suite, `ruff check`, `ruff format --check` and `mypy` pass, including
      the audit-runner mock-transport test that fails on the base branch.

## Out of scope

- Events, utterances, claims and knowledge acquisition (T-0016, T-0017).
- Resume from a partial run, or deleting old runs.

## Files likely touched

`src/pov_retell/infrastructure/neo4j_store.py`, `src/pov_retell/ingest/pipeline.py`,
`src/pov_retell/ingest/graph/extract_character/{graph,model,snapshot}.py`,
`src/pov_retell/cli.py`, `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`,
tests for ingest, CLI, Neo4j and the audit runner.

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
```

No live API calls. The opt-in Neo4j test runs only if a local Neo4j is up.

## Open questions

None.

## Completion report

Implemented by Claude on 2026-11-16 (the user asked Claude to code this directly).

**Changes**
- `neo4j_store.py`: `Neo4jGraphWriter` replaces `Neo4jCharacterWriter`. `write_chapter` runs
  the statements in `CHAPTER_STATEMENTS` inside one `session.execute_write` transaction:
  upsert nodes, delete nodes that left the snapshot (retired characters), rebuild the run's
  edges. Constraints are created once per writer for `IngestRun`, `Character`, `Location`
  and `Scene`.
- `extract_character/snapshot.py` (new): builds the chapter snapshot rows and resolves
  redirected character IDs in scenes.
- `extract_character/graph.py`: `scene_history` state, cumulative `scenes.json`, new
  `save_graph` node after `save_json` (`EXTRACT_NODES_PER_CHAPTER = 10`).
- `ingest/model.py`: `GraphWriter` protocol. `pipeline.py`: `start_run` before the summary
  graph, `fail_run` on any exception (message cut to 500 characters), `finish_run` at the end.
- `cli.py`: uses the new writer; `--neo4j` help text updated.
- `run_api_audit.py`: passes the extract client as the summary graph's card client (left
  over from T-0013 Revision 2) and reuses it for the extraction graph. Its mock-transport
  test now answers the card calls with `CardChanges` JSON.

**Criteria evidence**
- Per-chapter cumulative writes, merge handling, failure handling, single transaction:
  `tests/test_graph_writer.py` (4 tests).
- `--no-neo4j` and `scenes.json`: `test_ingest_without_a_writer_still_saves_json`.
- CLI with a fake driver (success and API error, run marked `complete` / `failed`):
  `test_cli_selects_summary_and_full_profile_models_and_closes_driver`.
- Opt-in Neo4j: `env POV_NEO4J=1 pytest tests/test_neo4j_integration.py -m neo4j` →
  `2 passed` against the local dev Neo4j 5 (`make neo4j-up`). Test data used a temporary
  book ID and was deleted.

**Commands**
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  → `312 passed, 4 skipped` (base branch: `1 failed, 307 passed, 4 skipped`; the failure
  was the audit mock-transport test).
- `ruff check` → passed; `ruff format --check` → all files formatted;
  `mypy src/pov_retell` → no issues in 45 source files; `git diff --check` → clean.
- `mypy src tests` reports 18 errors in `tests/test_config.py`, `tests/test_llm.py` and
  `tests/test_character_ingest.py`; the base branch has the same 18. Not changed here.

**Deviations**
- Stacked on `ticket/T-0014-transient-retry` + `main` instead of plain `main` (see PM
  recommendations).
- No live API call. The new Neo4j constraints now exist in the local dev database.

## Review

_Filled by the product manager._
