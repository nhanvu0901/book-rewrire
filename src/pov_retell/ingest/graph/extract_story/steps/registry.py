"""The extraction steps in order. Each step reads only what earlier steps produced."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import StoryState
from pov_retell.ingest.graph.extract_story.steps.characters.nodes import (
    characters_files,
    extract_characters,
    validate_characters,
)
from pov_retell.ingest.graph.extract_story.steps.events.nodes import (
    events_files,
    extract_events,
    validate_events,
)
from pov_retell.ingest.graph.extract_story.steps.knowledge.nodes import (
    extract_knowledge,
    knowledge_files,
    validate_knowledge,
)
from pov_retell.ingest.graph.extract_story.steps.locations.nodes import (
    extract_locations,
    locations_files,
    validate_locations,
)
from pov_retell.ingest.graph.extract_story.steps.relationships.nodes import (
    extract_relationships,
    relationships_files,
    validate_relationships,
)
from pov_retell.ingest.graph.extract_story.steps.scenes.nodes import (
    extract_scenes,
    scenes_files,
    validate_scenes,
)


class Node(Protocol):
    """A graph node. LangGraph passes the runtime context by keyword."""

    def __call__(self, state: StoryState, *, runtime: StoryRuntime) -> StoryState: ...


@dataclass(frozen=True)
class Step:
    """One extraction step: an LLM call, its validation, and the files it saves."""

    name: str
    extract: Node
    validate: Node
    # (path relative to the run directory, JSON value) for the chapter just validated.
    files: Callable[[StoryState], list[tuple[str, Any]]]


STEPS: tuple[Step, ...] = (
    Step("characters", extract_characters, validate_characters, characters_files),
    Step("relationships", extract_relationships, validate_relationships, relationships_files),
    Step("locations", extract_locations, validate_locations, locations_files),
    Step("scenes", extract_scenes, validate_scenes, scenes_files),
    Step("events", extract_events, validate_events, events_files),
    Step("knowledge", extract_knowledge, validate_knowledge, knowledge_files),
)
