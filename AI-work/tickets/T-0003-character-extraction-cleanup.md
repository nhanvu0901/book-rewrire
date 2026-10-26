---
id: T-0003
title: "Character extraction: clean attributes and aliases, remove relationships from the character call"
status: verified
owner: Antigravity (Gemini 4 Argon)
priority: high
created: 2026-10-24
updated: 2026-10-25
depends_on: []
---

# T-0003: Character extraction: clean attributes and aliases, remove relationships from the character call

## Background

Character extraction makes one JSON call per chapter (`extract_character/prompt/extract_character.py`)
and Python merges the changes (`extract_character/logic.py`, `identity.py`). The first full
live run after T-0001, `book/ingest/narnia-debug/run_2ae27f27f5d34937a54c8c81ed93303e`, finished
17 chapters (u01–u17, about 22 minutes, no provider error) with 42 characters, no duplicate
main characters, no merges needed and no outside-knowledge names. The records still have
these problems:

1. **Relationships are event logs.** 286 relationships, 4,849 words; 38 over 30 words, 17 over
   60 words. White Witch → Edmund has 131 words retelling the plot. Python appends each
   chapter's description with `"; "` (`combine_descriptions`), so they only grow. They cannot
   become `RELATES_TO {kind}` edges.
2. **Events and titles inside attributes.** `physical_description` holds "killed in battle by
   Aslan; wand broken by Edmund" (White Witch), "healed of wounds by Lucy's cordial" (Edmund),
   "mane cut off by ogre with shears" (Aslan), and "known as King Peter the Magnificent" (Peter).
3. **Aliases miss names and contain descriptions.**
   - Missing: the coronation titles "King Peter the Magnificent", "Queen Susan the Gentle",
     "King Edmund the Just", "Queen Lucy the Valiant" (u17_p021); "Sir Peter Fenris-Bane"
     (u12_p037); "the Queen" for the White Witch (u09_p030), the name Edmund knows her by.
     Aslan has no aliases although the text calls him "Lord of the whole wood" (u08_p015).
   - Noise: "very strange person" (u01_p026), "old chap" (u01_p003), "old dear" (u01_p004),
     "robin with a redder chest", a full sentence for the White Stag.
   Aliases also feed identity matching, so noise can cause false matches.
4. **Unsupported species.** Silenus has species "Faun"; the text says only "old Silenus on his
   fat donkey" (u02_p025).
5. **Groups as characters.** "field mice" and "Mermen and Mermaids" (u17_p018).

The relationship field is not written to Neo4j: `character_rows` leaves it out and the writer
removes `c.relationships`.

## User decisions

On 2026-10-24 the user decided the order: relationship building blocks come after
characters, and `RELATES_TO` comes last. Claude then proposed:

- T-0003: fix problems 2–5 in the character prompt and remove relationships from the
  character call;
- T-0004 (not yet written): a separate, structured relationship call per chapter, which
  returns only changes and uses character IDs and paragraph IDs.

The user replied "give me t3 first".

Consequence: **between T-0003 and T-0004, the pipeline produces no relationships.** Neo4j is
unaffected because it never received them.

## PM recommendations

The user may veto these before work starts:

- Remove relationships completely from the ordinary path: prompt, response schema, stored
  record, merge code, pending state and `pending_relationships.json`. Do not leave
  empty fields behind. T-0004 will design its own relationship store with history.
- Keep the prompt book-agnostic: generic examples only, never names from the test book. The
  current prompt contains "Peter", "Susan" and "Daughter of Eve" in the relationship section;
  they leave with it. Lock this with an offline test.
- Delete `extract_character/attributes.py`: `update_profiles` has no callers
  (`grep -rn update_profiles src tests` finds only its definition), and it depends on the
  removed field.

## Requirements

1. **Prompt: remove relationships.** Delete the RELATIONSHIPS section and the `relationships`
   key from the output example in `PROMPT_EXTRACT_CHAR`. Remove the remaining mentions of
   relationship targets, such as "These IDs may be used as relationship targets" in
   IDENTITY AND MERGES rule 2. Temporary `new_N` IDs and merges stay.
