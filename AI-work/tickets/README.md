# Tickets

Claude is the [product manager](../agents/product-manager.md): it writes tickets and reviews
finished ones. Other agents [implement](../agents/ticket-implementer.md) them. The user decides
scope and tells Claude when to review.

## Flow

```text
draft --(user approves)--> ready --(agent takes)--> in_progress --> done
                                                       |            |
                                                    blocked     (user asks Claude)
                                                                    |
                                          changes_requested <-- review --> verified
```

| Status | Meaning | Set by |
| --- | --- | --- |
| `draft` | Being written; not approved | Claude |
| `ready` | Scope approved by the user; can be taken | Claude |
| `in_progress` | Taken; `owner` names the agent | Implementer |
| `blocked` | Needs a user decision; question written in the ticket | Implementer |
| `done` | Implemented, checks recorded, user informed | Implementer |
| `changes_requested` | Review found problems; listed in Review | Claude |
| `verified` | Review passed | Claude |

The ticket file is the source of truth. Whoever changes a status also updates the board below.
One ticket per file: `T-NNNN-short-slug.md`, created from [TEMPLATE.md](TEMPLATE.md).

## Branches and commits

Standing user rule (2026-10-26): every ticket has its own branch, and every code change and
every review is committed.

- **Start from an up-to-date `main`.** Before taking a ticket, always run:
  ```bash
  git fetch origin
  git switch main && git pull --ff-only origin main
  git switch -c ticket/T-NNNN-short-slug
  ```
  If `git pull --ff-only` fails, or the working tree is not clean, stop and tell the user.
  Do not force, reset or stash someone else's work.
- **Branch:** `ticket/T-NNNN-short-slug`, created as above when the ticket is taken. Record it in the ticket's `branch:` field. Only that ticket's work goes on the
  branch: code, tests, the ticket file and its board row.
- **Parallel tickets** use separate worktrees, so two agents never share one working
  tree: `git worktree add ../book-clone-T-NNNN ticket/T-NNNN-short-slug`. `.env` is ignored
  by Git. If a worktree needs it, link it and never commit it.
- **Implementer commits:** at least one commit per implementation round, made before
  setting `done`. Message: `T-NNNN: <what changed>`. The Completion report names the commit
  hashes.
- **PM review commits:** the reviewer commits the Review section, the status and the board
  row on the same branch. Message: `T-NNNN review: verified` or
  `T-NNNN review: changes_requested`.
- **Merging:** only a `verified` ticket's branch is merged into `main`, and only when the
  user asks. Before merging, fetch and pull `main` again, then rebase or merge `main` into
  the ticket branch and rerun the ticket's verification. Nothing is pushed unless the user asks.
- **Never commit** `.env`, secrets, book text or raw API responses.

## Board

| ID | Title | Status | Owner | Updated |
| --- | --- | --- | --- | --- |
| [T-0001](T-0001-summary-memory-redesign.md) | Summary memory: chapter summaries + WHO IS WHO + core memory | verified | Antigravity (Gemini 4 Argon) | 2026-10-24 |
| [T-0002](T-0002-who-is-who-card-rules.md) | WHO IS WHO cards: lasting identity and status, no chapter references or event logs | verified | Antigravity (Gemini 4 Argon) | 2026-10-24 |
| [T-0003](T-0003-character-extraction-cleanup.md) | Character extraction: clean attributes and aliases, remove relationships from the character call | verified | Antigravity (Gemini 4 Argon) | 2026-10-25 |
| [T-0004](T-0004-relationship-call.md) | Relationships: separate structured call per chapter, changes only, with history | verified | Antigravity (Gemini 4 Argon) | 2026-10-25 |
| [T-0005](T-0005-glm-structured-json-client.md) | JSON client: JSON schema, pinned provider and reasoning for the extract client | verified | Antigravity (Gemini 4 Argon) | 2026-10-25 |
| [T-0006](T-0006-where-is-where.md) | WHERE IS WHERE: running place list in the summary graph | verified | Terra (gpt-5.6-sol) | 2026-10-25 |
| [T-0007](T-0007-location-ids.md) | Locations with IDs: structured place extraction per chapter | verified | Terra (gpt-5.6-sol) | 2026-10-25 |
| [T-0008](T-0008-scene-map.md) | Scene map: who is where, through whose eyes, per paragraph range | verified | Antigravity (Gemini 4 Argon) | 2026-10-25 |
| [T-0009](T-0009-langsmith-env.md) | LangSmith tracing works for `pov ingest` without an env-file flag | draft | unassigned | 2026-10-25 |
| [T-0010](T-0010-pov-graph-slides.md) | HTML slide deck (4–5 min), game style, ShiftKey structure, real sprint content (Revisions 4–5) | done | Antigravity (Gemini 4 Argon) | 2026-10-26 |
| [T-0011](T-0011-remove-scaledown-experiment.md) | Remove the unused ScaleDown experiment and its required setting | verified | Codex (GPT-6) | 2026-10-26 |
| [T-0012](T-0012-running-list-quote-normalization.md) | Running lists treat straight and curly quotes as the same name | verified | Antigravity (Gemini 4 Argon) | 2026-10-28 |

## Recommended order

Implement one ticket at a time; T-0004 to T-0008 touch the same graph, pipeline and audit runner.

T-0002 to T-0008 are verified offline (2026-10-25).
1. T-0012 (quote normalization) first: it blocks the real summary run of Harry Potter at chapter 6.
2. Live check of T-0002 to T-0008 after the extract model is switched to GLM in `.env` and the user gives the OK.
3. T-0010: fix the Revision 4 review findings and apply Revision 5 (real sprint content) together.
T-0011 (remove ScaleDown) is verified (2026-10-26).
T-0009 waits for the user's choice.
