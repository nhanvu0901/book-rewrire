# Restore LLM Character Extraction Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Work in the user's current workspace and preserve unrelated uncommitted changes. Do not commit or run live API requests for this restoration.

**Goal:** Restore summarization followed by full-profile character extraction with a general LLM.

**Architecture:** Keep the existing graph-local folders. Run the summary graph first, then pass each character extraction call the original chapter, cumulative character profiles, and the book summary through the preceding chapter. Python retains ID assignment, explicit merges, nonempty profile preservation, JSON persistence, and the final Neo4j write.

**Tech Stack:** Python, Pydantic, LangGraph, OpenRouter, pytest.

**Spec:** `AI-work/handoffs/HANDOFF_2026-10-22.md`, sections 9–10, and the user's request to restore the previous workflow.

## Global Constraints

- Responses in Vietnamese; code and prompts in English.
- No model defaults or model changes in `.env`; the user chooses better models.
- No ScaleDown attribute calls in ordinary ingestion; retain the experimental adapter and artifacts.
- Preserve run directories, graph-local organization, and the selected Neo4j Character properties.
- No checkpoint, relationship verification, or new graph edges.
- Personality traits must be explicitly described, not inferred from actions.

## Review Focus

- Previous summary context must exclude the current and future chapters.
- Renames and merges must retain aliases, complementary facts, and relationship targets.
- Partial/empty updates must preserve absent characters and existing facts.
- Invalid identity IDs must retry before saving; unknown relationship references must remain proposals without guessed IDs.
- Summary/extraction failures must retain completed files and prevent the final Neo4j write.

## Task 1: Restore full-profile extraction

**Files:** `prompt/extract_character.py`; `src/pov_retell/ingest/graph/extract_character/{model,logic,graph}.py`; `tests/test_character_{ingest,recovery}.py`.

**Interfaces:** `build_extract_character_graph(llm, on_step=None)` consumes chapters and summaries in state; `ExtractCharacterResponse` contains full character proposals and explicit merge IDs. Graph output retains cumulative records, redirects, pending relationships, and output directory.

- [x] Add failing tests for full profiles, renames, merges, absent records, relationship remapping, and invalid ID recovery.
- [x] Run the tests and observe failure against the hybrid implementation.
- [x] Restore the full-profile prompt and response model; reuse the existing identity merge helper and preserve source checks for new traits.
- [x] Replace per-character entity nodes with `extract_characters -> validate_characters -> save_json`.
- [x] Save raw `uNN.proposed.json` and cumulative `uNN.characters.json`, plus final records and redirects.

## Task 2: Restore summaries and CLI wiring

**Files:** `src/pov_retell/ingest/pipeline.py`; `src/pov_retell/cli.py`; `tests/test_summary_ingest.py`; `tests/test_character_openrouter_integration.py`; `README.md`; `.env.example`.

**Interfaces:** `ingest_book(..., summary_llm: TextLLM, ...)` replaces the active `attribute_llm` argument. CLI constructs extraction and summary clients using their existing settings.

- [x] Add failing tests for saved summaries, previous-only context, model selection, and failures before Neo4j writing.
- [x] Run tests and observe the expected failure.
- [x] Enable the summary graph and pass its results to character extraction, validating chapter correspondence before calls.
- [x] Update CLI, integration test, and current documentation; leave model values untouched.
- [x] Run offline pytest, Ruff, mypy, and diff whitespace checks. Review the changed code against the constraints.

## Execution Notes

- Initial baseline: 136 passed, 5 skipped; Ruff and mypy clean.
- Execute in place because the requested restoration concerns the user's existing uncommitted working tree. Do not reset it to a commit or move the user to another worktree.

- Restoration checks: targeted summary/character tests passed (26 tests); full offline suite passed before final review (130 passed, 5 skipped).
- No live API calls, model setting changes, data deletion, or commits were performed.

## Final Verification

- A separate review reproduced three issues: overwriting complementary descriptions, overwriting merged relationship facts, and matching unknown permanent targets to newly allocated IDs.
- Each issue received a failing regression test, then a fix; the three regressions now pass.
- Final offline suite: 133 passed, 5 skipped. Ruff, mypy (37 source files), and `git diff --check` passed.
- Retained the experimental attributes-model setting and adapter; ordinary ingestion uses only the summary and character models.
