---
id: T-0008
title: "Scene map: who is where, through whose eyes, per paragraph range"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: medium
created: 2026-10-25
updated: 2026-10-25
depends_on: [T-0003, T-0007]
---

# T-0008: Scene map: who is where, through whose eyes, per paragraph range

## Background

A POV retelling must know, for each stretch of text:

- where it happens;
- who is physically present;
- whose perceptions the narration follows;
- how its time relates to the surrounding text.

Today nothing records this. Example: in u12, Aslan takes only Peter to the eastern edge of
the hill-top (u12_p024–u12_p028), after the girls were sent to the pavilion (u12_p023).
A retelling from Lucy's point of view must not narrate that conversation. Our data
cannot tell her absence today: the chapter summary only says "Aslan shows Peter Cair Paravel".

The scene map is the backbone for later steps:

- events: each event belongs to a segment;
- knowledge: Python can derive who witnessed what from presence;
- POV: which segments a character can narrate;
- story order: `parallel`, `flashback` and `time_jump` separate story order from narrative
  order.

## User decisions

- 2026-10-25: accepted the scene map, item 5 and step 6 of the reading order, after the
  explanation with u12, and asked for all agreed tickets.
- JSON jobs use the extract client (GLM after T-0005).

## PM recommendations

The user may veto these before work starts:

- Python assigns segment IDs (`u12_s1`, `u12_s2`, …); the LLM does not.
- The time relation uses five fixed values (below), general to any novel.

## Requirements

1. **New per-chapter step** in the extraction graph, after the character step and T-0007's
   location step of the same chapter, using the extract client.
2. **Input:**
   - book title and chapter ID;
   - `format_previous_context` before N;
   - a compact roster (`character_id`, `candidate_name`, `aliases`);
   - a compact locations list (`location_id`, `name`, `aliases`, `part_of`);
   - the chapter text with paragraph IDs.
3. **Output:**
   ```json
   {"segments": [{"start": "uNN_pNNN", "end": "uNN_pNNN",
                  "location_id": "loc_NNN" | null,
                  "present_ids": [], "mentioned_ids": [], "viewpoint_ids": [],
                  "time": {"relation": "continues" | "later" | "parallel" | "flashback" | "time_jump",
                           "anchor": "uNN_pNNN" | null, "note": str | null},
                  "label": str}]}
   ```
4. **Prompt definitions:**
   - **Segment:** consecutive paragraphs in one place and continuous time. Start a new
     segment when the place changes, time jumps, or the narration moves to a different group.
   - **Present:** physically there according to the text.
   - **Mentioned:** named or referred to but not there.
   - **Viewpoint:** whose perceptions or thoughts the narration follows. Leave it empty when
     the narration follows no one.
   - **Anchor:** the earlier paragraph a `parallel` or `flashback` segment relates to.
   - **Note:** at most 8 words of time wording taken from the text.
   - **Label:** at most 15 words.
   - Only IDs from the inputs. Groups get no IDs. Generic examples only.
5. **Python validation**; reject with a reason and retry:
   - segments cover every paragraph of the chapter in order, with no gaps or overlaps;
   - `start` ≤ `end`, both in this chapter;
   - every character and location ID exists;
   - `viewpoint_ids` ⊆ `present_ids`;
   - `present_ids` ∩ `mentioned_ids` = ∅;
   - `relation` is one of the five values;
   - `anchor` is required for `parallel` and `flashback`, must be an existing paragraph
     before `start` (an earlier chapter is allowed), and is null otherwise;
   - `label` and `note` respect their length limits.
6. **Storage:** `chapters/uNN.scenes.json` (validated, with Python-assigned `segment_id`) and
   `chapters/uNN.scenes.proposed.json` (raw).
7. **Recursion limit** through the per-graph helper. Update the audit runner (call counts,
   test), `run-protocol.md`, README, and run a context-maintenance pass.

## Acceptance criteria

- [x] One scene-map call per chapter, after that chapter's character and location steps.
      Offline test.
- [x] A valid synthetic chapter saves segments with IDs `uNN_s1…`. Offline test.
- [x] Each rule in Requirement 5 rejects and retries with its reason. Offline tests: gap,
      overlap, wrong chapter, unknown ID, viewpoint not present, present and mentioned
      overlap, bad relation, missing or later anchor, label too long.
- [x] Book-agnostic prompt test. Synthetic test data, no book text. Runner test updated.
      All Verification commands pass. README updated. Context pass done.

## Out of scope

- Deriving knowledge or witnesses from presence, events, Neo4j `Scene` nodes, and any
  change to character, relationship or location logic.

## Files likely touched

