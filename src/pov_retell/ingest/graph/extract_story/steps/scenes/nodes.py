"""Nodes and saved files of the scenes step."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.scenes import logic


def extract_scenes(state: StoryState, runtime: StoryRuntime) -> StoryState:
    index = state["chapter_index"]
    chapter = current_chapter(state)
    runtime.context.report(f"extract_scenes {chapter.unit_id}")
    return {
        "proposed_scenes": logic.extract_scene_map(
            runtime.context.llm,
            state["title"],
            chapter,
            state["chapters"][: index + 1],
            state["characters"],
            state["locations"],
            state["identity_redirects"],
            earlier_summaries(state),
        )
    }


def validate_scenes(state: StoryState, runtime: StoryRuntime) -> StoryState:
    index = state["chapter_index"]
    chapter = current_chapter(state)
    runtime.context.report(f"validate_scenes {chapter.unit_id}")
    records = logic.validate_scene_map(
        state["proposed_scenes"],
        chapter,
        state["chapters"][: index + 1],
        state["characters"],
        state["locations"],
        state["identity_redirects"],
    )
    return {"scenes": records, "scene_history": [*state["scene_history"], *records]}


def scenes_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    redirects = state["identity_redirects"]
    return [
        (f"chapters/{chapter_id}.scenes.proposed.json", state["proposed_scenes"].model_dump()),
        (f"chapters/{chapter_id}.scenes.json", [s.model_dump() for s in state["scenes"]]),
        (
            "scenes.json",
            [logic.resolve_scene(s, redirects).model_dump() for s in state["scene_history"]],
        ),
    ]
