---
id: T-0013
title: WHO IS WHO and WHERE IS WHERE return changes only, merged by a reducer
status: done
owner: Antigravity (Gemini 4 Argon)
branch: ticket/T-0013-changes-only-lists
priority: medium
created: 2026-10-27
updated: 2026-10-28
depends_on: [T-0012]
---

# T-0013: WHO IS WHO and WHERE IS WHERE return changes only, merged by a reducer

## Background

`SummarizeChapterState` (`src/pov_retell/ingest/graph/summarize_chapter/model.py:31`) has no
reducers, so every key is replaced:

- `summaries` is appended by hand in `save_summary` (`graph.py:61`).
- `who_is_who` and `where_is_where` are rewritten in full by the LLM for every chapter
  (`logic.py:110-158`). The new text then replaces the old text (`graph.py:59-60`), and
  `validate_running_list` rejects a reply that left out an earlier entry.

The rewritten lists grow every chapter. Measured in
`book/ingest/harry-potter-1/run_67acaa7a1f624a548e0ca9d529bddda5/summaries/`:

| Chapter | WHERE IS WHERE | WHO IS WHO |
| --- | --- | --- |
| u01 | 22 lines, 3,318 chars | 15 lines, 1,480 chars |
| u03 | 55 lines, 7,887 chars | 25 lines, 2,913 chars |
| u05 | 82 lines, 11,630 chars | 34 lines, 4,507 chars |

By u05 the model copies about 16k characters per chapter, mostly unchanged, and every copy
can go wrong. The run failed at u06 for that reason (see T-0012). Precedents for
"changes only": T-0004 relationships in this project, LangGraph's `add_messages` (upsert
by ID), and LangChain's Trustcall (JSON Patch on existing data).

## User decisions

- 2026-10-27: do **not** change `summaries`. It stays a plain list appended in `save_summary`.
- 2026-10-27: WHO IS WHO and WHERE IS WHERE should not make the LLM rewrite the whole list
  each chapter. The LLM returns only what changed, and the state merges it.
- 2026-10-27: the user implements this ticket. Reference code with a fake-LLM demo:
  `scratch/changes_only_lists.py` (ruff and mypy clean; not application code).

## PM recommendations

- Key entries by short IDs that Python assigns (`C001` for characters, `P001` for places),
  not by names. Names break on spelling and quote differences (T-0012).
- The LLM sees the full current list with IDs. It returns `add` (new entries) and
  `update` (existing ID → rewritten entry). There is no `delete`: entries are never
  dropped.
- Merging uses one custom reducer, `upsert_cards(current, update) -> {**current, **update}`.
- Keep the saved `uNN.summary.json` text format (`name | other names | card`) unchanged,
  so the extract graph and its prompts do not change. IDs appear only in the prompts and
  in state.
- Input tokens do not drop, because the model still reads the whole list. Output tokens
  drop, and so does the copy-error risk. The trade-off: a forgotten update is silent,
  where a dropped entry is loud today.

## Requirements

1. `summaries` and its handling in `save_summary` stay unchanged.
2. Add a `Card` model (`name`, `other_names`, `card`) and a `CardChanges` model (`add`,
   `update`) with strict schemas.
3. `who_is_who` and `where_is_where` in state become
   `Annotated[dict[str, Card], upsert_cards]`.
4. The update prompts ask for `CardChanges` JSON instead of the full list. The card-text
   rules from T-0002 and T-0006 still apply to every added or updated card: at most 30
   words, lasting state, no chapter references, no event logs.
5. Python validates a reply before returning it to the reducer, with the existing retry
   loop (`MAX_RETRIES`):
   - an `update` ID that does not exist is rejected;
   - an `add` whose name or other name already belongs to an existing entry is rejected,
     with the message "use update with <ID>". Compare with the T-0012 name key;
   - blank fields are rejected.
6. Python assigns IDs to added entries in order, continuing from the highest existing ID.
7. A `render` helper writes the cards as today's text lines (no ID) for the saved summary
   and `BookMemory`. A second form with IDs is used inside the update prompts.
