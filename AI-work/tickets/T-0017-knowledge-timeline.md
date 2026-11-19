---
id: T-0017
title: Knowledge timeline — who learns which claim, how and when
status: done
owner: Claude (at the user's request)
branch: ticket/T-0017-knowledge-timeline
priority: high
created: 2026-11-16
updated: 2026-11-16
depends_on: [T-0016]
---

# T-0017: Knowledge timeline — who learns which claim, how and when

## Background

The POV narrator must receive only what the chosen character knows at the chosen point in
the story (README "Why", slide deck Sprint 3: Harry suspects Snape until Chapter 17). T-0016
extracts claims, events and utterances. This ticket records how each character acquires a
claim and what they believe about it, and adds a view of a character's knowledge at a point.

## User decisions

- 2026-11-16: tickets for (c) knowledge timeline, implemented by Claude.
- 2026-11-16 (confirming 2026-10-15): keep the full knowledge model with seven channels:
  `prior`, `witnessed`, `told`, `read`, `overheard`, `inferred`, `learns_truth`.
- 2026-11-16: Neo4j is written after each chapter (T-0015).

## PM recommendations

- One new structured call per chapter (`extract_knowledge`) after `validate_events`, given the
  chapter's validated scene map, events, utterances and all claims, plus the current beliefs
  of characters present in the chapter.
- Each acquisition has a `stance`: `believes`, `doubts` or `disbelieves`.
- Python ties channels to evidence so the model cannot invent access:
  - `witnessed`: an event of the same segment that shows the claim; the character is present.
  - `told`: a spoken utterance of the same segment that states the claim; the character is
    an addressee.
  - `overheard`: a spoken utterance of the same segment; the character is present but neither
    speaker nor addressee.
  - `read`: a written utterance of the same segment; the character is present.
  - `inferred`: no source; the character is present.
  - `prior`: no source; presence not required (the text reveals earlier knowledge).
  - `learns_truth`: the claim's truth is resolved (`true`/`false`) by the end of this
    chapter; stance must match (`believes` for true, `disbelieves` for false); optional source
    of the same segment that refers to the claim; the character is present.
- The knowledge call may add new claims, but only for `inferred` or `prior` acquisitions
  (thoughts and conclusions that no event or utterance states).
- The timeline view treats `prior` knowledge as known from the start of the story, and never
  shows a claim's real truth unless the character has learned it (`--reveal` for debugging).

## Requirements

1. `ExtractKnowledgeResponse` with `claims` (new, `new_N`) and `acquisitions`.
2. Validation as in the PM recommendations, plus: known characters (after redirects),
   segment of this chapter, non-empty paragraph IDs inside the segment, no duplicate
   (character, claim, channel, source) in one answer, new claims linked from at least one
   acquisition and not duplicating existing statements.
3. IDs: `uNN_kM` for acquisitions; new claims continue `claim_NNN`.
4. Files: `chapters/uNN.knowledge.proposed.json`, `chapters/uNN.knowledge.json`, cumulative
   `knowledge.json` (merged IDs resolved). `claims.json` includes knowledge-step claims.
5. Neo4j: `(:Character)-[:ACQUIRED]->(:KnowledgeAcquisition {channel, stance, ...})`,
   `-[:ABOUT]->(:Claim)`, `-[:VIA]->(:Event|:Utterance)`, `-[:IN_SCENE]->(:Scene)`, and
   `(:Character)-[:EXPERIENCED]->(:Event)` for `witnessed` acquisitions.
6. `pov knowledge <book_id> <character> [--run RUN] [--until uNN|uNN_sM] [--json] [--reveal]`
   prints what the character knows at that point: each claim with the latest stance, how
   and where it was learned, and whether the character knows it to be true or false.

## Acceptance criteria

- [x] Offline: one `extract_knowledge` call per chapter after `validate_events`; IDs, files and
      snapshot rows as above.
- [x] Offline: each channel rule rejects a bad answer with a reason.
- [x] Offline: the timeline for a character before and after a `learns_truth` acquisition
      differs as expected (belief kept before; truth known after); `prior` shows from the
      start; acquisitions after `--until` are excluded; real truth stays hidden without
      `--reveal`.
- [x] Offline: merged character IDs resolve in knowledge rows and the timeline.
- [x] Opt-in Neo4j test covers the new nodes and edges.
- [x] Full offline suite, ruff, format, mypy pass; audit mock-transport test covers the call.

## Out of scope

- The POV narrator (retelling). Live API runs.

## Files likely touched

`extract_character/{model,graph,snapshot,knowledge}.py`, `prompt/extract_knowledge.py`,
`ingest/timeline.py`, `cli.py`, `infrastructure/neo4j_store.py`, tests, audit-runner test.

## Verification

Same commands as T-0015. No live API calls.

## Open questions

- Should the speaker of an utterance automatically "believe" its claims? Default: no; a
  speaker may lie. The model can record `prior` or `inferred` when the text supports it.

## Completion report

Implemented by Claude on 2026-11-16 (the user asked Claude to code this directly).

**Changes**
- `extract_character/knowledge.py` (new): prompt assembly (scene map, all claims, this
  chapter's events and utterances, current beliefs of characters present in the chapter)
  and `validate_knowledge` with the channel rules from the PM recommendations.
  A belief the character already holds with the same stance (or a second `learns_truth`
  for the same claim) is dropped rather than rejected, so a harmless repeat cannot fail a run.
- `extract_character/events.py`: shared `ChapterChecks` (characters, segments, paragraphs,
  new claims) used by both the events and knowledge steps.
- `prompt/extract_knowledge.py` (new), book-agnostic.
- `graph.py`: `extract_knowledge` → `validate_knowledge` after `validate_events`
  (`EXTRACT_NODES_PER_CHAPTER = 14`), knowledge files; `snapshot.py`: knowledge rows.
- `neo4j_store.py`: `KnowledgeAcquisition` constraint and statements for `ACQUIRED`, `ABOUT`,
  `VIA` (event or utterance), `IN_SCENE`, and `EXPERIENCED` for witnessed events.
- `ingest/timeline.py` (new) and `pov knowledge` in `cli.py`: character by ID, merged ID or
  name; `--until uNN|uNN_sM`; `--json`; `--reveal`. `prior` acquisitions count from the start.

**Criteria evidence**
- Call order, IDs, files, snapshot: `test_knowledge_runs_after_events_and_is_saved`.
- Channel rules: `test_channel_rules_reject_with_a_reason` (16 cases),
  `test_new_claims_must_be_inferred_or_prior_and_used`, retry with reason:
  `test_a_rejected_answer_is_retried_with_the_reason`; valid answer and dropped repeats:
  `test_valid_acquisitions_get_ids_and_repeats_are_dropped`.
- Timeline: `test_timeline_keeps_the_belief_before_the_reveal_and_the_truth_after`,
  `test_prior_knowledge_counts_from_the_start`, `test_timeline_follows_merges`,
  `test_cli_prints_the_timeline`.
- Neo4j: knowledge assertions added to `test_events_utterances_and_claims_are_linked` →
  `3 passed` with `POV_NEO4J=1`. A scratch end-to-end run of `ingest_book` (fake LLM, real
  Neo4j writer, temporary run deleted afterwards) produced every node and edge type, run
  status `complete`, and the expected overheard → learns_truth history.
- Audit runner mock-transport test: 19 HTTP calls (2 knowledge calls added).

**Commands**
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  → `381 passed, 5 skipped`.
- `ruff check` passed; `ruff format --check` → 80 files formatted; `mypy src/pov_retell` → no
  issues in 50 files; `mypy src tests` → the same 18 pre-existing test errors; `git diff --check` clean.

**Deviations**
- Repeated beliefs are dropped instead of rejected (see Changes).
- Extraction now makes 6 calls per chapter (6N) before retries. Not live-tested.

## Review

_Filled by the product manager._
