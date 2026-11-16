---
id: T-0014
title: Retry overloaded or unreachable providers with exponential backoff
status: done
owner: Claude (at the user's request)
branch: ticket/T-0014-transient-retry
priority: high
created: 2026-10-28
updated: 2026-10-28
depends_on: [T-0013]
---

# T-0014: Retry overloaded or unreachable providers with exponential backoff

## Background

A real `pov ingest harry-potter-1` run on 2026-10-28 stopped with:

```text
Error: OpenRouter request failed: Upstream error from Nvidia: Service temporarily overloaded
```

OpenRouter reports upstream provider errors as HTTP 200 with an `error` body and no
`choices`. The `openai` SDK retries HTTP 429/5xx itself, but not this case.
`OpenRouterClient._ask` turned it into `LLMError` at once, so one busy moment of the free
Nemotron endpoint ended the whole run. The run cannot be resumed.

## User decisions

- 2026-10-28: add exponential retry when such an error happens. The user asked Claude to
  implement it.

## Requirements

1. Transient errors are retried inside `_ask`, with exponential backoff and full jitter
   (0–2 s, 0–4 s, 0–8 s, … capped at 60 s), at most `TRANSIENT_RETRIES = 5` extra
   attempts. These retries do not use up the `MAX_RETRIES` budget for wrong JSON.
2. Transient means:
   - `RateLimitError`, `APITimeoutError`, `APIConnectionError` or `InternalServerError`
     from the SDK;
   - an error body or choice error with code 408, 429, 500, 502, 503 or 504;
   - a message containing "overloaded", "rate limit", "temporarily", "timeout" or
     "unavailable".
3. Everything else fails at once, as before: other 4xx, `finish_reason == "length"`, a
   missing key and validation errors.
4. After the last attempt, `TransientLLMError` (a subclass of `LLMError`) is raised, so the
   CLI still reports a short message.
5. `OpenRouterClient` accepts `transient_retries` and an injectable `sleep`, so tests never
   wait.

## Out of scope

Resuming a failed run, provider fallbacks, and new `.env` settings.

## Completion report

Implemented by Claude at the user's explicit request ("you do it"). It needs an independent
review.

- `src/pov_retell/infrastructure/llm.py`:
  - adds `TransientLLMError`, `is_transient` and `backoff_delay`;
  - `_ask` retries around the new `_ask_once`, which holds the old request body;
  - the error paths classify errors as transient or final.
- `tests/test_llm.py`:
  - `make` uses a no-op sleep;
  - the two tests that expected no retry for 502/504 errors now expect 6 requests;
  - new tests: backoff then success on the Nvidia "temporarily overloaded" body; the
    budget is exhausted on 429; no retry on 400; the delay bounds.
- Results:
  - `uv run pytest -q`: 304 passed, 4 skipped (300 before; +4 tests);
  - `ruff check`, `ruff format --check` and `mypy src`: clean;
  - `git diff --check`: clean.
- **Deviation:** the branch starts from `ticket/T-0013-glm-card-updates`, not from `main`.
  The user runs ingest from that branch and T-0013 is not merged yet. Merge T-0013 first.
- No live run.

## Review

_Filled by the product manager: verdict, evidence per criterion, findings with file:line._
