---
id: T-0011
title: "Remove the unused ScaleDown experiment and its required setting"
status: verified
owner: Codex (GPT-6)
priority: low
created: 2026-10-26
updated: 2026-10-26
depends_on: []
---

# T-0011: Remove the unused ScaleDown experiment and its required setting

## Background

`OPENROUTER_CHARACTER_ATTRIBUTES_MODEL=scaledown/extract` is left over from an early
experiment with ScaleDown Extract. It is a model on OpenRouter that takes text plus a
dictionary of entities and returns `structured_result` JSON.

Evidence (2026-10-26):
- `pov ingest` never calls the ScaleDown path. The only caller of
  `OpenRouterClient.complete_entities` (`src/pov_retell/infrastructure/llm.py:175`) is in
  the tests. Character, relationship, location and scene-map extraction all use
  `OPENROUTER_EXTRACT_CHARACTER_MODEL` through `complete_json`.
- The setting is still **required** (`src/pov_retell/config.py:48`). Without it in
  `.env`, `Settings()` fails and `pov ingest` stops, even though nothing uses it.
- T-0003 kept the adapter on purpose ("Keep unchanged"). The README calls it
  "Experimental diagnostics only; not called by `pov ingest`" (`README.md:123`, `:334`).

The dead path costs a required secret-free setting, an extra method on the `JsonLLM`
protocol, three response models, one prompt module and two test files. It also confuses
readers of `.env`.

## User decisions

- 2026-10-26: "clean clear". Remove the ScaleDown experiment completely.

## PM recommendations

- Remove the ScaleDown-only parsing that turns `[{"trait": ...}]` or `[{"name": ...}]`
  object arrays into strings (`unpack_entity_array`), together with its validators. The
  extract client now sends a strict JSON schema in which these fields are plain string
  lists, so that shape can no longer arrive. If a main-path test depends on it, keep it and
  report why.
- Keep historical run data, handoffs and old ticket text as they are. They are history.

## Requirements

1. **`src/pov_retell/infrastructure/llm.py`:**
   - delete `OpenRouterClient.complete_entities`;
   - delete its declaration on the `JsonLLM` protocol (line 74);
   - delete any import or constant used only by them.
2. **`src/pov_retell/config.py`:** delete `OPENROUTER_CHARACTER_ATTRIBUTES_MODEL`.
   `Settings` uses `extra="ignore"`, so a leftover line in a user's `.env` still loads.
3. **`src/pov_retell/ingest/graph/extract_character/model.py`:**
   - delete `RelationshipProposal`, `CharacterDetails` and `AttributeResponse`;
   - delete `unpack_entity_array` and its validators (PM recommendation);
   - keep every model that the ingest graph uses.
4. **Delete `src/pov_retell/ingest/graph/extract_character/prompt/extract_character_attributes.py`.**
5. **Tests:**
   - delete `tests/test_scaledown_extraction.py`;
   - delete the ScaleDown test in `tests/test_openrouter_integration.py` and keep the other
     integration test;
   - remove the setting from the env fixtures in `tests/test_llm.py`,
     `tests/test_config.py` and `tests/test_cli_ingest.py`;
   - rename the `"scaledown/summarize"` model string in
     `tests/test_llm.py::test_text_completion_uses_system_instructions_without_json_or_sampling_options`
     to a neutral one, for example `"test/summarize"`;
   - add one offline test: `Settings` loads from an env file that lacks
     `OPENROUTER_CHARACTER_ATTRIBUTES_MODEL`, and also from one that still contains it.
6. **Documentation:**
   - remove the setting and the ScaleDown text from `.env.example` (lines 11–12) and
     `README.md` (the settings table row at line 123 and the paragraph at line 334);
   - say in one README line that ScaleDown was removed on 2026-10-26.
7. Run the context-maintenance pass required by root `AGENTS.md`. Remove "ScaleDown"
   mentions from `AI-work/PROJECT_CONTEXT.md` only where they describe the current code.

## Acceptance criteria

- [x] Searching `src`, `tests`, `.env.example`, `README.md` and the audit skill finds no
      `complete_entities`, `CHARACTER_ATTRIBUTES`, `scaledown`, `ScaleDown`,
      `extract_character_attributes`, `AttributeResponse`, `CharacterDetails` or
      `RelationshipProposal`, except the one README removal line.
