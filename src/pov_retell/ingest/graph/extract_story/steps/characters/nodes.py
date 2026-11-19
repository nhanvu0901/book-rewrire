"""Nodes and saved files of the characters step."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.characters import logic


def extract_characters(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"extract_characters {chapter.unit_id}")
    return {
        "proposed": logic.extract_characters(
            runtime.context.llm,
            state["title"],
            chapter,
            state["characters"],
            state["next_character_number"],
            state["identity_redirects"],
            earlier_summaries(state),
        )
    }


def validate_characters(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"validate_characters {chapter.unit_id}")
    records, active, next_number, redirects = logic.validate_characters(
        state["proposed"],
        state["characters"],
        state["next_character_number"],
        state["identity_redirects"],
        chapter,
    )
    return {
        "characters": records,
        "active_character_ids": active,
        "next_character_number": next_number,
        "identity_redirects": redirects,
    }


def characters_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    records = [c.model_dump() for c in state["characters"]]
    return [
        (f"chapters/{chapter_id}.proposed.json", state["proposed"].model_dump()),
        (f"chapters/{chapter_id}.characters.json", records),
        ("characters.json", records),
    ]
