# Current Project Context

Updated: 2026-10-27. This is the concise onboarding reference, not a session transcript.
Read [root AGENTS.md](../AGENTS.md) before acting. Verify mutable settings and source when needed.

## Goal and Boundaries

`pov-retell` is a Python CLI for book extraction and cumulative character ingestion, intended
to support later character knowledge analysis and POV retelling. Current work concerns
summaries, identity/profile accuracy, and real API diagnostics. It is not a FastAPI/web app.

User responses are Vietnamese; code, comments, prompts, and AI instructions are English.
Keep graph builders, models, logic, and prompts together by graph. Preserve the dirty working
tree and previous book runs. The inspected branch is `clean/ingest-base`; HEAD alone is stale.

## Current Workflow

```text
pov extract <source> --id <book_id>
  -> load HTML/EPUB/TXT -> LLM structure map -> validated units/paragraphs -> files

pov ingest <book_id>
  -> validate saved chapter files -> fresh run directory
  -> summarize_chapter graph -> extract_character graph -> final Neo4j Character write
pov ingest <book_id> --no-neo4j
  -> same, but no Neo4j connect/health check/write (pipeline step `skip_neo4j`, writer is None)
```

- Source validation compares chapter order, file set, paragraph IDs/order, and text with `book.json`.
- Summary graph: `initialize -> summarize_chapter -> validate_summary -> save_summary -> summarize_book`,
  looping across chapters before running `summarize_book` once after the last chapter.
- Character/extraction graph:
  `initialize -> extract_characters -> validate_characters -> extract_relationships -> validate_relationships -> extract_locations -> validate_locations -> extract_scenes -> validate_scenes -> save_json`,
  looping across chapters. Recursion limits use per-graph helpers `summarize_chapter_recursion_limit`
  (`SUMMARY_NODES_PER_CHAPTER = 3`) and `extract_character_recursion_limit`
  (`EXTRACT_NODES_PER_CHAPTER = 9`) shared by `pipeline.py` and the audit runner.
- `--neo4j` is the default. `--no-neo4j` (user decision: Neo4j is not needed while testing LLM
  output) still saves summaries, proposals, snapshots and `characters.json`. Added 2026-10-24,
  uncommitted; not exercised with a live run or a Neo4j write.
- Summaries run first. Both Call 1 (`summarize_chapter`) and `extract_character` use one shared
  Python helper (`format_previous_context`) to assemble prior context for chapter N: the `WHO IS WHO`
  and `WHERE IS WHERE` after chapter N-1 plus chapter summaries 1..N-1 in chapter order (each labeled
  with its chapter ID); u01 receives empty context.
