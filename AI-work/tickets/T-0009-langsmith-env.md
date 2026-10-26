---
id: T-0009
title: "LangSmith tracing works for `pov ingest` without an env-file flag"
status: draft
owner: unassigned
priority: low
created: 2026-10-25
updated: 2026-10-25
depends_on: []
---

# T-0009: LangSmith tracing works for `pov ingest` without an env-file flag

## Background

The full run `run_2ae27f27f5d34937a54c8c81ed93303e` sent no traces to LangSmith, although
`.env` sets `LANGSMITH_TRACING=true` and the project.

- The PyCharm configuration "dev" runs `.venv/bin/pov ingest narnia-debug --no-neo4j` with
  no env file.
- `Settings` reads `.env` into its own fields only, not into `os.environ`. LangSmith reads
  `os.environ`.
- Verified on 2026-10-24: in such a process `langsmith.utils.tracing_is_enabled()` is
  `False`; with `LANGSMITH_TRACING` in the environment it is `True`.

Workaround without code: set the env file in the PyCharm configuration, or run
`uv run --env-file .env pov ingest narnia-debug --no-neo4j`.

## User decisions

None yet. **Draft:** the user chooses between this ticket and the workaround.

## Requirements (if approved)

1. At CLI start, copy `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` and, if
   present, `LANGSMITH_ENDPOINT` from `.env` into `os.environ`, only when they are not already
   set. Never print or log the key.
2. Without these values in `.env`, behavior is unchanged and nothing fails.
3. Offline tests: values are exported, existing environment values win, nothing is exported
   when absent, and the key never appears in output.
4. README: one line on tracing.

## Acceptance criteria

- [ ] Requirements 1–3 proven by offline tests. Verification commands pass.

## Out of scope

- Trace content, run names, LangSmith projects.

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/mypy src/pov_retell
```

## Completion report

_Filled by the implementer._

## Review

_Filled by the product manager._
