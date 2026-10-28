"""WHO IS WHO / WHERE IS WHERE with "changes only" replies and an upsert reducer.

Reference code for T-0013. It runs on its own with a fake LLM (no API calls):

    uv run python scratch/changes_only_lists.py

Each section says which project file it belongs to.
"""

import json
from collections.abc import Callable
from typing import Annotated, Any, TypedDict, TypeVar

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

T = TypeVar("T", bound=BaseModel)
MAX_RETRIES = 2

# ======================================================================================
# summarize_chapter/model.py
# ======================================================================================
SummaryText = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class Card(BaseModel):
    """One line of WHO IS WHO or WHERE IS WHERE."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: SummaryText
    other_names: list[SummaryText]
    card: SummaryText


class CardUpdate(Card):
    id: SummaryText


class CardChanges(BaseModel):
    """What the LLM returns: only new and changed lines."""

    model_config = ConfigDict(extra="forbid", strict=True)

    add: list[Card]
    update: list[CardUpdate]


def upsert_cards(current: dict[str, Card], update: dict[str, Card]) -> dict[str, Card]:
    """LangGraph reducer: new ids are added, known ids are replaced, nothing is dropped."""
    return {**current, **update}


class SummarizeChapterState(TypedDict, total=False):
    title: str
    chapters: list[str]
    chapter_index: int
    who_cards: Annotated[dict[str, Card], upsert_cards]
    where_cards: Annotated[dict[str, Card], upsert_cards]


# ======================================================================================
# summarize_chapter/logic.py
# ======================================================================================
QUOTES = str.maketrans({"’": "'", "‘": "'", "‛": "'", "ʼ": "'", "“": '"', "”": '"'})


def name_key(name: str) -> str:
    """Comparison key for names (T-0012): case, quotes and spacing do not matter."""
    return " ".join(name.translate(QUOTES).split()).casefold()


def render_cards(cards: dict[str, Card], *, with_ids: bool) -> str:
    """Text form. With ids for the prompt; without ids for the saved summary file."""
    lines = []
    for card_id, card in cards.items():
        other_names = ", ".join(card.other_names) or "-"
        line = f"{card.name} | {other_names} | {card.card}"
        lines.append(f"{card_id} | {line}" if with_ids else line)
    return "\n".join(lines)


def check_changes(changes: CardChanges, cards: dict[str, Card]) -> None:
    """Raise ValueError for a reply that cannot be merged. The client then retries."""
    unknown = [item.id for item in changes.update if item.id not in cards]
    if unknown:
        raise ValueError(f"update uses unknown id(s): {', '.join(unknown)}")
    updated_ids = [item.id for item in changes.update]
    if len(updated_ids) != len(set(updated_ids)):
        raise ValueError("update lists the same id more than once")

    known = {
        name_key(name): card_id
        for card_id, card in cards.items()
        for name in [card.name, *card.other_names]
    }
    seen: set[str] = set()
    for item in changes.add:
        for name in [item.name, *item.other_names]:
            key = name_key(name)
            if key in known:
                raise ValueError(f"{name!r} is already listed as {known[key]}; use update")
            if key in seen:
                raise ValueError(f"{name!r} is added twice")
            seen.add(key)


def changes_to_update(changes: CardChanges, cards: dict[str, Card], prefix: str) -> dict[str, Card]:
    """Turn a checked reply into the dict the reducer merges. New lines get the next ids."""
    update = {item.id: Card(**item.model_dump(exclude={"id"})) for item in changes.update}
    start = 1 + max((int(card_id[1:]) for card_id in cards), default=0)
    for number, card in enumerate(changes.add, start=start):
        update[f"{prefix}{number:03d}"] = card
    return update


def update_cards(
    llm: "JsonLLM",
    rules: str,
    title: str,
    chapter_id: str,
    chapter_text: str,
    cards: dict[str, Card],
    prefix: str,
) -> dict[str, Card]:
    prompt = CHANGES_INPUT.format(
        rules=rules,
        book_title=title,
        chapter_id=chapter_id,
        previous=render_cards(cards, with_ids=True) or "(empty)",
        chapter_text=chapter_text,
    )
    changes = llm.complete_json(prompt, CardChanges, check=lambda c: check_changes(c, cards))
    return changes_to_update(changes, cards, prefix)


# ======================================================================================
# summarize_chapter/prompt/*.py
# Keep the existing card rules. Replace three parts of each prompt:
#   1. The opening "Your answer replaces the previous list ..." sentence.
#   2. The bullet "Keep every character/place from the previous list ...".
#   3. The closing "Return only the complete ... list. Do not return JSON ..." lines
#      and the *_REMINDER, with CHANGES_OUTPUT below.
# In WHO IS WHO, change the merge rule to: "When the chapter establishes that a new name
# belongs to a listed individual, update that line and add the name to its other names."
# ======================================================================================
CHANGES_OUTPUT = """\
OUTPUT
The program keeps the previous list. Each previous line starts with its id. Return only
what the current chapter changes, as JSON:
{"add": [{"name": "...", "other_names": ["..."], "card": "..."}],
 "update": [{"id": "C003", "name": "...", "other_names": ["..."], "card": "..."}]}
