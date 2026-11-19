---
id: T-0018
title: Refactor ingestion into cohesive LangGraph modules (behavior unchanged)
status: ready
owner: unassigned
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

_Filled by the implementer._

## Review

_Filled by the product manager._
