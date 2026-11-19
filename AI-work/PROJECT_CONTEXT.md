# Current Project Context

Updated: 2026-11-19 from branch `ticket/T-0018-langgraph-refactor` (clean at HEAD `ae0f2d7`, review commit).
This is the concise onboarding reference, not a session transcript.
Read [root AGENTS.md](../AGENTS.md) before acting. Verify mutable settings and source when needed.

## Goal and Boundaries

`pov-retell` is a Python CLI that extracts a book, then ingests it chapter by chapter into
summaries, a character/location/scene/event/knowledge graph (JSON files and Neo4j), so that
later work can answer "what does character X know at point P" and retell a story from one
character's POV. It is not a FastAPI/web app. The POV narrator/retelling is not started.

User responses are Vietnamese; code, comments, prompts, and AI instructions are English.
Keep graph builders, models, logic, and prompts together by graph. Preserve previous book runs.

Branch state: T-0013 to T-0016 are merged into `main` (PRs #7 and #8). Open: PR #9 (`ticket/T-0017-knowledge-timeline`,
`done`, not reviewed by Claude) and PR #10 (presentation). `ticket/T-0018-langgraph-refactor` (current, `verified`,
review commit `ae0f2d7`) is stacked on top of the T-0017 branch and nothing of it is pushed. Merge order: #9, then T-0018.

## Current Workflow

```text
pov extract <source> --id <book_id>
  -> load HTML/EPUB/TXT -> LLM structure map -> validated units/paragraphs -> files

pov ingest <book_id>            # --neo4j is the default
  -> validate saved chapter files -> fresh run directory
  -> (Neo4j) start_run
  -> summarize_chapter graph -> extract_story graph (writes Neo4j after every chapter)
  -> (Neo4j) finish_run, or fail_run + re-raise on error
pov ingest <book_id> --no-neo4j   # no connect/health check/write; JSON files only
pov knowledge <book_id> <character> [--run R] [--until uNN|uNN_sM] [--json] [--reveal]
  -> reads a run's JSON files (no LLM, no Neo4j)
```

- Source validation compares chapter order, file set, paragraph IDs/order, and text with `book.json`.
- Summary graph: `initialize -> summarize_chapter -> update_who_is_who -> update_where_is_where -> validate_summary -> save_summary -> summarize_book`,
  looping across chapters; `summarize_book` runs once after the last chapter.
  The builder takes no arguments. Dependencies come from LangGraph runtime context
  `SummaryContext(text_llm, card_llm, on_step)`, passed as `invoke(..., context=...)`: the text client writes the
  chapter summary and `summarize_book`; the card updates (WHO IS WHO, WHERE IS WHERE) use the extract (JSON) client
  (T-0013 Rev. 2).
- Extraction graph `extract_story` (renamed from `extract_character` in T-0018; behavior unchanged). Parent graph:
  `initialize -> chapter -> (next_chapter | done)`. The `chapter` subgraph is built from `STEPS`
  (`steps/registry.py`: characters, relationships, locations, scenes, events, knowledge) and runs
  `extract_<step> -> validate_<step>` for each, then `save_json -> save_graph`. Node names and `on_step` messages are
  unchanged. Dependencies come from `StoryContext(llm, writer, on_step)` via `invoke(..., context=...)`; builders take no arguments.
  Recursion limits come from `summarize_chapter_recursion_limit` (`SUMMARY_NODES_PER_CHAPTER = 5`) and
  `extract_story_recursion_limit` (`EXTRACT_NODES_PER_CHAPTER = len(STEPS) * 2 + 2 = 14`), shared by `pipeline.py` and
  the audit runner.
- Step modules (`extract_story/steps/<step>/{model,prompt,logic,nodes}.py`) import only earlier steps and shared
  modules (`ingest/text.py`, `ingest/storage.py`, `graph/base.py`, `steps/checks.py`); a test enforces this.
  The relationship rewrite after character merges now runs at the start of `extract_relationships`.
- Call counts before retries: summary graph `3N+1` (3 per chapter + `summarize_book`; 52 for 17 chapters);
  extraction graph `6N` (characters, relationships, locations, scene map, events, knowledge).