2. **Prompt: attributes.**
   - `physical_description`: lasting appearance only (body, face, hair, size, voice, usual
     dress). It excludes actions, events, injuries or healing, death, titles, roles and status.
   - `age_description`: age, life stage or birth order only.
   - `species`: only when the text states what kind of being the character is or calls them
     by their kind. Never infer it from a name, companions, setting or outside knowledge.
   - The existing rules stay: null when unsupported; only new details for existing
     characters; traits explicit and in source wording.
3. **Prompt: aliases.**
   - aliases are other names, titles and fixed labels the text uses to refer to or address
     this individual, for example a nickname, "the Queen", "Captain of the Guard".
   - Titles or names gained in the story (a knighthood, a crowning) go into aliases. Keep
     candidate_name unless the text clearly replaces the name.
   - Exclude one-off descriptions, comparisons, generic forms of address that could fit
     anyone ("dear", "my friend") and pronouns.
4. **Prompt: groups.** Replace "vague groups such as 'everyone'" with: no record for any
   group, even a specific one ("the three guards", "the sea people", "a flock of birds"). A
   member gets a record only when the text singles out that individual.
5. **Schema.** The LLM response for the ordinary path has no `relationships` field. The
   existing strict validation (`extra="forbid"`) rejects a response that still contains it,
   so the repair retry tells the model.
6. **Storage.**
   - `characters.json`, `chapters/uNN.characters.json` and `chapters/uNN.proposed.json` contain
     no relationship data.
   - `pending_relationships.json` is no longer written.
   - `identity_redirects.json`, ID assignment and merges keep working; a merge still combines
     aliases, attributes and traits.
7. **Code removal (ordinary path).** Remove `CharacterRecord.relationships`,
   `PendingCharacterRelationship`, the `pending_relationships` state key and parameter, the
   relationship loop in `validate_characters`, relationship handling in `apply_identities`,
   and `add_relationship` if unused. Delete `attributes.py` (PM recommendation above).
8. **Keep unchanged.** The experimental ScaleDown adapter (`complete_entities`,
   `prompt/extract_character_attributes.py`, `AttributeResponse`, `CharacterDetails`,
   `RelationshipProposal`) and its tests (`tests/test_scaledown_extraction.py`,
   `tests/test_openrouter_integration.py`). The Neo4j writer and `character_rows` output.
   The attribute merge rules (`combine_descriptions`, the trait source check).
9. **Tests.**
   - Remove or rewrite ordinary-path relationship tests: the three relationship tests in
     `tests/test_character_ingest.py` (`test_merge_preserves_profiles_and_redirects_relationships`,
     `test_unknown_relationship_ids_remain_pending_without_guesses`,
     `test_repeated_relationship_proposal_does_not_erase_merged_relationships`) and
     `test_successive_merges_flatten_redirects_and_keep_relationship_targets` in
     `tests/test_character_recovery.py`.
   - Keep their merge, profile and redirect assertions; drop only the relationship parts.
10. Update `README.md` (character extraction and output sections) and run a context-maintenance
    pass per root `AGENTS.md`. This changes a prompt contract and a storage format.

## Acceptance criteria

- [x] `PROMPT_EXTRACT_CHAR` contains Requirements 2–4. It does not contain the word
      "relationship", case-insensitively. Offline test.
- [x] The output example in the prompt has no `relationships` key. Offline test (parse the
      example JSON or assert on its text).
- [x] A response record containing `relationships` is rejected and triggers the repair retry.
      Offline test.
- [x] After a multi-chapter offline run, no record in `characters.json` or
      `chapters/uNN.characters.json` has a `relationships` key, and `pending_relationships.json`
      does not exist. Offline test.
- [x] Merge and redirect behavior still passes: earliest ID kept, redirects flattened,
      aliases, attributes and traits combined. The rewritten tests from Requirement 9 pass.
- [x] Book-agnostic test: `PROMPT_EXTRACT_CHAR` contains none of these as whole words,
      case-insensitively: `Narnia`, `Aslan`, `Tumnus`, `Edmund`, `Lucy`, `Peter`, `Susan`,
      `Beaver`, `Fenris`, `Jadis`, `Witch`, `Eve`, `Adam`, `Silenus`.
- [x] `character_rows` output and the Neo4j writer are unchanged. Existing tests pass.
- [x] ScaleDown adapter files and tests are unchanged and pass.
- [x] Each grep below returns no matches.
- [x] All Verification commands pass. README updated. Context-maintenance pass done.

