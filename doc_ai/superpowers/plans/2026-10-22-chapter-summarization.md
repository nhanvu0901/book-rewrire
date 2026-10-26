# Chapter Summarization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session.

**Goal:** Summarize chapters sequentially before character extraction, providing each extraction with book context through the preceding chapter.

**Architecture:** Each graph owns its graph, models and logic in one folder. The ingest pipeline prepares validated chapter inputs and one run directory, completes the summary graph, then invokes the character graph with the appropriate earlier summary for each chapter.

**Tech Stack:** Python 3.12, Pydantic, LangGraph, the existing JsonLLM/OpenRouter client, pytest.

**Spec:** The conversation's sequential-summary design and the user's graph-folder convention: `graph/<graph_name>/{graph.py,model.py,logic.py}`. This plan supersedes the earlier folder layout proposed in chat. This task creates the plan only; implementation follows separately.

## Global Constraints

- Code, comments, docstrings and prompts are English; user-facing explanations are Vietnamese.
- Use `summarize_chapter` and `extract_character` as graph folder names.
- Each chapter receives its original source text plus the accumulated summary through the previous chapter.
- One successful summary response contains both a current-chapter summary and an updated cumulative book summary.
- Character extraction retains its existing character records, validation and persistence behavior while receiving earlier book context.
- No checkpoints, resume, relationship verification, new dependencies or automatic factual-verification claims.
- Existing source files, completed book runs and diagnostics remain intact. Do not commit the user's existing refactor as part of this plan.

## Review Focus

- First-chapter input must have empty earlier context; later chapters must use the preceding cumulative summary.
- Precomputing all summaries must not expose current-chapter summaries or future summaries to character extraction.
- Missing or edited chapter files must fail before any LLM call; existing run directories must never be overwritten.
- Invalid summary responses must preserve saved summaries and prevent character extraction and Neo4j writes.
- Both graphs must complete a 17-chapter book with an appropriate recursion limit and numeric source order.

## Target Structure

```text
prompt/
    summarize_chapter.py
    extract_character.py
src/pov_retell/ingest/
    pipeline.py
    source.py
    model.py
    graph/
        summarize_chapter/
            __init__.py
            graph.py
            model.py
            logic.py
        extract_character/
            __init__.py
            graph.py
            model.py
            logic.py
```

`source.py` owns the existing chapter-loading and directory-name validation functions. `ingest/model.py` owns shared input `Chapter` and pipeline output `IngestResult`. Graph-specific response, saved-record and state models stay in their graph's `model.py`.

## Data and Execution Contract

### Summary models

- `SummarizeChapterResponse`: strict Pydantic object with exactly two required, nonblank strings: `chapter_summary` and `book_summary_so_far`.
- `ChapterSummary`: the same fields plus application-assigned `chapter_id`; the LLM does not assign chapter IDs.
- `SummarizeChapterState`: run metadata, title, chapters, output directory, chapter index, accumulated book summary, proposed response and accepted summary records.

`chapter_summary` covers the current chapter only. `book_summary_so_far` updates the previous cumulative summary using the current chapter. Both are returned by one LLM call, without character records as input.

### Summary graph

```text
START -> initialize -> summarize_chapter -> validate_summary -> save_summary
                           ^                                    |
                           +----------- next chapter ------------+
                                                                |
                                                           last -> END
```

The first call receives an empty previous summary. Subsequent calls receive only the preceding accepted cumulative summary and the current original chapter. Save one record atomically before advancing the index and accumulated context.

### Character context

After all summaries are complete, the pipeline constructs `context_by_chapter: dict[str, str]`:

```text
u01 -> ""
u02 -> u01.book_summary_so_far
u03 -> u02.book_summary_so_far
...
u17 -> u16.book_summary_so_far
```

The character graph receives this mapping, not the complete summary records. Its initialization checks that every input chapter has context, the first context is empty, and subsequent contexts are nonblank. Each extraction uses the current original chapter, its mapped previous context and the existing cumulative character records.

### Output

```text
book/ingest/<book_id>/<run_id>/
    summaries/
        u01.summary.json
        ...
        u17.summary.json
    chapters/
        u01.characters.json
        ...
        u17.characters.json
    characters.json
```

The pipeline creates the run directory once, after source validation. Graphs write their own outputs without recreating the run directory; the character graph also maintains the root `characters.json`. A failed summary stage leaves earlier accepted summary files for inspection and does not start character extraction. There is no resume behavior.

## Task 1: Share Validated Inputs and Run Preparation

**Files:** Create `ingest/source.py`; modify `ingest/model.py`, `ingest/pipeline.py`, `graph/extract_character/{graph.py,model.py,logic.py}`, `tests/test_character_ingest.py` and `tests/test_character_recovery.py`.

