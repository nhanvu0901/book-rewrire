---
id: T-0004
title: "Relationships: separate structured call per chapter, changes only, with history"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: high
created: 2026-10-25
updated: 2026-10-25
depends_on: [T-0003, T-0005]
---

# T-0004: Relationships: separate structured call per chapter, changes only, with history

## Background

T-0003 removed relationships from the character call. In run
`run_2ae27f27f5d34937a54c8c81ed93303e` they had become event logs: 286 entries, 4,849 words,
17 over 60 words. They could not become `RELATES_TO {kind, valid_from, valid_to, evidence}`
edges, the shape in `doc/pov_neo4j_character_graph.drawio`.

The agreed pattern for every entity is "the LLM reads, Python remembers":

- the LLM receives the chapter and the current state with IDs;
- it returns only changes;
- Python validates them and keeps the state with history.

Paragraph IDs are the evidence, so relationships do not have to wait for events. Events
will share the same paragraph IDs.

## User decisions

- 2026-10-24: relationships move to a separate structured call after the character call;
  write T-0003 first ("give me t3 first").
- 2026-10-25: write all agreed tickets ("give me all the new ticket we came up so far").
- `RELATES_TO` edges in Neo4j come last; this ticket writes JSON files only.
- JSON jobs use the extract client (GLM after T-0005).

## PM recommendations

The user may veto these before work starts:

- Two operations only: `start` and `end`. A change of kind is an `end` plus a `start`.
- `kind` is free text of 1–5 words, describing the source's stable relation to the target
  ("brother of", "servant of", "enemy of", "friend of"). It is not a feeling of the moment, a
  single action or an event. Family relations never end.
- Define the graph recursion limit in one place, because each new step adds nodes per chapter.

## Requirements

1. **New per-chapter step** in the extraction graph, after the character step for the same
   chapter: one JSON call through the extract client. The character step must expose this
   chapter's active character IDs (the IDs in its validated proposal) in graph state.
2. **Input:**
   - book title and chapter ID;
   - `format_previous_context` for chapters before N;
   - a compact roster (`character_id`, `candidate_name`, `aliases`);
   - this chapter's active IDs;
   - open relationships where the source or target is active, one line each;
   - the chapter text with paragraph IDs.
3. **Output:**
   `{"relationships": [{"op": "start" | "end", "source_id", "target_id", "kind",
   "paragraph_ids": [...]}]}`. Return only relationships this chapter establishes, first
   states, or ends, each with the paragraphs that show it. Return `{"relationships": []}`
   when nothing changes.
4. **Python validation**; reject with a reason and retry like other JSON calls:
   - `source_id` and `target_id` exist after identity redirects, and differ;
   - `paragraph_ids` is non-empty and every ID belongs to the current chapter;
   - `kind` is normalized (trim, lowercase, single spaces) and has 1–5 words;
   - `end` must match an open record with the same source, target and kind.
   - `start` for a pair and kind that is already open is a no-op: keep the first evidence.
5. **History storage:**
   - `relationships.json` holds a list of
     `{"relationship_id": "rel_NNN", "source_id", "target_id", "kind",
     "valid_from": {"chapter_id", "paragraph_ids"}, "valid_to": null | {"chapter_id", "paragraph_ids"}}`;
   - per chapter, `chapters/uNN.relationships.proposed.json` (raw) and
     `chapters/uNN.relationships.json` (snapshot).
6. **Character merges:** when IDs are redirected, rewrite the relationship records to the
   kept ID. Merge identical open records, keeping the earliest `valid_from`.
7. **Recursion limit:** replace the duplicated `max(25, len(chapters) * 4 + 10)` in
   `pipeline.py` and the audit runner with one helper per graph that counts its nodes per
   chapter. Use it in both places.
8. Update the audit runner (call counts and its offline test), `run-protocol.md`, README, and
   run a context-maintenance pass.
9. The prompt is book-agnostic, with generic examples only. Add a test like T-0003's.

## Acceptance criteria

- [x] One relationship call per chapter, after that chapter's character step. Offline test
      with N chapters.
- [x] The relationship prompt for chapter N contains:
      - the roster;
      - the active IDs;
      - only the open relationships that involve active characters;
      - previous context through N-1;
      - chapter N's text.

      Offline marker test.
- [x] Each validation rule in Requirement 4 rejects and retries with its reason. Offline
      tests: unknown ID, self-reference, a paragraph from another chapter, `end` without an
      open record, a 6-word kind.
- [x] `start` then a later `end` produce one record with `valid_to` set. A repeated `start`
      is a no-op. Offline tests.
- [x] A character merge rewrites relationship IDs. Offline test.
- [x] Saved files have the exact shapes above. Offline test.
- [x] One recursion-limit helper per graph is used by the pipeline and the runner. The
      runner test passes.
- [x] Book-agnostic prompt test. All Verification commands pass. README updated. Context
      pass done.

## Out of scope

- Neo4j `RELATES_TO` edges, a fixed vocabulary of kinds, automatic mirroring of symmetric
  relations, `viewpoint` and `confidence` from the drawio.
- Events, locations, scene map.

## Files likely touched

- `src/pov_retell/ingest/graph/extract_character/{graph.py,model.py,logic.py}` or a new
  `extract_relationship/` package with `prompt/`
