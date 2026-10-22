# Character Discovery Implementation Plan

**Goal:** Run the approved character-discovery nodes over chapter files and persist their results.

**Architecture:** Chapter processing and validation live in `ingest/extrac_character.py`.
`ingest/graph/character_discovery.py` wires a sequential LangGraph loop without a checkpointer.
`ingest/pipeline.py` contains the ingest entry point.
The existing JSON LLM interface and a Neo4j Character writer form the external boundaries.

**Spec:** `docs/NEXT_STEPS.md` and the approved node/edge design in this conversation.

## Constraints and decisions

- Keep all code and prompts in English.
- Read chapter text from `units/`, validating it against the extraction's paragraph IDs.
- Preserve the prompt's response schema and cumulative character list.
- Assign stable local character IDs by preserved mention evidence, not by name matching.
- Keep new and merged records as `candidate`; never claim automatic verification.
- Store `personality` as joined trait descriptions; do not invent a separate summary.
- Save per-chapter JSON and the latest list under a unique ingest run directory.
- Do not add checkpoints, resume, parallel chapter execution, or automatic real API calls in tests.

## Tasks

- [ ] Add failing tests for sequential accumulation, invalid/lost mentions, merges, and input files.
- [ ] Add typed character models and chapter-processing functions.
- [ ] Wire load → extract → validate → save JSON → next chapter / Neo4j.
- [ ] Add the Character projection/writer and keep the CLI driver open through ingestion.
- [ ] Package the root `prompt` module so imports work outside the repository directory.
- [ ] Run offline tests, lint, type checks, and an installed-import check.
- [ ] Update operational documentation with the implemented behavior and remaining limits.

## Review focus

- A failed chapter must not overwrite the last valid cumulative result or publish to Neo4j.
- Earlier evidence must not disappear or be reassigned to an unrelated character.
- Merges must retain the earliest character ID without reusing retired IDs.
- Long chapter lists must not hit LangGraph's default recursion limit.
- The CLI must report failures without closing its Neo4j driver before the write.
