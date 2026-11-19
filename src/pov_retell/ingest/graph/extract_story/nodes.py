"""Book-level nodes of the extract_story graph: setup and the chapter loop."""

from typing import Literal

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import StoryState


def initialize(state: StoryState, runtime: StoryRuntime) -> StoryState:
    if not state["chapters"]:
        raise ValueError("Character extraction requires chapters")
    if [s.chapter_id for s in state["summaries"]] != [c.unit_id for c in state["chapters"]]:
        raise ValueError("Chapter summaries must match the source chapters in order")
    return {
        "chapter_index": 0,
        "characters": [],
        "active_character_ids": [],
        "next_character_number": 1,
        "identity_redirects": {},
        "relationships": [],
        "next_relationship_number": 1,
        "locations": [],
        "next_location_number": 1,
        "scenes": [],
        "scene_history": [],
        "claims": [],
        "next_claim_number": 1,
        "events": [],
        "utterances": [],
        "knowledge": [],
    }


def next_step(state: StoryState) -> Literal["next_chapter", "done"]:
    return "next_chapter" if state["chapter_index"] < len(state["chapters"]) else "done"
