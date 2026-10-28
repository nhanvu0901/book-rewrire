from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from pov_retell.infrastructure.llm import JsonLLM, TextLLM
from pov_retell.ingest.graph.summarize_chapter.model import (
    BookMemory,
    Card,
    CardChanges,
    ChapterSummary,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.summarize_book import (
    BOOK_SUMMARY_INPUT,
    PROMPT_SUMMARIZE_BOOK,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.summarize_chapter import (
    PROMPT_SUMMARIZE_CHAPTER,
    SUMMARY_INPUT,
)
from pov_retell.ingest.model import Chapter


def format_chapter_summaries(summaries: Sequence[ChapterSummary]) -> str:
    return "\n\n".join(
        f"[{summary.chapter_id}]\n{summary.chapter_summary}" for summary in summaries
    )


def format_previous_context(summaries: Sequence[ChapterSummary]) -> str:
    if not summaries:
        return ""
    chapter_summaries = format_chapter_summaries(summaries)
    last = summaries[-1]
    return (
        f"WHO IS WHO\n{last.who_is_who}\n\n"
        f"WHERE IS WHERE\n{last.where_is_where}\n\n"
        f"CHAPTER SUMMARIES\n{chapter_summaries}"
    )


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


def _name_key(text: str) -> str:
    return name_key(text)


def render_cards(cards: dict[str, Card], *, with_ids: bool) -> str:
    """Text form. With ids for the prompt; without ids for the saved summary file."""
    lines = []
    for card_id, card in cards.items():
        other_names = ", ".join(card.other_names) or "-"
        line = f"{card.name} | {other_names} | {card.card}"
        lines.append(f"{card_id} | {line}" if with_ids else line)
    return "\n".join(lines)


def check_changes(changes: CardChanges, cards: dict[str, Card]) -> None:
    """Raise ValueError for a reply that cannot be merged. The client then retries."""
    unknown = [item.id for item in changes.update if item.id not in cards]
    if unknown:
        raise ValueError(f"update uses unknown id(s): {', '.join(unknown)}")
    updated_ids = [item.id for item in changes.update]
    if len(updated_ids) != len(set(updated_ids)):
        raise ValueError("update lists the same id more than once")

    known = {
        name_key(name): card_id
        for card_id, card in cards.items()
        for name in [card.name, *card.other_names]
    }
    seen: set[str] = set()
    for item in changes.add:
        for name in [item.name, *item.other_names]:
            key = name_key(name)
            if key in known:
                raise ValueError(f"{name!r} is already listed as {known[key]}; use update")
            if key in seen:
                raise ValueError(f"{name!r} is added twice")
            seen.add(key)


def changes_to_update(changes: CardChanges, cards: dict[str, Card], prefix: str) -> dict[str, Card]:
    """Turn a checked reply into the dict the reducer merges. New lines get the next ids."""
    update = {item.id: Card(**item.model_dump(exclude={"id"})) for item in changes.update}
    start = 1 + max((int(card_id[1:]) for card_id in cards), default=0)
    for number, card in enumerate(changes.add, start=start):
        update[f"{prefix}{number:03d}"] = card
    return update


def update_cards(
    llm: JsonLLM,
    rules: str,
    input_template: str,
    title: str,
    chapter_id: str,
    chapter_text: str,
    cards: dict[str, Card],
    prefix: str,
) -> dict[str, Card]:
    prompt = input_template.format(
        rules=rules,
        book_title=title,
        chapter_id=chapter_id,
        previous=render_cards(cards, with_ids=True) or "(empty)",
        chapter_text=chapter_text,
    )
    changes = llm.complete_json(prompt, CardChanges, check=lambda c: check_changes(c, cards))
    return changes_to_update(changes, cards, prefix)


def _running_list_lines(text: str, label: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and lines[0].rstrip(":").strip().casefold() == label.casefold():
        return lines[1:]
    return lines


def validate_running_list(
    text: str,
    previous_text: str = "",
    *,
    label: str,
    item_kind: str,
) -> str:
    lines = _running_list_lines(text, label)
    if not lines:
        raise ValueError(f"{label} must not be blank")
    parsed: list[tuple[str, str, str]] = []
    for line in lines:
        fields = [field.strip() for field in line.split("|")]
        if len(fields) != 3 or not all(fields):
            raise ValueError(
                f"{label} line must have three non-empty fields separated by '|': {line!r}"
            )
        parsed.append((fields[0], fields[1], fields[2]))
    surviving_keys = {
        name_key(entry)
        for first, second, _ in parsed
        for entry in [first, *second.split(",")]
        if entry.strip()
    }
    previous_names = [
        line.split("|")[0].strip() for line in _running_list_lines(previous_text, label)
    ]
    missing = [name for name in previous_names if name and name_key(name) not in surviving_keys]
    if missing:
        raise ValueError(f"{label} dropped earlier {item_kind}(s): {', '.join(missing)}")
    return "\n".join(f"{first} | {second} | {third}" for first, second, third in parsed)


def validate_who_is_who(text: str, previous_who_is_who: str = "") -> str:
    return validate_running_list(
        text,
        previous_who_is_who,
        label="WHO IS WHO",
        item_kind="character",
    )


def validate_where_is_where(text: str, previous_where_is_where: str = "") -> str:
    return validate_running_list(
        text,
        previous_where_is_where,
        label="WHERE IS WHERE",
        item_kind="place",
    )


def summarize_chapter(
    llm: TextLLM,
    title: str,
    chapter: Chapter,
    previous_summaries: Sequence[ChapterSummary] = (),
) -> str:
    source = SUMMARY_INPUT.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=format_previous_context(previous_summaries),
        chapter_text=chapter.text,
    )
    return llm.complete_text(source, system_prompt=PROMPT_SUMMARIZE_CHAPTER)


def summarize_book(
    llm: TextLLM,
    title: str,
    summaries: Sequence[ChapterSummary],
    who_is_who: str,
    where_is_where: str = "",
) -> BookMemory:
    prompt = BOOK_SUMMARY_INPUT.format(
        book_title=title,
        chapter_summaries=format_chapter_summaries(summaries),
    )
    core_memory = llm.complete_text(prompt, system_prompt=PROMPT_SUMMARIZE_BOOK)
    return BookMemory(
        who_is_who=who_is_who,
        where_is_where=where_is_where,
        core_memory=core_memory,
    )


def save_summary(path: Path, summary: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    try:
        temporary.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