8. Graph order by default: `summarize_chapter` → `update_who_is_who` →
   `update_where_is_where` → `validate_summary` → `save_summary`, as separate nodes.
   `SUMMARY_NODES_PER_CHAPTER` and the recursion limit follow the new node count.

## Acceptance criteria

- [x] With a fake LLM over 3 chapters, `final["summaries"]` still has `u01`, `u02`, `u03`
      once each, in order.
- [x] A fake chapter that returns one `update` and no `add` keeps every earlier card, and
      changes only that card.
- [x] Unknown update IDs and duplicate-name adds are retried and then raise `LLMError`
      after `1 + MAX_RETRIES` attempts.
- [x] IDs are stable across chapters and new IDs continue the sequence.
- [x] Saved `uNN.summary.json` keeps the `name | other names | card` lines. The extract
      graph tests pass unchanged.
- [x] The full offline suite, `ruff check`, `ruff format --check` and `mypy` pass.

## Out of scope

- Character and location extraction (T-0003, T-0007, T-0008).
- Model choice and provider settings, apart from what Open question 4 decides.
- Resuming a failed run.
- Rewriting existing run data.

## Files likely touched

- `src/pov_retell/infrastructure/llm.py`
- `src/pov_retell/ingest/graph/summarize_chapter/model.py`
- `src/pov_retell/ingest/graph/summarize_chapter/graph.py`
- `src/pov_retell/ingest/graph/summarize_chapter/logic.py`
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_who_is_who.py`
- `src/pov_retell/ingest/graph/summarize_chapter/prompt/update_where_is_where.py`
- `src/pov_retell/ingest/pipeline.py`
- `tests/test_chapter_summarization.py`

## Verification

```bash
uv run pytest -q
uv run ruff check src tests AI-work/skills/run-ingest-api-audit && uv run ruff format --check src tests AI-work/skills/run-ingest-api-audit && uv run mypy src
git diff --check
```

No live API calls or Neo4j writes. After review, the user may run one real summary run
and compare it with `run_67acaa7a1f624a548e0ca9d529bddda5`: output size per chapter and
card quality.

## Open questions

1. Run `update_who_is_who` and `update_where_is_where` in parallel (fan-out, then join
   before `validate_summary`)? Default: no, sequential.
2. Add a `merge` operation (two entries turn out to be one, such as a stranger revealed
   as a known character)? Default: no. The model updates the surviving card and adds the
   other name to it, and the duplicate stays.
3. Write IDs into the saved summary files as well? Default: no, to keep the format that
   the extract graph reads.
4. The summary graph uses `TextLLM` (free text). `CardChanges` needs JSON output. Reuse
   the JSON client from T-0005 with the summary model, or ask for JSON in plain text and
   parse it with Pydantic? Default: the T-0005 JSON client with the summary model, and no
   new settings.

## Completion report

### Changes
1. **Models and Reducers (`src/pov_retell/ingest/graph/summarize_chapter/model.py`)**:
   - Added `Card`, `CardUpdate`, and `CardChanges` models with `extra="forbid", strict=True`.
   - Added LangGraph reducer `upsert_cards(current, update) -> {**current, **update}`.
   - Updated `SummarizeChapterState` with `who_cards: Annotated[dict[str, Card], upsert_cards]` and `where_cards: Annotated[dict[str, Card], upsert_cards]`.
   - Preserved `summaries: list[ChapterSummary]` as a plain list appended by `save_summary`.
2. **Prompts (`src/pov_retell/ingest/graph/summarize_chapter/prompt/`)**:
   - `update_who_is_who.py` & `update_where_is_where.py`: updated opening instructions and closing output format to request JSON `CardChanges` (`{"add": [...], "update": [...]}`). Removed the requirement to repeat every previous character/place from the prompt.
   - Updated merge instructions to update the existing card and append alternative names.
3. **Logic (`src/pov_retell/ingest/graph/summarize_chapter/logic.py`)**:
   - Added `render_cards(cards, *, with_ids: bool)`: outputs cards with IDs (`C001 | Name | ...`) for prompts, or without IDs (`Name | ...`) for saved summary files and `BookMemory`.
   - Added `check_changes(changes, cards)`: rejects unknown `update` IDs, duplicate update IDs, and `add` operations attempting to re-add existing names (supporting T-0012 full quote normalization via `name_key`), raising `ValueError` to trigger the retry loop.
   - Added `changes_to_update(changes, cards, prefix)`: assigns new sequential IDs (`C001`, `C002`, `P001`, `P002`, ...) continuing from the highest ID in state.
   - Added `update_cards(...)`: formats inputs and delegates JSON parsing and validation to `llm.complete_json`.
   - Refactored `summarize_chapter(...)` to solely produce the plain-text chapter summary.
4. **Graph & Nodes (`src/pov_retell/ingest/graph/summarize_chapter/graph.py`)**:
   - Separated chapter processing into 5 nodes per chapter: `summarize_chapter` -> `update_who_is_who` -> `update_where_is_where` -> `validate_summary` -> `save_summary`.
   - Updated `SUMMARY_NODES_PER_CHAPTER = 5` and updated recursion limits accordingly.
   - In `validate_summary`, generated `ChapterSummary` by rendering cards with `with_ids=False`.
5. **Protocols & Pipeline (`src/pov_retell/infrastructure/llm.py`, `src/pov_retell/ingest/pipeline.py`)**:
   - Added `SummarizeLLM(TextLLM, JsonLLM, Protocol)` implemented by `OpenRouterClient` and `ScriptedLLM`.
6. **Tests & Test Suites**:
   - Comprehensively updated `tests/test_chapter_summarization.py` to cover 3-chapter order, single-card updates without additions, unknown ID rejection/retry, duplicate-add rejection/retry with quote normalization, ID stability across chapters, and 17-chapter execution.
   - Updated `summary_client` and test fixtures in `tests/test_character_ingest.py`, `tests/test_location_ingest.py`, `tests/test_relationship_ingest.py`, and `tests/test_summary_ingest.py` to use `CardChanges` dicts.

### Criterion-by-criterion evidence
- **Criterion 1 (3 chapters order)**: `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory` passes; `final["summaries"]` contains `u01`, `u02`, `u03` in order with chapter index 3.
- **Criterion 2 (Update-only preserves cards)**: `test_fake_chapter_update_only_preserves_earlier_cards` passes; earlier card `C002` (Jo) is preserved intact while `C001` (Mara) is updated.
- **Criterion 3 (Unknown IDs and duplicate adds retry and raise `LLMError`)**: `test_unknown_update_id_retries_and_raises_after_max_retries` and `test_duplicate_name_add_retries_and_raises_after_max_retries` verify rejection with exact reasons and failure after `1 + MAX_RETRIES` attempts. `test_unknown_update_id_retries_and_recovers` and `test_quote_normalized_duplicate_name_add_retries_and_recovers` verify recovery after rejection.
- **Criterion 4 (Stable IDs and sequence continuation)**: `test_ids_are_stable_across_chapters_and_continue_sequence` passes; `C001`, `C002` remain stable across an update-only chapter and the next addition is assigned `C003`.
- **Criterion 5 (Saved files keep text format without IDs)**: Verified in `test_summary_graph_passes_previous_context_and_saves_chapter_and_book_memory`; `uNN.summary.json` and `book_memory.json` contain `name | other names | card` lines without IDs; all downstream extract tests pass.
- **Criterion 6 (Full test suite and linters pass)**:
  - `uv run pytest -q`: 293 passed, 4 skipped in 1.48s.
  - `uv run ruff check src tests AI-work/skills/run-ingest-api-audit`: All checks passed.
  - `uv run ruff format --check src tests AI-work/skills/run-ingest-api-audit`: 71 files already formatted.
  - `uv run mypy src`: Success: no issues found in 44 source files.
  - `git diff --check`: Clean, no whitespace issues.

### Deviations
None.

### Follow-ups
None. Ready for Claude product manager review.

## Review

_Filled by the product manager: verdict, evidence per criterion, findings with file:line._
