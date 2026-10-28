---
name: run-ingest-api-audit
description: Use when the user requests a real API test or monitored run of book-clone chapter summarization and character extraction, including truncation, provider failures, stalls, or saved-output quality investigation.
---

# Run Ingest API Audit

## Contract

The initiating higher-capability model owns launch, analysis, and the user report. Terra is
the observer. An audit produces evidence and suggested remedies; it does not repair the app.
Read root `AGENTS.md` and `AI-work/PROJECT_CONTEXT.md` first.

Creating or reading this skill is not a request to call APIs. When the user requests execution,
use the authorized scope: two synthetic chapters for a smoke test, or the specified book/chapter
limit. A full-book run must match the requested scope. Existing authorization need not be requested again.

## Run

1. Read [the protocol](references/run-protocol.md). Verify current graph/config interfaces.
   Choose a unique output path under `book/diagnostics/`; never overwrite another run.
2. Start the bundled runner as an owned background/session process:

   ```bash
   uv run python AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py \
     --smoke --live --output book/diagnostics/api-audit-UNIQUE-ID
   ```

   For book input replace `--smoke` with `--book-id narnia-debug`; add `--max-chapters N`
   when bounded. Without `--live`, the runner only plans: no API calls or database writes.
   It tests production summary/character graphs, not the CLI's final Neo4j persistence.
3. Immediately spawn the monitor using [the Terra role](../../agents/terra-api-monitor.md).
   On Codex select `gpt-5.6-sol`, task `terra_api_monitor`, fresh context. On Claude select
   Sonnet 5.5 only if explicitly exposed. Supply the exact audit path, scope, parent address,
   and process/session ID. If delegation/model selection is unavailable, disclose it and
   monitor in the initiator; never claim an unavailable model ran.
4. The initiator retains the process handle, checks exit status, and gives user progress
   updates. Terra observes artifacts every 30–60 seconds and immediately escalates anomalies.
   Neither role launches extra retries, changes models/limits, or fixes application files.
5. On failure, inspect recorded HTTP evidence before naming a cause. On completion, verify
   artifact counts and review character/summary claims against original paragraphs. Valid
   JSON and exit 0 establish execution, not factual accuracy.
6. Write `<audit_dir>/report.md` using [the report contract](references/report-contract.md).
   Summarize findings and proposed fixes in Vietnamese for the user. Stop before implementation.

## Evidence

The runner captures requests without headers/prompts, full response bodies with key redaction,
usage, finish reasons, phase/chapter, timestamps, and failures before production parsing.
SDK transport retries are disabled; existing application semantic repairs remain observable.
Model values and reasoning behavior come from current production code/settings, unchanged.
Missing usage stays unknown. Keep raw artifacts in the ignored data directory.

For offline validation, run the skill-local pytest file; no real API is needed. See
[validation notes](references/validation.md). Follow the root context-maintenance trigger
only when medium code changes occur; an audit does not authorize such changes.
