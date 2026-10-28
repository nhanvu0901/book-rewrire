---
id: T-0012
title: Running lists treat straight and curly quotes as the same name
status: done
owner: Antigravity (Gemini 4 Argon)
branch: ticket/T-0012-quote-normalization
priority: high
created: 2026-10-27
updated: 2026-10-27
depends_on: []
---

# T-0012: Running lists treat straight and curly quotes as the same name

## Background

The summary run `book/ingest/harry-potter-1/run_67acaa7a1f624a548e0ca9d529bddda5`
(2026-10-27) saved `u01` to `u05` and then stopped at `u06` with:

```text
no valid WHERE IS WHERE after 3 attempts: WHERE IS WHERE dropped earlier place(s):
Madam Malkin’s Robes for All Occasions
```

Evidence:

- In `u05.summary.json` the model wrote the place name with a curly apostrophe (U+2019)
  and its other name with a straight one:
  `Madam Malkin’s Robes for All Occasions | Madam Malkin's | ...`.
  The same file also has `King's Cross | King’s Cross`, so the model mixes both forms.
- `validate_running_list` (`src/pov_retell/ingest/graph/summarize_chapter/logic.py:58-88`)
  compares names after `casefold()` only. `'` (U+0027) and `’` (U+2019) are different, so a
  place kept with a straight apostrophe counts as dropped.
- The retry message repeats the curly name, and the model kept answering with the straight
  one. All 3 attempts (`MAX_RETRIES = 2`, `src/pov_retell/infrastructure/llm.py:15`) failed.
- Reproduced offline by the PM, calling the validator directly with
  `previous = "Madam Malkin’s Robes for All Occasions | Madam Malkin's | robe shop"`:

  | New list | Result |
  | --- | --- |
  | `Madam Malkin's Robes for All Occasions \| - \| robe shop` | rejected |
  | `Madam Malkin’s Robes for All Occasions \| - \| robe shop` | accepted |

The pipeline cannot resume, so one such mismatch loses the whole run. WHO IS WHO uses the
same function and can fail the same way, for example on a name like `O’Brien`.

## User decisions

- 2026-10-27: option 1. Normalize quote characters when comparing names, in both WHO IS
  WHO and WHERE IS WHERE, and add a test for the Malkin case.

## PM recommendations

- Normalize only for **comparison**. Store the lines as the model wrote them, so no saved
  text changes.
- Map at least `’ ‘ ‛ ʼ ′` to `'` and `“ ” „ ″` to `"`. Also collapse runs of whitespace,
  as `identity.normalized` already does.
- The retry message should still name the missing entries as written in the previous list.

## Requirements

1. Add one small name-key helper used by `validate_running_list` for both the surviving
   names and the previous names. It casefolds, maps the quote characters above to their
   ASCII forms and collapses whitespace.
2. A previous entry counts as kept when its key matches the key of any first-field name or
   any comma-separated other name in the new list. This is the current rule, with the
   new key.
3. The returned text is unchanged: same lines, same characters, as today.
4. Behavior for blank, malformed or truly dropped entries is unchanged.

## Acceptance criteria

- [x] A test with previous `Madam Malkin’s Robes for All Occasions | Madam Malkin's | ...`
      and new `Madam Malkin's Robes for All Occasions | - | ...` passes
      `validate_where_is_where`.
- [x] The reverse direction (straight before, curly after) also passes.
- [x] A WHO IS WHO test with a curly apostrophe or curly double quote in a name passes the
      same way.
- [x] A test proves that the returned text keeps the model's original characters.
- [x] A test where the entry is really missing still raises
      `dropped earlier place(s)` / `character(s)`.
- [x] The existing tests in `tests/test_chapter_summarization.py` pass unchanged.
- [x] The full offline suite, `ruff check`, `ruff format --check` and `mypy` pass.

## Out of scope

- Accepting a new list that keeps only an earlier other name (option 2), and resuming or
  saving a failed chapter (option 3).
- Prompt changes, model or provider settings, `MAX_RETRIES`.
- Character and location extraction code (see Open questions).
- Rewriting existing run data.

## Files likely touched

- `src/pov_retell/ingest/graph/summarize_chapter/logic.py`
- `tests/test_chapter_summarization.py`

## Verification

```bash
uv run pytest -q
uv run pytest -q tests/test_chapter_summarization.py
uv run ruff check . && uv run ruff format --check . && uv run mypy src
git diff --check
```

No live API calls or Neo4j writes. The user decides when to rerun the real summary graph.

## Open questions

- `src/pov_retell/ingest/graph/extract_character/identity.py:7-12` (`normalized`,
  `appears_in_source`) checks that names appear in the chapter text, without quote
  normalization. The Harry Potter chapter units use only curly apostrophes
  (`book/extracted/harry-potter-1/units/05_*.txt`: 266 curly, 0 straight). A straight-quote name
  from the extract model may therefore be rejected there in the same way. Should this
  ticket use the same helper there? Default if nobody answers: no; the PM writes a separate
  ticket after the user decides.

## Completion report

- **Changes**:
  - `src/pov_retell/ingest/graph/summarize_chapter/logic.py`:
    - Defined `_QUOTE_TRANSLATION` mapping `’ ‘ ‛ ʼ ′` to `'` and `“ ” „ ″` to `"`.
    - Implemented `_name_key(text: str) -> str` which applies translation, collapses whitespace via `" ".join(text.split())`, and calls `.casefold()`.
    - Updated `validate_running_list` to map surviving names and previous first-field names using `_name_key`.
    - Preserved exact returned text formatting and line order.
  - `tests/test_chapter_summarization.py`:
    - Added 5 new unit tests:
      - `test_where_is_where_accepts_quote_normalized_survival_malkin_case`
      - `test_where_is_where_accepts_quote_normalized_survival_reverse_case`
      - `test_who_is_who_accepts_quote_normalized_apostrophe_and_double_quote`
      - `test_running_list_returns_models_original_characters_unmodified`
      - `test_running_list_raises_when_entry_truly_missing_even_with_quotes`
- **Commit hash**: `66fbabd`
- **Verification results**:
  - `uv run pytest -q`: `314 passed, 4 skipped, 1 warning` (pre-existing LangSmith deprecation warning).
  - `uv run pytest -q tests/test_chapter_summarization.py`: `56 passed, 1 warning`.
  - `uv run ruff check src tests AI-work/skills/run-ingest-api-audit`: All checks passed!
  - `uv run ruff format --check src tests AI-work/skills/run-ingest-api-audit`: 71 files already formatted.
  - `uv run mypy src`: Success: no issues found in 44 source files.
  - `git diff --check`: clean (0 errors).
- **Deviations**: None.
- **Follow-ups**: The question in Open questions remains tracked for PM and user consideration regarding `identity.py`.

## Review

_Filled by the product manager: verdict, evidence per criterion, findings with file:line._