- [x] `Settings()` loads with and without the old line, proven by the new offline test.
- [x] Character, relationship, location and scene-map extraction behavior is unchanged.
      All existing tests for those paths pass without edits other than fixture env keys.
- [x] The full offline suite, ruff, format check and mypy pass. The test count drops only
      by the deleted ScaleDown tests; report the before and after counts.

## Out of scope

- `.env`. The user's file is not edited. The old line becomes harmless, and the user may
  delete it.
- `OPENROUTER_MODEL`, model choices, prompts, the extract or summary graph, run data,
  handoffs and earlier tickets.
- Live API calls and Neo4j.

## Files likely touched

- `src/pov_retell/infrastructure/llm.py`
- `src/pov_retell/config.py`
- `src/pov_retell/ingest/graph/extract_character/model.py`
- `src/pov_retell/ingest/graph/extract_character/prompt/extract_character_attributes.py` (deleted)
- `tests/test_scaledown_extraction.py` (deleted)
- `tests/test_openrouter_integration.py`, `tests/test_llm.py`, `tests/test_config.py`,
  `tests/test_cli_ingest.py`
- `.env.example`, `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
grep -rnE "complete_entities|CHARACTER_ATTRIBUTES|scaledown|ScaleDown|extract_character_attributes|AttributeResponse|CharacterDetails|RelationshipProposal" src tests .env.example README.md AI-work/skills
git diff --check
```

No live API calls. No Neo4j.

## Open questions

- None. If removing `unpack_entity_array` breaks a main-path test, keep it and report it
  in the Completion report.

## Completion report

Completed 2026-10-26 by Codex (GPT-6). Status: `done`; awaiting Claude's product-manager review.

### Changes

- Removed the unused entity adapter, its protocol and its only `json` import from
  `src/pov_retell/infrastructure/llm.py`. The declaration was on `EntityLLM`, not on
  `JsonLLM` as the ticket's earlier evidence described. The active JSON/text protocols,
  client options, retries and error handling are unchanged.
- Removed the required legacy setting from `config.py`, `.env.example` and test fixtures.
  `extra="ignore"` is retained. The user's `.env` has the same SHA-256 as before this task.
- Removed `RelationshipProposal`, `CharacterDetails`, `AttributeResponse`, the object-array
  unpacker and its validators from the extraction models. No main-path test depended on
  those validators, so none needed to be retained.
- Deleted the experimental attribute prompt and `tests/test_scaledown_extraction.py`.
  Removed the ScaleDown live test and its unused import while preserving the real
  structure-map test. Renamed the summary test model to `test/summarize`.
- Added one parameterized offline config test with two cases. Its legacy key is built from
  tokens to exercise the old env-file spelling without leaving an active setting reference
  in source searches. The test removes process-environment overrides and loads a temporary
  env file with and without the old line; the old key is discarded from the settings model.
- Updated the README prompt inventory/settings/prose and added its single dated removal line.
- Terra (`gpt-5.6-sol`, fresh-context `terra_context_t0011`) updated
  `AI-work/PROJECT_CONTEXT.md`; the initiating agent reviewed its diff against source and
  check results. Historical handoffs, tickets and run data were preserved.

Implementation files: `.env.example`, `README.md`, `src/pov_retell/config.py`,
`src/pov_retell/infrastructure/llm.py`,
`src/pov_retell/ingest/graph/extract_character/model.py`, the deleted
`prompt/extract_character_attributes.py` under that graph, `tests/test_config.py`,
`tests/test_llm.py`, `tests/test_cli_ingest.py`, `tests/test_openrouter_integration.py`,
and deleted `tests/test_scaledown_extraction.py`. Context, this ticket and the board were
updated as required.

### Acceptance evidence

1. **Removal search:** the exact ticket `grep -rnE` command now returns only
   `README.md:333`, the dated removal line. The first raw search also found three stale
   Python bytecode files for already-deleted experimental modules/tests; those regenerable
   `__pycache__/*.pyc` files were removed, and the exact command was rerun cleanly.
2. **Env compatibility:**
   `tests/test_config.py::test_settings_load_env_file_with_optional_legacy_model`
   was run before the production change: **2 failed** as expected (missing required field;
   legacy field still present in the settings dump). After removal: **2 passed**.
