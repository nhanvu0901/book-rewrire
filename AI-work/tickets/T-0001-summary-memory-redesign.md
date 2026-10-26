---
id: T-0001
title: "Summary memory: chapter summaries + WHO IS WHO + core memory"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: high
created: 2026-10-24
updated: 2026-10-24
depends_on: []
---

# T-0001: Summary memory: chapter summaries + WHO IS WHO + core memory

## Background

Each chapter currently makes two summary calls in
`src/pov_retell/ingest/graph/summarize_chapter/logic.py`:

1. Call 1 (`prompt/summarize_chapter.py`) writes `chapter_summary` for the current chapter.
2. Call 2 (`prompt/update_book_summary.py`) rewrites the whole `book_summary_so_far`
   (sections `WHO IS WHO` and `STORY SO FAR`) from the previous one plus the chapter text.
   u01 skips call 2 and reuses its chapter summary. 17 chapters = 33 calls.

Because call 2 rewrites everything, older story content can shrink or disappear:

- Run `run_dfea8d63f87e40bb87d4a37b151a83fb`: STORY SO FAR fell from 1,168 to 562 words at
  u09→u10 and from 428 to 339 at u03→u04, although the prompt forbids shrinking.
  Audit: `book/diagnostics/audit-run_dfea8d63-20261024/report.md`.
- Prompt test v5 (`book/diagnostics/summary_prompt_tuning/v5_*`): the story fell from 654 to
  409 words at u05 with the same prompt.
- Ivy, Margaret and Betty (named only in u01_p004) never enter WHO IS WHO, because u01
  never goes through call 2.
- An older prompt variant copied the book (run `run_03207a33db03401e9babba7aa23f2a25`: 77%
  of source length, 52% verbatim 8-word sequences) and produced a truncated u17.

