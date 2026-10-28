---
id: T-0005
title: "JSON client: JSON schema, pinned provider and reasoning for the extract client"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: high
created: 2026-10-25
updated: 2026-10-25
depends_on: []
---

# T-0005: JSON client: JSON schema, pinned provider and reasoning for the extract client

## Background

Every JSON job goes through `OpenRouterClient.complete_json` → `_ask` in
`src/pov_retell/infrastructure/llm.py`. Today a JSON request carries only `model`,
`messages`, `response_format={"type": "json_object"}`, `max_tokens` and `temperature=0`.
JSON shape is then enforced by Pydantic validation plus up to two repair retries.

OpenRouter metadata checked 2026-10-24/25 (mutable, re-check before relying on it):

- `nvidia/nemotron-3-ultra-550b-a55b:free` supports neither `response_format` nor
  `structured_outputs`; OpenRouter ignores our `json_object`.
- `z-ai/glm-5.3-flash` supports `response_format`, `structured_outputs` (JSON schema) and
  `reasoning`. Some of its providers lack `structured_outputs` (Z.AI, Novita, AtlasCloud,
  SiliconFlow at check time).
- Endpoint `open-inference/fp4` (OpenInference, fp4 quantization): `response_format`,
  `structured_outputs`, `reasoning` supported; context 1,048,576; max output 943,718;
  $0.030 / $0.069 per 1M input / output tokens.

Evidence for provider errors: the u13 replay
(`book/diagnostics/extract_u13_replay_20261024T150836Z/`) ended with `finish_reason`
`"error"` (504 upstream idle timeout) and empty content. `_ask` only checks `"length"`, so
the user saw "Invalid JSON input_value=''" after three attempts.

## User decisions

- 2026-10-24: jobs that need JSON use `z-ai/glm-5.3-flash`.
- 2026-10-25: pin provider `open-inference/fp4` with no fallbacks (the user's sample request
  used `"provider": {"only": ["open-inference/fp4"], "allow_fallbacks": false}` and
  `"reasoning": {"enabled": true}`).
- The text summary jobs stay on their own model and must not change.

## PM recommendations

The user may veto these before work starts:

- Send a JSON schema derived from the Pydantic response model instead of `json_object`, with
  `provider.require_parameters: true`, so a provider that cannot honor the schema is never used.
- Make `_ask` raise a clear `LLMError` when the provider reports a failure
  (`finish_reason == "error"` or an `error` object on the choice) instead of returning empty
  content. With one pinned provider and no fallbacks, provider failures reach us directly.

## Requirements

1. **New settings for the extract client**, required like every other setting (no Python
   defaults; `tests/test_config.py` checks that), documented in `.env.example` and README:
   - `OPENROUTER_EXTRACT_CHARACTER_PROVIDER`: comma-separated provider tags; empty means
     OpenRouter's default routing (no `provider.only`).
   - `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS`: `true` or `false`.
   - `OPENROUTER_EXTRACT_CHARACTER_REASONING`: `none` (send no `reasoning`), `enabled`
     (`{"enabled": true}`), or `low` / `medium` / `high` (`{"effort": "<value>"}`).
   - `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS`: `true` sends a JSON schema;
     `false` keeps today's `json_object`.
2. **Extract client request body:**
   - Structured outputs on: `response_format` is
     `{"type": "json_schema", "json_schema": {"name": <response model name>, "strict": true,
     "schema": <schema>}}`. The schema comes from the Pydantic response model passed to
     `complete_json`. Every object in it has `additionalProperties: false` and lists all its
     properties as required, as strict mode demands. Fields the prompt does not ask for
     (for example the excluded `identity_context`) must not appear; report any difference.
   - Provider set: `provider` contains `only` and `allow_fallbacks` from the settings, plus
     `require_parameters: true` when structured outputs are on.
   - `reasoning` according to the setting.
   - Pydantic validation, the `check` callback and the repair retries stay unchanged.
3. **The summary client is unchanged.** Its request body has no `provider`, no `reasoning`
   and no `response_format`, exactly as today.
4. `cli.py` and the audit runner (`AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`)
   build the extract client from the new settings. The runner manifest records provider,
   allow-fallbacks, reasoning and structured-outputs values.
5. `_ask` raises `LLMError("OpenRouter generation failed: …")` when the choice reports
   `finish_reason == "error"` or carries an `error` object (PM recommendation above). The
   `"length"` check stays.