- new `src/pov_retell/ingest/graph/scene_map/` (or inside the extraction graph package) with `prompt/`
- extraction graph wiring, `src/pov_retell/ingest/pipeline.py`
- audit runner, its test, `run-protocol.md`, `tests/`, `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK): compare u12 with the PM's reference.
Boundaries may differ by one or two paragraphs.

| Segment | Paragraphs | Place | Present | Viewpoint | Time |
| --- | --- | --- | --- | --- | --- |
| 1 | u12_p001–p005 | Narnia (wood) | Peter, Susan, Lucy, Mr. and Mrs. Beaver | the three children | parallel, anchor u11_p034 |
| 2 | u12_p006–p023 | the Stone Table | the above plus Aslan | the three children | continues |
| 3 | u12_p024–p028 | the Stone Table | Peter, Aslan only | Peter | continues |
| 4 | u12_p029–p032 | the pavilion | Peter, Susan, Lucy, Fenris Ulf | Peter | continues |
| 5 | u12_p033–p037 | the pavilion | Peter, Aslan | Peter | continues |

The key checks are segment 3 (Lucy absent) and segment 1 (`parallel` anchored in u11).

## Open questions

- Should a segment allow several places, for a journey? Default: no. Use the larger
  containing place (for example the land) for a journey.

## Completion report

- **What changed:**
  - Added `SceneTimeRelation`, `SceneTime`, `SceneSegmentProposal`, `SceneSegmentRecord`, `SceneMapResponse`, and state fields (`proposed_scenes`, `scenes`) in `src/pov_retell/ingest/graph/extract_character/model.py`.
  - Created book-agnostic `src/pov_retell/ingest/graph/extract_character/prompt/extract_scene_map.py` (`PROMPT_EXTRACT_SCENE_MAP`).
  - Created `src/pov_retell/ingest/graph/extract_character/scene_map.py` (`extract_scene_map`, `validate_scene_map`) validating complete ordered paragraph coverage with no gaps or overlaps, `start <= end` in the current chapter, existing character and location IDs (after redirects), `viewpoint_ids <= present_ids`, `present_ids & mentioned_ids == empty`, valid `time.relation` (`continues|later|parallel|flashback|time_jump`), `time.anchor` required for `parallel`/`flashback` (an existing paragraph before `start` in this or an earlier chapter) and `null` otherwise, `time.note` <= 8 words, and `label` <= 15 words; assigning `segment_id` (`uNN_sM`).
  - Wired `extract_scenes` and `validate_scenes` into `src/pov_retell/ingest/graph/extract_character/graph.py` after `validate_locations` (`EXTRACT_NODES_PER_CHAPTER = 9`), saving `chapters/uNN.scenes.proposed.json` and `chapters/uNN.scenes.json` in `save_json`.
  - Added `tests/test_scene_map.py` and updated `tests/test_character_ingest.py`, `tests/test_character_recovery.py`, `tests/test_relationship_ingest.py`, `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`, `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`, `README.md`, and `AI-work/PROJECT_CONTEXT.md`.
- **Files touched:**
  - `src/pov_retell/ingest/graph/extract_character/model.py`
  - `src/pov_retell/ingest/graph/extract_character/prompt/extract_scene_map.py`
  - `src/pov_retell/ingest/graph/extract_character/scene_map.py`
  - `src/pov_retell/ingest/graph/extract_character/graph.py`
  - `tests/test_scene_map.py`
  - `tests/test_character_ingest.py`
  - `tests/test_character_recovery.py`
  - `tests/test_relationship_ingest.py`
  - `AI-work/skills/run-ingest-api-audit/tests/test_run_api_audit.py`
  - `AI-work/skills/run-ingest-api-audit/references/run-protocol.md`
  - `README.md`
  - `AI-work/PROJECT_CONTEXT.md`
  - `AI-work/tickets/T-0008-scene-map.md`
  - `AI-work/tickets/README.md`
- **Verification outputs:**
  - `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q` -> `298 passed, 5 skipped`
  - `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit` -> `All checks passed!`
  - `.venv/bin/ruff format --check src tests` -> `65 files already formatted`
  - `.venv/bin/mypy src/pov_retell` -> `Success: no issues found in 45 source files`
  - `git diff --check` -> clean (0 output)
- **Context maintenance:** Performed bounded context-maintenance pass in `AI-work/PROJECT_CONTEXT.md` directly (Codex `gpt-5.6-sol` and Claude Sonnet 5.5 are not exposed in this Antigravity runtime).
- **Remaining risks / notes:** Not yet exercised with a live OpenRouter run; ready for Claude review.

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
| One scene-map call per chapter, after the character and location steps | pass | `graph.py:248-251`; `test_one_scene_map_call_per_chapter_after_location_step_and_saves_segments` (`tests/test_scene_map.py:66`) |
| Valid synthetic chapter saves segments `uNN_s1...` | pass | `scene_map.py:179-191`; same test reads `chapters/uNN.scenes.json` |
| Each Requirement 5 rule rejects and retries with its reason | pass | `scene_map.py:103-177`; parametrized test (`tests/test_scene_map.py:345`): gap, end gap, overlap, start after end, wrong chapter, unknown character and location ID, viewpoint not present, present/mentioned overlap, bad relation, missing anchor, anchor on `continues`, later anchor, unknown anchor, label and note too long |
| Book-agnostic prompt, synthetic data, runner test, verification, README, context pass | pass | `tests/test_scene_map.py:426`; prompt example uses "Mara and Jo ... the old manor"; `run-protocol.md:28-29` and README line 339 state 4N extraction calls |

The prompt's definitions match Requirement 4 (`extract_scene_map.py:14-45`). Input matches
Requirement 2: compact roster and locations (`scene_map.py:36-60`), context before N
(`graph.py:154`). IDs are checked after identity redirects, and anchors may point into
earlier chapters (`scene_map.py:90-95`, `:153-165`).

### Findings

None required.

**Note (follow-up for the knowledge step).** Scene files are written per chapter and are not
rewritten when a later chapter merges two characters. Earlier `uNN.scenes.json` files can
hold a merged-away ID; readers must apply `identity_redirects.json`. Relationships, by
contrast, are rewritten (T-0004).

### Not measured

Segment boundaries, presence and viewpoint quality. Next step: the u12 comparison under
Verification (segment 3 without Lucy, segment 1 `parallel` anchored in u11), after the
user's OK.