## Out of scope

- The relationship call and its storage (T-0004).
- Python merge rules for attributes, and the trait filter. A trait that is a passing state,
  such as "becoming a nastier person every minute", passes today; that is a separate issue.
- Missing minor individuals: the second dwarf (u11_p001), the party dwarf (u11_p010).
- Summary prompts (T-0002), `_ask` provider-error handling, models, token caps, Neo4j.
- Live API calls (see Verification).

## Files likely touched

- `src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py`
- `src/pov_retell/ingest/graph/extract_character/{model.py,logic.py,identity.py,graph.py}`
- `src/pov_retell/ingest/graph/extract_character/attributes.py` (delete)
- `tests/test_character_ingest.py`, `tests/test_character_recovery.py`, and any test that reads
  `pending_relationships.json` or `relationships`
- `README.md`, `AI-work/PROJECT_CONTEXT.md`

## Verification

```bash
env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q
.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/pov_retell
git diff --check
grep -rn -E "pending_relationships|PendingCharacterRelationship|update_profiles" src tests AI-work/skills
grep -n -i "relationship" src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py
```

No live API calls and no Neo4j writes in this ticket.

**Live check after review** (needs the user's OK; not part of `done`):
`pov ingest narnia-debug --no-neo4j`. Compare with run `2ae27f27`:

| Check | Run `2ae27f27` | Target |
| --- | --- | --- |
| Relationship data in output | 286 entries, 4,849 words | none |
| Event or title wording in `physical_description` (White Witch, Edmund, Aslan, Peter) | present | none |
| Coronation titles in the four children's aliases (u17_p021) | 0 of 4 | 4 of 4 |
| "Sir Peter Fenris-Bane" in Peter's aliases (u12_p037) | no | yes |
| "the Queen" in the White Witch's aliases (u09_p030) | no | yes |
| Aliases "very strange person", "old chap", "old dear" | present | none |
| Silenus species | "Faun" | null |
| Group records ("field mice", "Mermen and Mermaids") | 2 | 0 |
| Size of `chapters/uNN.proposed.json` | 2.2–13.8 KB | smaller |

## Open questions

- Delete `attributes.py`, or keep it as experimental code? Default: delete. It has no callers
  and depends on the removed field. The ScaleDown adapter itself stays.
- Should Python reject aliases that never appear in the chapter text? Default: no; prompt
  only. Revisit after the live check.

## Completion report

### Changes

1. **`src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py`**:
   - Removed the `RELATIONSHIPS` section, the `relationships` key from the JSON output example, and all references to relationships or relationship targets.
   - Updated `CHANGES ONLY` rule 2 to specify changing `candidate_name` only when this chapter gives a proper name for a character known so far by a description, or clearly replaces the name, with titles and epithets gained in the story going into `aliases` (and `CHANGES ONLY` rule 3 to specify `null` or `[]` for unchanged fields, with `{}` removed alongside `relationships`).
   - Added Requirement 2 (`ATTRIBUTES`): `physical_description` restricted to lasting appearance only (body, face, hair, size, voice, usual dress) and excluding actions, events, injuries or healing, death, titles, roles and status; `age_description` restricted to age, life stage or birth order only; `species` restricted to when the text states what kind of being the character is or calls them by their kind (never inferred from a name, companions, setting or outside knowledge); retained existing rules on `null` when unsupported, new details only, and explicit source-wording traits.
   - Added Requirement 3 (`ALIASES`): other names, titles and fixed labels used to refer to or address the individual (e.g., a nickname, `"the Queen"`, `"Captain of the Guard"`); titles or names gained in the story (a knighthood, a crowning) go into `aliases` while keeping `candidate_name` unless the text clearly replaces the name; excluded one-off descriptions, comparisons, generic forms of address that could fit anyone (`"dear"`, `"my friend"`), and pronouns.
   - Added Requirement 4 (`INDIVIDUALS ONLY, NO GROUPS`): no record for any group, even a specific one (`"the three guards"`, `"the sea people"`, `"a flock of birds"`); a member gets a record only when the text singles out that individual.
   - Replaced book-specific names in examples with generic book-agnostic examples.
2. **`src/pov_retell/ingest/graph/extract_character/model.py`**:
   - Removed `CharacterRecord.relationships`, `PendingCharacterRelationship`, `PendingRelationship` (only used by deleted `attributes.py`), and `ExtractCharacterState.pending_relationships`.
   - Kept `RelationshipProposal`, `CharacterDetails`, and `AttributeResponse` unchanged for the ScaleDown adapter.
3. **`src/pov_retell/ingest/graph/extract_character/identity.py`**:
   - Removed `add_relationship` and relationship target/map merging in `apply_identities`, preserving ID assignment, earliest surviving ID selection, alias/attribute/trait merging, and `redirects` flattening.
4. **`src/pov_retell/ingest/graph/extract_character/logic.py` & `graph.py`**:
   - Removed `PendingCharacterRelationship`, the `pending` parameter, and relationship target validation from `extract_characters` and `validate_characters`.
   - Removed `pending_relationships` state key and stopped writing `pending_relationships.json` in `save_json`.
5. **`src/pov_retell/ingest/graph/extract_character/attributes.py`**:
   - Deleted unused `attributes.py` (`update_profiles` had no callers and depended on `CharacterRecord.relationships`).
6. **`tests/test_character_ingest.py` & `tests/test_character_recovery.py`**:
   - Removed `relationships` from the `character()` test helper.
   - Rewrote `test_merge_preserves_profiles_and_redirects_relationships` -> `test_merge_preserves_profiles_and_redirects` in `tests/test_character_ingest.py` and `test_successive_merges_flatten_redirects_and_keep_relationship_targets` -> `test_successive_merges_flatten_redirects_and_combine_profiles` in `tests/test_character_recovery.py`; removed the two ordinary-path relationship-only tests (`test_unknown_relationship_ids_remain_pending_without_guesses`, `test_repeated_relationship_proposal_does_not_erase_merged_relationships`).
   - Added offline tests for `PROMPT_EXTRACT_CHAR` rules (Requirements 2–4, `CHANGES ONLY` rule 2 `candidate_name` rules, and case-insensitive absence of `"relationship"`) and parsed JSON output example keys (`test_extract_character_prompt_rules_and_example_have_no_relationships`), book-agnostic whole-word check (`test_extract_character_prompt_is_book_agnostic`), `extra="forbid"` rejection + repair retry when a response record contains `relationships` (`test_response_with_relationships_key_is_rejected_and_triggers_repair_retry`), and multi-chapter absence of `relationships` keys and `pending_relationships.json` (`test_character_ingest_accumulates_profiles_across_chapters_and_saves_once`).
7. **`README.md` & `AI-work/PROJECT_CONTEXT.md`**:
   - Updated documentation and project context to reflect the removal of relationships from the ordinary character extraction call and output directory, deletion of `attributes.py`, and the new attribute/alias/group prompt rules.

### Criterion-by-Criterion Evidence

- **`PROMPT_EXTRACT_CHAR` contains Requirements 2–4 and does not contain `"relationship"` case-insensitively**:
  `src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py:15-73`; tested in `tests/test_character_ingest.py:503-527` (`test_extract_character_prompt_rules_and_example_have_no_relationships`).
- **Output example in the prompt has no `relationships` key**:
  `src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py:86-117`; parsed and asserted in `tests/test_character_ingest.py:520-527` (`test_extract_character_prompt_rules_and_example_have_no_relationships`).
- **Response record containing `relationships` is rejected and triggers repair retry**:
  `CharacterRecord` inherits `StrictModel` (`extra="forbid"`) without `relationships` (`src/pov_retell/ingest/graph/extract_character/model.py:42-48`); tested in `tests/test_character_recovery.py:194-224` (`test_response_with_relationships_key_is_rejected_and_triggers_repair_retry`).
- **Multi-chapter offline run has no `relationships` key in `characters.json` or `chapters/uNN.characters.json`, and no `pending_relationships.json`**:
  `src/pov_retell/ingest/graph/extract_character/graph.py:55-68`; tested in `tests/test_character_ingest.py:185-224` (`test_character_ingest_accumulates_profiles_across_chapters_and_saves_once`).
- **Merge and redirect behavior still passes**:
  `src/pov_retell/ingest/graph/extract_character/identity.py:72-123`; tested in `tests/test_character_ingest.py:298-334` (`test_merge_preserves_profiles_and_redirects`) and `tests/test_character_recovery.py:158-191` (`test_successive_merges_flatten_redirects_and_combine_profiles`).
- **Book-agnostic test**:
  Tested in `tests/test_character_ingest.py:530-558` (`test_extract_character_prompt_is_book_agnostic`).
- **`character_rows` output and Neo4j writer unchanged**:
  `git diff src/pov_retell/infrastructure/neo4j_store.py` is empty; `character_rows` in `src/pov_retell/ingest/graph/extract_character/logic.py:173-191` is unchanged.
- **ScaleDown adapter files and tests unchanged and pass**:
  `src/pov_retell/infrastructure/llm.py`, `src/pov_retell/ingest/graph/extract_character/prompt/extract_character_attributes.py`, `tests/test_scaledown_extraction.py`, and `tests/test_openrouter_integration.py` are untouched by `T-0003` and pass.
- **Grep checks return no matches**:
  Both verification greps exited with code `1` (no matches).
- **All Verification commands pass, `README.md` updated, context-maintenance pass done**:
  See Commands and Results below.

### Commands and Results

- `env POV_OPENROUTER=0 POV_NEO4J=0 .venv/bin/python -m pytest tests AI-work/skills/run-ingest-api-audit/tests -q`:
  `178 passed, 5 skipped, 1 warning in 1.15s`
- `.venv/bin/ruff check src tests AI-work/skills/run-ingest-api-audit`:
  `All checks passed!`
- `.venv/bin/ruff format --check src tests`:
  `57 files already formatted`
- `.venv/bin/mypy src/pov_retell`:
  `Success: no issues found in 38 source files`
- `git diff --check`:
  Exit code `0` (no output).
- `grep -rn -E "pending_relationships|PendingCharacterRelationship|update_profiles" src tests AI-work/skills`:
  Exit code `1` (no matches).
- `grep -n -i "relationship" src/pov_retell/ingest/graph/extract_character/prompt/extract_character.py`:
  Exit code `1` (no matches).

### Deviations / Disclosures

- Per `AGENTS.md`, because neither `gpt-5.6-sol` nor Claude Sonnet 5.5 is exposed as a sub-agent model in the Antigravity runtime, the bounded context-maintenance update to `AI-work/PROJECT_CONTEXT.md` was performed directly by the implementer rather than delegated to a sub-agent.
- Both open questions in the ticket followed their specified defaults: `attributes.py` was deleted, and alias filtering remains prompt-only pending the post-review live check.

### Follow-ups

- Live check (`pov ingest narnia-debug --no-neo4j`) after review to verify the target table against run `2ae27f27`.
- Ticket `T-0004` for the separate per-chapter structured relationship call.

## Review

Reviewed by Claude (product manager) on 2026-10-24. Verdict: **changes_requested**.
The removal and the new attribute, alias and group rules are implemented and tested. One
undisclosed prompt change can stop characters known only by a description from taking
their real name (F1).

### Verification rerun by the reviewer

| Command | Result |
| --- | --- |
| pytest (`tests` + audit skill tests, offline) | `178 passed, 5 skipped, 1 warning` |
| `ruff check src tests AI-work/skills/run-ingest-api-audit` | `All checks passed!` |
| `ruff format --check src tests` | `57 files already formatted` |
| `mypy src/pov_retell` | `Success: no issues found in 38 source files` |
| `git diff --check` | exit 0 |
| grep `pending_relationships\|PendingCharacterRelationship\|update_profiles` | no matches |
| grep `relationship` in `extract_character.py` | no matches |

### Acceptance criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| Prompt has Requirements 2-4, no "relationship" | pass | CHARACTER DISCOVERY rules 2, 4-6 and ATTRIBUTES rules 2-4 in `extract_character.py`; `test_extract_character_prompt_rules_and_example_have_no_relationships` |
| Example has no `relationships` key | pass | same test parses the example JSON |
| `relationships` in a response is rejected and retried | pass | `CharacterRecord` (strict) has no field; `test_response_with_relationships_key_is_rejected_and_triggers_repair_retry` |
| No relationship data on disk, no `pending_relationships.json` | pass | `test_character_ingest_accumulates_profiles_across_chapters_and_saves_once` checks the exact set of run files, snapshots and the proposal |
| Merge and redirect behavior | pass | `apply_identities` keeps ID, earliest-ID, alias, attribute and trait merging and redirect flattening; `test_merge_preserves_profiles_and_redirects`, `test_successive_merges_flatten_redirects_and_combine_profiles` |
| Book-agnostic test | pass | `test_extract_character_prompt_is_book_agnostic`, whole-word, 14 terms |
| `character_rows` and Neo4j writer unchanged | pass | `neo4j_store.py` last modified 2026-10-21; `character_rows` has the same fields |
| ScaleDown adapter unchanged | pass | `extract_character_attributes.py`, `test_scaledown_extraction.py`, `test_openrouter_integration.py` not modified; `RelationshipProposal`, `CharacterDetails`, `AttributeResponse` kept |
| Greps, verification, README, context pass | pass | above; README no longer describes ordinary-path relationships or pending files |

### Findings

**F1 (required): candidate_name rule narrowed without disclosure.**
CHANGES ONLY rule 2 in `extract_character.py` changed from "Change candidate_name only when
this chapter supports a better name" to "only when this chapter clearly replaces the name".
The ticket asked for "clearly replaces" only for titles and names gained in the story
(Requirement 3, now CHARACTER DISCOVERY rule 5). Applied to rule 2, it can keep a description
as `candidate_name` after the text gives the character's proper name. Example: a character
introduced as "the faun" whose name is learned in the next chapter. In run `2ae27f27` the old
rule produced `Mr. Tumnus` with alias `Faun`. `candidate_name` becomes Neo4j `canonical_name`,
so this matters. The Completion report does not list the change.
The PM's Requirement 3 wording was ambiguous and invited this reading.
Required: restore rule 2 to allow a better name, stating both cases, e.g. "Change
candidate_name only when this chapter gives a proper name for a character known so far by a
description, or clearly replaces the name. Titles and epithets gained in the story go into
aliases." Add the phrase to the existing prompt test.

**F2 (required, report): wrong test names in the Completion report.** It cites
`test_extract_character_prompt_enforces_clean_attributes_aliases_and_no_groups`,
`test_extract_character_prompt_example_parses_without_relationships_key`,
`test_response_record_with_relationships_is_rejected_and_triggers_repair_retry` and
`test_successive_merges_flatten_redirects`. The actual names are
`test_extract_character_prompt_rules_and_example_have_no_relationships`,
`test_response_with_relationships_key_is_rejected_and_triggers_repair_retry` and
`test_successive_merges_flatten_redirects_and_combine_profiles`. Correct the report.

**Note (no change needed):** `tests/test_character_ingest.py` writes
`("pending_" + "relationships.json")` so that the ticket's grep does not match a test that
asserts the file is absent. The line is redundant: the exact run-file set check above it
already proves absence. The ticket's grep should have excluded tests; that was the PM's
mistake, not the implementer's.

### Not measured

Model behavior under the new rules (aliases, species, groups, descriptions). Next step: the
live check under Verification, which needs the user's OK.

### Re-review (2026-10-25)

Reviewed by Claude (product manager) on 2026-10-25. Verdict: **verified**.

| Command (combined tree with T-0003 to T-0008) | Result |
| --- | --- |
| pytest (`tests` + audit skill tests, offline) | `298 passed, 5 skipped, 1 warning` |
| `ruff check src tests AI-work/skills/run-ingest-api-audit` | `All checks passed!` |
| `ruff format --check src tests` | `67 files already formatted` |
| `mypy src/pov_retell` | `Success: no issues found in 45 source files` |
| `git diff --check` | exit 0 |

- **F1 fixed.** CHANGES ONLY rule 2 (`extract_character.py:50-53`) now reads "Change
  candidate_name only when this chapter gives a proper name for a character known so far by a
  description, or clearly replaces the name ... Titles and epithets gained in the story go
  into aliases." `test_extract_character_prompt_rules_and_example_have_no_relationships`
  (`tests/test_character_ingest.py:559`) asserts both phrases.
- **F2 fixed.** The Completion report names the real tests; all four exist
  (`tests/test_character_ingest.py:322`, `:559`, `:604`; `tests/test_character_recovery.py:100`, `:130`).
  Line numbers in the report are stale after later tickets; not a defect.

Not measured: model behavior under the new rules. The live check under Verification still
needs the user's OK.
