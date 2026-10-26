# Character Identity and Attribute Extraction Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for implementation in this session.

**Goal:** Resolve character identities with a general LLM, then extract explicit chapter attributes with ScaleDown for each relevant character.

**Architecture:** The character graph resolves chapter identities against a compact accumulated roster, assigns permanent IDs and applies explicit merges, extracts each active character's attributes, then saves cumulative records. A dedicated structured extraction method sends original chapter text through OpenRouter provider options without JSON mode or conversational repair. Summarization remains disabled.

**Tech Stack:** Python 3.12, Pydantic, LangGraph, OpenAI SDK, OpenRouter, pytest.

**Spec:** Approved design in the current conversation: chapter loop, identity resolution and aliases, application IDs, per-character ScaleDown extraction, explicit personality descriptions only.

## Global Constraints

- Code, comments, docstrings and prompts are English; user-facing discussion is Vietnamese.
- Keep all character graph models and domain logic in its existing graph folder.
- No checkpoints, no summary context, no relationship verification graph or edges.
- Preserve unrelated workspace edits and existing saved book data; do not commit.
- Current chapter text is the extraction source; roster names are search criteria, not evidence.

## Review Focus

- An absent character and missing attributes preserve earlier accepted data.
- Merges preserve aliases, profile data, relationship targets and transitive ID redirects.
- Identical names belonging to different people leave ambiguous relationship names unresolved.
- Malformed structured responses and upstream failures do not save an incomplete chapter or write Neo4j.
- ScaleDown retries always retain the original source text and never send JSON mode or sampling options.

## Tasks

- [x] Add failing tests for structured OpenRouter extraction and identity/profile graph behavior.
- [x] Implement complete_entities(text, entities, schema), structured_result parsing and bounded validation retries.
- [x] Replace character prompt and models with compact identity proposals plus explicit profile schemas.
- [x] Implement identity application, stable ID redirects, focused extraction, profile accumulation and pending relationships.
- [x] Wire graph, pipeline, CLI and required per-role model settings; retain summary graph disabled.
- [x] Update regression tests and README, verify full suite, Ruff, mypy, and diff checks.
- [x] Run a minimal real ScaleDown smoke test to verify nested provider options; review the final implementation.

## Execution Notes

- User explicitly authorized implementation after reviewing the design; continue inline without another approval gate.
- Work in the current dirty workspace to preserve the user's active PyCharm paths and ongoing refactor.
- OPENROUTER_EXTRACT_CHARACTER_MODEL selects the identity LLM. OPENROUTER_CHARACTER_ATTRIBUTES_MODEL selects ScaleDown.
- Attribute proposals retain raw aliases/relationship names in chapter diagnostics; only identity-approved aliases enter the accepted roster.

- Live findings: OpenRouter accepts nested entity objects. Description-string arrays returned [{}]; arrays of objects returned correct values. Provider-facing aliases and traits now use object arrays and are normalized before saving. Explicit typed schema objects inside entities were echoed as data and are not used.
- Review fixes: retain complementary merged descriptions; carry short source-backed identifying phrases and skip indistinguishable shared-name profiles.
- Live first request timed out at 45 seconds; subsequent flat, nested and focused integration calls succeeded. No SDK retry policy was changed based solely on that transient timeout.
- Verification: real focused ScaleDown integration passed, and the full real two-chapter identity/merge/profile integration passed (11.40 seconds). These use synthetic text and no Neo4j writes.
- Additional review regression: historical identity hints must not disambiguate an ambiguous current chapter; current chapter names/context now control extraction eligibility and focus.
