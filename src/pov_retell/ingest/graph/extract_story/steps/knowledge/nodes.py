"""Nodes and saved files of the knowledge step."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.knowledge import logic


def extract_knowledge(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"extract_knowledge {chapter.unit_id}")
    return {
        "proposed_knowledge": logic.extract_knowledge(
            runtime.context.llm,
            state["title"],
            chapter,
            state["scenes"],
            state["characters"],
            state["chapter_events"],
            state["claims"],
            state["next_claim_number"],
            state["knowledge"],
            state["identity_redirects"],
            earlier_summaries(state),
        )
    }


def validate_knowledge(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"validate_knowledge {chapter.unit_id}")
    chapter_knowledge, claims, next_number = logic.validate_knowledge(
        state["proposed_knowledge"],
        chapter,
        state["scenes"],
        state["characters"],
        state["identity_redirects"],
        state["chapter_events"],
        state["claims"],
        state["next_claim_number"],
        state["knowledge"],
    )
    return {
        "chapter_knowledge": chapter_knowledge,
        "claims": claims,
        "next_claim_number": next_number,
        "knowledge": [*state["knowledge"], *chapter_knowledge.acquisitions],
    }


def knowledge_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    redirects = state["identity_redirects"]
    return [
        (
            f"chapters/{chapter_id}.knowledge.proposed.json",
            state["proposed_knowledge"].model_dump(),
        ),
        (f"chapters/{chapter_id}.knowledge.json", state["chapter_knowledge"].model_dump()),
        (
            "knowledge.json",
            [logic.resolve_knowledge(k, redirects).model_dump() for k in state["knowledge"]],
        ),
    ]
