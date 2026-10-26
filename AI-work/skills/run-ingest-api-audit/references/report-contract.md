# Initiator Report Contract

Write `<audit_dir>/report.md` in English, then give the user a Vietnamese summary.
Use these sections so the next agent can verify conclusions without rereading the session.

## Run and Outcome

Record audit path, requested scope, actual initiator/monitor models when known, UTC times,
process exit code, terminal status, and completed/expected summaries and character chapters.
Separate a dry plan, an API execution pass, a factual-quality finding, and a failure.

## Evidence

For each issue include phase, chapter, call/attempt number, exact artifact, and relevant fields:
HTTP status, finish reason, response ID, requested/returned model, configured token cap,
measured completion/reasoning usage, or exception. Use `unknown` for absent data.
For story claims cite source paragraph IDs and the proposed/accepted field being assessed.
Do not paste API keys, authorization headers, or whole book chapters into the report.

## Analysis

State confirmed observations first, followed by the most likely explanation and competing
explanations. Mark a hypothesis as a hypothesis. A cap of 32,768 is not proof that 32,768
tokens were consumed or that reasoning was responsible. A correct name is not proof that
the profile's attributes belong to that character.

## Suggested Remedies — Not Applied

List targeted options with the evidence needed to choose them, affected component, and a
small verification case. Explain how each addresses the observed issue. Do not change source,
prompts, model settings, limits, or database contents as part of this report.

## Preservation and Limits

State which files remain valid, what was not measured, whether Neo4j was touched, and
whether any runtime limitation prevented monitoring or metadata collection. End with the
next concrete investigation or implementation decision for the user, without claiming a fix.