6. **Do not edit `.env`.** In the Completion report, list the lines the user must add or
   change in `.env` with the user's values:
   `OPENROUTER_EXTRACT_CHARACTER_MODEL=z-ai/glm-5.3-flash`,
   `OPENROUTER_EXTRACT_CHARACTER_PROVIDER=open-inference/fp4`,
   `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS=false`,
   `OPENROUTER_EXTRACT_CHARACTER_REASONING=enabled`,
   `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS=true`.
7. Update README (configuration) and run a context-maintenance pass per root `AGENTS.md`.

## Acceptance criteria

- [x] Offline request-capture tests (as in `tests/test_llm.py`) show, for the extract client:
      the `json_schema` response format with `strict: true`; `provider.only`,
      `allow_fallbacks`, `require_parameters`; and `reasoning` for each of `none`,
      `enabled` and an effort value.
- [x] With structured outputs `false` and an empty provider, the request equals today's.
- [x] A schema test walks the generated schema for `ExtractCharacterResponse`: every
      object has `additionalProperties: false` and all properties required, and the
      property names match the prompt's OUTPUT example.
- [x] The summary client request is unchanged. Offline test.
- [x] `finish_reason "error"` and a choice `error` object raise `LLMError` with the provider
      message. `complete_json` does not loop on them silently. Offline tests.
- [x] Settings tests cover the new names and invalid values (for example
      `REASONING=maybe`).
- [x] CLI and audit runner pass the settings. Runner offline test updated.
- [x] All Verification commands pass. README and `.env.example` updated. Context pass done.

## Out of scope

- Any prompt, schema field or merge-logic change in the character step.
- Passing `reasoning_details` back during repair retries.
- The summary model, token caps, Neo4j.

## Files likely touched

