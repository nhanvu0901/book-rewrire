"""Small text helpers shared by several steps: number patterns, title merging, text blocks.

A *block* is the unit that everything else counts in: a run of non-blank lines of the canonical
text. Candidates sit at block starts, and paragraphs are blocks.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

NUMBER_WORD = (
    r"(?:the\s+)?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|"
    r"twelfth|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
)
# A real roman numeral, so "MILD" or "DID" do not count; the lookahead keeps it non-empty.
ROMAN = r"(?=[MDCLXVI])M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"
# A chapter or part number, written as digits, a roman numeral or a word.
NUMBER = rf"(?:\d+|{ROMAN}|{NUMBER_WORD})"


def words(title: str) -> list[str]:
    """Case- and punctuation-insensitive words of a title."""
    return re.findall(r"\w+", title.casefold())


def contains_words(haystack: list[str], needle: list[str]) -> bool:
    """True when `needle` occurs as a run of whole words inside `haystack`."""
    if not needle or len(needle) > len(haystack):
        return False
    return any(
        haystack[i : i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1)
    )


def merge_titles(first: str, second: str) -> str:
    """Join a heading and its subtitle: ('CHAPTER I.', 'The Lamp') -> 'CHAPTER I: The Lamp'.

    Books split one title over two lines ("CHAPTER I." then "The Lamp"); both are candidates,
    and the unit should carry the whole title once.
    """
    head = first.strip().rstrip(".:;,- ")
    tail = second.strip()
    if contains_words(words(head), words(tail)):
        return head
    if contains_words(words(tail), words(head)):
        return tail
    return f"{head}: {tail}"


@dataclass(frozen=True)
class Block:
    start: int  # absolute offsets in the canonical text, trimmed of whitespace
    end: int
    text: str  # whitespace collapsed to single spaces


_BLOCK = re.compile(r"\S[^\n]*(?:\n[^\S\n]*\S[^\n]*)*")


def iter_blocks(text: str, start: int = 0, end: int | None = None) -> Iterator[Block]:
    """Yield the blocks of `text[start:end]`, with offsets relative to the whole text."""
    for match in _BLOCK.finditer(text, start, len(text) if end is None else end):
        raw = match.group(0).rstrip()
        yield Block(match.start(), match.start() + len(raw), " ".join(raw.split()))
