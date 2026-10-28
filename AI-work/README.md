# AI Workspace

This folder is the entry point for AI collaboration on book-clone.

## Read in this order

1. [Root instructions](../AGENTS.md) and [workspace instructions](AGENTS.md).
2. [Current project context](PROJECT_CONTEXT.md): architecture, active contracts, verified facts, and open questions.
3. A relevant [handoff](handoffs/HANDOFF_2026-10-23.md) for history. Handoffs are snapshots, not live specifications.
4. The skill or role needed for the task.

```text
AI-work/
    README.md
    AGENTS.md
    PROJECT_CONTEXT.md
    handoffs/                         # Dated session history
    tickets/
        README.md                      # Ticket flow, statuses and board
        TEMPLATE.md
        T-NNNN-*.md                    # One ticket per file
    agents/
        product-manager.md             # Claude: writes and reviews tickets, no app code
        ticket-implementer.md          # Other agents: take, implement, mark done, inform user
        terra-api-monitor.md           # Observer -> initiator escalation
        context-maintainer.md          # Bounded documentation updates
    skills/
        run-ingest-api-audit/
            SKILL.md
            agents/openai.yaml
            references/
            scripts/run_api_audit.py
            tests/test_run_api_audit.py
```

## Workflows

- **Plan and change code through tickets:** Claude, as [product manager](agents/product-manager.md),
  writes tickets in [tickets/](tickets/README.md). Another agent takes one as
  [implementer](agents/ticket-implementer.md), marks it `done`, and tells the user. The user
  asks Claude to review, and Claude marks it `verified` or `changes_requested`.
- **Run a real API audit:** read [run-ingest-api-audit](skills/run-ingest-api-audit/SKILL.md).
  The initiating model owns the run and analysis. Terra observes; it does not repair.
- **After a medium code change:** automatically delegate the [context maintainer](agents/context-maintainer.md),
  then verify its update. The standing trigger is in root `AGENTS.md`.
- **Record session history:** add a dated handoff under `handoffs/`; keep current facts in
  `PROJECT_CONTEXT.md`. Do not copy every log or turn into the universal context.

These are repository-local instructions and skill files. Any AI can read their paths directly;
this does not install a global skill or guarantee that every runtime indexes the folder automatically.

## Artifact locations

Raw API requests/responses, logs, snapshots, and reports stay under the ignored
`book/diagnostics/<audit_id>/`. Source book data stays under `book/`. `AI-work` contains
instructions and knowledge that can be versioned, without credentials or book text.

Earlier plans and ingest documentation remain under [doc_ai](../doc_ai/).

## Handoffs

- [2026-10-23](handoffs/HANDOFF_2026-10-23.md): restoration, latest audited failure, and open goals.
- [2026-10-22](handoffs/HANDOFF_2026-10-22.md): ScaleDown experiments and restoration history.
- [2026-10-17](handoffs/HANDOFF_2026-10-17.md): earlier project baseline.
