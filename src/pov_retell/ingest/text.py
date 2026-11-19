"""Text helpers shared by the summary and extraction graphs. Pure functions, no I/O."""

import re

_QUOTE_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "‛": "'",
        "ʼ": "'",
        "′": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "″": '"',
    }
)


def name_key(text: str) -> str:
    """Comparison key for names (T-0012): case, quotes and spacing do not matter."""
    return " ".join(text.translate(_QUOTE_TRANSLATION).split()).casefold()


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def appears_in_source(value: str, source: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(normalized(value)) + r"(?!\w)", source) is not None


def unique_names(names: list[str]) -> list[str]:
    result: dict[str, str] = {}
    for name in names:
        result.setdefault(normalized(name), name)
    return list(result.values())


def combine_descriptions(first: str | None, second: str | None) -> str | None:
    parts = [part for value in (first, second) if value for part in value.split("; ")]
    return "; ".join(unique_names(parts)) or None
