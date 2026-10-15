"""Phase A in one function: file or URL -> validated units -> paragraphs.

    A1  load + detect format + sha256            load.py
    A2a find structure candidates                candidates.py
    A2b build the structure map (heuristic|llm)  heuristic_map.py / llm_map.py
    A2c cut by position and VALIDATE             cut.py
    A3  split paragraphs, flag anomalies         paragraphs.py

Nothing here touches a database or the network (except downloading a URL and, for the optional
LLM map, one DeepSeek call). The result is a plain `ExtractedBook`; output.py saves it as files.
"""

from pov_retell.candidates import find_candidates
from pov_retell.cut import cut_units
from pov_retell.heuristic_map import heuristic_map
from pov_retell.llm import JsonLLM
from pov_retell.llm_map import llm_map
from pov_retell.load import Source, load_source, make_book
from pov_retell.models import NARRATIVE_KINDS, ExtractedBook, MapMethod
from pov_retell.paragraphs import split_paragraphs


def extract_book(
    source: str | Source,
    map_method: MapMethod = "heuristic",
    llm: JsonLLM | None = None,
    book_id: str | None = None,
) -> ExtractedBook:
    """Run A1-A3. `source` is a path, an http(s) URL, or an already loaded `Source`."""
    loaded = source if isinstance(source, Source) else load_source(source)

    # A1: what file is this?
    book = make_book(loaded, book_id)

    # A2a: the text we will cut, and every place that could start a unit
    canonical_text, candidates = find_candidates(loaded.content, book.format)

    # A2b: decide which candidates are real units
    if map_method == "llm":
        if llm is None:
            raise ValueError("--map llm needs an LLM client")
        items = llm_map(book, candidates, llm)
    else:
        items = heuristic_map(candidates, canonical_text)

    # A2c: cut by position; raises StructureMapError if the cut is not valid
    units, warnings = cut_units(canonical_text, candidates, items)

    # A3: paragraphs with stable ids
    paragraphs = split_paragraphs(units, canonical_text, candidates)
    with_text = {p.unit_id for p in paragraphs}
    warnings += [
        f"unit {u.id} ({u.title!r}) has no paragraphs"
        for u in units
        if u.kind in NARRATIVE_KINDS and u.id not in with_text
    ]

    return ExtractedBook(
        book=book,
        map_method=map_method,
        candidates=candidates,
        map_items=items,
        units=units,
        paragraphs=paragraphs,
        warnings=warnings,
        canonical_text=canonical_text,
    )
