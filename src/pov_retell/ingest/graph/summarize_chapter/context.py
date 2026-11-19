from collections.abc import Callable
from dataclasses import dataclass

from pov_retell.infrastructure.llm import JsonLLM, TextLLM


@dataclass(frozen=True)
class SummaryContext:
    """Dependencies of the summarize_chapter graph, passed at invoke time."""

    text_llm: TextLLM
    # WHO IS WHO / WHERE IS WHERE card updates need JSON, so they use the extract client.
    card_llm: JsonLLM
    on_step: Callable[[str], None] | None = None

    def report(self, message: str) -> None:
        if self.on_step is not None:
            self.on_step(message)