**Interfaces:** Preserve `load_chapters(extracted_dir: Path, book_id: str) -> tuple[str, list[Chapter]]` and `validate_directory_name(value: str) -> None` in `source.py`. Change the character graph builder to `build_extract_character_graph(llm: JsonLLM, on_step: Callable[[str], None] | None = None)`; its invocation state supplies validated chapters, title, output directory and run metadata.

- [x] Adapt the independent graph test to prepare validated chapter inputs and a run directory explicitly. Run it before changing the builder and confirm the old interface rejects the new invocation.
- [x] Move shared source functions and `Chapter` without changing their behavior. Have `ingest_book` validate source and create the run directory; replace the graph's source-loading node with state initialization.
- [x] Preserve the tests for invalid source files, existing-run protection, ID resolution, alias retention and failed chapter persistence. Run `pytest -q tests/test_character_ingest.py tests/test_character_recovery.py`; all must pass.

## Task 2: Implement the Independent Summary Graph

**Files:** Create `prompt/summarize_chapter.py`, `graph/summarize_chapter/{__init__.py,graph.py,model.py,logic.py}` and `tests/test_chapter_summarization.py`.

**Interfaces:** `build_summarize_chapter_graph(llm: JsonLLM, on_step: Callable[[str], None] | None = None)` consumes prepared state and returns accepted `ChapterSummary` records. `summarize_chapter(llm: JsonLLM, title: str, chapter: Chapter, previous_book_summary: str) -> SummarizeChapterResponse` makes the existing validated JSON call. `save_summary(path: Path, summary: ChapterSummary) -> None` writes atomically.

- [x] Write failing tests asserting an empty first context, the exact preceding cumulative context on the second call, current source paragraph labels in each prompt, and distinct saved current/cumulative summaries.
- [x] Write failure tests using the existing OpenRouter test transport: blank or malformed responses exhaust the existing retry policy; prior accepted files remain unchanged and no file is written for the failed chapter. Add a 17-chapter numeric-order test.
- [x] Implement the strict models, prompt, logic and graph. The prompt retains explicitly referenced names and significant events, separates narration from reported beliefs, updates disproven beliefs and forbids outside knowledge. It requests no character IDs, attributes or relationship records.
- [x] Run `pytest -q tests/test_chapter_summarization.py`. Structural validation must not be described as proof of factual correctness.

## Task 3: Integrate Prior Context into Character Extraction

**Files:** Modify `ingest/pipeline.py`, `ingest/model.py`, `graph/extract_character/{graph.py,model.py,logic.py}`, `prompt/extract_character.py`, relevant ingest/CLI tests and `README.md`.

**Interfaces:** Add required `previous_book_summary: str` to `logic.extract_characters(...)` and `context_by_chapter` to `ExtractCharacterState`. Add `summaries_dir: Path` to `IngestResult`. Preserve the `ingest_book(...)` and CLI command interfaces.

- [x] Add an integration test with three distinct summary responses followed by three character responses. Assert all summaries run first, then chapter 1 extraction receives empty context, chapter 2 receives only context after chapter 1, and chapter 3 receives only context after chapter 2. Unique future-summary markers must be absent from earlier extraction prompts.
- [x] Add tests asserting missing context is rejected before extraction calls, failed summarization prevents character calls and writer calls, and Neo4j receives characters only after both stages finish.
- [x] Invoke summary then extraction graphs in `ingest_book`, using `max(25, len(chapters) * 4 + 10)` for each. Build the context mapping from accepted summaries in source order; never substitute the final cumulative summary for earlier chapters.
- [x] Add a clearly delimited earlier-summary block to the character prompt and include that summary in the prompt's allowed-input instructions. Describe it as fallible context: retain uncertainty and use the current chapter to resolve contradictions. Keep the existing character JSON schema and resolution rules.
- [x] Update existing fixtures to supply summary responses where they exercise `ingest_book`. Preserve focused extraction-graph tests with explicitly supplied contexts. Update saved-file counts and document the summary output directory and new stage logs.
- [x] Run `pytest -q`, `ruff check src prompt tests`, `mypy src` and `git diff --check`. Report skipped external integration tests separately. Do not launch a new live multi-run benchmark as part of unit verification.

## Completion Criteria

- Both graphs and all graph-specific models/logic follow the requested folder convention.
- One normal ingest uses one summary call and one character call per chapter, excluding retries.
- Source validation, run protection and character persistence regressions stay covered.
- Tests demonstrate no current/future-summary leakage and no Neo4j writes after summary failure.
- No claim of improved extraction accuracy until a separate real-output comparison is performed.
