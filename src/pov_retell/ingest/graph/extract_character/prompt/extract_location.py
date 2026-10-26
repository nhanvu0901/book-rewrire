PROMPT_EXTRACT_LOCATION = """\
Extract new and updated story locations for one chapter of an English novel.

You may already know this book from outside knowledge. Ignore that knowledge completely.
Use only the supplied prior context, existing locations JSON, and the current chapter text.

INPUTS
- <previous_book_summary>: WHO IS WHO, WHERE IS WHERE, and chapter summaries through the
  previous chapter. Use WHERE IS WHERE to recognize recurring places and alternative names,
  but treat the current chapter text as the primary evidence.
- <existing_locations_json>: all locations extracted through the previous chapter, each with
  location_id, name, aliases, kind, and part_of.
- <chapter_text>: the original text of the current chapter with paragraph IDs.

WHAT COUNTS AS A PLACE
- Places are buildings, rooms, lands, regions, landmarks, and natural features where scenes
  happen or that characters travel through or refer to as settings.
- Include named places, and unnamed places where action happens under their clearest
  supported description (for example "the back kitchen" or "the river ford").
- Objects (for example a cup, chair, or sword) and people are not places, unless
  the text uses a landmark name for a site where scenes take place.

CHANGES ONLY
- Return only:
  1. new places that appear in this chapter (`"location_id": "new_1"`, `"new_2"`, ...);
  2. existing places (`"location_id": "loc_001"`, ...) that appear in or gain new information
     from this chapter.
- Omit existing places that do not appear and gain no new information in this chapter.
- Return `{{"locations": []}}` when no new places appear and no existing place changes.
- Before creating any `"new_N"`, check every `name` and `aliases` entry in
  <existing_locations_json>. If the place already exists under any name or description,
  reuse its existing `"loc_NNN"` ID.
- Each existing `"loc_NNN"` may appear at most once in the response.

FIELD RULES
- `name`: clearest canonical name supported by the text so far. If this chapter reveals a
  proper name for a place known so far by a description, update `name` to the proper name
  and include the old name in `aliases`.
- `aliases`: new alternative names, titles, or descriptions used for this place in this
  chapter. Send `[]` when no new aliases appear.
- `kind`: a concise lasting description of what kind of place it is, at most 12 words (for
  example `"coastal village"`, `"underground passage"`, `"desert oasis"`,
  `"timber watchtower"`). Set `kind` only when unknown or when this chapter corrects
  or sharpens it; otherwise send `null`.
- `part_of`: the `location_id` (`"loc_NNN"` or `"new_N"` from the same response) of the
  immediately containing larger place when the text explicitly places this location inside
  another place (for example a room inside a house, or a camp inside a forest). Send `null`
  when no containment is stated or when `part_of` is unchanged. Never set a place as
  `part_of` itself or create a containment cycle.

OUTPUT FORMAT
Return valid JSON matching this shape:
{{
  "locations": [
    {{
      "location_id": "new_1",
      "name": "the old manor",
      "aliases": ["the country house"],
      "kind": "large stone country house",
      "part_of": null
    }},
    {{
      "location_id": "new_2",
      "name": "the north attic",
      "aliases": [],
      "kind": "low upstairs room under the roof",
      "part_of": "new_1"
    }}
  ]
}}

Book title: {book_title}
Current chapter: {chapter_id}

<previous_book_summary>
{previous_book_summary}
</previous_book_summary>

<existing_locations_json>
{existing_locations_json}
</existing_locations_json>

<chapter_text>
{chapter_text}
</chapter_text>
"""
