# Ticket Implementer

## Role

Any agent other than the product manager (for example Codex) that implements a ticket from
[tickets/](../tickets/README.md). Follow root `AGENTS.md` and `AI-work/AGENTS.md`.
You are not alone in the workspace: preserve other agents' and the user's edits.

## Taking a ticket

1. Take only a ticket with status `ready` or `changes_requested`. If its `owner` is another
   agent and the status is `in_progress`, do not take it.
2. Set `status: in_progress`, `owner: <agent and model>`, `updated: <date>` in the ticket and
   on the board before changing code.
3. Read the whole ticket, the linked evidence, and `AI-work/PROJECT_CONTEXT.md`.

## Doing the work

- Implement exactly the ticket scope. Use test-first changes where behavior changes.
- If a requirement is unclear, conflicts with the code, or needs a user decision, stop:
  write the question under Open questions, set `status: blocked`, and tell the user.
- Do not run live APIs or write Neo4j unless the ticket or the user explicitly allows it.
- First `git fetch origin` and `git pull --ff-only origin main` on `main`, then branch from it.
- Work on the ticket's own branch `ticket/T-NNNN-short-slug`, in its own worktree when
  another ticket is in progress. See [Branches and commits](../tickets/README.md#branches-and-commits).
- Commit every implementation round (`T-NNNN: <what changed>`) before setting `done`. Never
  commit `.env`, secrets, book text or raw API responses. Do not push or merge unless the user asks.
- After a medium or larger change, run the context-maintenance pass required by root `AGENTS.md`.

## Finishing

1. Run every verification command in the ticket and record the exact results.
2. Fill the Completion report: what changed (files), how each acceptance criterion is met,
   commands and results, deviations from the ticket, and follow-ups you noticed.
3. Set `status: done`, update the date and the board.
4. Tell the user in Vietnamese: "Ticket T-XXXX is done; ask Claude to review it." Include a
   short summary and any failed or skipped check. Do not mark a ticket `verified` yourself.
