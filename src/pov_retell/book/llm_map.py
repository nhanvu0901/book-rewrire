"""Step A2b: let the LLM classify the candidates (`pov extract`).

"The LLM proposes, code anchors and checks." The model never sees the book text and never
returns an offset: it receives the candidate list (id, kind, text, a short preview) and answers
with an id, a role and a clean title for each one. Code cuts the text (cut.py) and validates the
result.
"""

from functools import partial

from pov_retell.book.models import Book, Candidate, MapItem, MapResponse
from pov_retell.infrastructure.llm import JsonLLM

BATCH_SIZE = 80  # candidates per call, so the JSON answer fits well inside the token limit

PROMPT = """\
You are a literary structure analyst inside an automated book-ingestion system.
A program has already extracted *candidates*: places in the text that might start a structural
unit (headings, table-of-contents targets, heading-like lines). Say what each candidate is. You
do not see the full text and you must never invent positions.

Book: {title} by {author} ({format}). Candidates in this request: batch {batch} of {batches}.
{open_parts}
Candidates in reading order:
{candidates}

Instructions:
1. Give every candidate one role:
   - "front": title page, dedication, preface, introduction, or a subtitle line that merely
     continues the heading just above it.
   - "toc": a table-of-contents listing or one of its entries.
   - "license": Project Gutenberg header or footer, licence text.
   - "body_unit": the start of a narrative unit that will be retold (chapter, letter, numbered
     or titled section, a prologue or epilogue that is part of the story).
   - "part_heading": a heading that groups chapters ("PART ONE", "BOOK II").
   - "back": appendix, glossary, notes, index, anything after the story.
2. A chapter often shows up as several adjacent candidates (a number, a title, a navigation
   entry). Mark exactly ONE of them "body_unit": the earliest. Give it the full clean title
   ("Chapter I: The Old Sea-dog"). Mark the others "front".
   A caption inside a chapter heading ('He rode a black horse. CHAPTER III.') is still the
   heading of that chapter: use only the chapter heading as the title.
3. Mark "body_unit" only the divisions at the same level as the other chapters. A letter or
   poem inside a chapter is not a unit.
4. A table of contents lists titles BEFORE the story starts; its entries have no story text
   after them. A real heading is followed by story text: never mark it "toc".
5. "unit_kind" is one of "chapter", "letter", "part", "section", "front", "back": "part" for a
   part_heading, "front" for front and toc, "back" for license and back; a body_unit is a
   "chapter", "letter" or "section".
6. "parent_cand_id" is the cand_id of the part_heading a chapter belongs to, or null. It may
   only name a part_heading that comes earlier in the reading order.
7. Answer for every candidate listed above, using only the cand_ids listed above.

Reply with one JSON object and nothing else (json only). Shape:
{{"items": [{{"cand_id": "cand_005", "role": "part_heading", "unit_kind": "part",
 "title": "Part One: The Old Buccaneer", "parent_cand_id": null}},
 {{"cand_id": "cand_006", "role": "body_unit", "unit_kind": "chapter",
 "title": "Chapter I: The Old Sea-dog", "parent_cand_id": "cand_005"}}]}}
"""


def llm_map(book: Book, candidates: list[Candidate], llm: JsonLLM) -> list[MapItem]:
    """Ask the LLM for the role of every candidate, in batches, and return the answers in order."""
    batches = [candidates[i : i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
    answers: dict[str, MapItem] = {}
    for number, batch in enumerate(batches, start=1):
        asked = [c.cand_id for c in batch]

        parts = [(i.cand_id, i.title) for i in answers.values() if i.role == "part_heading"]
        prompt = PROMPT.format(
            title=book.title,
            author=book.author,
            format=book.format,
            batch=number,
            batches=len(batches),
            open_parts=(
                "Part headings found in earlier batches: "
                + "; ".join(f'{cand_id} "{title}"' for cand_id, title in parts)
                + "\n"
                if parts
                else ""
            ),
            candidates="\n".join(
                f"- {c.cand_id} | kind={c.kind} | position={c.char_pos} | text={c.text!r} "
                f"| preview={c.preview!r}"
                for c in batch
            ),
        )
        for item in llm.complete_json(
            prompt, MapResponse, partial(_check_covers, asked=asked)
        ).items:
            answers[item.cand_id] = item
    return [answers[c.cand_id] for c in candidates]


def _check_covers(response: MapResponse, *, asked: list[str]) -> None:
    """Reject an answer that skips, repeats or invents candidate ids (the LLM then retries)."""
    answered = [item.cand_id for item in response.items]
    unknown = sorted(set(answered) - set(asked))
    repeated = sorted({i for i in answered if answered.count(i) > 1})
    missing = [i for i in asked if i not in answered]
    problems = [
        f"{label}: {', '.join(ids)}"
        for label, ids in (
            ("unknown ids", unknown),
            ("repeated ids", repeated),
            ("missing ids", missing),
        )
        if ids
    ]
    if problems:
        raise ValueError("; ".join(problems))