- Extraction prompt is changes-only (section "CHANGES ONLY"): the model returns new characters
  and existing ones that appear or gain information, with only new info (null/[] = unchanged,
  each existing ID at most once, `{"characters": []}` if nothing is new). In `T-0003`,
  relationships were completely removed from the character prompt, response schema, `CharacterRecord`,
  merge/validation logic, and run output (`pending_relationships.json` is no longer written, and
  unused `extract_character/attributes.py` was deleted). In `T-0004`, relationships were added as
  a separate per-chapter structured JSON call (`extract_relationships` / `validate_relationships` in
  `extract_character/relationship.py` using `extract_character/prompt/extract_relationship.py`)
  running after `validate_characters` for the same chapter. It receives book title, chapter ID,
  `format_previous_context`, a compact character roster (`character_id`, `candidate_name`, `aliases`),
  the chapter's `active_character_ids`, open relationships involving active characters, and the
  chapter text with paragraph IDs, and returns `{"relationships": [{"op": "start" | "end", "source_id",
  "target_id", "kind", "paragraph_ids": [...]}]}`. Python validates existing distinct character IDs
  (after redirects), non-empty current-chapter paragraph IDs, normalized 1–5 word lowercase `kind`,
  and matching open records for `end` (while repeated `start` for an already-open record is a no-op
  keeping earliest evidence), rewrites relationships when character IDs merge (merging identical
  open records and keeping earliest `valid_from`), and saves `relationships.json`,
  `chapters/uNN.relationships.proposed.json`, and `chapters/uNN.relationships.json`.
  In `T-0007`, structured location extraction was added (`extract_locations` / `validate_locations`
  in `extract_character/location.py` using `extract_character/prompt/extract_location.py`),
  validating `new_N` format, existing IDs and duplicates, `part_of` references, no self-reference or
  containment cycles, and `kind` <= 12 words. A permanent `part_of="loc_NNN"` must refer to the
  immutable input roster, so an ID allocated earlier in the same response cannot accidentally make
  an unseen permanent reference valid; forward `part_of="new_N"` references within the response
  remain valid. The step assigns `loc_NNN` in order, unions aliases (keeping the old name in `aliases`
  on rename), and saves `locations.json`,
  `chapters/uNN.locations.proposed.json`, and `chapters/uNN.locations.json`.
  In `T-0008`, per-chapter scene-map extraction was added (`extract_scenes` / `validate_scenes` in
  `extract_character/scene_map.py` using `extract_character/prompt/extract_scene_map.py`), running
  after `validate_locations` and validating complete ordered paragraph coverage with no gaps or
  overlaps, `start <= end` in the current chapter, existing character/location IDs,
  `viewpoint_ids <= present_ids`, `present_ids & mentioned_ids == empty`, valid `time.relation`
  (`continues|later|parallel|flashback|time_jump`), `time.anchor` required for `parallel`/`flashback`
  (existing paragraph before `start` in this or an earlier chapter) and `null` otherwise, `time.note`
  <= 8 words, and `label` <= 15 words; assigning `segment_id` (`uNN_sM`) and saving
  `chapters/uNN.scenes.proposed.json` and `chapters/uNN.scenes.json`.
  `T-0003` also tightened book-agnostic `PROMPT_EXTRACT_CHAR`
  rules: `physical_description` is lasting appearance only (excluding actions, events, injuries/healing,
  death, titles, roles, status), `age_description` is age/life stage/birth order only, `species` is
  set only when the text states what kind of being the character is or calls them by their kind,
  `aliases` cover other names/titles/fixed labels and story-gained titles (excluding one-off
  descriptions, comparisons, generic address like `"dear"`/`"my friend"`, and pronouns; `candidate_name`
  changes only when a chapter gives a proper name for a character known so far by a description or
  clearly replaces the name, while titles/epithets gained in the story go into `aliases`), and no
  record is created for any group (even a specific one like `"the three guards"`) unless an
  individual is singled out. Not yet verified live after `T-0003`.
