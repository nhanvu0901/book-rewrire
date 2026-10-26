# Validation Record

The real historical truncation run was used as an offline baseline. Terra on `gpt-5.6-sol`
correctly separated observed saved progress from an inferred failing chapter, but could not
determine token allocation because the application had not captured the failed response.
This is the operational gap the diagnostic runner addresses; no baseline root cause was invented.

The runner tests were written and run before its implementation. They initially failed
because the runner did not exist. The tests then passed for:

- Capturing a truncated HTTP response, its usage and partial content before the production client raises.
- Redacting the configured API key and omitting authorization headers.
- Making zero requests and no database writes in dry mode.
- Refusing an existing output directory without overwriting it.
- Preserving unknown usage in failure reports.

These are offline tests using a mock HTTP transport. They do not claim real API success,
model availability, story accuracy, or an actual live monitoring session.

Run them from the repository root:

```bash
uv run pytest AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py -q
```

On 2026-10-24, a fresh `gpt-5.6-sol` Terra monitor used the completed skill on an offline
synthetic failure fixture. It immediately escalated extraction u02, HTTP 200 with `length`,
2/2 summaries and 1/2 character snapshots. It cited measured completion/reasoning usage,
kept the unmatched effective-cap cause unknown, wrote only `monitor.md`, and did not retry
or modify the application. This validates the terminal escalation scenario, not a live API run.

A separate `gpt-5.6-sol` context-maintainer agent verified current source paths/configuration
and updated only `AI-work/PROJECT_CONTEXT.md`. The initiating agent reviewed that update.

Final offline checks for this task: 140 passed, 5 skipped across application and skill-local
tests; skill Ruff, runner mypy, and skill frontmatter validation passed. Real API success and
long-running live monitoring remain untested during this skill-creation task.
