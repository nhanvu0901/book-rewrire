# Language

- Respond to the user in Vietnamese.
- Write code, comments, docstrings, and prompts in English.
- Keep comments brief and useful. Do not add commentary about the editing process.

# AI Workspace

- Start onboarding with `AI-work/README.md` and `AI-work/PROJECT_CONTEXT.md`.
- Treat `AI-work/handoffs/` as dated history. Confirm current facts against source and settings.
- For real summarization and character-extraction API audits, read
  `AI-work/skills/run-ingest-api-audit/SKILL.md` and use its initiator/monitor split.
- API audit mode is investigation only: report evidence, causes, uncertainty, and suggested
  fixes to the user. Do not change application code, prompts, models, limits, or data to fix a run.

# Roles and Tickets

- Claude is the product manager: it writes tickets and reviews finished ones, and it does not
  edit application code, tests, prompts or settings. See `AI-work/agents/product-manager.md`.
- Other agents implement tickets from `AI-work/tickets/`, following
  `AI-work/agents/ticket-implementer.md`.
- Every ticket starts with `git fetch origin` and `git pull --ff-only origin main`. It then
  gets its own branch `ticket/T-NNNN-short-slug` from `main`. Every code change and every
  review is committed on it. Merge or push only when the user asks. See
  `AI-work/tickets/README.md` (Branches and commits). When a ticket is done, mark it `done` and tell the
  user; the user asks Claude to review it.

# Automatic Context Maintenance

After a medium or larger code change, automatically delegate a context-maintenance pass
before reporting completion. This is a standing user instruction; do not ask again.

A change qualifies when it alters a workflow, prompt/model contract, configuration,
storage format, CLI behavior, or behavior across multiple modules. A typo-only edit does not.

Use `AI-work/agents/context-maintainer.md`. On Codex, prefer a fresh-context agent named
`terra_context` with model `gpt-5.6-sol`. On Claude, use Sonnet 5.5 only when the runtime
explicitly exposes that model. Do not invent model identifiers or silently substitute one.
If the requested model or delegation is unavailable, disclose it and perform the same bounded
context update yourself; do not claim a sub-agent ran.

Give the maintainer the actual diff scope, verified test results, and any user decisions.
It owns `AI-work/PROJECT_CONTEXT.md` and directly affected AI-work navigation only; it must
not edit application code or rewrite historical handoffs. Review its changes against evidence.
Unknowns remain unknown. Keep credentials, book text, and raw API responses out of context docs.
