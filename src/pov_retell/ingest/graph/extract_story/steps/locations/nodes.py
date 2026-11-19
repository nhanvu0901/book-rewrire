"""Nodes and saved files of the locations step."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.locations import logic


def extract_locations(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"extract_locations {chapter.unit_id}")
    return {
        "proposed_locations": logic.extract_locations(
            runtime.context.llm,
            state["title"],
            chapter,
            state["locations"],
            state["next_location_number"],
            earlier_summaries(state),
        )
    }


def validate_locations(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"validate_locations {chapter.unit_id}")
    records, next_number = logic.validate_locations(
        state["proposed_locations"],
        state["locations"],
        state["next_location_number"],
    )
    return {"locations": records, "next_location_number": next_number}


def locations_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    records = [loc.model_dump() for loc in state["locations"]]
    return [
        (
            f"chapters/{chapter_id}.locations.proposed.json",
            state["proposed_locations"].model_dump(),
        ),
        (f"chapters/{chapter_id}.locations.json", records),
        ("locations.json", records),
    ]
