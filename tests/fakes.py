"""A fake LLM: lets the tests run the LLM-map code path with no network and no money."""

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from pov_retell.models import Candidate

T = TypeVar("T", bound=BaseModel)


class FakeLLM:
    """Implements `JsonLLM`. Like the real client it validates the answer with Pydantic and runs
    `check`, but it does not retry: a rejected answer raises, so tests see the exact problem."""

    def __init__(self, answer: Callable[[str], dict[str, Any]]) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        self.prompts.append(prompt)
        value = schema.model_validate(self.answer(prompt))
        if check is not None:
            check(value)
        return value


def classify_like_an_llm(candidates: list[Candidate]) -> dict[str, Any]:
    """What a good model would answer for the sample story. Written WITHOUT the heuristic code,
    so the LLM-map path is tested against its own expectations."""
    items: list[dict[str, Any]] = []
    part: str | None = None
    for index, cand in enumerate(candidates):
        text = cand.text
        following = candidates[index + 1].text if index + 1 < len(candidates) else ""
        parent: str | None = None
        if "gutenberg" in text.lower() or text.startswith("Licence"):
            role, kind = "license", "front"
        elif text in ("CONTENTS", "The Lantern Keeper") or (
            cand.kind == "toc_link" and "Chapter" in text
        ):
            role, kind = "toc", "front"
        elif text.startswith("PART") and following.startswith("PART"):
            role, kind = "toc", "front"  # a part line right before another one: a contents list
        elif text.startswith("PART"):
            role, kind, part = "part_heading", "part", cand.cand_id
        elif text.upper().startswith("CHAPTER"):
            role, kind, parent = "body_unit", "chapter", part
        else:
            role, kind = "front", "front"  # a subtitle such as "The Lamp"
        items.append(
            {
                "cand_id": cand.cand_id,
                "role": role,
                "unit_kind": kind,
                "title": text.title() if role == "part_heading" else text,
                "parent_cand_id": parent,
            }
        )
    return {"items": items}
