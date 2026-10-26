from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from pov_retell.infrastructure.llm import MAX_RETRIES, LLMError, TextLLM
from pov_retell.ingest.graph.summarize_chapter.model import (
    BookMemory,
    ChapterSummary,
    SummarizeChapterResponse,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.summarize_book import (
    BOOK_SUMMARY_INPUT,
    PROMPT_SUMMARIZE_BOOK,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.summarize_chapter import (
    PROMPT_SUMMARIZE_CHAPTER,
    SUMMARY_INPUT,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_where_is_where import (
    PROMPT_UPDATE_WHERE_IS_WHERE,
    UPDATE_WHERE_IS_WHERE_REMINDER,
    WHERE_IS_WHERE_INPUT,
)
from pov_retell.ingest.graph.summarize_chapter.prompt.update_who_is_who import (
    PROMPT_UPDATE_WHO_IS_WHO,
    UPDATE_WHO_IS_WHO_REMINDER,
    WHO_IS_WHO_INPUT,
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
    surviving_names = {
        entry.strip().casefold()
        for first, second, _ in parsed
        for entry in [first, *second.split(",")]
        if entry.strip()
    }
    previous_names = [
        line.split("|")[0].strip() for line in _running_list_lines(previous_text, label)
    ]
    missing = [name for name in previous_names if name and name.casefold() not in surviving_names]
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


def update_who_is_who(
    llm: TextLLM,
    title: str,
    chapter: Chapter,
    previous_who_is_who: str,
) -> str:
    prompt = (
        WHO_IS_WHO_INPUT.format(
            book_title=title,
            chapter_id=chapter.unit_id,
            previous_who_is_who=previous_who_is_who,
            chapter_text=chapter.text,
        )
        + UPDATE_WHO_IS_WHO_REMINDER
    )
    error = ""
    for attempt in range(1 + MAX_RETRIES):
        request = prompt if attempt == 0 else f"{prompt}\n\nRejected: {error}"
        reply = llm.complete_text(request, system_prompt=PROMPT_UPDATE_WHO_IS_WHO)
        try:
            return validate_who_is_who(reply, previous_who_is_who)
        except ValueError as exc:
            error = str(exc)
    raise LLMError(f"no valid WHO IS WHO after {1 + MAX_RETRIES} attempts: {error}")


def update_where_is_where(
    llm: TextLLM,
    title: str,
    chapter: Chapter,
    previous_where_is_where: str,
) -> str:
    prompt = (
        WHERE_IS_WHERE_INPUT.format(
            book_title=title,
            chapter_id=chapter.unit_id,
            previous_where_is_where=previous_where_is_where,
            chapter_text=chapter.text,
        )
        + UPDATE_WHERE_IS_WHERE_REMINDER
    )
    error = ""
    for attempt in range(1 + MAX_RETRIES):
        request = prompt if attempt == 0 else f"{prompt}\n\nRejected: {error}"
        reply = llm.complete_text(request, system_prompt=PROMPT_UPDATE_WHERE_IS_WHERE)
        try:
            return validate_where_is_where(reply, previous_where_is_where)
        except ValueError as exc:
            error = str(exc)
    raise LLMError(f"no valid WHERE IS WHERE after {1 + MAX_RETRIES} attempts: {error}")


def summarize_chapter(
    llm: TextLLM,
    title: str,
    chapter: Chapter,
    previous_summaries: Sequence[ChapterSummary] = (),
) -> SummarizeChapterResponse:
    source = SUMMARY_INPUT.format(
        book_title=title,
        chapter_id=chapter.unit_id,
        previous_book_summary=format_previous_context(previous_summaries),
        chapter_text=chapter.text,
    )
    chapter_summary = llm.complete_text(source, system_prompt=PROMPT_SUMMARIZE_CHAPTER)
    previous_who_is_who = previous_summaries[-1].who_is_who if previous_summaries else ""
    who_is_who = update_who_is_who(llm, title, chapter, previous_who_is_who)
    previous_where_is_where = previous_summaries[-1].where_is_where if previous_summaries else ""
    where_is_where = update_where_is_where(llm, title, chapter, previous_where_is_where)
    return SummarizeChapterResponse(
        chapter_summary=chapter_summary,
        who_is_who=who_is_who,
        where_is_where=where_is_where,
    )


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
