---
id: T-0018
title: Refactor ingestion into cohesive LangGraph modules (behavior unchanged)
status: verified
owner: Claude Sonnet (subagent, at the user's request)
branch: ticket/T-0018-langgraph-refactor
priority: high
created: 2026-11-19
updated: 2026-11-19
depends_on: [T-0017]
---

# T-0018: Refactor ingestion into cohesive LangGraph modules (behavior unchanged)

## Background

The user (2026-11-19): "the current code looks very confusing. I want to separate this like
production code: high cohesion, low coupling. Refactor the code ... based on best practice for
LangGraph." Claude designs and reviews only; a Sonnet agent implements.

Problems in the current code (branch `ticket/T-0017-knowledge-timeline`):

1. `extract_character/graph.py` (411 lines) defines all 14 per-chapter nodes as closures inside
   one builder. The graph's name no longer matches its job: it extracts characters,
   relationships, locations, scenes, events, utterances, claims and knowledge.
2. One `ExtractCharacterState` TypedDict (~30 keys) and one `model.py` (281 lines) hold the
   models of every step.
3. `save_json` knows every step's file names; adding a step means editing it.
4. Dependencies (LLM clients, writer, `on_step`) are captured by closures, not injected.
5. Cross-graph coupling: extraction imports `format_previous_context` and `name_key` from
   `summarize_chapter.logic`; `knowledge.py` imports `ChapterChecks` from `events.py`;
   `extract_character/logic.py` mixes character validation, file writing and Neo4j rows.
6. `infrastructure/neo4j_store.py` holds connection, schema, one long Cypher tuple for every
   entity, and the writer.

## User decisions

- 2026-11-19: refactor for high cohesion and low coupling, following LangGraph best practice.
  Claude is the designer and reviewer only; a Sonnet agent (high effort) writes the code.

## PM design (the implementer follows this; deviations go in the Completion report)

### Principles

- **Pure refactor.** Behavior, prompts, validation rules, error messages, saved files and the
  Neo4j schema stay the same. The only intended visible change is the rename in item 1 below.
- **One module, one job.** `graph.py` only wires nodes and edges. Node functions are thin:
  read state, call pure logic, return a state update. Logic modules are pure functions
  (no LangGraph imports, no file I/O).
- **Dependencies are injected** with LangGraph's runtime context (`context_schema` +
  `Runtime[...]`, langgraph 1.2.15), not with closures.
- **Dependencies point one way.** The extraction steps form a chain:
  characters → relationships → locations → scenes → events → knowledge.
  A step may import from earlier steps (their models) and from shared modules, never from a
  later step or from the graph wiring.

### Target layout

```text
src/pov_retell/ingest/
├── pipeline.py            run orchestration (builds contexts, invokes graphs, run status)
├── model.py               Chapter, IngestResult, GraphWriter (unchanged)
├── source.py, timeline.py (imports only)
├── text.py                NEW shared text helpers: name_key, normalized, appears_in_source,
│                          unique_names, combine_descriptions
├── storage.py             NEW save_json (atomic write)
└── graph/
    ├── base.py            NEW StrictModel, Text
    ├── summarize_chapter/
    │   ├── graph.py       wiring only
    │   ├── nodes.py       node functions
    │   ├── context.py     SummaryContext(text_llm, card_llm, on_step)
    │   ├── state.py       SummarizeChapterState (+ input schema)
    │   ├── model.py, logic.py, prompt/   (logic keeps format_previous_context)
    │   └── __init__.py    public contract for other graphs: ChapterSummary, format_previous_context
    └── extract_story/     RENAMED from extract_character
        ├── graph.py       wiring only: book loop + chapter subgraph built from STEPS
        ├── state.py       StoryState (+ StoryInput)
        ├── context.py     StoryContext(llm, writer, on_step)
        ├── output.py      save_json and save_graph nodes; files collected from the steps
        ├── snapshot.py    Neo4j rows (as now)
        └── steps/
            ├── __init__.py   Step dataclass + STEPS registry in order
            ├── checks.py     ChapterChecks (shared validation helpers, moved from events.py)
            ├── characters/   model.py, prompt.py, logic.py, identity.py, nodes.py
            ├── relationships/  model.py, prompt.py, logic.py, nodes.py
            ├── locations/      "
            ├── scenes/         "
            ├── events/         "
            └── knowledge/      "
src/pov_retell/infrastructure/neo4j/
├── __init__.py            re-exports connect, check_health, Neo4jUnavailable, Neo4jGraphWriter
├── connection.py          connect, check_health, Neo4jUnavailable
├── cypher.py              KEYS and one statements tuple per entity group;
│                          CHAPTER_STATEMENTS = the same statements in the same order as today
└── writer.py              Neo4jGraphWriter
```