- `src/pov_retell/ingest/pipeline.py`
- `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`, its test and `references/run-protocol.md`
- `tests/` (new relationship tests), `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK): full `--no-neo4j` run. Checks:

- relationship kinds are short;
- the four children are linked as siblings from u01;
- the servant relation between Tumnus and the White Witch is stated in u02, and its end
  appears where the text shows it;
- no kind describes a single event.

## Open questions

- Symmetric relations: default directed only. The LLM returns both directions when the
  text supports both.
- Restated relations: default no-op, without adding evidence.

## Completion report

### What changed

- **`src/pov_retell/ingest/graph/extract_character/model.py`**: Added `RelationshipSpan`, `RelationshipRecord`, `RelationshipChange`, and `ExtractRelationshipResponse`, and extended `ExtractCharacterState` with `active_character_ids`, `relationships`, `proposed_relationships`, and `next_relationship_number`.
- **`src/pov_retell/ingest/graph/extract_character/prompt/extract_relationship.py`**: Added book-agnostic `PROMPT_EXTRACT_RELATIONSHIP` instructing the LLM to return `start` and `end` operations with 1–5 lowercase words for `kind` and current-chapter `paragraph_ids`.
- **`src/pov_retell/ingest/graph/extract_character/relationship.py` and `logic.py`**:
  - Exposed `active_character_ids` from `validate_characters`.
  - Added `extract_relationships`, `validate_relationships`, `format_open_relationships`, and `rewrite_relationships_for_redirects` (rewriting redirected character IDs on merge, dropping self-links, and merging identical open records while keeping the earliest `valid_from` and `relationship_id`).
- **`src/pov_retell/ingest/graph/extract_character/graph.py`, `summarize_chapter/graph.py`, `pipeline.py`, and `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`**:
  - Wired `extract_relationships` and `validate_relationships` into `build_extract_character_graph` after `validate_characters` and persisted `relationships.json`, `chapters/uNN.relationships.proposed.json`, and `chapters/uNN.relationships.json` in `save_json`.
  - Replaced duplicated recursion-limit expressions with `summarize_chapter_recursion_limit` and `extract_character_recursion_limit`.
- **`tests/test_relationship_ingest.py`, `tests/test_character_ingest.py`, `tests/test_character_recovery.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`, `README.md`, and `AI-work/PROJECT_CONTEXT.md`**: Added comprehensive offline tests and updated docs/context.

### Verification results

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`: `222 passed, 5 skipped`
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: `All checks passed!`
- `.venv/bin/ruff format --check src tests`: `60 files already formatted`
- `.venv/bin/mypy src/pov_retell`: `Success: no issues found in 40 source files`
- `git diff --check`: clean
- Context maintenance pass performed directly on `AI-work/PROJECT_CONTEXT.md` (sub-agent delegation with `gpt-5.6-sol` or Claude Sonnet 5.5 is unavailable in this runtime).

## Review

Reviewed by Claude (product manager) on 2026-10-25. Verdict: **verified**.

### Verification rerun by the reviewer

Run on 2026-10-25 on the combined working tree (T-0003 to T-0008 are implemented together, so
per-ticket isolation is not measured).

| Command | Result |
| --- | --- |
| pytest (`tests` + audit skill tests, offline) | `298 passed, 5 skipped, 1 warning` |
| `ruff check src tests AI-work/skills/run-ingest-api-audit` | `All checks passed!` |
| `ruff format --check src tests` | `67 files already formatted` |
| `mypy src/pov_retell` | `Success: no issues found in 45 source files` |
| `git diff --check` | exit 0 (tracked files only; new files are untracked) |

### Acceptance criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| One relationship call per chapter, after the character step | pass | `graph.py:245-246`; `test_one_relationship_call_per_chapter_after_character_step_and_prompt_markers` (`tests/test_relationship_ingest.py:53`) |
| Prompt has roster, active IDs, only open relationships of active characters, context through N-1, chapter N text | pass | `relationship.py:90-106`, `format_open_relationships` (`:23-33`); `graph.py:90` uses `summaries[:index]`; same marker test |
| Each Requirement 4 rule rejects and retries with its reason | pass | `relationship.py:132-149`, `:162-166`; parametrized `test_relationship_validation_rejects_and_retries_with_reason` (`:267`): unknown ID, self-reference, other-chapter paragraph, `end` without open record, 6-word kind |
| `start` then `end` gives one record with `valid_to`; repeated `start` is a no-op | pass | `relationship.py:151-182`; `tests/test_relationship_ingest.py:182` checks the u02 snapshot and the final file exactly |
| Merge rewrites relationship IDs | pass | `rewrite_relationships_for_redirects` (`relationship.py:41-76`) runs in `validate_characters` (`graph.py:72-77`); `tests/test_relationship_ingest.py:312` |
| Saved file shapes | pass | `graph.py:197-205`; exact dict comparison in the `:182` test |
| One recursion-limit helper per graph, used by pipeline and runner | pass | `extract_character_recursion_limit` (`graph.py:15`), `summarize_chapter_recursion_limit`; `pipeline.py:51`, `:72`; `run_api_audit.py:306`, `:336`; `tests/test_relationship_ingest.py:379` |
| Book-agnostic prompt test, README, context pass | pass | `tests/test_relationship_ingest.py:407`; README line 296 documents the node order |

### Findings

None required.

**Note 1 (undisclosed prompt rule).** `extract_relationship.py:34` adds "Family relationships
never end; never return op "end" for a family relation." The ticket did not ask for it. It
is reasonable for blood relations but would block ending a marriage. Keep it unless the live
check shows a problem.

**Note 2.** After a merge, a record that becomes a self-link is dropped silently
(`relationship.py:56-57`), and duplicate open records keep the smallest `relationship_id` by
string order (correct up to `rel_999`). Both are acceptable for now.

### Not measured

Kind quality, direction and the Narnia checks under Verification (siblings from u01, the
servant relation from u02). Next step: the live run, after the user's OK.