- Per-chapter summary calls (`T-0001` verified 2026-10-24; Call 2 card rules updated in `T-0002`;
  Call 3 `WHERE IS WHERE` added in `T-0006`):
  1. Call 1 (`summarize_chapter/prompt/summarize_chapter.py`): writes plain-text `chapter_summary`
     for the current chapter in its own words (no copied sentences or dialogue), given book title,
     chapter ID, `format_previous_context`, and current chapter text.
  2. Call 2 (`summarize_chapter/prompt/update_who_is_who.py`): updates the complete `WHO IS WHO`
     list (`name | comma-separated other names or titles used in the text, or - | identity card`,
     at most 40 words per card describing who the character is as of the end of the current chapter
     plus story status and cause, no chapter/presence references or event lists, no groups unless an
     individual is singled out, no unattributed guessed outcomes or intensified wording, keep earlier
     characters, only names in the inputs, no outside knowledge, explicit family relations only)
     from the previous `WHO IS WHO` (empty for u01) and current chapter text plus
     `UPDATE_WHO_IS_WHO_REMINDER`. It receives no chapter summaries or call-1 output.
  3. Call 3 (`summarize_chapter/prompt/update_where_is_where.py`): updates the complete
     `WHERE IS WHERE` list (`name | comma-separated other names used in the text, or - | place card`,
     at most 30 words per card describing what kind of place it is, where it lies or what larger
     place it is part of by name, who owns/rules/lives there, and its lasting state, with no chapter
     references or event lists, named places and unnamed action settings under clearest description,
     no objects/people, keep earlier places, merge only when explicit, no outside knowledge) from the
     previous `WHERE IS WHERE` (empty for u01) and current chapter text plus
     `UPDATE_WHERE_IS_WHERE_REMINDER`. It receives no chapter summaries, `WHO IS WHO`, or call-1 output.
     Both Call 2 and Call 3 share `validate_running_list` (nonblank output, 3 non-empty `|`-separated
     fields per line ignoring optional header line, case-insensitive whole-name survival of every
     previous first-field name in field 1 or comma-separated field 2 on some new line), retrying up
     to 2 extra times with `Rejected: <reason>` appended before raising `LLMError`.
     The Call 3 and structured-location prompts use generic place/object examples; regression tests
     reject the cited test-book names and place/object terms, including `wardrobe`, `lamp`,
     `spare room`, `hilltop`, `Stone Table`, `pavilion`, `Professor`, `Cair`, and `Paravel`.
- Final summary node `summarize_book` (`summarize_chapter/prompt/summarize_book.py`): runs once
  after the last chapter on book title and all chapter summaries in order to produce plain-text
  `core_memory` (~400-700 words, main characters, central conflict, turning points/revelations,
  ending, own words, beliefs kept attributed/uncertain). Saves `summaries/book_memory.json` as
  `{"who_is_who", "where_is_where", "core_memory"}`. Per-chapter `summaries/uNN.summary.json` stores
  `{"chapter_id", "chapter_summary", "who_is_who", "where_is_where"}`.
- Summary calls: 3 per chapter (including u01) plus 1 final call = `3N+1` before repairs (52 for 17 chapters).
  Extraction calls: 4 per chapter (`extract_characters` + `extract_relationships` + `extract_locations` + `extract_scenes`) = `4N` before repairs.
- Summaries are fallible context; original chapter text remains evidence.
- There is no checkpoint, resume, automatic summary reuse, or parallel chapter extraction.
- Each CLI run starts from chapter 1. `recursion_limit` caps graph steps, not model reasoning.

## Current Source Map

| Path | Responsibility |
| --- | --- |
| `src/pov_retell/cli.py` | Commands, settings, model clients, Neo4j lifetime. |
| `src/pov_retell/config.py` | Required settings from repository `.env` and environment. |
| `src/pov_retell/book/` | Phase A loading, structure mapping, cutting and file output. |
| `src/pov_retell/ingest/pipeline.py` | Summary + extraction orchestration, final writer. |
| `src/pov_retell/ingest/source.py`, `model.py` | Validated Chapter inputs and result type. |
| `src/pov_retell/ingest/graph/summarize_chapter/` | Summary graph, models, logic and `prompt/`. |
| `src/pov_retell/ingest/graph/extract_character/` | Character graph, models, logic, identity helpers and `prompt/`. |
| `src/pov_retell/infrastructure/llm.py` | Synchronous OpenRouter JSON and text adapters. |
| `src/pov_retell/infrastructure/neo4j_store.py` | Connectivity and selected Character properties. |

Prompts now live inside each graph's `prompt/` folder. The old top-level `prompt/` paths
in dated handoff prose are historical. Token caps are separate by graph (configured, not measured usage).

## Data Contracts

- `u01_p001` means a source paragraph/block, not a sentence. Blocks can contain several sentences.
- Extraction output is a delta merged by Python. Character fields: app ID, candidate name, aliases, gender/species/age/appearance, explicit
  personality traits, and candidate/verified status. Ordinary-path character records have no
  `relationships` field (`extra="forbid"` rejects responses containing `relationships` and triggers
  repair retry).
