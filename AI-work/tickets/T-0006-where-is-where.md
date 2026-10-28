---
id: T-0006
title: "WHERE IS WHERE: running place list in the summary graph"
status: verified
owner: Terra (gpt-5.6-sol)
priority: medium
created: 2026-10-25
updated: 2026-10-25
depends_on: [T-0002]
---

# T-0006: WHERE IS WHERE: running place list in the summary graph

## Background

Events (`OCCURRED_AT`) and the scene map (T-0008) need places with stable identities. Places
have the same duplication risk as characters: one place can have several names. WHO IS WHO
already gives the LLM a running "who is who" before structured extraction. Places need the
same running list.

Places exist in every novel, so this stays general.

## User decisions

- 2026-10-25: accepted the reading list.
  - Item 4: WHERE IS WHERE, a text list like WHO IS WHO.
  - Item 5: the scene map, which needs place IDs.
- 2026-10-25: write all agreed tickets.

## PM recommendations

The user may veto these before work starts:

- Add `WHERE IS WHERE` to `format_previous_context`, so call 1 and every extraction step see
  the places known through chapter N-1.
- Reuse the WHO IS WHO validator, generalized with a list label for its messages.

## Requirements

1. **Call 3 per chapter** in the summary graph, after call 2, on the summary (text) client.
   - **Input:** the previous WHERE IS WHERE (empty for u01), the chapter text, and a
     trailing reminder.
   - **Output:** the complete list, one line per place:
     `name | comma-separated other names used in the text, or - | place card`.
2. **Place card rules** in `prompt/update_where_is_where.py`:
   - The card says:
     - what kind of place it is;
     - where it lies, or what larger place it is part of, by name;
     - who owns, rules or lives there;
     - its lasting state (for example abandoned, destroyed).
   - At most 30 words.
   - No chapter references and no event lists.
   - Include places that are named, and unnamed places where action happens, under their
     clearest description. Places are buildings, rooms, lands, landmarks and natural
     features. Objects and people are not places.
   - Keep every earlier place. Merge two names only when the text says they are one place.
   - Use no outside knowledge.
   - Use generic examples only.
3. **Validation and retry** as for WHO IS WHO:
   - three non-empty fields per line;
   - every previous name survives as a whole name in field 1 or field 2;
   - at most 2 extra attempts with the rejection reason.
4. **Storage:**
   - `summaries/uNN.summary.json` gains `where_is_where`;
   - `summaries/book_memory.json` gains the final `where_is_where`.
5. **Context:** `format_previous_context` adds a `WHERE IS WHERE` section after `WHO IS WHO`
   (PM recommendation).
6. **Calls:** 3 per chapter plus 1 final (52 for 17 chapters). Keep the recursion limit
   correct, using T-0004's helper if it exists.
7. Update the audit runner (call counts, offline test), `run-protocol.md`, README, and run a
   context-maintenance pass.

## Acceptance criteria

- [x] 17 chapters → 52 summary calls. Offline test.
- [x] Call 3 receives the previous WHERE IS WHERE and the chapter text only: no summaries,
      no WHO IS WHO, no call-1 output. u01 gets an empty list. Offline marker test.
- [x] A dropped place triggers a retry with the reason. Three invalid answers raise, and
      saved chapters remain. Offline tests.
- [x] Saved shapes include `where_is_where` in per-chapter and book files. Offline test.
- [x] Call 1 and character extraction for chapter N see WHERE IS WHERE after N-1, never N.
      Offline test.
- [x] Book-agnostic prompt test. All Verification commands pass. README updated. Context
      pass done.

## Out of scope

- Place IDs (T-0007), the scene map (T-0008), Neo4j.
- Changes to the WHO IS WHO rules.

## Files likely touched

- `src/pov_retell/ingest/graph/summarize_chapter/{logic.py,graph.py,model.py}`,
  new `prompt/update_where_is_where.py`
