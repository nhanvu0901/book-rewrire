---
id: T-0002
title: "WHO IS WHO cards: lasting identity and status, no chapter references or event logs"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: medium
created: 2026-10-24
updated: 2026-10-24
depends_on: [T-0001]
---

# T-0002: WHO IS WHO cards: lasting identity and status, no chapter references or event logs

## Background

T-0001 made call 2 (`summarize_chapter/prompt/update_who_is_who.py`) the only writer of the
WHO IS WHO list. The first full live run after T-0001,
`book/ingest/narnia-debug/run_2ae27f27f5d34937a54c8c81ed93303e`, completed 17 chapters.
Chapter summaries and core memory were good (verbatim 8-word copying at most 3.3%, no
outside-knowledge names, core memory 429 words). The WHO IS WHO cards were not:

1. **Chapter-relative wording.** Cards describe presence in the current chapter instead of
   lasting status: "not present in this chapter", "not mentioned in this chapter", "flew away at
   start of previous chapter", "currently in house passage with visitors". Cards containing
   `this chapter|previous chapter|not present|not mentioned`: 10 of 22 at u10, 11 of 39 at u13,
   22 of 48 in the final list saved in `summaries/book_memory.json`. Read after the book ends,
   these phrases are wrong or meaningless.
2. **Event logs instead of identity.** Cards append what the character did in each chapter
   ("sews with machine; prepares dinner; comforts Lucy"). Cards over 40 words: 4 at u09,
   8 at u10, 11 at u11, 11 at u12, 13 at u13 (longest 87 words). The prompt already says
   "rewrite the card instead of appending" and "do not narrate events"; the model ignored it.
3. **Group lines.** The final list has `Reindeer`, `Two satyrs`, `Four centaurs`, `Four hags`,
   `Field mice`, although the prompt says "Do not list ... unnamed groups".
4. **Guesses and stronger wording than the text.** "presumably revived by Aslan" in 6 final
   cards. "mortally wounded" for Edmund, where the text says "terribly wounded" (u17_p002).

Later chapters and character extraction read this list as context, so these errors spread.

## User decisions

Made by the user on 2026-10-24 ("okay agree write ticket"), approving the proposal:

1. Fix only the call-2 prompt in a small ticket.
2. Forbid chapter-relative wording in cards.
3. The status part of a card records story state (alive, dead, captured, crowned, ...),
   not a list of events.
4. Restate the rule that groups get no line.

## PM recommendations

The user may veto these before work starts:

- Keep the prompt book-agnostic: examples must be generic, never names or creatures from the
  test book. The user wants rules that fit any novel. Lock this with an offline test.
- Forbid guesses about outcomes ("presumably", "probably") unless a character in the text
  holds that belief, and forbid wording stronger than the text.
- Extend the trailing reminder with the card rules, because a trailing reminder reduced
  omissions in earlier testing.

## Requirements

1. In `PROMPT_UPDATE_WHO_IS_WHO`, define the identity card as a description of who the
   character is **as of the end of the current chapter**, not a history:
   - who they are: species or kind, role, family, allegiance, key relationships;
   - their story status in a few words, with its cause when the text states it
     (for example "dead, killed by <name>", "captured", "freed", "crowned");
   - at most 40 words (not "about 40").
2. Forbid in cards:
   - references to chapters or to presence in them, such as "this chapter",
     "previous chapter", "not present", "not mentioned", or where the character currently
     stands or what they are doing in the current scene;
   - lists of actions or events. When a chapter changes the character, rewrite the card to
     the new state and drop details that no longer define them.
3. Restate that groups ("two guards", "a flock of birds", "the villagers") get no line. A
   member of a group gets a line only when the text singles out that individual.
4. Forbid guessed outcomes ("presumably", "probably") unless a character in the text holds
   that belief; then attribute it. Keep the strength of the text's wording; do not intensify
   it (for example, "badly hurt" must not become "mortally wounded").
5. Update `UPDATE_WHO_IS_WHO_REMINDER` to repeat, briefly: every earlier character kept,
   three ` | `-separated fields, each card at most 40 words describing who they are now,
   with no chapter references and no event lists.
