# Character ingestion

The ingest pipeline runs the character-discovery LangGraph through every chapter,
then writes selected Character properties to Neo4j. Relationship verification has
been removed. The character extraction graph, logic, models, and prompt are unchanged.

## Run

From the repository root:

```bash
uv sync --extra dev
make neo4j-up
uv run pov neo4j-status
uv run pov ingest narnia-debug
```

Configure OpenRouter, Neo4j, and `BOOK_CLONE_DATA_DIR` in `.env`.
Each run reads `<BOOK_CLONE_DATA_DIR>/extracted/<book_id>/units/*.txt`.
Chapter filenames, paragraph IDs, order, and text must agree with `book.json`.

## Workflow

```text
ingest_book
  character_discovery graph:
    START -> load_chapters -> extract_characters -> validate_characters -> save_json
                                  ^                                        |
                                  +------------ next chapter --------------+
                                                        last chapter -> END
  write Character nodes to Neo4j
  return IngestResult
```

The graph itself saves JSON and does not write Neo4j. The pipeline writes Character
nodes only after all chapters succeed. A failed chapter preserves earlier JSON and
does not publish that run's characters. If the database write fails, discovery JSON
remains available.

Each invocation creates a new run. There is no checkpointer or resume command.

## Character discovery

Each LLM request receives one chapter and the cumulative character list. Existing
characters retain their application-assigned IDs. New characters use chapter-local
IDs such as `new_1` and `new_2`. The application assigns permanent `char_NNN` IDs
and rewrites references.

Merges explicitly name retired IDs in `merged_character_ids` and retain the earliest
existing ID. Incoming and outgoing references are redirected, self-relations caused
by merges disappear, and retired IDs are not reused. Known names and aliases are
retained by ID. Merge instructions are excluded from saved snapshots.

Character-reference and preservation checks run inside the LLM validation callback,
allowing two correction attempts after the first response. These checks validate
structure and references; they do not prove factual accuracy.

The character's relationship map remains part of the extraction output:

```json
{
  "character_id": "char_001",
  "candidate_name": "Peter",
  "relationships": {
    "char_002": "older brother of Susan"
  }
}
```

The description states the source character's relationship to the target. Every
target must resolve to another character in the same run. Prior omitted proposals
are retained by the existing extraction logic. They remain unverified proposals;
the current pipeline does not review them or create relationship edges.

## Output

```text
book/ingest/<book_id>/<run_id>/
    characters.json
    chapters/
        u01.characters.json
        u02.characters.json
        ...
```

Chapter files are cumulative snapshots. `characters.json` contains the latest
accepted discovery state. Each JSON file is replaced atomically. Existing output
from previous runs, including historical relationship files, is retained.

## Neo4j

Each Character is keyed by `(book_id, run_id, character_id)`. Selected properties:

- canonical_name, aliases
- gender, species, age_description, physical_description
- personality, resolution_status

Personality joins `personality_traits` with `; `. The relationship map stays in
JSON. The current pipeline creates no `RELATES_TO` edges, Book, Unit, Paragraph,
Event, or Mention nodes. Data from other runs is unchanged.

## Code

| File | Responsibility |
|---|---|
| `src/pov_retell/ingest/pipeline.py` | Run discovery and publish Character nodes |
| `src/pov_retell/ingest/graph/character_discovery.py` | Chapter-by-chapter discovery graph |
| `src/pov_retell/ingest/extrac_character.py` | Chapter loading, character validation, IDs, JSON |
| `src/pov_retell/ingest/models/character_discovery.py` | Character schemas and discovery state |
| `src/pov_retell/ingest/models/ingest_result.py` | Run result and character output path |
| `src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py` | Character extraction prompt |
| `src/pov_retell/infrastructure/neo4j_store.py` | Connectivity and Character writes |

## Verification and limits

`make test` uses local fixtures and no external services. `make test-neo4j` checks
connection and scoped, idempotent Character writes with temporary data.
`make test-openrouter` sends a real OpenRouter request.

The complete cumulative character list is returned after each chapter, so request
and response sizes grow with the book. The OpenRouter client reads its output limit
from `OPENROUTER_MAX_TOKENS` in `.env` and reports truncated responses explicitly.
