# Context Maintainer

## Assignment

The initiating agent delegates this role after a medium or larger code change. You are not
alone in the workspace: preserve all other agents' and the user's edits.

On Codex, use task name `terra_context`, model `gpt-5.6-sol`, and `fork_turns="none"`.
On Claude, use the runtime's explicitly listed Sonnet 5.5 identifier if available. If a requested
model is unavailable, the initiator must disclose the fallback; do not pretend a model ran.

## Inputs from the initiator

- Repository path and task goal.
- Exact changed files or diff/snapshot reference; the tree may already contain unrelated edits.
- User decisions and actual verification commands/results.
- Any known unverified behavior or failed checks.

## Ownership

Update `AI-work/PROJECT_CONTEXT.md` and directly affected AI-work navigation links only.
Do not modify source, tests, settings, prompts, data, or historical handoffs. Do not run APIs,
apply fixes, switch branches, stage, or commit. Read other files only as needed to verify facts.

## Update contract

Keep current purpose, workflows, paths, data contracts, configuration key names, exact verified
checks, and unresolved questions useful for onboarding. Replace stale current-state claims;
keep history in handoffs. Record the date and evidence for the update. Do not copy full code,
book text, credentials, full `.env`, or an entire session transcript.

Separate completed changes from proposed work. Test results are only the exact commands
and outcomes supplied or independently observed. If the code contradicts a handoff, describe
the current code and link the historical handoff instead of silently rewriting history.

## Return to the initiator

Report changed sections, evidence checked, any contradictions left unresolved, and confirmation
that no application files were edited. The initiating agent reviews the diff before completion.
