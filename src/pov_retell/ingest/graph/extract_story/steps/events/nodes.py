"""Nodes and saved files of the events step (events, utterances and claims)."""

from typing import Any

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import (
    StoryState,
    current_chapter,
    earlier_summaries,
)
from pov_retell.ingest.graph.extract_story.steps.events import logic


def extract_events(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"extract_events {chapter.unit_id}")
    return {
        "proposed_events": logic.extract_events(
            runtime.context.llm,
            state["title"],
            chapter,
            state["scenes"],
            state["characters"],
            state["claims"],
            state["next_claim_number"],
            state["identity_redirects"],
            earlier_summaries(state),
        )
    }


def validate_events(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(f"validate_events {chapter.unit_id}")
    chapter_events, claims, next_number = logic.validate_events(
        state["proposed_events"],
        chapter,
        state["scenes"],
        state["characters"],
        state["identity_redirects"],
        state["claims"],
        state["next_claim_number"],
    )
    return {
        "chapter_events": chapter_events,
        "claims": claims,
        "next_claim_number": next_number,
        "events": [*state["events"], *chapter_events.events],
        "utterances": [*state["utterances"], *chapter_events.utterances],
    }


def events_files(state: StoryState) -> list[tuple[str, Any]]:
    chapter_id = current_chapter(state).unit_id
    redirects = state["identity_redirects"]
    return [
        (f"chapters/{chapter_id}.events.proposed.json", state["proposed_events"].model_dump()),
        (f"chapters/{chapter_id}.events.json", state["chapter_events"].model_dump()),
        ("claims.json", [logic.resolve_claim(c, redirects).model_dump() for c in state["claims"]]),
        ("events.json", [logic.resolve_event(e, redirects).model_dump() for e in state["events"]]),
        (
            "utterances.json",
            [logic.resolve_utterance(u, redirects).model_dump() for u in state["utterances"]],
        ),
    ]
