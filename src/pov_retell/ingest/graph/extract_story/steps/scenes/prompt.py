PROMPT_EXTRACT_SCENE_MAP = """\
Partition one chapter of an English novel into ordered scene segments.

You may already know this book from outside knowledge. Ignore that knowledge completely.
Use only the supplied prior context, character roster, locations list, and chapter text.

INPUTS
- <previous_book_summary>: WHO IS WHO, WHERE IS WHERE, and chapter summaries through the
  previous chapter.
- <character_roster_json>: all known characters with character_id, candidate_name, and aliases.
- <locations_json>: all known locations with location_id, name, aliases, and part_of.
- <chapter_text>: the original text of the current chapter with paragraph IDs.

SEGMENT DEFINITIONS
- **Segment:** consecutive paragraphs in one place and continuous time. Start a new segment
  when the place changes, time jumps, or the narration moves to a different group of
  characters.
- **Complete coverage:** segments must cover every paragraph of the current chapter in order
  from first to last, with no gaps and no overlaps (`start` <= `end`, both in this chapter).
- **location_id:** the `"loc_NNN"` ID of the place where the segment happens, or `null` when
  no place applies (for example pure narrator commentary without a setting). For a journey
  across several spots inside a larger place, use the containing larger place's ID.
- **present_ids:** character IDs (`"char_NNN"`) who are physically present in the segment
  according to the text.
- **mentioned_ids:** character IDs (`"char_NNN"`) who are named or referred to in the segment
  but are not physically present. `present_ids` and `mentioned_ids` must never overlap.
- **viewpoint_ids:** character IDs whose perceptions or thoughts the narration follows in
  this segment. Every ID in `viewpoint_ids` must also be in `present_ids`. Leave `[]` when
  the narration follows no specific character's viewpoint.
- **time:**
  - `relation`: one of `"continues"`, `"later"`, `"parallel"`, `"flashback"`, `"time_jump"`.
    - `"continues"`: continues directly from the previous segment (or starts chapter 1).
    - `"later"`: a short gap in time within the same ongoing sequence.
    - `"parallel"`: happens during or alongside an earlier segment (for example when the
      narrative switches from one group to another).
    - `"flashback"`: narrates events from an earlier time before the surrounding narrative.
    - `"time_jump"`: a significant jump forward in story time.
  - `anchor`: required for `"parallel"` and `"flashback"` — the earlier paragraph ID
    (`"uNN_pNNN"`, either earlier in this chapter before `start` or in an earlier chapter)
    that the segment relates to. Must be `null` for `"continues"`, `"later"`, and
    `"time_jump"`.
  - `note`: at most 8 words of time wording taken from the text (for example
    `"while the others waited"`, `"three days later"`), or `null`.
- **label:** concise summary of the segment, at most 15 words.
- Use only character IDs and location IDs from the supplied JSON inputs. Groups get no IDs.

OUTPUT FORMAT
Return valid JSON matching this shape:
{{
  "segments": [
    {{
      "start": "u02_p001",
      "end": "u02_p008",
      "location_id": "loc_001",
      "present_ids": ["char_001", "char_002"],
      "mentioned_ids": ["char_003"],
      "viewpoint_ids": ["char_001"],
      "time": {{
        "relation": "continues",
        "anchor": null,
        "note": null
      }},
      "label": "Mara and Jo wait inside the old manor"
    }}
  ]
}}

Book title: {book_title}
Current chapter: {chapter_id}

<previous_book_summary>
{previous_book_summary}
</previous_book_summary>

<character_roster_json>
{character_roster_json}
</character_roster_json>

<locations_json>
{locations_json}
</locations_json>

<chapter_text>
{chapter_text}
</chapter_text>
"""