- "add": entries that are not in the previous list under any name.
- "update": a listed entry whose name, other names or card must change because of the
  current chapter. Copy its id exactly and return the whole new entry, keeping every
  earlier other name.
- Leave out entries the current chapter does not change.
- Return {"add": [], "update": []} when nothing changes.
"""

CHANGES_INPUT = """\
{rules}

Book title: {book_title}
Current chapter: {chapter_id}

<previous_list>
{previous}
</previous_list>

<chapter_text>
{chapter_text}
</chapter_text>
"""

WHO_RULES = "Update the WHO IS WHO character list. <existing card rules>\n\n" + CHANGES_OUTPUT
WHERE_RULES = "Update the WHERE IS WHERE place list. <existing card rules>\n\n" + CHANGES_OUTPUT


# ======================================================================================
# summarize_chapter/graph.py
# ======================================================================================
def build_graph(llm: "JsonLLM") -> CompiledStateGraph[Any, Any, Any, Any]:
    def initialize(state: SummarizeChapterState) -> SummarizeChapterState:
        return {"chapter_index": 0, "who_cards": {}, "where_cards": {}}

    def update_who_is_who(state: SummarizeChapterState) -> SummarizeChapterState:
        index = state["chapter_index"]
        cards = state["who_cards"]
        update = update_cards(
            llm,
            WHO_RULES,
            state["title"],
            f"u{index + 1:02d}",
            state["chapters"][index],
            cards,
            "C",
        )
        return {"who_cards": update}  # only the changes; the reducer merges them

    def update_where_is_where(state: SummarizeChapterState) -> SummarizeChapterState:
        index = state["chapter_index"]
        cards = state["where_cards"]
        update = update_cards(
            llm,
            WHERE_RULES,
            state["title"],
            f"u{index + 1:02d}",
            state["chapters"][index],
            cards,
            "P",
        )
        return {"where_cards": update}

    def save_summary(state: SummarizeChapterState) -> SummarizeChapterState:
        # In the project: build ChapterSummary(who_is_who=render_cards(..., with_ids=False), ...)
        # so the saved file keeps the "name | other names | card" lines.
        print(f"--- after chapter {state['chapter_index'] + 1}")
        print(render_cards(state["where_cards"], with_ids=True))
        return {"chapter_index": state["chapter_index"] + 1}

    def next_step(state: SummarizeChapterState) -> str:
        return "next" if state["chapter_index"] < len(state["chapters"]) else "done"

    graph = StateGraph(SummarizeChapterState)
    for node in (initialize, update_who_is_who, update_where_is_where, save_summary):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "update_who_is_who")
    graph.add_edge("update_who_is_who", "update_where_is_where")
    graph.add_edge("update_where_is_where", "save_summary")
    graph.add_conditional_edges(
        "save_summary", next_step, {"next": "update_who_is_who", "done": END}
    )
    return graph.compile()


# ======================================================================================
# Demo only: a fake LLM with the same complete_json contract as OpenRouterClient
# ======================================================================================
class JsonLLM:
    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = [json.dumps(reply) for reply in replies]

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        error = ""
        for _ in range(1 + MAX_RETRIES):
            reply = self.replies.pop(0)
            try:
                value = schema.model_validate_json(reply)
                if check is not None:
                    check(value)
                return value
            except (ValidationError, ValueError) as exc:
                error = str(exc)
                print(f"    rejected, retrying: {error}")
        raise RuntimeError(f"no valid answer after {1 + MAX_RETRIES} attempts: {error}")


NOTHING: dict[str, Any] = {"add": [], "update": []}


def place(name: str, card: str, *other_names: str) -> dict[str, Any]:
    return {"name": name, "other_names": list(other_names), "card": card}


if __name__ == "__main__":
    replies = [
        # chapter 1: who, where
        NOTHING,
        {
            "add": [
                place("Diagon Alley", "hidden shopping street in London"),
                place("Madam Malkin’s Robes", "robe shop in Diagon Alley", "Madam Malkin's"),
            ],
            "update": [],
        },
        # chapter 2: who, where (first where reply re-adds a listed place, so it is retried)
        NOTHING,
        {"add": [place("Madam Malkin's Robes", "robe shop")], "update": []},
        {"add": [place("Gringotts", "wizarding bank in Diagon Alley")], "update": []},
        # chapter 3: who, where (only one card changes)
        NOTHING,
        {
            "add": [],
            "update": [{"id": "P003", **place("Gringotts", "wizarding bank; vault 713 emptied")}],
        },
    ]
    build_graph(JsonLLM(replies)).invoke(
        {"title": "Demo", "chapters": ["text 1", "text 2", "text 3"]}
    )
