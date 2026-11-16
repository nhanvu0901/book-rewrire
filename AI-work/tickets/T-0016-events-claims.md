---
id: T-0016
title: Extract events, utterances and claims per chapter
status: done
owner: Claude (at the user's request)
branch: ticket/T-0016-events-claims
priority: high
created: 2026-11-16
updated: 2026-11-16
depends_on: [T-0015]
---

# T-0016: Extract events, utterances and claims per chapter

## Background

The POV graph design (README, slide deck Sprint 1) has three layers that the pipeline does not
extract yet: what happened (`Event`), what someone said or wrote (`Utterance`), and the
propositions involved (`Claim`), kept apart from whether they are true. The knowledge
timeline (T-0017) needs these as the things a character can witness, be told or overhear.

## User decisions

- 2026-11-16: tickets for (b) events and claims, implemented by Claude.
- 2026-11-16: Neo4j is written after each chapter (T-0015), so these nodes join that write.

## PM recommendations

- One new structured call per chapter (`extract_events`), after the scene map, so each event
  and utterance is tied to a validated scene segment. One job per step (Sprint 2 lesson).
- Claims are book-level records (`claim_NNN`) that later chapters reuse and can resolve
  (`truth_changes`), so a twist in chapter 17 can mark a chapter-12 claim false.
- Utterances are recorded only when they convey a claim, and carry an exact quote that
  Python finds in the cited paragraphs. This keeps volume down and blocks invented speech.
- Event and utterance locations come from their segment, not from the model.

## Requirements

1. Response `ExtractEventResponse` with four arrays: `claims` (new, local keys `new_N`),
   `events`, `utterances`, `truth_changes`.
2. Python validation (rejections go back to the model through the existing retry loop):
   - `segment_id` is a segment of the current chapter; `paragraph_ids` non-empty and inside
     that segment's range.
   - Event `participant_ids` are known characters present in the segment; summary at most
     20 words.
   - Spoken utterances: speaker present in the segment; addressees present and not the
     speaker. Written utterances: speaker is a known character or `null`; addressees known.
   - `quote` at most 40 words and found in the cited paragraphs (case, quotes and spacing
     ignored); at least one claim per utterance.
   - New claims: keys `new_N` unique, statement at most 25 words, `about_ids` known, not a
     duplicate of an existing statement, referenced by at least one event or utterance.
   - `claim_ids` refer to existing claims or new keys of the same answer.
   - `truth_changes`: existing claim, evidence in the current chapter, a real change.
3. Python assigns `claim_NNN` in order, `uNN_eM` to events and `uNN_qM` to utterances, and
   copies the segment's location onto each event.
4. Saved files: `chapters/uNN.events.proposed.json`, `chapters/uNN.events.json`, and
   cumulative `claims.json`, `events.json`, `utterances.json`. Character IDs follow merges.
5. Neo4j (inside the T-0015 chapter transaction): `Event`, `Utterance`, `Claim` nodes;
   `PARTICIPATED_IN`, `IN_SCENE`, `OCCURRED_AT`, `HAS_CLAIM`, `SAID`, `ADDRESSED_TO`,
   `ASSERTS`, `CONCERNS` edges.
6. The prompt is book-agnostic (no test-book names), like the existing extraction prompts.

## Acceptance criteria

- [x] Offline: one `extract_events` call per chapter after the scene map; IDs assigned as
      above; files saved; snapshot contains events, utterances and claims.
- [x] Offline: each validation rule in requirement 2 rejects a bad answer with a reason.
- [x] Offline: a `truth_changes` entry in chapter 2 updates a chapter-1 claim and records
      the evidence chapter.
- [x] Offline: after a merge, event, utterance and claim character IDs use the survivor.
- [x] Opt-in Neo4j test covers the new nodes and edges.
- [x] Full offline suite, ruff, format, mypy pass; the audit mock-transport test covers the
      new call.

## Out of scope

- Knowledge acquisition (T-0017). Live API runs.

## Files likely touched

`extract_character/{model,graph,snapshot,events}.py`, `extract_character/prompt/extract_events.py`,
`infrastructure/neo4j_store.py`, tests, audit-runner test.

## Verification

Same commands as T-0015. No live API calls.

## Open questions

- Should Python also reject an event whose summary is not supported by the cited paragraphs?
  Default: no (not checkable without another model call).

## Completion report

Implemented by Claude on 2026-11-16 (the user asked Claude to code this directly).

**Changes**
- `extract_character/model.py`: `ExtractEventResponse` (claims, events, utterances,
  truth_changes), `ClaimRecord`, `EventRecord`, `UtteranceRecord`, `ChapterEvents`, state keys.
- `extract_character/events.py` (new): prompt assembly (roster, this chapter's scene map,
  existing claims as `claim_NNN | truth | statement (about: ...)`) and `validate_events`
  with every rule of requirement 2. Quotes are compared with the T-0012 `name_key`
  (case, curly/straight quotes and spacing ignored) after trimming surrounding quote marks.
- `extract_character/prompt/extract_events.py` (new), book-agnostic.
- `graph.py`: `extract_events` → `validate_events` after `validate_scenes`
  (`EXTRACT_NODES_PER_CHAPTER = 12`); new per-chapter and cumulative files.
- `snapshot.py`: resolves merged IDs in claims, events and utterances; rows carry
  `chapter_id` and reading `order`.
- `neo4j_store.py`: `Claim`, `Event`, `Utterance` constraints and the statements for
  `CONCERNS`, `IN_SCENE`, `OCCURRED_AT`, `PARTICIPATED_IN`, `HAS_CLAIM`, `SAID`,
  `ADDRESSED_TO`, `ASSERTS`, inside the same chapter transaction.
- Tests that script every HTTP reply in order now include one events reply per chapter.

**Criteria evidence**
- Call order, IDs, files, snapshot, truth change in chapter 2:
  `test_events_run_after_the_scene_map_and_claims_resolve_later`.
- Validation rules: `test_invalid_answers_are_rejected_with_a_reason` (22 cases) and
  `test_a_truth_change_that_changes_nothing_is_rejected`; retry with reason:
  `test_a_rejected_answer_is_retried_with_the_reason`.
- Merges: `test_merged_characters_are_rewritten_in_events_utterances_and_claims`,
  `test_a_valid_answer_gets_ids_location_and_redirects`.
- Neo4j: `test_events_utterances_and_claims_are_linked` → `3 passed` with `POV_NEO4J=1`.
- Audit runner: mock-transport test now records 17 HTTP calls (2 events calls added).

**Commands**
- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
  → `348 passed, 5 skipped`.
- `ruff check` passed; `ruff format --check` → 76 files formatted; `mypy src/pov_retell` → no
  issues in 47 files; `mypy src tests` → the same 18 pre-existing test errors; `git diff --check` clean.

**Deviations**
- None in scope. Extraction now makes 5 calls per chapter (5N) before retries.
- Not live-tested: how well a cheap model follows the claim/quote rules is unmeasured.

## Review

_Filled by the product manager._