- Every JSON call goes through `_ask`, which retries transient provider errors (HTTP 408/429/500/502/503/504 or
  words such as "overloaded", "rate limit", "timeout") up to `TRANSIENT_RETRIES = 5` extra times with
  full-jitter exponential backoff capped at 60 s (T-0014). This is separate from the validation retry loop
  (`MAX_RETRIES`, "Rejected: <reason>" messages). A `finish_reason == "error"` raises `LLMError` immediately (T-0005).
- Prior context for chapter N (`format_previous_context`, shared by summary and extraction prompts): WHO IS WHO
  and WHERE IS WHERE after chapter N-1 plus chapter summaries 1..N-1; u01 gets empty context.
- Summaries are fallible context; original chapter text remains evidence.
- No checkpoint, resume, automatic summary reuse, or parallel chapter extraction. Each run starts from chapter 1.

### Step contracts (all structured JSON, Python-validated, changes-only where noted)

- **Summary calls** (`summarize_chapter/prompt/`; `ChapterSummary` and `format_previous_context` are the package's public contract): Call 1 plain-text chapter summary in own words; Call 2/3
  `CardChanges` (`add` + `update`) for WHO IS WHO (`C001`) and WHERE IS WHERE (`P001`), reducer
  `upsert_cards`, rejecting unknown/duplicate update IDs and duplicate-name adds (quote-normalized `name_key`);
  Call 4 `validate_summary` renders cards without IDs into `ChapterSummary`; Call 5 `save_summary` writes
  `summaries/uNN.summary.json` (up to 2 extra attempts with `Rejected: <reason>`). The old full-list
  validators were removed in T-0013 Rev. 2. `summarize_book` writes `summaries/book_memory.json`
  (`who_is_who`, `where_is_where`, `core_memory`).
- **Characters** (`steps/characters/`, incl. `identity.py`): changes-only delta (new characters plus existing ones
  that gain information; null/[] = unchanged). No relationships field (`extra="forbid"`). `new_N` proposals get
  stable `char_NNN`; explicit merges keep the earliest ID and flatten redirects.
- **Relationships** (`steps/relationships/`): ops `start`/`end` with `source_id`, `target_id`, 1-5 word `kind`,
  current-chapter `paragraph_ids`; a repeated `start` for an open record is a no-op; merges rewrite IDs.
- **Locations** (`steps/locations/`): `new_N` -> `loc_NNN`, `part_of` references without self-reference or cycles,
  permanent `part_of` must refer to the immutable input roster.
- **Scene map** (`steps/scenes/`): complete ordered paragraph coverage without gaps/overlap, `segment_id` `uNN_sM`,
  `viewpoint_ids <= present_ids`, `present_ids & mentioned_ids == empty`, `time.relation`
  `continues|later|parallel|flashback|time_jump` (anchor required for `parallel`/`flashback`).
- **Events/claims** (`steps/events/`, T-0016): a claim is a short statement (<= 25 words) with
  `truth` `unknown|true|false`; events (<= 20 words) with participants and paragraph evidence; utterances
  (`spoken|written`, speaker or null, addressees, exact quote <= 40 words, checked against its cited paragraphs) that
  assert claims; `truth_changes` set a claim's truth later with paragraph evidence. Claim IDs are Python-assigned.
  Per-chapter files: `uNN.events.proposed.json`, `uNN.events.json`.
- **Knowledge** (`steps/knowledge/`, T-0017): acquisitions `(character, claim, channel,
  stance, segment, optional source, paragraph evidence)`. Channels: `prior`, `witnessed`, `told`, `read`,
  `overheard`, `inferred`, `learns_truth`. Stances: `believes`, `doubts`, `disbelieves`. The prompt receives the scene
  map, all claims, this chapter's events/utterances, and current beliefs of characters in the chapter. A repeated
  belief with the same stance (or a second `learns_truth`) is dropped rather than rejected. New claims here must be
  `prior` or `inferred` and used. Per-chapter files: `uNN.knowledge.proposed.json`, `uNN.knowledge.json`.
  The knowledge timeline (`ingest/timeline.py`) orders acquisitions (`prior` first), supports `--until`, follows
  merge redirects, and hides the book's real truth unless `--reveal`.

## Neo4j

- Writer: `Neo4jGraphWriter` in `infrastructure/neo4j/writer.py` (package `infrastructure/neo4j/`: `connection.py`,
  `cypher.py` statements per entity, `writer.py`; replaced `neo4j_store.py` in T-0018; methods
  `ensure_schema`, `start_run`, `write_chapter`, `finish_run`, `fail_run`). `save_graph` (last node per chapter)
  writes the cumulative run graph in one transaction, so merges/redirects that change earlier data cannot leave
  stale nodes. Without a writer (`--no-neo4j`) it does nothing.
- Every node is keyed `(book_id, run_id, <id>)`. Nodes: `IngestRun` (`status` running/complete/failed,
  `chapters_done`, `last_chapter_id`), `Character`, `Location`, `Scene`, `Claim`, `Event`, `Utterance`,
  `KnowledgeAcquisition`.
- Edges: `RELATES_TO`, `PART_OF`, `OCCURRED_AT`, `NEXT` (scene order), `PRESENT_IN {viewpoint}`, `MENTIONED_IN`,
  `CONCERNS`, `IN_SCENE`, `PARTICIPATED_IN`, `HAS_CLAIM`, `SAID`, `ADDRESSED_TO`, `ASSERTS`, `ACQUIRED`, `ABOUT`,
  `VIA` (event or utterance), `EXPERIENCED` (witnessed events). Read statements in the source for exact properties.
- `extract_story/snapshot.py` builds plain rows and applies identity redirects; the audit runner never invokes the writer.

## Current Source Map

| Path | Responsibility |
| --- | --- |
| `src/pov_retell/cli.py` | Commands (`extract`, `ingest`, `show`, `knowledge`, `neo4j-status`), settings, model clients, Neo4j lifetime. |
| `src/pov_retell/config.py` | Required settings from repository `.env` and environment. |
| `src/pov_retell/book/` | Phase A loading, structure mapping, cutting and file output. |
| `src/pov_retell/ingest/pipeline.py` | Run orchestration, run status (`start_run`/`finish_run`/`fail_run`), writer lifetime. |
| `src/pov_retell/ingest/source.py`, `model.py` | Validated Chapter inputs and result type. |
| `src/pov_retell/ingest/text.py`, `storage.py` | Shared text helpers (`name_key`, ...) and atomic JSON saving. |
| `src/pov_retell/ingest/timeline.py` | Character knowledge at a point in the story, from a run's JSON files. |
| `src/pov_retell/ingest/graph/base.py` | Shared `StrictModel`, `Text`. |
| `src/pov_retell/ingest/graph/summarize_chapter/` | `graph.py` (wiring), `nodes.py`, `context.py`, `state.py`, `model.py`, `logic.py`, `prompt/`. |
| `src/pov_retell/ingest/graph/extract_story/` | `graph.py` (wiring), `nodes.py`, `context.py`, `state.py`, `output.py` (`save_json`, `save_graph`), `snapshot.py`, `steps/` (`registry.py`, `checks.py`, one folder per step). |
| `src/pov_retell/infrastructure/llm.py` | Synchronous OpenRouter JSON and text adapters, transient retry. |
| `src/pov_retell/infrastructure/neo4j/` | `connection.py` (connectivity, health check), `cypher.py`, `writer.py` (`Neo4jGraphWriter`). |

Prompts live with their graph (`summarize_chapter/prompt/`, `extract_story/steps/<step>/prompt.py`); old `prompt/`, `extract_character/` and `neo4j_store.py` paths in handoffs and older tickets are historical.
Token caps are separate by graph (configured, not measured usage).

## Data Contracts

- `u01_p001` means a source paragraph/block, not a sentence. Scene IDs are `uNN_sM`.
- Python assigns stable IDs: `char_NNN`, `loc_NNN`, claim/event/utterance/acquisition IDs (acquisition IDs end `_kN`).
- Absent characters, null updates, and omitted known facts are preserved. Same names alone do not merge people.
- Personality must be explicitly written, not inferred from behavior. Records stay candidates unless verified.
- Evidence is paragraph IDs from the current chapter; utterance quotes are checked against their cited paragraphs.
- Claim truth is the book's truth; a character's belief is separate (stance on an acquisition).

## Configuration

Do not paste secrets or the whole `.env`. Required names include:

- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL` for structure mapping.
- `OPENROUTER_SUMMARIZE_CHAPTER_MODEL`, `OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS`,
  `OPENROUTER_SUMMARIZE_CHAPTER_REASONING` (`none` omits the parameter; otherwise sends `reasoning: {"effort": ...}`;
  set to `medium` locally on 2026-10-27, not verified against the live provider).
- `OPENROUTER_EXTRACT_CHARACTER_MODEL`, `OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS`,
  `OPENROUTER_EXTRACT_CHARACTER_PROVIDER` (comma-separated; empty = default routing),
  `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS`, `OPENROUTER_EXTRACT_CHARACTER_REASONING`
  (`none`, `enabled`, `low`, `medium`, `high`), `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS`.
  The names keep `EXTRACT_CHARACTER` although the graph is now `extract_story` (the audit manifest keys mirror them).
  This client now serves all JSON steps: characters, relationships, locations, scenes, events, knowledge, and
  the summary card updates. It sends a strict JSON schema, `provider` (with `require_parameters: true` when
  structured outputs are on), and `reasoning`.
- `OPENROUTER_MAX_TOKENS` for other calls; `BOOK_CLONE_DATA_DIR`, Neo4j credentials and host ports.
- `Settings` uses `extra="ignore"`; the removed ScaleDown setting (T-0011) is harmless if left in `.env`.

User decisions on models: JSON-producing jobs use `z-ai/glm-5.3-flash` pinned to provider `open-inference/fp4`
(`only`, no fallbacks; decided 2026-10-24/25; cheap models only, no Claude writer). Observed 2026-10-25: that
endpoint supports `response_format`, `structured_outputs` and `reasoning`. The user sets `.env`; at the
2026-10-25 inspection `OPENROUTER_EXTRACT_CHARACTER_MODEL` was still the Nemotron free model, which supports neither
`response_format` nor `structured_outputs`. The current `.env` was not inspected for this update. These are mutable
observations, not proof of historical run models or pricing.

## Data and Evidence Locations

```text
book/extracted/<book_id>/book.json, canonical.txt, units/*.txt
book/ingest/<book_id>/<run_id>/summaries/uNN.summary.json, book_memory.json
book/ingest/<book_id>/<run_id>/chapters/uNN.{proposed,characters}.json
book/ingest/<book_id>/<run_id>/chapters/uNN.{relationships,locations,scenes,events,knowledge}.json   # plus .proposed.json each
book/ingest/<book_id>/<run_id>/characters.json, identity_redirects.json
book/ingest/<book_id>/<run_id>/relationships.json, locations.json, scenes.json
book/ingest/<book_id>/<run_id>/claims.json, events.json, utterances.json, knowledge.json
book/diagnostics/<audit_id>/...          # Isolated audits and raw evidence, ignored by git
AI-work/handoffs/HANDOFF_YYYY-MM-DD.md   # Historical session snapshots
```

`proposed.json` is a successfully parsed/validated proposal before accumulation, not a raw HTTP response.
Existing app runs do not persist failed response bodies or token usage. Cumulative files apply identity redirects.

Earlier audit evidence (2026-10, Nemotron free, summary and extraction errors such as split identities, belief treated
as fact, reversed relationships, and length truncation around u11 of a 17-chapter test book) is recorded in the
handoffs, not repeated here; the code has changed substantially since, and those runs predate T-0003 to T-0017.

## AI Operating Workflows

- Since 2026-10-24 code changes go through [tickets](tickets/README.md); board and statuses live there. Claude is the
  product manager (writes/reviews tickets, no application code); other agents implement and mark `done`.
  Exception (user decision 2026-11-16): for the "finish the rest of the project" roadmap, Claude wrote T-0013 Rev. 2
  and T-0014 to T-0017 code directly. This exception is scoped to that roadmap.
- Ticket status at 2026-11-19: T-0001 to T-0008, T-0010 to T-0012, T-0018 are `verified`; T-0013 to T-0016 are merged;
  T-0017 is `done` (unreviewed, PR #9 open); T-0009 (LangSmith env export) is `draft` awaiting the user.
- The slide deck (T-0010, `doc/presentation/`) and its English rehearsal script were built and checked in
  October; details are in the ticket and handoffs. They describe an earlier design and numbers whose provenance was
  not established, so treat them as presentation material, not as a spec of the current pipeline.
- For a requested real API audit, load [run-ingest-api-audit](skills/run-ingest-api-audit/SKILL.md).
  The initiating model owns the run, analysis and suggested fixes; Terra observes and escalates. The runner calls
  the current production graphs (including the card client, T-0015), captures HTTP responses before client errors,
  writes only isolated diagnostics, never invokes the Neo4j writer, and without `--live` its status is `planned`.
  Its mock-transport test currently expects 19 HTTP calls (includes events and knowledge).
- API audit mode reports failures, evidence, uncertainty and suggested fixes; it does not change code, prompts,
  limits, models or data.
- After medium code changes, automatically delegate [context maintenance](agents/context-maintainer.md), then have
  the initiating agent review the diff.

## Commands and Verification

```bash
uv sync --extra dev
make neo4j-up
uv run pov neo4j-status
uv run pov ingest narnia-debug
uv run pov ingest narnia-debug --no-neo4j   # skip Neo4j
uv run pov knowledge narnia-debug char_001 --until u05_s2 [--json] [--reveal]

env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
env POV_NEO4J=1 .venv/bin/python -m pytest tests/test_neo4j_integration.py -q -m neo4j   # needs make neo4j-up
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
```

`make dev` starts Compose without waiting for health; `make neo4j-up` waits. For PyCharm, use `.venv/bin/pov`.
Real-provider tests require `POV_OPENROUTER=1`.

### Latest Offline Verification (2026-11-19, HEAD of T-0018, verified by the reviewer)

- Pytest command above -> `397 passed, 5 skipped` (T-0017 had 381; T-0018 added 16 structure tests).
- `ruff check` and `ruff format --check` clean (113 files); `mypy src/pov_retell` -> no issues in 82 files;
  `mypy src tests` -> the same 18 pre-existing errors in test files.
- T-0018 is a pure refactor: prompts and Cypher are byte-identical, and two golden fake-LLM runs (before/after) give
  identical files, rendered prompts, snapshots and steps (apart from the intended `extract_story` rename).
- Opt-in Neo4j: the implementer reported `3 passed`; the reviewer did not rerun it.
- No live OpenRouter call was made. The events and knowledge prompts are untested with a real model. A passing
  schema/test suite is not factual story validation.
- Older per-ticket verification blocks (T-0001 to T-0012, 2026-10-24 to 2026-10-28) live in the ticket Completion
  reports and handoffs.

## Unresolved Decisions

- Live-check the new events and knowledge steps (T-0016, T-0017) on a real book with the chosen model, after the
  user's OK; also the earlier unverified live items: extract client with `z-ai/glm-5.3-flash` on `open-inference/fp4`
  (strict JSON schema, reasoning `enabled` vs `medium`), card updates on that client, and whether summary reasoning
  `medium` is honored. Offline request checks cannot establish these.
- Review T-0017 and merge PR #9, then T-0018 (not pushed); before merging, follow the ticket README (fetch, pull
  `main`, rerun verification). Nothing is pushed or merged without the user.
- T-0018 follow-ups (not done): remove the unused `focus_is_ambiguous`; replace long positional argument lists with one
  input object per step; tighten the recursion-limit helper and its comment.
- T-0009 (LangSmith env export) remains `draft`.
- POV narrator / retelling is not started (user did not choose it on 2026-11-16).
- Open question (T-0017): the speaker of an utterance does not automatically believe its claims (a speaker may lie);
  the model may record `prior` or `inferred` when the text supports it.
- Decide whether Python should reject aliases that never appear in the chapter text (prompt-only per T-0003).
- Revisit whether call 1 should receive only the last K chapter summaries for longer books (currently all).
- Truncation diagnosis should use captured response/usage, not a guessed cap.
- Identity resolution, evidence attribution, relationship direction and memory retention remain quality risks;
  similarity retrieval was discussed, not implemented.
- Do not implement pending ideas during an audit or context-maintenance pass.

## Further Reading

- [AI workspace navigation](README.md), [workspace instructions](AGENTS.md), [tickets](tickets/README.md).
- Completion reports: [T-0018](tickets/T-0018-langgraph-refactor.md) (module layout and design), [T-0015](tickets/T-0015-neo4j-graph-per-chapter.md), [T-0016](tickets/T-0016-events-claims.md),
  [T-0017](tickets/T-0017-knowledge-timeline.md).
- [Detailed October 23 handoff](handoffs/HANDOFF_2026-10-23.md), [October 22 experiments](handoffs/HANDOFF_2026-10-22.md),
  [earlier October 17 baseline](handoffs/HANDOFF_2026-10-17.md).
- [Ingest documentation](../doc_ai/INGEST_BASE.md), [restoration plan](../doc_ai/superpowers/plans/2026-10-22-restore-llm-character-extraction.md).