`infrastructure/neo4j_store.py` and `ingest/graph/extract_character/` are removed (no
compatibility shims). Small placement choices inside this layout are the implementer's call.

### Graph shape

- **extract_story**: a parent graph loops over chapters; a compiled **chapter subgraph** runs
  one chapter. Parent: `START → initialize → chapter → (route) → chapter | END`. Subgraph:
  for each step in `STEPS`, `extract_<name> → validate_<name>`, then `save_json → save_graph`
  (`save_graph` advances `chapter_index`, as today).
- Parent and subgraph share `StoryState`. Cumulative keys (characters, claims, knowledge, …)
  keep **overwrite** semantics. Do not put `operator.add` reducers on keys the subgraph
  returns in full, or the parent will append the whole list again (known LangGraph pitfall).
- Node names stay exactly as today (`extract_characters`, `validate_characters`, …,
  `save_json`, `save_graph`), and so do the `on_step` messages they report.
- `Step` (per step package): `name`, `extract` node, `validate` node, and
  `files(state) -> list[tuple[str, Any]]` returning (path relative to the run directory,
  JSON value) for that chapter's and the cumulative files. `save_json` writes what the steps
  return, plus `identity_redirects.json`, in the same files and content as today.
- Rename: graph `extract_character` → `extract_story` everywhere, including `run_name`,
  `on_step` text ("Build extract_story graph: model=…") and the recursion-limit helper
  (`extract_story_recursion_limit`). Keep its value a safe upper bound for the new shape.
- **summarize_chapter**: same pattern (nodes module, runtime context); its shape is unchanged.
- If the runtime context does not reach the chapter subgraph in langgraph 1.2.15, prove it
  with a small test, then use one flat `extract_story` graph built from `STEPS`, with the
  same node names. Record this as a deviation.

## Requirements

1. Implement the layout, principles and graph shape above.
2. Update `cli.py`, `pipeline.py`, `timeline.py` and the audit runner
   (`AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`) for the new modules and
   the context-based invoke.
