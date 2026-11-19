"""Nodes and saved files of the relationships step."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.relationships import logic


def extract_relationships(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"extract_relationships {chapter.unit_id}")
    # Characters merged in this chapter retire IDs: point the open relationships at the survivors.
    relationships = logic.rewrite_relationships_for_redirects(
        state["relationships"],
        state["identity_redirects"],
        {c.unit_id: i for i, c in enumerate(state["chapters"])},
    )
    return {
        "relationships": relationships,
        "proposed_relationships": logic.extract_relationships(
            runtime.context.llm,
            state["title"],
            chapter,
            state["characters"],
            state["active_character_ids"],
            relationships,
            state["next_relationship_number"],
            state["identity_redirects"],
            earlier_summaries(state),
        ),
    }


def validate_relationships(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"validate_relationships {chapter.unit_id}")
    records, next_number = logic.validate_relationships(
        state["proposed_relationships"],
        state["relationships"],
        state["next_relationship_number"],
        state["characters"],
        state["identity_redirects"],
        chapter,
    )
    return {"relationships": records, "next_relationship_number": next_number}


def relationships_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    records = [r.model_dump() for r in state["relationships"]]
    return [
        (
            f"chapters/{chapter_id}.relationships.proposed.json",
            state["proposed_relationships"].model_dump(),
        ),
        (f"chapters/{chapter_id}.relationships.json", records),
        ("relationships.json", records),
    ]