- `tests/test_chapter_summarization.py`, `tests/test_summary_ingest.py`, `tests/test_character_ingest.py`
- audit runner, its test, `run-protocol.md`, `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK): compare the list after u12 with the PM's
reference, which has ten places: the Professor's house, the spare room, Narnia, the
lamp-post, Tumnus's cave, the Beavers' house, the Witch's house, the Stone Table, the
pavilion, Cair Paravel. Evidence: u01_p001, u01_p020, u02_p012, u02_p013, u02_p022,
u06_p031, u07_p039, u09_p009, u12_p006, u12_p026.

## Open questions

- Should the final core-memory call also see WHERE IS WHERE? Default: no. It keeps the T-0001
  decision.

## Completion report

- **What changed:**
  - Created `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_where_is_where.py` (`PROMPT_UPDATE_WHERE_IS_WHERE`, `WHERE_IS_WHERE_INPUT`, `UPDATE_WHERE_IS_WHERE_REMINDER`) with book-agnostic place card rules (at most 30 words describing what kind of place it is, where it lies or what larger place it is part of by name, who owns/rules/lives there, and its lasting state; no chapter references or event lists; named places and unnamed action settings under clearest description; no objects/people; keep every earlier place; merge only when explicit; no outside knowledge).
  - Updated `src/pov_retell/ingest/graph/summarize_chapter/model.py` (`where_is_where: SummaryText` on `SummarizeChapterResponse` and `BookMemory`; `where_is_where: str` on `SummarizeChapterState`).
  - Updated `src/pov_retell/ingest/graph/summarize_chapter/logic.py` (`format_previous_context` includes `WHERE IS WHERE` after `WHO IS WHO`; generalized `validate_running_list` shared by `validate_who_is_who` and `validate_where_is_where`; added `update_where_is_where` as Call 3 in `summarize_chapter`; passed `where_is_where` in `summarize_book`).
  - Updated `src/pov_retell/ingest/graph/summarize_chapter/graph.py` to initialize, persist, and forward `where_is_where` into `summaries/uNN.summary.json` and `summaries/book_memory.json`.
  - Updated `tests/test_chapter_summarization.py`, `tests/test_summary_ingest.py`, `tests/test_character_ingest.py`, `tests/test_relationship_ingest.py`, `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`, `README.md`, and `AI-work/PROJECT_CONTEXT.md`.
- **Files touched:**
  - `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_where_is_where.py`
  - `src/pov_retell/ingest/graph/summarize_chapter/model.py`
  - `src/pov_retell/ingest/graph/summarize_chapter/logic.py`
  - `src/pov_retell/ingest/graph/summarize_chapter/graph.py`
  - `tests/test_chapter_summarization.py`
  - `tests/test_summary_ingest.py`
  - `tests/test_character_ingest.py`
  - `tests/test_relationship_ingest.py`
  - `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`
  - `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`
  - `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`
  - `README.md`
  - `AI-work/PROJECT_CONTEXT.md`
  - `AI-work/tickets/T-0006-where-is-where.md`
  - `AI-work/tickets/README.md`
- **Verification outputs:**
  - `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q` -> `235 passed, 5 skipped`
  - `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit` -> `All checks passed!`
  - `.venv/bin/ruff format --check src tests` -> `61 files already formatted`
  - `.venv/bin/mypy src/pov_retell` -> `Success: no issues found in 41 source files`
  - `git diff --check` -> clean (0 output)
- **Context maintenance:** Performed bounded context-maintenance pass in `AI-work/PROJECT_CONTEXT.md` directly (Codex `gpt-5.6-sol` and Claude Sonnet 5.5 are not exposed in this Antigravity runtime).
- **Remaining risks / notes:** Not yet exercised with a live OpenRouter run; ready for Claude review.

### Repair follow-up — 2026-10-25

- **Claude F1 repair:** Replaced the Narnia-derived unnamed-place and object examples in
  `update_where_is_where.py` with generic examples (`the back kitchen`, `the river ford`,
  `a cup`, `a chair`, `a sword`). The existing rules and runtime contract are unchanged.
- **Regression coverage:** Extended the book-agnostic prompt test with `wardrobe`, `lamp`,
  `spare room`, `hilltop`, `Stone Table`, `pavilion`, `Professor`, `Cair`, and `Paravel`.
- **RED:** The two targeted parametrized prompt tests produced `8 failed, 42 passed,
  1 warning`; the failures were the four terms present in both prompts: `wardrobe`, `lamp`,
  `spare room`, and `hilltop`.
- **GREEN:** The same targeted tests produced `50 passed, 1 warning`.
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
The call, validation, storage and context wiring are correct and tested. The prompt's
examples are taken from the test book, which the ticket forbids (F1).

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
| 17 chapters -> 52 summary calls | pass | `logic.py:173-177` (3 calls per chapter) + `summarize_book`; offline call-count tests; README line 339 |
| Call 3 gets only the previous list and the chapter text; u01 gets an empty list | pass | `WHERE_IS_WHERE_INPUT` (`update_where_is_where.py:52-63`); `logic.py:135-158`, `:176` |
| Dropped place retries with the reason; three invalid answers raise; saved chapters remain | pass | shared `validate_running_list` (`logic.py:58-88`), retry loop `:150-158`; offline tests |
| `where_is_where` in per-chapter and book files | pass | `graph.py:59-60`, `:66-73`; `BookMemory` / `SummarizeChapterResponse` fields |
| Call 1 and extraction for chapter N see the list after N-1 only | pass | `format_previous_context` (`logic.py:39-48`) is built from `summaries[:index]` |
| Book-agnostic prompt test | **fail** | the test passes, but its word list (`tests/test_chapter_summarization.py:252-273`) has only character names; see F1 |

### Findings

**F1 (required): prompt examples come from the test book.** Requirement 2 says "Use generic
examples only".
- `update_where_is_where.py:35` gives "the spare room" and "the hilltop camp" as examples of
  unnamed places. Both are places in the Narnia test book (the room with the wardrobe,
  Aslan's camp).
- `:37` lists "a lamp, a wardrobe, a table" as objects that are not places. These are the
  test book's lamp-post, wardrobe and Stone Table.

Examples that match the test book bias the live check toward success and hint at that book
only, while the user asked for a model general to any novel. Replace them with examples no
test book uses (for example "the back kitchen", "the river ford"; "a cup, a chair, a
sword"). Add the test book's place and object words to the book-agnostic test list:
"wardrobe", "lamp", "spare room", "hilltop", "Stone Table", "pavilion", "Professor", "Cair",
"Paravel". The same defect is in T-0007's prompt; fix both together.

**Note (risk, no change required).** `validate_running_list` rejects an empty list
(`logic.py:66-67`). If the first chapter of some book has no setting at all (a pure
reflection or letter), call 3 fails three times and stops the run. Most chapters name or
imply a place, so this is unmeasured, not a defect.

### Not measured

The ten-place reference list after u12 (Verification); needs a live run and the user's OK.

### Re-review (2026-10-25)

Verdict: **verified**. The reviewer reran the checks on the combined tree.

- Offline pytest: `317 passed, 5 skipped, 1 warning` (the LangSmith deprecation warning).
- `ruff check`: all checks passed. `ruff format --check`: 73 files already formatted
  (`src`, `tests` and the audit skill). `mypy src/pov_retell`: no issues in 45 source files.
  `git diff --check`: clean.
- A case-insensitive scan of every prompt under `src/pov_retell/ingest/graph/*/prompt/` for
  the test book's names, places and objects finds none. The only hit was "switches",
  which contains "witch" as a substring.
- F1 fixed: `update_where_is_where.py:34-37` now uses "the back kitchen" and "the river ford"
  as place examples, and "a cup, a chair or a sword" as object examples. The book-agnostic
  test in `tests/test_chapter_summarization.py` includes all nine requested words. The
  rules and runtime contract are unchanged.
- Still not measured: the live reference check and the empty-list risk noted above. Both
  need a live run and the user's OK.
