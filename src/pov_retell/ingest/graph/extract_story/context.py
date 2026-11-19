from collections.abc import Callable
from dataclasses import dataclass

from langgraph.runtime import Runtime

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.model import GraphWriter


@dataclass(frozen=True)
class StoryContext:
    """Dependencies of the extract_story graph, passed at invoke time."""

    llm: JsonLLM
    writer: GraphWriter | None = None
    on_step: Callable[[str], None] | None = None

    def report(self, message: str) -> None:
        if self.on_step is not None:
            self.on_step(message)


StoryRuntime = Runtime[StoryContext]