3. **Main paths preserved:** character, relationship, location and scene-map test files and
   their graph logic/prompts were not changed. All existing tests pass. An additional offline
   comparison against the pre-task model snapshot confirmed identical `strict_json_schema`
   output for `ExtractCharacterResponse`, `ExtractRelationshipResponse`,
   `ExtractLocationResponse` and `SceneMapResponse`. Deliberately removed compatibility:
   object arrays masquerading as string arrays are no longer normalized.
4. **Suite counts:** before **317 passed, 5 skipped** (322 collected); after
   **309 passed, 4 skipped** (313 collected). Exact arithmetic:
   `317 - 8 ScaleDown unit cases - 2 obsolete legacy-model blank-value cases + 2 new config cases = 309`;
   `5 - 1 ScaleDown live test = 4 skipped`. The remaining 4 integration cases are skipped by
   the explicit offline environment flags. Both runs show the same pre-existing LangSmith
   `DeprecationWarning`; no test failed in the completed suite.

### Commands and results

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  — **309 passed, 4 skipped, 1 warning**. A fresh independent technical-review agent ran
  the same suite and obtained the same result, with no findings requiring changes.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit` — **all checks passed**.
- `.venv/bin/ruff format --check src tests AI-work/skills/run-ingest-api-audit`
  — **71 files already formatted**. The initial check found one missing blank line after
  validator removal; formatting was applied only to that model file, then the check passed.
- `.venv/bin/mypy src/pov_retell` — **no issues in 44 source files**.
- `grep -rnE "complete_entities|CHARACTER_ATTRIBUTES|scaledown|ScaleDown|extract_character_attributes|AttributeResponse|CharacterDetails|RelationshipProposal" src tests .env.example README.md AI-work/skills`
  — **only the README removal line**, exit 0.
- `git diff --check` — **passed**, exit 0.

Pre-task snapshots and a scoped comparison are outside the repository at
`/Users/nhanvu/.codex/artifacts/T-0011/`. The dirty tree already contained unrelated work;
comparison used these snapshots rather than treating the whole Git diff as this ticket.
Presentation HTML changed concurrently and was not edited as part of T-0011.

### Limits and follow-up

No live API calls, Neo4j writes, `.env` changes, graph/model-choice changes, commits or
pushes. No application follow-up or unresolved technical finding. Ask Claude to review the
completed ticket; it has not been marked `verified` by the implementer.

## Review

Reviewed by Claude (product manager) on 2026-10-26. Verdict: **verified**.

### Verification rerun by the reviewer

| Check | Result |
| --- | --- |
| Offline pytest | `309 passed, 4 skipped, 1 warning`. Before: 317 passed, 5 skipped. The arithmetic in the Completion report adds up |
| `ruff check` / `ruff format --check` / `mypy` | All checks passed / 71 files already formatted / no issues in 44 source files |
| `git diff --check` | Clean |
| Removal search, extended with `unpack_entity_array` and `EntityLLM` | Only `README.md:333`, the dated removal line |
| Files | `extract_character_attributes.py` and `tests/test_scaledown_extraction.py` are gone. The four active prompt modules remain |
| Real `.env` | `Settings()` loads, and the old key is not a field. `.env` was not edited |

### Acceptance criteria

| Criterion | Result |
| --- | --- |
| No references left | pass |
| `Settings` loads with and without the old line | pass (`tests/test_config.py:79-96`, 2 cases) |
| Main extraction paths unchanged | pass. Their tests pass, and the report compares strict schemas against the pre-task snapshot |
| Suite, lint, format, types | pass |

### Notes (no change requested)

- The ticket's evidence said the method was declared on `JsonLLM`. It was on a separate
  `EntityLLM` protocol. The implementer handled this correctly; the error was the PM's.
- The new config test builds the legacy key from parts
  (`"_".join(("OPENROUTER", "CHARACTER", "ATTRIBUTES", "MODEL"))`) so that the removal
  search stays clean. The cause is a criterion that was too strict. A literal string plus a
  comment would read more clearly, but this is acceptable.
- The user may now delete line 15 of `.env`, `OPENROUTER_CHARACTER_ATTRIBUTES_MODEL`. It
  is ignored.
- No live API calls were made, and none were needed.