6. Use only generic examples. No name, place or creature from the test book may appear in the
   prompt or the reminder.
7. Keep everything else in the prompt: inputs, outside-knowledge rules, explicit family
   relations, separate referenced figures, merging only when the text says so, attribution
   of beliefs, the `name | other names | card` format and comma-separated field 2
   (required by the T-0001 validator).

## Acceptance criteria

- [x] The prompt contains Requirements 1–4 and 7. The PM checks this by reading the diff.
- [x] The reminder contains Requirement 5 and is still the last text of every call-2 input
      (existing tests keep passing).
- [x] New offline test: neither `PROMPT_UPDATE_WHO_IS_WHO` nor `UPDATE_WHO_IS_WHO_REMINDER`
      contains, case-insensitively, any of: `Narnia`, `Aslan`, `Tumnus`, `Edmund`, `Lucy`,
      `Peter`, `Susan`, `Beaver`, `Fenris`, `Jadis`, `Witch`, `satyr`, `centaur`.
- [x] No Python behavior changes: `summarize_chapter/logic.py`, `graph.py`, `model.py` and the
      validator are unchanged.
- [x] All commands under Verification pass.
- [x] Context-maintenance pass done per root `AGENTS.md` (this changes a prompt contract).

## Out of scope

- Python enforcement of card length, or any validator change (user default below).
- Call 1 (`summarize_chapter.py`): uneven summary length (u04 923 and u13 1,071 words) and
  the `<previous_book_summary>` label.
- The core-memory prompt (`summarize_book.py`). Its "mortally wounded" and "though he knows
  she is cruel" wording is a separate issue.
- Extraction prompts and merge logic.
- Live API calls (see Open questions).

## Known limitation

The T-0001 validator rejects any answer that drops an earlier first-field name. A group line
that slips into one list can therefore never be removed in later chapters. This ticket
only lowers the chance that one enters. Revisit if the live check still shows group lines.

## Files likely touched

- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_who_is_who.py`
- `tests/test_chapter_summarization.py`
- `AI-work/PROJECT_CONTEXT.md` (context-maintenance pass)
- `README.md` only if it states the card rules (currently it states only the format)

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK; not part of `done`): run call 2 alone as a
chain from u01 to u17 (17 calls plus retries), each with the previous new list and the
chapter text. Then measure the final list against the run above:

| Metric | Run `2ae27f27` | Target |
| --- | --- | --- |
| Cards matching `this chapter\|previous chapter\|not present\|not mentioned` | 22 / 48 | 0 |
| Cards over 40 words, worst chapter | 13 (u13, max 87) | 0 |
| Group lines | 5 | 0 |
| Cards with `presumably\|probably` not attributed to a character | 6 | 0 |

## Open questions

- Should unnamed but specifically identified minor creatures (a pelican, a great dog) stay in
  WHO IS WHO? Default: yes, the current rule stays (named or specifically identified
  individuals). Only groups are excluded.
- Should Python reject cards over 40 words and retry? Default: no; prompt only, as the user
  agreed. Revisit after the live check.
- May the implementer run the live check? Default: no; the PM proposes it after review.

## Completion report

### Files changed
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_who_is_who.py`: Updated `PROMPT_UPDATE_WHO_IS_WHO` and `UPDATE_WHO_IS_WHO_REMINDER` with Requirements 1–7 (identity card as of the end of the current chapter, at most 40 words, story status with stated cause, no chapter/presence references, no action/event lists, rewrite and drop obsolete details, generic group exclusion examples, no unattributed guessed outcomes, no intensified wording).
- `tests/test_chapter_summarization.py`: Added `test_who_is_who_prompt_and_reminder_are_book_agnostic` verifying that none of the 13 forbidden book-specific terms appear in `PROMPT_UPDATE_WHO_IS_WHO` or `UPDATE_WHO_IS_WHO_REMINDER`, and checking key rule phrases.
- `AI-work/PROJECT_CONTEXT.md`: Updated Call 2 contract description, ticket status, verification results, and open live-check item.

