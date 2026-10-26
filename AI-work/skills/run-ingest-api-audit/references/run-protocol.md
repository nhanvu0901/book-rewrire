# Run Protocol

## Scope and startup

Use the existing `.venv` through `uv run`; do not install or change dependencies just to audit.
Read the current graph builders and Settings key names, because dated handoffs can be stale.
The runner uses `OPENROUTER_SUMMARIZE_CHAPTER_MODEL` with its summary token cap, and
`OPENROUTER_EXTRACT_CHARACTER_MODEL` with its extraction cap. It does not override reasoning.

The bundled two-chapter smoke story tests a revealed identity, preserved appearance, and an
explicit trait. Book mode calls `load_chapters` to validate the original extraction before
selecting the first N chapters. It never rewrites the extraction or its saved metadata.

Example commands from the repository root:

```bash
# Inspect the planned two-chapter test without calling an API.
uv run python AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py \
  --smoke --output book/diagnostics/api-audit-plan-UNIQUE-ID

# Execute only when the user requested a real API run.
uv run python AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py \
  --book-id narnia-debug --max-chapters 2 --live \
  --output book/diagnostics/api-audit-live-UNIQUE-ID
```

Use a fresh ID for each invocation. Each selected N-chapter run normally performs `3N+1`
summary calls and `4N` extraction calls (`N` character calls, `N` relationship calls,
`N` location calls, and `N` scene-map calls), before application repair attempts. Calls can incur
charges even if a model name contains `free` or an error occurs; use actual returned usage
and cost fields when available instead of making a pricing promise.

The default HTTP timeout is 120 seconds and SDK transport retries are zero. The application
may make up to two extra schema/semantic repair calls. The initiator may set an authorized
timeout with `--timeout-seconds`; do not change a running configuration to rescue a failure.

## Coordination

The initiating model owns the process/session and main report. It should start the runner
using the execution tool's yield/session facility so monitoring can happen concurrently.
Do not launch another full ingest in the monitor or wait synchronously for an entire book.

Spawn Terra with the standalone role file and explicit inputs. Example Codex selection:

```json
{
  "task_name": "terra_api_monitor",
  "model": "gpt-5.6-sol",
  "fork_turns": "none",
  "message": "Read AI-work/agents/terra-api-monitor.md. Repo=<absolute repo>; audit=<exact absolute directory>; parent=<initiator task address>; session=<owned session>; expected scope=<book and selected chapters>. Monitor and escalate evidence; do not fix or rerun."
}
```

Resolve these fields before dispatch; do not literally send placeholders. For Claude, select
the Sonnet 5.5 model identifier from runtime capabilities rather than guessing it. The current
Codex collaboration tool exposes `gpt-5.6-sol`; Claude Sonnet 5.5 is not listed there.

Save actual initiator/monitor identities and session information in `<audit_dir>/coordination.json`
when known. Unknown initiator model identifiers should be recorded as unknown, not inferred
from a role name. No outgoing email/Slack message is part of this workflow.

## Artifacts

| File | Purpose |
| --- | --- |
| `manifest.json` | Scope, source hash, requested models/caps, timeout, and no-Neo4j flag. |
| `progress.json` | Atomic latest state, phase/chapter, HTTP count, expected/completed chapter counts. |
| `events.jsonl`, `run.log` | Timestamped graph progress. |
| `http/http_NNNN.request.json` | Call context, selected request parameters, size/hash; no auth headers or full prompt. |
| `http/http_NNNN.response.json` | Full parsed response or non-JSON text, status, time and call context; API key redacted. |
| `failure.json` | Exception, traceback, stage and last captured HTTP metadata. |
| `summaries/`, `chapters/`, `characters.json`, `relationships.json`, `locations.json` | Production graph outputs for this isolated run. |
| `monitor.md` | Terra's observations; Terra owns only this note. |
| `report.md` | Initiator's analysis and proposed remedies. |

Response hooks persist bodies before `OpenRouterClient` checks finish reasons or parses schemas.
A network failure may have a request record but no response. In that case the last HTTP response
can belong to a previous call; correlate call numbers and request context before attributing it.
The manifest records requested models; returned response models/providers, when present, are
separate evidence. Provider effective caps and missing reasoning usage must remain unknown.

`planned` means dry run, `completed` means graph execution finished, `failed` or `interrupted`
means it did not. For a completed selected scope, compare expected chapter count with both
summary files and character snapshots. No runner stage writes Neo4j.

## Escalation and analysis

Terra alerts on HTTP errors, length finishes, terminal errors, or missing expected artifacts.
If progress is unchanged for several minutes, it reports a possible stall with last timestamps;
the initiator checks its owned session before concluding a hang. The monitor does not kill it.

The initiator checks original source paragraphs and the proposal before accumulation to locate
whether an error arose in source loading, summary content, extraction output, or bookkeeping.
For truncation, compare configured caps with measured completion and reasoning usage. State
what can and cannot be concluded. Do not automatically increase limits or assert reasoning
caused an error when the usage breakdown is absent.

After an actual failure, finish the evidence report before proposing another experiment.
Additional runs or fixes need to fit the user's current request; do not silently turn an audit
into a model comparison, prompt rewrite, or repair task.
