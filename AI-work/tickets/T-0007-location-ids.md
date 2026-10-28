---
id: T-0007
title: "Locations with IDs: structured place extraction per chapter"
status: verified
owner: Terra (gpt-5.6-sol)
priority: medium
created: 2026-10-25
updated: 2026-10-25
depends_on: [T-0005, T-0006]
---

# T-0007: Locations with IDs: structured place extraction per chapter

## Background

WHERE IS WHERE (T-0006) helps the LLM recognize places but has no IDs. The scene map (T-0008)
and later events need stable place IDs. Character IDs work this way already:

- the LLM proposes temporary `new_N` IDs and reuses existing IDs;
- Python assigns permanent IDs and keeps the state.

Places follow the same pattern with `loc_NNN`.

## User decisions

- 2026-10-25: accepted step 5 of the reading order, "places with IDs", and asked for all
  agreed tickets.
- JSON jobs use the extract client (GLM after T-0005).

## PM recommendations

The user may veto these before work starts:

- No place merges in this ticket. The prompt says to reuse existing IDs. Add merges later
  only if the live check shows duplicates.
- `kind` is set only when unknown or corrected, like `species` for characters.

## Requirements

1. **New per-chapter step** in the extraction graph, after the character step, using the
   extract client. It may run before or after T-0004's relationship step; document the order.
2. **Input:**
   - book title and chapter ID;
   - `format_previous_context` before N, which includes WHERE IS WHERE after T-0006;
   - the current locations list as JSON (`location_id`, `name`, `aliases`, `kind`, `part_of`);
   - the chapter text.
3. **Output (changes only):**
   `{"locations": [{"location_id": "new_N" | "loc_NNN", "name", "aliases": [], "kind": str | null,
   "part_of": "loc_NNN" | "new_N" | null}]}`.
   - It contains new places, plus existing places that appear or gain information in this
     chapter.
   - Return `{"locations": []}` when nothing changes.
4. **Prompt rules:** the same notion of place as T-0006.
   - Reuse an existing ID after checking every name and alias.
   - A changed name keeps the old name as an alias.
   - `kind` is a lasting description of at most 12 words.
   - `part_of` only when the text places it inside another place.
   - Use generic examples only.
5. **Python validation**; reject with a reason and retry:
   - `new_N` format;
   - existing IDs exist and appear at most once;
   - `part_of` refers to an existing ID or a `new_N` in the same response;
   - no self-reference or containment cycle.

   **Merge:**
   - Python assigns `loc_NNN` in order;
   - aliases are unioned;
   - `kind` is replaced only by a non-null value;
   - `part_of` is updated when given.
6. **Storage:** `locations.json`, `chapters/uNN.locations.json` (snapshot) and
   `chapters/uNN.locations.proposed.json`.
7. **Recursion limit** through the per-graph helper. Update the audit runner (call counts,
   test), `run-protocol.md`, README, and run a context-maintenance pass.

## Acceptance criteria

- [x] One location call per chapter. IDs `loc_001…` are assigned in order. Existing IDs are
      reused across chapters. Offline test.
- [x] Each validation rule rejects and retries with its reason: unknown ID, duplicate ID, bad
      `part_of`, cycle. Offline tests.
- [x] A name change keeps the old name as an alias. Offline test.
- [x] Saved files have the shapes above. Offline test.
- [x] Book-agnostic prompt test. Runner test updated. All Verification commands pass. README
      updated. Context pass done.

## Out of scope

- Place merges, Neo4j `Location` nodes, `OCCURRED_AT`, the scene map, events.

## Files likely touched