3. Tests: assertions keep their meaning. Allowed test edits: imports, how graphs are built
   and invoked (context), the renamed graph name and helper, moved monkeypatch targets.
   Add tests for: the `STEPS` order and node names, `graph.py` holding no business logic
   (for example, the compiled graph's node list), and the context reaching every node.
4. README ("How it works today", "Repository layout") uses the new names and paths.
   Do not edit `AI-work/PROJECT_CONTEXT.md` (Claude runs context maintenance afterwards).

## Acceptance criteria

- [ ] Before refactoring, the implementer snapshots every prompt constant and
      `CHAPTER_STATEMENTS` to a scratch JSON file. Afterwards a script shows they are
      byte-identical.
- [ ] Golden run: the fake-LLM 2-chapter story from `tests/test_knowledge.py` (`STORY`) is run
      through `ingest_book` before and after, into two temp dirs. Every saved file is
      identical, and so are the recorded writer snapshots. The comparison script and its
      output are reported.
- [ ] No module under `extract_story/steps/<x>/` imports a later step, `extract_story.graph`,
      or `summarize_chapter` internals (only its package `__init__` contract). Checked by a
      test or a grep reported in the Completion report.
- [ ] `graph.py` files contain only wiring; no node function body is longer than ~25 lines.
- [ ] `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
      passes with at least the base count (`381 passed, 5 skipped`) plus the new tests.
- [ ] `ruff check`, `ruff format --check`, `mypy src/pov_retell` are clean. `mypy src tests`
      reports no errors beyond the 18 existing ones (in `tests/test_config.py`,
      `tests/test_llm.py`, `tests/test_character_ingest.py`).
- [ ] Opt-in Neo4j tests pass (`env POV_NEO4J=1 … -m neo4j`) if a local Neo4j can be started.

## Out of scope

- Any change to prompts, validation rules, models' fields, file formats, Neo4j schema, LLM
  client (`infrastructure/llm.py`), Phase A (`book/`), or the knowledge model.
- Live API calls. Pushing, merging.

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
.venv/bin/mypy src tests
git diff --check
```

Neo4j: the implementer may run `open -a Docker`, `make neo4j-up`, the opt-in tests, then
`make neo4j-down` and quit Docker. No live OpenRouter calls.

## Branch

`ticket/T-0018-langgraph-refactor`, stacked on `ticket/T-0017-knowledge-timeline` (PR #9,
not merged yet) because the refactor must include the knowledge step. Merge order: #9, then
this branch.

## Open questions

None. If something in the design does not work, record the deviation and the evidence.

## Completion report

Implemented by Claude Sonnet (subagent). Commits on `ticket/T-0018-langgraph-refactor`:
`01066da` take ticket, `09e679b` neo4j package and shared helpers, `3ded125` steps, runtime context,
chapter subgraph, pipeline, tests and audit runner, `59fda6a` new structure tests, `47f1e7a` README.
The `T-0018: done` commit follows this report.

### Changes by module

- `ingest/text.py` (new): `name_key` (moved from `summarize_chapter.logic`), `normalized`,
  `appears_in_source`, `unique_names`, `combine_descriptions` (moved from `identity.py`).
- `ingest/storage.py` (new): atomic `save_json` (was `extract_character/logic.py`) and `save_model`
  (was `summarize_chapter.logic.save_summary`; same bytes).
- `ingest/graph/base.py` (new): `StrictModel`, `Text`.
- `infrastructure/neo4j/` (replaces `neo4j_store.py`): `connection.py`, `cypher.py` (`KEYS`, one
  statements tuple per entity, `CHAPTER_STATEMENTS` = the concatenation in the old order, `SNAPSHOT_LISTS`),
  `writer.py`, `__init__.py` re-exports.
- `ingest/graph/extract_story/` (replaces `extract_character/`):
  - `graph.py` wiring only: `build_chapter_graph` (subgraph built from `STEPS`),
    `build_extract_story_graph` (`initialize -> chapter -> route`), `extract_story_recursion_limit`.
  - `state.py` (`StoryState`, `StoryInput`, two small accessors), `context.py` (`StoryContext`,
    `StoryRuntime`), `nodes.py` (`initialize`, route), `output.py` (`save_json`, `save_graph`),
    `snapshot.py` (Neo4j rows, incl. `character_rows`).
  - `steps/{characters,relationships,locations,scenes,events,knowledge}/` with `model.py`, `prompt.py`
    (git-moved, byte-identical), `logic.py`, `nodes.py` (extract and validate nodes plus the step's
    `*_files(state)`), and `identity.py` for characters. `steps/checks.py` (`ChapterChecks`),
    `steps/registry.py` (`Step`, `STEPS`).
  - The `resolve_*` helpers moved from `snapshot.py` to the step that owns the record
    (`scenes/logic.py`, `events/logic.py`, `knowledge/logic.py`); `resolve_ids` (new, in
    `characters/identity.py`) replaces three copies of the same redirect-and-dedupe expression.
- `ingest/graph/summarize_chapter/`: `graph.py` wiring only, `nodes.py`, `context.py` (`SummaryContext`),
  `state.py` (state, input schema, `upsert_cards` reducer), `__init__.py` (public contract:
  `ChapterSummary`, `format_previous_context`); `logic.py` and `model.py` lost the moved pieces.
- `ingest/pipeline.py`, `cli.py`, audit runner: build contexts and call `invoke(..., context=...)`;
  graph/run name, "Build extract_story graph" message and the `on_step("extract_story")` marker renamed.
  The audit runner's phase label is now `extract_story`; its manifest keys stay `extract_character`
  because they mirror the `OPENROUTER_EXTRACT_CHARACTER_*` settings, not the graph.
- Tests: imports, graph build and invoke (context), renamed helper and message; new
  `tests/test_ingest_graph_structure.py` (16 tests). README "How it works today" and "Repository layout".

### Acceptance criteria and evidence

Scratch files are in `/private/tmp/claude-501/-Users-nhanvu-Documents-code-book-clone/ebefb236-2596-49f1-8100-c977c55d7378/scratchpad/t0018/`
(`dump_constants.py`, `golden_run.py`, `golden_merge.py`, `compare.py`, `baseline_*.json`, `after_*.json`).

- Prompts and Cypher byte-identical: `dump_constants.py` dumped 14 prompt constants (`PROMPT_*`, `*_INPUT`),
  45 `CHAPTER_STATEMENTS` and 8 `KEYS` before and after; `cmp baseline_constants.json after_constants.json`
  printed no difference ("CONSTANTS IDENTICAL").
- Golden run: `golden_run.py` (STORY from `tests/test_knowledge.py`, 2 chapters, `ingest_book`, fake LLM)
  compared with `compare.py baseline_golden.json after_golden.json`:
  ```text
  files: IDENTICAL (36 entries)          llm_calls: IDENTICAL (12 entries)
  result: IDENTICAL (3 entries)          snapshots: IDENTICAL (2 entries)
  steps: IDENTICAL (46 entries)          summary_calls: IDENTICAL (3 entries)
  writer_events: IDENTICAL (4 entries)   RESULT: all identical
  ```
  `llm_calls` holds every rendered prompt. The only step messages that differ are the two intended
  renames (`extract_character` -> `extract_story`, "Build extract_character graph" -> "Build extract_story
  graph"); `compare.py` maps these before comparing. A second golden, `golden_merge.py`, covers a chapter-2 merge
  that retires a character with open relationships (rewrite, duplicate collapse, end of a relationship):
  files (36), snapshots, llm_calls and steps are identical (baseline run on a worktree of `01066da`).
  No existing test covered that path through `ingest_book`, because the rewrite moved (see Deviations).
- Step imports: `tests/test_ingest_graph_structure.py::test_steps_import_only_earlier_steps_and_shared_modules`
  (AST, per step) plus a grep loop over `steps/<x>/` printed "no forbidden imports" for all six steps
  (no later step, no `extract_story.graph`, no `steps.registry`, no `summarize_chapter.*` module). The test fails
  when a later-step import is added (checked by hand with a temporary import).
- `graph.py` only wiring: `test_graph_modules_only_wire` (only `build_*` and `*_recursion_limit` functions);
  `test_node_functions_stay_short` (every function in the nodes modules and `output.py` is <= 25 lines; the
  longest are 23). `extract_story/graph.py` is 51 lines.
- Pytest: `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  -> `397 passed, 5 skipped, 1 warning` (base 381 + 16 new).
- `ruff check src tests AI-work/skills/run-ingest-api-audit` -> `All checks passed!`;
  `ruff format --check ...` -> `113 files already formatted`; `mypy src/pov_retell` -> `Success: no issues found
  in 82 source files`; `mypy src tests` -> `Found 18 errors in 3 files` (test_config 10, test_llm 6,
  test_character_ingest 2: the same 18 as the base); `git diff --check` clean.
- Neo4j: Docker started in about 10 s. `make neo4j-up` first failed on a stale exited container
  (`RWLayer ... is unexpectedly nil`); `make neo4j-down` removed it (the named data volume is untouched) and
  `make neo4j-up` then reached `Healthy`. `env POV_NEO4J=1 .venv/bin/python -m pytest tests/test_neo4j_integration.py -q -m neo4j`
  -> `3 passed`. Then `make neo4j-down` and Docker quit.
- Runtime context in a subgraph (design check before the build): `ctx_probe.py` (scratch) and
  `test_context_reaches_nodes_of_a_subgraph_used_as_a_node` show the parent's `context=` reaches nodes of a
  compiled subgraph used as a node, and that overwrite state keys work without reducers. The subgraph design
  was used; the flat fallback was not needed. `test_story_context_reaches_every_node` and
  `test_summary_context_reaches_every_node` check the LLM, writer and `on_step` reach every node of both graphs.

### Deviations

1. **`Step` and `STEPS` live in `steps/registry.py`, not `steps/__init__.py`.** `state.py` imports every
   step's models, and every step's nodes import `state.py`. If `steps/__init__.py` imported the nodes, importing
   `state.py` first would run `steps/__init__.py`, which imports a nodes module that imports the half-loaded
   `state.py` (circular import). Keeping `steps/__init__.py` and the step `__init__.py` files empty and putting
   the registry in its own module avoids it.
2. **The relationship rewrite after a character merge moved from `validate_characters` to the start of
   `extract_relationships`.** In the old graph `validate_characters` called the relationships module, which breaks
   "a step never imports a later step". The same function now runs at the start of `extract_relationships`
   with the same inputs (cumulative redirects, chapter order) and stores the rewritten list before the LLM call
   and validation use it. Node names, `on_step` messages, saved files and results are unchanged (golden and
   merge golden identical).
3. **`extract_story/nodes.py` added** for `initialize` and the route function (the layout had no home for them).
   `StoryRuntime`, `current_chapter` and `earlier_summaries` were also added as tiny helpers.
4. **Node type in `Step`** is a `Protocol` with a keyword-only `runtime` (that is what LangGraph's typing
   expects), so `StateGraph.add_node` type-checks under `mypy --strict`.
5. `on_step("extract_character")` in `pipeline.py` and the audit runner phase label were renamed to
   `extract_story` along with the graph (the ticket lists the "Build" message, run name and helper only).
   The audit manifest keys `extract_character` are left, since they mirror the settings names.
6. `save_summary` (summary file writer) moved to `storage.save_model`; output bytes are identical
   (`model_dump_json(indent=2)` is kept).

### Follow-ups noticed

- `characters/identity.py::focus_is_ambiguous` is unused anywhere (source, tests); kept to stay a pure refactor.
- Chapter nodes still pass 7 to 11 positional arguments to the logic functions; a per-step "inputs" object
  would be a separate, behavior-neutral cleanup.
- `AI-work/PROJECT_CONTEXT.md` is not updated (the product manager runs context maintenance).

## Review

Reviewed by Claude (product manager) on 2026-11-19. Verdict: **verified**.

### Verification rerun by the reviewer (branch at `57fba21`)

| Check | Result |
| --- | --- |
| `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q` | `397 passed, 5 skipped` (base 381 + 16 new) |
| `ruff check` / `ruff format --check` | passed / 113 files already formatted |
| `mypy src/pov_retell` / `mypy src tests` | no issues in 82 files / the same 18 pre-existing test errors |
| `git diff --check 89fea0e HEAD` | clean |
| Constants script (14 prompt constants, 45 statements, 8 keys) | `cmp` byte-identical with the pre-refactor baseline |
| Golden run (`STORY`, 2 chapters) | files 36, LLM prompts 12, summary prompts 3, snapshots 2, writer events 4, steps 46: all identical (after mapping the two intended rename messages) |
| Merge golden | Reviewer rebuilt the baseline from a fresh worktree of `01066da` (pre-refactor): all identical |
| Neo4j opt-in | Not rerun by the reviewer (Docker off); implementer reports `3 passed` |

### Acceptance criteria

| Criterion | Result |
| --- | --- |
| Prompts and `CHAPTER_STATEMENTS` byte-identical | pass (rerun above) |
| Golden run identical | pass (rerun above, two scenarios) |
| Dependency direction | pass: `test_steps_import_only_earlier_steps_and_shared_modules`, `test_shared_step_helpers_do_not_import_the_knowledge_step_or_graph`; reviewer grep found no later-step import and no `langgraph` or file I/O in `steps/*/logic.py`, `steps/*/model.py`, `summarize_chapter/logic.py` |
| `graph.py` only wiring, short nodes | pass: `test_graph_modules_only_wire`, `test_node_functions_stay_short`; reviewer read both `graph.py` files |
| Suite, lint, format, types | pass |
| Neo4j opt-in | pass per implementer; not independently rerun |

### Design check

- `extract_story/graph.py` builds the chapter subgraph from `STEPS` and a parent loop
  `initialize → chapter → (next_chapter | done)`. Runtime context reaches subgraph nodes
  (`test_context_reaches_nodes_of_a_subgraph_used_as_a_node`). No list reducers; overwrite semantics.
- Each step package holds model, prompt, pure logic and thin nodes; `save_json` collects
  `Step.files`; Neo4j is split into `connection`, `cypher`, `writer`.
- Deviations 1–6 in the Completion report are accepted. Deviation 2 (relationship rewrite
  moved to the start of `extract_relationships`) keeps the dependency direction and was
  covered by the reviewer's merge golden. Deviation 5 (the `extract_story` step and audit
  phase labels) follows the rename decision.

### Findings (no change requested)

- **N1:** the comment on `EXTRACT_NODES_PER_CHAPTER` says "plus initialize", but the value
  (`len(STEPS) * 2 + 2`) does not count it. `extract_story_recursion_limit` is still sized for
  the old flat graph; with the subgraph the parent needs about `N + 3` supersteps. It is safe
  but loose.
- **N2:** `initialize` still raises "Character extraction requires chapters" (old wording,
  kept to preserve behavior).
- **Follow-ups (separate tickets if wanted):** remove unused
  `characters/identity.py::focus_is_ambiguous`; replace the long positional argument lists
  of the logic functions with one input object per step.

A passing suite and identical golden output prove the refactor preserved behavior on the
covered paths; they say nothing about story-fact quality, which is still unmeasured live.