Saved files and the extraction graph read `book_summary_so_far`
(`extract_character/graph.py` passes the previous chapter's value as context).

## User decisions

Made by the user on 2026-10-24:

1. Remove STORY SO FAR as LLM-written memory. The story is the chapter summaries from call 1,
   accumulated by Python in chapter order. No LLM rewrites earlier chapters.
2. Call 2 only updates WHO IS WHO. Input: the previous WHO IS WHO and the current chapter
   text. It does not receive the story. Output: the complete WHO IS WHO list.
3. After the last chapter, add one node that writes a clean summary of the call-1 chapter
   summaries, keeping what matters, "like the core memory someone keeps after reading a book".

Agreed during the same discussion (proposed by Claude, accepted with the design):

4. u01 also runs call 2, with an empty previous WHO IS WHO.
5. Python checks that call 2 did not drop earlier characters and retries when it did.

## PM recommendations

The user may veto these before work starts:

- Call 1 must write in its own words, with no copied sentences or dialogue. Chapter summaries
  are now the story memory. The audit found the u17 chapter summary at 1,189 words with 8.4%
  verbatim 8-word sequences.
- Call 2 keeps a short reminder after the chapter text: "write the complete list, including
  every earlier character". In testing, a trailing reminder reduced omissions.
- Save the final output as `summaries/book_memory.json`, not `*.summary.json`, so per-chapter
  file counts (including the audit runner's `summary_files`) stay unchanged.

## Requirements

1. **Call 1, chapter summary.** Input:
   - book title and chapter id;
   - the WHO IS WHO after the previous chapter;
   - all previous chapter summaries in chapter order, each labeled with its chapter id;
   - the current chapter text.

   It never receives the current or a later chapter's summary. For u01 both context parts are
   empty. Output: plain-text `chapter_summary` for this chapter only.
2. **Call 2, WHO IS WHO update.** Input: the previous WHO IS WHO (empty for u01) and the
   current chapter text, plus the trailing reminder. It does not receive chapter summaries or
   the call-1 output. Output: the complete list, one line per individual:
   `name | other names or titles used in the text, or - | identity card`.
   Reuse the WHO IS WHO rules of the current `update_book_summary.py`:
   - at most about 40 words per card;
   - keep every earlier character;
   - no places, objects or unnamed groups;
   - only names in the inputs, and ignore outside knowledge of the book;
   - family relations need an explicit statement;
   - merge two names only when the text says they are the same individual, keeping both names;
   - identity, role, allegiance, key relationships and current status, without event narration.
3. **WHO IS WHO validation in Python.** Ignore an optional first line `WHO IS WHO`. Then:
   - the text is nonblank;
   - every non-empty line has exactly three fields separated by `|`;
   - every name in the first field of the previous list appears, case-insensitively, in the
     first or second field of some new line.

   On a violation, call 2 again with the rejection reason appended to the input, at most 2
   extra attempts, then raise. Already saved chapters stay intact.
4. **Saved chapter file** `summaries/uNN.summary.json`:
   `{"chapter_id", "chapter_summary", "who_is_who"}`. Remove `book_summary_so_far`.
   Keep the existing atomic write.
5. **Final node, core memory.** Runs once after the last chapter. Input:
   - the book title;
   - all chapter summaries in order with chapter ids.

   Output: plain-text `core_memory` that an attentive reader keeps after finishing the book:
   - the main characters and who they are;
   - the central conflict;
   - the key turning points and revelations;
   - how it ends.

   Leave out minor detail, keep beliefs and guesses attributed and uncertain, write in its own
   words, and use only the supplied summaries. Target roughly 400–700 words.
   Save `summaries/book_memory.json` as `{"who_is_who": <final list>, "core_memory": <text>}`.
6. **Context for extraction.** For chapter N, the extract_character graph receives
   Python-assembled context: the WHO IS WHO after chapter N-1 plus chapter summaries 1..N-1.
   u01 receives empty context. Build it with one shared Python function also used by call 1.
   The extraction prompt itself is unchanged.
7. **Remove cumulative-story code.** Delete `prompt/update_book_summary.py`,
   `UPDATE_BOOK_SUMMARY_REMINDER`, the `book_summary_so_far` model fields and graph-state
   keys, and every other STORY SO FAR reference in source and tests.
8. Keep `build_summarize_chapter_graph(llm, on_step)` and the final state key `summaries`
   (a list of per-chapter summaries in order), so the pipeline and the audit runner
   (`AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`) keep working.
   Confirm the pipeline's `recursion_limit` (`len(chapters) * 4 + 10`) still covers the
   new node count, and adjust it if not.
9. Update `README.md` (the ingest and summary sections) to describe the new memory.

## Acceptance criteria

- [x] With 17 chapters, the summary graph makes exactly 35 LLM calls: 2 per chapter
      (including u01) plus 1 final call. Offline test.
- [x] Call 1 for chapter N contains the WHO IS WHO after N-1, the summaries of chapters
      1..N-1 in order, and chapter N's text. It contains no summary of chapter N or later.
      Offline test with marker strings.
- [x] Call 2 contains the previous WHO IS WHO and the chapter text. It contains no chapter
      summary and no call-1 output. Offline test.
- [x] u01 runs call 2 with an empty previous list. Offline test.
- [x] Dropping a previous character in call 2 triggers a retry with the rejection reason.
      Three invalid answers raise, and earlier saved chapter files remain. Offline tests.
- [x] A line without three `|` fields is rejected. Offline test.
- [x] `summaries/uNN.summary.json` holds exactly `chapter_id`, `chapter_summary`, `who_is_who`.
      `summaries/book_memory.json` holds `who_is_who` and `core_memory`. Offline test.
- [x] Extraction for chapter N receives the WHO IS WHO after N-1 and summaries 1..N-1 only.
      u01 gets empty context. The existing previous-only boundary tests are updated and pass.
- [x] No `book_summary_so_far`, `STORY SO FAR`, `update_book_summary` or
      `UPDATE_BOOK_SUMMARY_REMINDER` remains in `src/`, `tests/` or the audit skill
      (`grep -rn` shows none).
- [x] The audit-runner offline test passes, updated for the new call count.
- [x] All commands under Verification pass.
- [x] README updated. Context-maintenance pass done per root `AGENTS.md`.

## Out of scope

- Extraction prompt and character merge logic.
- The `_ask` provider-error handling (`finish_reason="error"`).
- Reasoning controls, models and token caps.
- An automatic check for names absent from the book (the "Pevensie" problem).
- Limiting how many previous chapter summaries go into the context window.
- Resume or checkpointing.
- Neo4j.

## Files likely touched

- `src/pov_retell/ingest/graph/summarize_chapter/{graph.py,model.py,logic.py}`
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/summarize_chapter.py`
- New `prompt/update_who_is_who.py` and `prompt/summarize_book.py`; delete `prompt/update_book_summary.py`
- `src/pov_retell/ingest/graph/extract_character/graph.py` (context source)
- `src/pov_retell/ingest/pipeline.py` (only if the recursion limit needs it)
- `tests/test_chapter_summarization.py`, `tests/test_summary_ingest.py`, `tests/test_character_ingest.py`
  (the `summary_client` helper), `tests/test_character_openrouter_integration.py` if affected
- `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`
- `README.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
grep -rn -E "book_summary_so_far|STORY SO FAR|update_book_summary|UPDATE_BOOK_SUMMARY" src tests AI-work/skills
```

No live API calls and no Neo4j writes in this ticket. After review, the product manager will
propose a live audit, starting with chapters u09–u10, where the story previously shrank.

## Open questions

- Should the final core-memory call also receive the final WHO IS WHO? Default: no. The user
  asked for a summary of the call-1 summaries.
- Should call 1 receive all previous chapter summaries, or only the last K? Default: all.
  Narnia's 16 previous summaries are about 6–8k words. Revisit for longer books.

## Completion report

### Files changed
- `src/pov_retell/ingest/graph/summarize_chapter/model.py`: Replaced `book_summary_so_far` with `who_is_who` in `SummarizeChapterResponse`, `ChapterSummary`, and `SummarizeChapterState`; added `BookMemory(who_is_who, core_memory)`.
- `src/pov_retell/ingest/graph/summarize_chapter/logic.py`: Added `format_chapter_summaries`, `format_previous_context`, `validate_who_is_who`, `update_who_is_who` (with up to 2 extra repair attempts appending `Rejected: <reason>`), and `summarize_book`. Updated `summarize_chapter` to pass `format_previous_context(previous_summaries)` into Call 1 and run Call 2 (`update_who_is_who`) for every chapter including `u01`.
- `src/pov_retell/ingest/graph/summarize_chapter/graph.py`: Added final `summarize_book` node after `save_summary` when all chapters complete, saving `summaries/book_memory.json` atomically.
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/summarize_chapter.py`: Added rule 6 requiring `chapter_summary` to be written in its own words with no copied sentences or dialogue.
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_who_is_who.py` (new): Prompt, input template (`WHO_IS_WHO_INPUT`), and trailing reminder (`UPDATE_WHO_IS_WHO_REMINDER`) for Call 2 (`WHO IS WHO` only).
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/summarize_book.py` (new): Prompt (`PROMPT_SUMMARIZE_BOOK`) and input template (`BOOK_SUMMARY_INPUT`) for the final `core_memory` node.
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_book_summary.py`: Deleted.
- `src/pov_retell/ingest/graph/extract_character/graph.py`: Updated `extract_characters` to assemble prior context via the shared `format_previous_context(state["summaries"][:index])` helper.
- `src/pov_retell/infrastructure/llm.py`, `src/pov_retell/ingest/pipeline.py`, `tests/test_llm.py`: Minor formatting/import-order cleanup so `ruff check` and `ruff format --check` pass cleanly across `src` and `tests`. Confirmed `max(25, len(chapters) * 4 + 10)` (78 for 17 chapters) covers the 53 graph steps (`3N + 2`) of `summarize_chapter`.
- `tests/test_chapter_summarization.py`, `tests/test_summary_ingest.py`, `tests/test_character_ingest.py`: Updated `summary_client` and tests for the new 2-calls-per-chapter + 1-final-call workflow, context assembly, `WHO IS WHO` validation/retries, and `book_memory.json`.
- `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`: Updated audit runner step/repair tracking, protocol call count (`2N+1`), and mock-transport test (7 HTTP calls for 2 smoke chapters).
- `README.md`, `AI-work/PROJECT_CONTEXT.md`: Updated documentation and project context.

### How each acceptance criterion is met
- **17 chapters -> 35 LLM calls:** Verified in `test_summary_graph_completes_seventeen_chapters_in_source_order` (`tests/test_chapter_summarization.py`) and `test_many_chapters_complete_in_numeric_order` (`tests/test_character_ingest.py`).
- **Call 1 context (WHO IS WHO after N-1 + summaries 1..N-1 in order + chapter N text, no summary of N or later):** Verified with marker strings in `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory`.
- **Call 2 context (previous WHO IS WHO + chapter text + reminder, no chapter summary or call-1 output):** Verified in `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory`.
- **u01 runs Call 2 with empty previous list:** Verified in `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory` (`<previous_who_is_who>\n\n</previous_who_is_who>`).
- **Dropping previous character triggers retry with rejection reason; 3 invalid answers raise and preserve earlier saved chapters:** Verified in `test_dropping_previous_character_retries_with_rejection_reason_and_recovers` and `test_three_invalid_who_is_who_answers_raise_and_preserve_saved_chapters`.
- **Line without three `|` fields rejected:** Verified in `test_who_is_who_rejects_blank_or_malformed_lines`.
- **Saved JSON shapes (`uNN.summary.json` and `book_memory.json`):** Verified in `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory` and `test_ingest_passes_only_preceding_who_is_who_and_chapter_summaries_with_full_roster`.
- **Extraction context for chapter N:** Verified in `test_ingest_passes_only_preceding_who_is_who_and_chapter_summaries_with_full_roster` (`tests/test_summary_ingest.py`).
- **No old identifiers remain:** `grep -rn -E "book_summary_so_far|STORY SO FAR|update_book_summary|UPDATE_BOOK_SUMMARY" src tests AI-work/skills` returns 0 matches.
- **Audit-runner offline test passes:** Verified in `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`.

### Verification commands and exact results
1. `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`
   -> `152 passed, 5 skipped, 1 warning in 1.18s` (5 skipped are opt-in live OpenRouter/Neo4j tests).
2. `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`
   -> `All checks passed!`
3. `.venv/bin/ruff format --check src tests`
   -> `58 files already formatted`
4. `.venv/bin/mypy src/pov_retell`
   -> `Success: no issues found in 39 source files`
5. `git diff --check`
   -> exit 0 (no output).
6. `grep -rn -E "book_summary_so_far|STORY SO FAR|update_book_summary|UPDATE_BOOK_SUMMARY" src tests AI-work/skills`
   -> no matches (exit 1).

### Review fixes (F1–F3)
- **F1 (`src/pov_retell/ingest/graph/summarize_chapter/logic.py`, `prompt/update_who_is_who.py`, `tests/test_chapter_summarization.py`):** Updated `validate_who_is_who` to compare whole names (case-insensitively and trimmed) against the first field and comma-separated entries of the second field, rather than substring containment. Added `test_substring_matches_do_not_hide_dropped_characters_and_trigger_retry` covering both `"Eve"` vs `"Daughter of Eve"` and `"Tumnus"` vs `"Tumnus's father"`.
- **F2 (`tests/test_chapter_summarization.py`):** Updated `test_dropping_previous_character_retries_with_rejection_reason_and_recovers` to assert `"Rejected: WHO IS WHO dropped earlier character(s): Jo" in retry_prompt`.
- **F3 (`README.md`, `AI-work/PROJECT_CONTEXT.md`):** Updated `README.md:12` to describe `WHO IS WHO` after chapter N-1 plus chapter summaries 1..N-1 instead of "preceding cumulative book summary", and updated `AI-work/PROJECT_CONTEXT.md` Prompt Evidence to label the deleted two-section `update_book_summary.py` prompt as the former prompt.

### Deviations and disclosures
- None in implementation scope. Used the ticket defaults for both open questions (final `core_memory` call receives chapter summaries only; Call 1 receives all previous chapter summaries).
- For automatic context maintenance (`AI-work/agents/context-maintainer.md`), neither `gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed in the Antigravity runtime, so per `AGENTS.md` the bounded update to `AI-work/PROJECT_CONTEXT.md` was performed directly by the implementing agent.

### Follow-ups noticed
- `tests/test_character_openrouter_integration.py` is an opt-in live test (`@pytest.mark.openrouter`) and continues to check `summaries/u02.summary.json` existence; when a live run is authorized, it will also exercise `summaries/book_memory.json`.
- For much longer books (e.g., 60+ chapters), Call 1 and `extract_character` receive all preceding chapter summaries (`1..N-1`); a sliding window (`last K` chapters + `core_memory` or `who_is_who`) may be worth revisiting if prompt size grows too large.

## Review

Reviewed by Claude (product manager) on 2026-10-24. Verdict: **changes_requested**.
The design is implemented as specified. One required fix: the Python check that call 2 kept
every earlier character misses realistic drops (F1).

### Verification rerun by the reviewer

| Command | Result |
| --- | --- |
| pytest (`tests` + audit skill tests, offline) | `150 passed, 5 skipped, 1 warning` |
| `ruff check src tests AI-work/skills/run-ingest-api-audit` | `All checks passed!` |
| `ruff format --check src tests` | `58 files already formatted` |
| `mypy src/pov_retell` | `Success: no issues found in 39 source files` |
| `git diff --check` | exit 0 |
| `grep` for removed identifiers | no matches (exit 1) |

### Acceptance criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| 35 calls for 17 chapters | pass | `test_summary_graph_completes_seventeen_chapters_in_source_order`; `test_many_chapters_complete_in_numeric_order` |
| Call 1 context, previous-only | pass | `logic.py` `summarize_chapter` + `format_previous_context`; marker test asserts u03 sees u01 < u02 and no u03 |
| Call 2 context without summaries | pass | `update_who_is_who` formats only previous list + chapter text; markers checked for u01 and u02 |
| u01 runs call 2 with empty list | pass | marker `<previous_who_is_who>\n\n</previous_who_is_who>` |
| Dropped character triggers retry; 3 failures raise, saved chapters kept | **partial** | Works for an exact drop (tests pass); misses drops whose name is a substring of another kept name (F1) |
| Line without three fields rejected | pass | `test_who_is_who_rejects_blank_or_malformed_lines` |
| Saved file shapes | pass | exact-dict asserts for `u01`, `u02` and `book_memory.json` |
| Extraction context N-1 only | pass | `extract_character/graph.py` uses `format_previous_context(state["summaries"][:index])`; `test_ingest_passes_only_preceding_who_is_who_and_chapter_summaries_with_full_roster` |
| Old identifiers removed | pass | grep above |
| Audit-runner test updated | pass | 7 HTTP calls for 2 chapters; `book_memory.json` asserted; repair detection covers `\n\nRejected:` |
| Verification commands | pass | table above |
| README + context pass | **partial** | Stale sentences remain (F3) |

Also checked: recursion limit (`3N+2` = 53 steps for 17 chapters, limit 78); call-2 prompt
contains every rule listed in Requirement 2; core-memory prompt matches Requirement 5;
the `llm.py`/`pipeline.py`/`test_llm.py` edits from this ticket are formatting only.

### Findings

**F1 (required): the drop check matches substrings, not names.**
`summarize_chapter/logic.py:61-69` accepts a previous name when it occurs anywhere inside a
new first or second field (`name.casefold() in first.casefold()`). The reviewer ran the
validator directly:

- previous `Lucy | Daughter of Eve | ...` and `Eve | - | ...`, new list without Eve → **accepted**
  (`"eve"` is inside `"daughter of eve"`). Narnia uses "Son of Adam" and "Daughter of Eve" as titles.
- previous `Tumnus` and `Tumnus's father` (u02_p035), new list without Tumnus → **accepted**.

Required: compare whole names. A previous first-field name survives only if it equals,
case-insensitively and trimmed, the first field or one comma-separated entry of the second
field of some new line. Add tests for both cases above (each must be rejected and retried).

**F2 (required): retry test assertion is always true.**
`tests/test_chapter_summarization.py`,
`test_dropping_previous_character_retries_with_rejection_reason_and_recovers`, asserts
`"Jo" in retry_prompt`, but the retry prompt always contains `Jo | - | friend` from the
previous list. Assert the rejection text instead, e.g. `"Rejected: WHO IS WHO dropped earlier
character(s): Jo"`.

**F3 (required, docs): stale descriptions.**
- `README.md:12` still says each extraction receives "the preceding cumulative book summary".
  It now receives the WHO IS WHO after N-1 plus chapter summaries 1..N-1.
- `AI-work/PROJECT_CONTEXT.md:112-117` (Prompt Evidence) calls the v5 two-section prompt
  "the adopted prompt". It was deleted by this ticket; label it as the former prompt.

**F4 (optional, record only): naming and format robustness.**
- Call 1 still labels its context `<previous_book_summary>` and the prompt says "previous book
  summary" (`prompt/summarize_chapter.py`), although the content is now WHO IS WHO plus
  chapter summaries. Works, but the name is misleading.
- A markdown header such as `**WHO IS WHO**` or a markdown table is rejected, and a bulleted
  line `- Mara | ...` is accepted with `- Mara` as the name. A model that prefers markdown
  could spend all three attempts. Watch for this in the live audit before changing code.

### Not measured

No live call was made. Quality of the WHO IS WHO cards, the core memory, the own-words rule,
prompt size (call 1 carries all previous summaries) and latency remain unmeasured until the
live audit proposed under Verification.

### Re-review (2026-10-24): verified

Verification rerun by the reviewer: pytest `152 passed, 5 skipped, 1 warning`; ruff check
`All checks passed!`; ruff format `58 files already formatted`; mypy `Success: no issues found
in 39 source files`; `git diff --check` exit 0; grep for removed identifiers: no matches.

- **F1 fixed.** `validate_who_is_who` (`summarize_chapter/logic.py`) now builds a set of whole
  names from field 1 and the comma-separated entries of field 2 and compares case-insensitively.
  The reviewer's probe now rejects the Eve and Tumnus drops and still accepts a merge that keeps
  the old name as an alias. `test_substring_matches_do_not_hide_dropped_characters_and_trigger_retry`
  covers both cases through the graph (retry, rejection text, recovered list). The call-2 prompt
  now says field 2 is comma-separated, which matches the check.
- **F2 fixed.** The retry test asserts `Rejected: WHO IS WHO dropped earlier character(s): Jo`.
- **F3 fixed.** `README.md:10-14` and the Prompt Evidence section of `PROJECT_CONTEXT.md` are current.
- **F4 still open (optional).** Watch in the live audit: the `<previous_book_summary>` label in
  call 1; markdown headers or tables; aliases separated by `;` instead of `,`. The probe showed a
  `;` list is rejected as a dropped name. The retry tells the model why, but repeated cases cost calls.

Unmeasured, as before: card and core-memory quality, the own-words rule, prompt size and latency.
Next step proposed to the user: a live audit starting with u09-u10.