- new `src/pov_retell/ingest/graph/extract_location/` (or inside the extraction graph package) with `prompt/`
- `src/pov_retell/ingest/graph/extract_character/graph.py` (wiring), `src/pov_retell/ingest/pipeline.py`
- audit runner, its test, `run-protocol.md`, `tests/`, `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK):

- the ten reference places from T-0006 have one ID each;
- the pavilion is `part_of` the Stone Table;
- no objects or people appear in the list.

## Open questions

- Should the summary-stage WHERE IS WHERE be dropped once IDs exist? Default: keep it. It is
  the reader's context; the IDs are the data.

## Completion report

- **What changed:**
  - Added `LocationRecord`, `LocationCandidate`, `ExtractLocationResponse`, and state fields (`locations`, `proposed_locations`, `next_location_number`) in `src/pov_retell/ingest/graph/extract_character/model.py`.
  - Created book-agnostic `src/pov_retell/ingest/graph/extract_character/prompt/extract_location.py` (`PROMPT_EXTRACT_LOCATION`).
  - Created `src/pov_retell/ingest/graph/extract_character/location.py` (`extract_locations`, `validate_locations`) validating `new_N` format, existing IDs and duplicate IDs, `part_of` references (`loc_NNN` or `new_N` in the same response), no self-reference or containment cycles, and `kind` <= 12 words; assigning `loc_NNN` in order, unioning aliases while keeping the old name in `aliases` on rename, replacing `kind` when non-null, and updating `part_of` when given.
  - Wired `extract_locations` and `validate_locations` into `src/pov_retell/ingest/graph/extract_character/graph.py` after `validate_relationships` (`EXTRACT_NODES_PER_CHAPTER = 7`), persisting `locations.json`, `chapters/uNN.locations.json`, and `chapters/uNN.locations.proposed.json`.
  - Added `tests/test_location_ingest.py` and updated `tests/test_character_ingest.py`, `tests/test_relationship_ingest.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`, `README.md`, and `AI-work/PROJECT_CONTEXT.md`.
- **Files touched:**
  - `src/pov_retell/ingest/graph/extract_character/model.py`
  - `src/pov_retell/ingest/graph/extract_character/prompt/extract_location.py`
  - `src/pov_retell/ingest/graph/extract_character/location.py`
  - `src/pov_retell/ingest/graph/extract_character/graph.py`
  - `tests/test_location_ingest.py`
  - `tests/test_character_ingest.py`
  - `tests/test_relationship_ingest.py`
  - `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`
  - `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`
  - `README.md`
  - `AI-work/PROJECT_CONTEXT.md`
  - `AI-work/tickets/T-0007-location-ids.md`
  - `AI-work/tickets/README.md`
- **Verification outputs:**
  - `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q` -> `262 passed, 5 skipped`
  - `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit` -> `All checks passed!`
  - `.venv/bin/ruff format --check src tests` -> `62 files already formatted`
  - `.venv/bin/mypy src/pov_retell` -> `Success: no issues found in 43 source files`
  - `git diff --check` -> clean (0 output)
- **Context maintenance:** Performed bounded context-maintenance pass in `AI-work/PROJECT_CONTEXT.md` directly (Codex `gpt-5.6-sol` and Claude Sonnet 5.5 are not exposed in this Antigravity runtime).
- **Remaining risks / notes:** Not yet exercised with a live OpenRouter run; ready for Claude review.

### Repair follow-up — 2026-10-25

- **Claude F1 repair:** Replaced the Narnia-derived unnamed-place, object, and `kind`
  examples in `extract_location.py` with generic examples. The output example, field rules,
  schema, validation, graph wiring, and model settings are unchanged.
- **Regression coverage:** Extended the book-agnostic prompt test with `wardrobe`, `lamp`,
  `spare room`, `hilltop`, `Stone Table`, `pavilion`, `Professor`, `Cair`, and `Paravel`.
- **RED:** The two targeted parametrized prompt tests produced `8 failed, 42 passed,
  1 warning`; the failures were the four terms present in both prompts: `wardrobe`, `lamp`,
  `spare room`, and `hilltop`.
- **GREEN:** The same targeted tests produced `50 passed, 1 warning`.
- **Parent-review F2 repair:** Permanent `part_of` targets are now checked only against an
  immutable set of IDs supplied in the input roster. IDs assigned to `new_N` entries during
  the current merge cannot accidentally satisfy an unseen `loc_NNN` reference; complete
  `new_id_map` resolution still permits valid forward local `new_N` containment.
- **F2 RED / GREEN:** The direct regression produced `1 failed, 2 passed, 1 warning` before
  the fix: parent-first order incorrectly accepted `part_of="loc_001"`, while reversed order
  rejected it and a forward local `new_N` reference passed. After the fix, all three cases
  produced `3 passed, 1 warning`.
- **Verification:** Full offline pytest produced `317 passed, 5 skipped, 1 warning`;
  `ruff check` passed; `ruff format --check` reported `67 files already formatted`; mypy
  reported no issues in 45 source files; `git diff --check` exited 0 with no output.
- **Deviation / follow-up:** No live API or Neo4j run was performed. Parent technical review and the
  separate context-maintenance pass are complete; status is `done`, pending Claude re-review.

### Parent technical re-review — 2026-10-25

- The initiating Codex agent reviewed Terra's changes against the pre-repair file snapshot,
  then independently reran every Verification command on the combined working tree.
- No additional blocking findings remain in the reviewed scope. Claude F1 is addressed by
  generic prompt examples and regressions for all cited place/object terms. T-0007's additional
  F2 is covered in both response orders, with a valid forward local-ID case still passing.
- Verification: `317 passed, 5 skipped, 1 warning`; Ruff check passed; format check reported
  `67 files already formatted`; mypy found no issues in 45 source files; `git diff --check` passed.
  The warning is the pre-existing LangSmith deprecation warning, not a new failure.
- A separate Terra (`gpt-5.6-sol`) context-maintenance pass updated `AI-work/PROJECT_CONTEXT.md`;
  the initiating agent reviewed it. No live API/Neo4j validation was performed.
- Implementation status is `done`, pending Claude's product-manager re-review. The historical
  Review section below is retained; this technical pass does not mark the ticket `verified`.

## Review

Reviewed by Claude (product manager) on 2026-10-25. Verdict: **changes_requested**.
ID assignment, validation, merge and storage are correct and tested. The prompt's examples
come from the test book (F1), as in T-0006.

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
| One call per chapter; `loc_001...` in order; existing IDs reused | pass | `graph.py:247-248`; `location.py:69-76`; `test_one_location_call_per_chapter_assigns_ids_reuses_existing_and_saves_files` (`tests/test_location_ingest.py:52`) |
| Each validation rule rejects and retries with its reason | pass | `location.py:60-124`; parametrized test (`tests/test_location_ingest.py:273`): unknown ID, duplicate ID, unknown `part_of` (existing and `new_N`), self-reference, two cycles |
| A name change keeps the old name as an alias | pass | `location.py:105-110`; aliases asserted in the `:52` test |
| Saved file shapes | pass | `graph.py:206-214`; exact comparisons in the `:52` test |
| Book-agnostic prompt test | **fail** | the test passes, but its word list (`tests/test_location_ingest.py:339-359`) has only character and two place names; see F1 |
| Runner test, verification, README, context pass, step order documented | pass | `run-protocol.md:28-29`; README line 296 shows the order (after relationships) |

### Findings

**F1 (required): prompt examples come from the test book.** Requirement 4 says "Use generic
examples only".
- `extract_location.py:19`: "the spare room", "the hilltop camp" (as in T-0006).
- `:20`: "a lamp, wardrobe, table" (the test book's lamp-post, wardrobe, Stone Table).
- `:42-43`: kind examples "large country house", "upstairs room", "snowy forest clearing",
  "stone fortress on a hill" match the Professor's house, the spare room, the snowy wood at
  the lamp-post and Cair Paravel.

The OUTPUT example ("the old manor", "the north attic") is fine. Replace the examples above
with ones no test book uses, and extend the book-agnostic test with the same words as T-0006
F1.

### Not measured

The Verification live checks (ten places with one ID each, the pavilion `part_of` the Stone
Table, no objects or people); need a live run and the user's OK.

### Re-review (2026-10-25)

Verdict: **verified**. The reviewer reran the checks on the combined tree.

- Offline pytest: `317 passed, 5 skipped, 1 warning` (the LangSmith deprecation warning).
- `ruff check`: all checks passed. `ruff format --check`: 73 files already formatted
  (`src`, `tests` and the audit skill). `mypy src/pov_retell`: no issues in 45 source files.
  `git diff --check`: clean.
- A case-insensitive scan of every prompt under `src/pov_retell/ingest/graph/*/prompt/` for
  the test book's names, places and objects finds none. The only hit was "switches",
  which contains "witch" as a substring.
- F1 fixed: `extract_location.py` uses the same generic place and object examples as
  T-0006. Its `kind` examples are now "coastal village", "underground passage", "desert
  oasis" and "timber watchtower". The book-agnostic test lists all nine requested words
  (`tests/test_location_ingest.py:369-397`).
- Parent-review F2, an extra fix that is correct: `validate_locations` now checks an
  existing `part_of` only against the IDs in the input roster (`location.py:55, 87`). A
  `new_N` place given an ID during the same merge can no longer satisfy an unseen
  `loc_NNN` reference. Forward `new_N` references still resolve through `new_id_map`. A
  regression test covers both orders (`tests/test_location_ingest.py:320-332`).
- Still not measured: the live checks in Verification. They need a live run and the
  user's OK.