- New proposal IDs are local `new_N`; Python assigns stable `char_NNN` within that run.
- Explicit merges keep the earliest surviving ID, aliases, complementary descriptions,
  traits, and flattened redirects. Same names alone do not merge people.
- Absent characters, null updates, and omitted known facts are preserved.
- Known names need not appear verbatim in the current chapter; valid renames are allowed.
- Personality must be explicitly written, not inferred from behavior. Python checks new trait
  wording against source, but this does not establish ownership or distinguish feelings reliably.
- Records remain candidates unless a real verification process establishes otherwise.
- Current Neo4j key: `(book_id, run_id, character_id)`. Selected scalar properties and aliases
  are written only after all chapters finish. No mentions, relationship maps, or `RELATES_TO` edges.

## Prompt Evidence (2026-10-24, Nemotron free, ignored dirs under `book/diagnostics/`)

- Old full-roster extraction replay of u13 (~42.7k prompt tokens) ended with finish_reason
  "error" (choice error 504 upstream idle timeout) after ~302 s, 6,394 reasoning tokens, empty
  content. Previously `_ask` only checked finish_reason "length", so the user saw "no valid
  answer after 3 attempts ... Invalid JSON". In `T-0005`, `_ask` now raises
  `LLMError("OpenRouter generation failed: ...")` immediately when `finish_reason == "error"`
  or `choice.error` is present.
- An earlier summary prompt variant produced cumulative summaries up to 77% of source length with
  52% verbatim 8-gram copying and a truncated u17. The former two-section `update_book_summary.py`
  prompt (deleted in `T-0001`) was tested live on u01-u14 only: no collapse, verbatim 8-gram
  copying at most 1.2%, cards mostly up to ~60 words (max 93), story section once shrank
  (u05 654 -> 409 words), latency up to ~241 s per call. u15-u17 untested.
  Spot checks at u10 matched the story for White Witch/Jadis/Queen of Narnia, Father Christmas
  vs Aslan, and Edmund's uncertain guess. Length is not enforced by code.

## Configuration

Do not paste secrets or the whole `.env`. Required names include:

- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL` for structure mapping.
- `OPENROUTER_SUMMARIZE_CHAPTER_MODEL`, `OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS`.
- `OPENROUTER_SUMMARIZE_CHAPTER_REASONING` is read by `Settings` and passed to the summary
  client in both the CLI and audit runner. On 2026-10-27 the user set it to `medium` in the
  local `.env`; text requests send `reasoning: {"effort": "medium"}`. The `none` setting
  omits the reasoning parameter and uses the provider default. This change has not been
  verified against the live provider.
- `OPENROUTER_EXTRACT_CHARACTER_MODEL`, `OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS`.
- `OPENROUTER_EXTRACT_CHARACTER_PROVIDER` (comma-separated provider tags; empty = default routing),
  `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS` (`bool`),
  `OPENROUTER_EXTRACT_CHARACTER_REASONING` (`none`, `enabled`, `low`, `medium`, `high`),
  `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS` (`bool`).
- `OPENROUTER_MAX_TOKENS` for other calls.
- `BOOK_CLONE_DATA_DIR`, Neo4j credentials and host ports.

The unused ScaleDown entity/attribute experiment and its required model setting were removed in
`T-0011` on 2026-10-26. `Settings` uses `extra="ignore"`, so a leftover
`OPENROUTER_CHARACTER_ATTRIBUTES_MODEL` line in a user's `.env` is harmless and is not included in
the settings model. The user's `.env` was not changed.

At inspection on 2026-10-24, all three active model settings selected
`nvidia/nemotron-3-ultra-550b-a55b:free`; all three output-token caps were 65,536.
These are mutable configuration observations, not proof of historical run models or pricing.

User decision (2026-10-24): JSON-producing jobs (character extraction and later structured
extraction) will use `z-ai/glm-5.3-flash`; the user sets it in `.env`. OpenRouter metadata
on that date: reasoning supported, `response_format` and `structured_outputs` (JSON schema)
supported at model level, but some providers (for example Z.AI, Novita, AtlasCloud,
SiliconFlow) lack `structured_outputs`. `nvidia/nemotron-3-ultra-550b-a55b:free` supports
neither `response_format` nor `structured_outputs`.
User decision (2026-10-25): pin the provider `open-inference/fp4` (`only`, no fallbacks) for
these jobs. Its endpoint metadata that day: fp4 quantization, `response_format`,
`structured_outputs` and `reasoning` supported, 1,048,576 context, 943,718 max output,
$0.030 / $0.069 per 1M input / output tokens.
Implemented in `T-0005`: the extract client (`cli.py` and `run_api_audit.py`) reads the four
`OPENROUTER_EXTRACT_CHARACTER_*` routing/reasoning/schema settings, sends strict JSON schema
(`strict_json_schema(schema)` from `mode="serialization"`, with `additionalProperties: false`
and all properties required on every object, excluding `exclude=True` fields such as
`identity_context`), `provider` (`only`, `allow_fallbacks`, and `require_parameters: true`
when structured outputs are enabled), and `reasoning` (`{"enabled": true}` or
`{"effort": "<level>"}`); summary reasoning was wired separately on 2026-10-27. Not yet verified
live with `open-inference/fp4`.

## Data and Evidence Locations

```text
book/extracted/<book_id>/book.json, canonical.txt, units/*.txt
book/ingest/<book_id>/<run_id>/summaries/uNN.summary.json, book_memory.json
book/ingest/<book_id>/<run_id>/chapters/uNN.proposed.json, uNN.characters.json
book/ingest/<book_id>/<run_id>/characters.json, identity_redirects.json
book/diagnostics/<audit_id>/...          # Isolated audits and raw evidence, ignored by git
AI-work/handoffs/HANDOFF_YYYY-MM-DD.md   # Historical session snapshots
```

`proposed.json` is a successfully parsed/validated proposal before accumulation, not a raw
HTTP response. Existing app runs do not persist failed response bodies or token usage.

The latest run previously audited in the session was `run_afddb5b1b4794098ba5c5dc79c01e00e`:
17 summaries, character snapshots through u10, 20 cumulative characters, 4 pending targets,
no explicit merges. The user reported length truncation before the next snapshot. The failing
u11 stage is inferred from the artifact boundary; reasoning's contribution was not measured.

Audited errors included separate White Witch/Queen identities, Aslan receiving Father
Christmas's appearance, mixed reindeer identities, reversed relationships, belief treated as
fact, and missing referenced characters. Some summaries were correct where extraction was wrong.
Earlier ScaleDown summaries/extractions also had attribution and meaning errors; full-book
single-character input did not eliminate them. Read handoffs for exact source/artifact pointers.

## AI Operating Workflows

- Since 2026-10-24, code changes go through [tickets](tickets/README.md). Claude is the product
  manager (writes and reviews tickets, no application code); other agents implement and mark
  tickets `done`. Ticket T-0001 (summary memory redesign) is `verified`; its first live run
  `run_2ae27f27f5d34937a54c8c81ed93303e` completed 17 chapters. Ticket T-0002 (WHO IS WHO card
  rules) is `verified` offline. Reviewed 2026-10-25 on the combined tree (offline only):
  T-0003 (character extraction cleanup), T-0004 (relationship call with history), T-0005 (JSON
  schema, pinned provider, reasoning for the extract client) and T-0008 (scene map) are
  `verified`. Repairs for T-0006 (WHERE IS WHERE) and T-0007 (locations with IDs) are complete in
  the current code: their test-book-derived prompt examples were replaced with generic alternatives,
  and T-0007 permanent `part_of` resolution was corrected as described above. Claude re-reviewed both
  on 2026-10-25 (offline): `verified`. T-0010 (slide deck): Revisions 2–3 (game style, AI-drawn
  characters, GSAP) were reviewed 2026-10-26; Revision 4 (Philosopher's Stone "through the trapdoor",
  Quirrell, no on-screen instructions, strict ShiftKey structure) had an iteration 2 that fixes F1–F5 and
  makes Quirrell selectable. Revision 5 (2026-10-26, user decision) aligns the sprint slides to the real
  sprints (Slide 2: Sprint 1 World Map, Slide 3: Sprint 2 Trapdoor with tools caption, Slide 4: Sprint 3
  Inventory with two-step strip, Quirrell "Carries a secret", Voldemort twist in Table B text); implemented
  and verified: `done`, awaiting Claude review.
  T-0011 (remove the unused ScaleDown experiment) is `verified` (2026-10-26). T-0009 (LangSmith env export) is a
  `draft` awaiting the user's choice. Order and board:
  [tickets/README.md](tickets/README.md).
- The working-tree presentation file inspected on 2026-10-26 currently has eight `data-screen`
  sections, with a character selector on slide 2. This differs from the five-slide T-0010
  Revision 5 ticket snapshot above; the file is modified in the working tree. A direct user
  request changed slide 2 to keep four character positions stable and show a translucent
  attribute card only while a character is hovered or keyboard-focused. The card sits beside
  that character, follows pointer height within the slide bounds, and hides on leave; click or
  Enter/Space locks the POV.
  Headless Chrome screenshots were inspected at 1920×1080, 1280×720, 1024×768, 900×700,
  and 800×600;
  JavaScript syntax and keyboard selection were checked. This is a slide-2 UI check, not a
  review of the whole deck.
- A later direct UI pass on 2026-10-26 inspected current slides 2–8 at 1280×720 and
  1920×1080. The Sprint 1 SVG now sizes within its card; node hover changes its glow and
  circle stroke without replacing the SVG node's `translate(...)` position. Short-viewport
  spacing keeps the content of slides 4–7 (including the Chapter 17 timeline state) and the
  slide-8 replay bar above navigation; the
  pipeline displays five steps in one row. Headless checks exercised the then-existing graph
  label toggle and replay, pipeline simulation, timeline toggle, notes, and replaying a selected POV.
- A subsequent presentation polish pass on 2026-10-26 changed the eight-slide deck's visible
  copy and speaker notes to plainer English and softened its palette, type, panels, and glow.
  The slide sequence, story facts, metrics, and interactive JavaScript were retained. All eight
  slides rendered without visible clipping in headless Chrome at 1280×720 and 1920×1080;
  the inline script passed `node --check`, and `git diff --check` was clean. The requested
  `gpt-5.6-sol` context-maintenance model was unavailable, so this bounded update was made
  directly rather than attributed to a sub-agent.
- On 2026-10-27, a direct presentation request removed the persistent POV lens badge, the
  Sprint 1 source-path label, story-label toggle, and model-rule banner. The user's follow-up
  removed the replay button: Sprint 1 now enters with the first of four graph groups visible;
  Next, Space, ArrowRight, and PageDown reveal the next group before advancing slides. Prev,
  ArrowLeft, and PageUp reverse the groups, and returning from slide 4 shows the complete graph.
  Sprint 2 and Sprint 3 copy/notes use plain English and a concrete before/after Harry example.
  The pipeline trace is explicitly an illustrative example; the knowledge timeline is labeled
  as a design. The existing numeric metrics were retained without a new factual audit.
  Headless Chrome checks verified all four graph states, forward/back navigation, the pipeline
  demo, and absence of runtime errors. Slides 3–7 were rendered at 1280×720 and 1920×1080;
  the revised Sprint 2/3 slides were visually inspected at 1280×720. This context update was
  performed directly because the requested `gpt-5.6-sol` model was unavailable.
- For a requested real API audit, load [run-ingest-api-audit](skills/run-ingest-api-audit/SKILL.md).
  The initiating model owns the run, analysis, and suggested fixes. Terra observes and escalates.
- The skill-local runner calls current production graphs, captures HTTP responses before client
  errors, and writes only isolated diagnostics. It never invokes the Neo4j writer.
- Skill creation is not permission to execute live calls. Without `--live` its status is `planned`.
- On Codex, prefer Terra via `gpt-5.6-sol` with fresh context. Claude Sonnet 5.5 is conditional
  on that runtime exposing it. Disclose unavailable models rather than silently substituting.
- API audit mode reports what failed, where, evidence, uncertainty, and how it could be fixed;
  it does not change application code, prompts, limits, models, or database data.

- After medium code changes, automatically delegate [context maintenance](agents/context-maintainer.md).
  Update this file from the actual diff/checks, then have the initiating agent review it.

### Latest Offline Verification (2026-10-26)

For the current tree after the T-0011 removal, the implementing parent reported:

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  -> `309 passed, 4 skipped`, with one pre-existing LangSmith `DeprecationWarning`.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit` -> passed.
- `.venv/bin/ruff format --check src tests AI-work/skills/run-ingest-api-audit` -> `71 files already formatted`.
- `.venv/bin/mypy src/pov_retell` -> no issues in 44 source files.
- `git diff --check` -> clean.

The pre-removal baseline was `317 passed, 5 skipped`. T-0011 removed eight offline ScaleDown
tests and two obsolete model-name blank cases, added two configuration cases covering env files
with and without the old key, and removed one skipped ScaleDown integration test. No live API or
Neo4j run, `.env` edit, or commit was performed.

## Commands and Verification

```bash
uv sync --extra dev
make neo4j-up
uv run pov neo4j-status
uv run pov ingest narnia-debug
uv run pov ingest narnia-debug --no-neo4j   # skip Neo4j

env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
```

`make dev` starts Compose without waiting for health; `make neo4j-up` waits.
For PyCharm, use `.venv/bin/pov`, parameters `ingest narnia-debug --no-neo4j` (or without the flag to write Neo4j), working directory the repo.
Real tests require `POV_OPENROUTER=1`; skill validation uses offline mock HTTP and dry runs.

Verified after `T-0004` relationship extraction step on 2026-10-25 (implemented by Antigravity /
Gemini 4 Argon; context maintenance performed directly by the implementer because neither
`gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in this runtime):
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  222 passed, 5 skipped.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: passed.
- `.venv/bin/ruff format --check src tests`: 60 files already formatted.
- `.venv/bin/mypy src/pov_retell`: no issues found in 40 source files.
- `git diff --check`: clean.
- No live API call or Neo4j write was made during `T-0004`.

Verified earlier after `T-0005` extract JSON client update on 2026-10-25 (implemented by Antigravity /
Gemini 4 Argon; context maintenance performed directly by the implementer because neither
`gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in this runtime):
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  198 passed, 5 skipped.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: passed.
- `.venv/bin/ruff format --check src tests`: 57 files already formatted.
- `.venv/bin/mypy src/pov_retell`: no issues found in 38 source files.
- `git diff --check`: clean.
- No live API call or Neo4j write was made during `T-0005`.

Verified earlier after `T-0003` character-extraction cleanup on 2026-10-24 (implemented by Antigravity /
Gemini 4 Argon; context maintenance performed directly by the implementer because neither
`gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in this runtime):
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  178 passed, 5 skipped.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: passed.
- `.venv/bin/ruff format --check src tests`: 57 files already formatted.
- `.venv/bin/mypy src/pov_retell`: no issues found in 38 source files.
- `git diff --check`: clean.
- `grep -rn -E "pending_relationships|PendingCharacterRelationship|update_profiles" src tests AI-work/skills`:
  no matches.
- `grep -n -i "relationship" src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py`:
  no matches.
- No live API call or Neo4j write was made during `T-0003`.

Verified earlier after `T-0002` WHO IS WHO card-rule changes on 2026-10-24 (implemented by Antigravity /
Gemini 4 Argon; context maintenance performed directly by the implementer because neither
`gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in this runtime):
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  165 passed, 5 skipped.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: passed.
- `.venv/bin/ruff format --check src tests`: 58 files already formatted.
- `.venv/bin/mypy src/pov_retell`: no issues found in 39 source files.
- `git diff --check`: clean.
- No live API call or Neo4j write was made during `T-0002`.

Verified earlier after `T-0001` summary-memory redesign on 2026-10-24:
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  152 passed, 5 skipped.
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: passed.
- `.venv/bin/ruff format --check src tests`: 58 files already formatted.
- `.venv/bin/mypy src/pov_retell`: no issues found in 39 source files.
- `git diff --check`: clean.
- `grep -rn -E "book_summary_so_far|STORY SO FAR|update_book_summary|UPDATE_BOOK_SUMMARY" src tests AI-work/skills`:
  no matches.
- No live API call or Neo4j write was made during `T-0001`.

Verified earlier after the 2026-10-24 `--no-neo4j` / delta-extraction / summary-prompt changes
(initiator-run): the pytest command above on `tests AI-work/skills/run-ingest-api-audit/tests`
gave 142 passed, 5 skipped; `ruff check src tests AI-work/skills/run-ingest-api-audit` passed;
`mypy src/pov_retell` found no issues in 38 files; `git diff --check` was clean. No live API
call or Neo4j write was made for `--no-neo4j`.

Earlier, for the AI-work/audit-skill task on 2026-10-24:

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  completed with 140 passed and 5 skipped.
- `.venv/bin/ruff check AI-work/skills/run-ingest-api-audit` passed.
- `.venv/bin/mypy AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py` passed for one source file.
- The skill quick validator passed, and all checked links across the moved handoffs and AI-work
  Markdown had no missing targets (57+ links checked).

These checks used dry CLI and mock HTTP paths only. No live API call or Neo4j write was made.
A passing schema/test suite is not factual story validation.

## Unresolved Decisions

- Diagnose truncation from captured response/usage rather than guessing from a cap.
- Live-check `T-0002` to `T-0008` (`z-ai/glm-5.3-flash` on `open-inference/fp4` with strict JSON schema and `reasoning="enabled"` vs `"medium"`) with a smoke run, then a book run, after the user's OK. The four extract-client keys were added to `.env` on 2026-10-25 (`open-inference/fp4`, no fallbacks, reasoning `enabled`, structured outputs on), but `OPENROUTER_EXTRACT_CHARACTER_MODEL` is still `nvidia/nemotron-3-ultra-550b-a55b:free`; switching it to `z-ai/glm-5.3-flash` is the user's call.
- Decide whether Python should reject aliases that never appear in the chapter text (currently prompt-only per `T-0003`).
- Revisit whether call 1 should receive only the last K chapter summaries for longer books (currently receives all).
- Improve identity resolution, evidence attribution, relationship direction, and memory retention.
- Incremental Neo4j writes and similarity retrieval were discussed, not implemented or selected.
- Live-check whether summary reasoning `medium` is honored by the configured provider and
  whether it avoids the u14 WHO IS WHO repetition; offline request checks cannot establish this.
- Relationship verification, events, knowledge over time, and retelling remain future stages.
- Do not implement these pending ideas during an audit or context-maintenance pass.

## Further Reading

- [AI workspace navigation](README.md), [workspace instructions](AGENTS.md).
- [Detailed October 23 handoff](handoffs/HANDOFF_2026-10-23.md).
- [October 22 experiments](handoffs/HANDOFF_2026-10-22.md).
- [Earlier October 17 baseline](handoffs/HANDOFF_2026-10-17.md).
- [Ingest documentation](../doc_ai/INGEST_BASE.md), [restoration plan](../doc_ai/superpowers/plans/2026-10-22-restore-llm-character-extraction.md).
