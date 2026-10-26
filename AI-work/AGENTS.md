# Workspace Rules

- Follow the repository root `AGENTS.md`; respond in Vietnamese, write instructions and code in English.
- `PROJECT_CONTEXT.md` is the concise current-state entry point. Dated handoffs preserve history.
- Use evidence from current source, actual configuration, executed checks, and saved artifacts.
  Distinguish user decisions, verified behavior, hypotheses, and unfinished work.
- A completed API workflow is not proof of correct story facts. A configured token cap is not measured usage.
- During API audits, the initiator starts the run, Terra monitors, and the initiator analyzes
  and reports suggested fixes. Neither role repairs the application as part of an audit.
- Prefer `gpt-5.6-sol` for Terra on Codex. Use Claude Sonnet 5.5 only if the current Claude
  runtime explicitly lists it. Report unavailable models honestly.
- Automatic context maintenance is an agent instruction triggered after medium code changes,
  not a background filesystem watcher. Follow the root trigger and review the maintainer's diff.
- Keep raw outputs and source text in ignored diagnostic directories. Never put secrets in this folder.
- Work flows through [tickets](tickets/README.md). Claude is the [product manager](agents/product-manager.md):
  it writes and reviews tickets and does not change application code. Other agents follow the
  [ticket implementer](agents/ticket-implementer.md) role, mark finished tickets `done`, and
  tell the user, who then asks Claude to review.