### Criterion-by-criterion evidence
- **Requirements 1–4 and 7 in `PROMPT_UPDATE_WHO_IS_WHO`:** `update_who_is_who.py:16-58` defines the card as who the character is as of the end of the current chapter (species/kind, role, family, allegiance, key relationships; story status in a few words with cause when stated; at most 40 words), forbids chapter/presence/scene references and lists of actions/events, restates group exclusion (`"two guards"`, `"a flock of birds"`, `"the villagers"`), forbids unattributed guessed outcomes (`"presumably"`, `"probably"`) and intensified wording (`"badly hurt"` -> `"mortally wounded"`), and retains all existing input/outside-knowledge/kinship/merge/comma-separated field-2 rules.
- **Requirement 5 in `UPDATE_WHO_IS_WHO_REMINDER`:** `update_who_is_who.py:72-77` repeats keeping every earlier character, three `' | '`-separated fields, and each card at most 40 words describing who they are now with no chapter references and no event lists. Existing tests in `tests/test_chapter_summarization.py` confirm it remains the trailing text of every Call 2 prompt.
- **Book-agnostic offline test:** `test_who_is_who_prompt_and_reminder_are_book_agnostic` in `tests/test_chapter_summarization.py` checks all 13 terms (`Narnia`, `Aslan`, `Tumnus`, `Edmund`, `Lucy`, `Peter`, `Susan`, `Beaver`, `Fenris`, `Jadis`, `Witch`, `satyr`, `centaur`) case-insensitively.
- **No Python behavior changes:** `summarize_chapter/logic.py`, `graph.py`, and `model.py` were not modified.
- **Verification commands:** All passed (exact outputs below).
- **Context-maintenance pass:** Updated `AI-work/PROJECT_CONTEXT.md` directly (disclosed: neither `gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in the Antigravity runtime).

### Verification commands and exact results
1. `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
   -> `165 passed, 5 skipped, 1 warning in 1.33s`
2. `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`
   -> `All checks passed!`
3. `.venv/bin/ruff format --check src tests`
   -> `58 files already formatted`
4. `.venv/bin/mypy src/pov_retell`
   -> `Success: no issues found in 39 source files`
5. `git diff --check`
   -> exit 0 (no output).

### Deviations and follow-ups
- **Deviations:** None. Followed all three open-question defaults (unnamed specifically identified minor creatures stay allowed; no Python word-count validator; no live API calls executed).
- **Follow-ups:** Run the post-review live Call 2 chain on `u01`–`u17` once approved by the user and product manager.

## Review

Reviewed by Claude (product manager) on 2026-10-24. Verdict: **verified** (offline).

### Verification rerun by the reviewer

Run on the working tree that also contains T-0003, so the counts include its tests:
pytest `178 passed, 5 skipped, 1 warning`; ruff check `All checks passed!`; ruff format
`57 files already formatted`; mypy `Success: no issues found in 38 source files`;
`git diff --check` exit 0.

### Acceptance criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| Prompt contains Requirements 1-4 and 7 | pass | `update_who_is_who.py`: card "as of the end of the current chapter, not a history"; status with cause and a `<name>` placeholder; "at most 40 words" (no "about"); bans chapter/presence references and event lists; rewrite and drop rule; generic group examples; guessed outcomes and intensified wording banned; all earlier rules kept (outside knowledge, explicit family relations, separate referenced figures, merge only when stated, attribution, comma-separated field 2) |
| Reminder contains Requirement 5 and stays last | pass | `UPDATE_WHO_IS_WHO_REMINDER`; existing `endswith` assertions pass |
| Book-agnostic test | pass | `test_who_is_who_prompt_and_reminder_are_book_agnostic`, 13 terms |
| No Python behavior change | pass | `summarize_chapter/logic.py`, `graph.py`, `model.py` last modified before this ticket |
| Verification commands | pass | above |
| Context-maintenance pass | pass | `PROJECT_CONTEXT.md` Call 2 contract updated; done by the implementer directly (disclosed) |

### Findings

None blocking. The known limitation stands: the drop validator keeps any group line that
slips in once.

### Not measured

Whether the model now follows the card rules. Next step: the live call-2 chain u01-u17 under
Verification, which needs the user's OK.
