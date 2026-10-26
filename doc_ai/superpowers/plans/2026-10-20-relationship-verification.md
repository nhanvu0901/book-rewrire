# Separate discovery and relationship graphs

Updated after the user's correction: relationship verification runs only after character
extraction has completed for all chapters. Keep two independent graphs with their own states.

## Decisions

- Character graph: load chapters, extract, validate IDs/maps, save cumulative character JSON.
  It never verifies relationships or writes Neo4j. Preserve map targets until verification.
- Relationship graph: prepare pairs from final maps, verify batches of 20 pairs against the
  full book text, validate/apply results, save JSON, then publish nodes and edges to Neo4j.
- Each graph's TypedDict state lives in its matching schema module in ingest/models/.
- No relationship comparison, structured-record remapping, or confidence merging during
  discovery. Identity resolution remains part of character extraction.
- A reviewed pair returns a corrected summary and zero or more structured facts.
  Rejection uses null and an empty fact list. Evidence may reference any source chapter.
- Event boundaries remain null until event extraction exists. Verification status means
  an LLM review. No checkpoint, resume command, or real OpenRouter invocation is added.
- Keep character snapshots by chapter and relationship snapshots by verification batch.
  Full-book input can exceed provider context limits even when output pairs are batched.

## Tasks

1. Prove extraction completes before verification and test each graph independently.
2. Move discovery state, add verification state/graph, simplify relationship preparation,
   and orchestrate both graphs in ingest_book.
3. Update prompts, retain endpoint/evidence validation and failure preservation, and test
   batching and final IDs after merges.
4. Update operational docs; run pytest, Ruff, mypy, and temporary Neo4j integration tests.