- `src/pov_retell/infrastructure/llm.py`, `src/pov_retell/config.py`, `src/pov_retell/cli.py`
- `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py` and its test
- `tests/test_llm.py`, `tests/test_config.py`, `tests/test_cli_ingest.py`
- `.env.example`, `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK): audit-runner smoke run on two chapters.
It confirms that `open-inference/fp4` accepts the strict schema and returns valid character
JSON without repair retries.

## Open questions

- Reasoning level: default is `enabled`, as in the user's sample. Compare with `medium` in the
  live check if calls are slow.

## Completion report

### What changed

- **`src/pov_retell/config.py`**: Added required settings `OPENROUTER_EXTRACT_CHARACTER_PROVIDER` (`ProviderSetting`), `OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS` (`bool`), `OPENROUTER_EXTRACT_CHARACTER_REASONING` (`ReasoningMode`: `none` | `enabled` | `low` | `medium` | `high`), and `OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS` (`bool`) with no Python defaults.
- **`src/pov_retell/infrastructure/llm.py`**:
  - Added `strict_json_schema(model)` using `model.model_json_schema(mode="serialization")` (so `exclude=True` fields such as `identity_context` are omitted) and recursively enforcing `additionalProperties: false` and `required: list(properties.keys())` on every object schema.
  - Updated `OpenRouterClient` to accept `provider`, `allow_fallbacks`, `reasoning`, and `structured_outputs`. When `structured_outputs` is `True`, `complete_json` sends `response_format={"type": "json_schema", "json_schema": {"name": schema.__name__, "strict": True, "schema": strict_json_schema(schema)}}` and `provider.require_parameters: True`. When `provider` is non-empty, `extra_body["provider"]` sets `only` and `allow_fallbacks`. When `reasoning` is `"enabled"` or `"low"`/`"medium"`/`"high"`, `extra_body["reasoning"]` sets `{"enabled": True}` or `{"effort": <value>}`. When `structured_outputs` is `False`, `provider` is empty, and `reasoning` is `"none"`, the request is identical to today's (`response_format={"type": "json_object"}` and no `extra_body`).
  - Left `complete_text` (the summary client) completely unchanged.
  - Updated `_ask` to raise `LLMError("OpenRouter generation failed: ...")` immediately when `finish_reason == "error"` or `choice.error` is present, preserving the `"length"` truncation check.
- **`src/pov_retell/cli.py` and `AI-work/skills/run-ingest-api-audit/scripts/run_api_audit.py`**: Passed the four new extract-character settings to the extract `OpenRouterClient`, recorded `extract_character` options (`provider`, `allow_fallbacks`, `reasoning`, `structured_outputs`) in the audit runner's `manifest.json`, and captured `"provider"` in recorded HTTP request artifacts.
- **`.env.example`, `README.md`, `AI-work/PROJECT_CONTEXT.md`, and tests (`tests/test_config.py`, `tests/test_llm.py`, `tests/test_cli_ingest.py`, `tests/test_character_ingest.py`, `tests/test_pipeline.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`)**: Documented the new settings and added offline unit tests covering all acceptance criteria.

### Schema check (`ExtractCharacterResponse`)

- `strict_json_schema(ExtractCharacterResponse)` produces 3 object definitions (`ExtractCharacterResponse`, `CharacterCandidate`, `CharacterAttributes`), each with `additionalProperties: false` and all properties listed in `required`.
- Excluded field `identity_context` does not appear anywhere in the schema, and property names match the `OUTPUT` example in `PROMPT_EXTRACT_CHAR` with zero differences.

### Lines for `.env` (not edited by implementer)

Please add or update these lines in `.env`:

```dotenv
OPENROUTER_EXTRACT_CHARACTER_MODEL=z-ai/glm-5.3-flash
OPENROUTER_EXTRACT_CHARACTER_PROVIDER=open-inference/fp4
OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS=false
OPENROUTER_EXTRACT_CHARACTER_REASONING=enabled
OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS=true
```

### Verification results

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`: `198 passed, 5 skipped`
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`: `All checks passed!`
- `.venv/bin/ruff format --check src tests`: `57 files already formatted`
- `.venv/bin/mypy src/pov_retell`: `Success: no issues found in 38 source files`
- `git diff --check`: clean
- Context maintenance pass performed directly on `AI-work/PROJECT_CONTEXT.md` (sub-agent delegation with `gpt-5.6-sol` or Claude Sonnet 5.5 is unavailable in this runtime).

## Review

Reviewed by Claude (product manager) on 2026-10-25. Verdict: **verified**.

### Verification rerun by the reviewer

Run on 2026-10-25 on the combined working tree (T-0003 to T-0008 are implemented together, so
per-ticket isolation is not measured).

| Command | Result |
| --- | --- |
| pytest (`tests` + audit skill tests, offline) | `298 passed, 5 skipped, 1 warning` |
| `ruff check src tests AI-work/skills/run-ingest-api-audit` | `All checks passed!` |
| `ruff format --check src tests` | `67 files already formatted` |
| `mypy src/pov_retell` | `Success: no issues found in 45 source files` |
| `git diff --check` | exit 0 (tracked files only; new files are untracked) |

### Acceptance criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| `json_schema` strict, `provider.only` / `allow_fallbacks` / `require_parameters`, `reasoning` for none, enabled, effort | pass | `llm.py:115-147`; `test_extract_client_sends_strict_json_schema_pinned_provider_and_reasoning` (`tests/test_llm.py:249`) |
| Structured outputs off + empty provider equals today's request | pass | `test_structured_outputs_false_with_empty_provider_equals_todays_request` compares the full request dict |
| Strict schema walk for `ExtractCharacterResponse`, names match the prompt example | pass | `strict_json_schema` (`llm.py:23-40`, serialization mode drops `identity_context`); `tests/test_llm.py:317`. The reviewer also generated the strict schemas of the relationship, location and scene-map responses: every object has `additionalProperties: false` and all properties required, no free-form dict fields |
| Summary client unchanged | pass | `complete_text` sends no `response_format`, `provider` or `reasoning`; `test_summary_client_request_remains_unchanged`; `cli.py:87-91` builds it without the new options |
| `finish_reason "error"` and a choice `error` object raise `LLMError` without a retry loop | pass | `llm.py:239-248`; `LLMError` is not caught by `complete_json`'s `(ValidationError, ValueError)`; two tests assert one request |
| Settings tests incl. invalid values | pass | `config.py:18-57`; `tests/test_config.py:98`, `:122` |
| CLI and runner pass the settings; runner test | pass | `cli.py:77-85`, `run_api_audit.py:249-259`, `:315-323`; `tests/test_cli_ingest.py:96-101`; runner test checks the manifest options |
| Verification, README, `.env.example`, context pass | pass | README `:127-130`; `.env.example:19-26`; above |

### Findings

None required.

**Note 1 (user action before any run).** `.env` currently has none of the four new keys
(checked by key name only). Every setting is required, so `pov ingest` and the audit runner
stop at `Settings()` until the user adds the five lines listed in the Completion report.
`Settings()` in `cli.py:72` is outside the `try`, so the failure shows as a Pydantic
traceback rather than a one-line message (behavior predates this ticket).

**Note 2 (unmeasured).** The strict schemas keep Pydantic's `title`, `default` and
`minLength` keywords. Whether `open-inference/fp4` accepts them in strict mode is only known
after the live smoke run. With reasoning on, reasoning tokens count against
`OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS`; truncation risk is also unmeasured.

### Not measured

Provider acceptance of the schema, latency and cost with reasoning `enabled`. Next step: the
two-chapter live smoke run under Verification, after the user's OK and the `.env` update.
