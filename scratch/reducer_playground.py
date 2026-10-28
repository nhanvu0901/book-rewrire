"""LangGraph reducer playground. No LLM, no API calls, no project imports.

Run:  uv run python scratch/reducer_playground.py

Each example builds a tiny graph and prints the final state, so you can see how a
node's return value is merged into the state.
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Overwrite


def run_in_order(state_type, nodes, start_state):
    """Build START -> node1 -> node2 -> ... -> END and return the final state."""
    graph = StateGraph(state_type)
    for node in nodes:
        graph.add_node(node.__name__, node)
    names = [START, *(node.__name__ for node in nodes), END]
    for left, right in zip(names, names[1:]):
        graph.add_edge(left, right)
    return graph.compile().invoke(start_state)


# --------------------------------------------------------------------------------------
# Example 1: no reducer -> the new value REPLACES the old one (LangGraph's default)
# --------------------------------------------------------------------------------------
class ReplaceState(TypedDict):
    notes: list[str]


def write_chapter_1(state: ReplaceState) -> dict:
    return {"notes": ["chapter 1 summary"]}


def write_chapter_2(state: ReplaceState) -> dict:
    return {"notes": ["chapter 2 summary"]}


# --------------------------------------------------------------------------------------
# Example 2: operator.add -> the new list is APPENDED to the old one
# Reducer signature: reducer(current_value, node_update) -> new_value
# operator.add(["a"], ["b"]) == ["a", "b"]
# --------------------------------------------------------------------------------------
class AppendState(TypedDict):
    notes: Annotated[list[str], operator.add]


# The same two nodes are reused: they still return only their own chapter.


# --------------------------------------------------------------------------------------
# Example 3: a custom reducer -> UPSERT by key (add new keys, update existing ones,
# never drop anything). This is the "LLM returns only the changes" idea.
# --------------------------------------------------------------------------------------
def upsert(current: dict[str, str], update: dict[str, str]) -> dict[str, str]:
    merged = dict(current)
    for key, value in update.items():
        action = "update" if key in merged else "add"
        print(f"    reducer {action}: {key!r} -> {value!r}")
        merged[key] = value
    return merged


class PlaceState(TypedDict):
    where_is_where: Annotated[dict[str, str], upsert]


def fake_llm_chapter_4(state: PlaceState) -> dict:
    # A real LLM would read state["where_is_where"] plus the chapter text,
    # then return ONLY new or changed places.
    return {"where_is_where": {"The shack on the rock": "broken-down hut on a sea rock"}}


def fake_llm_chapter_5(state: PlaceState) -> dict:
    return {
        "where_is_where": {
            "Diagon Alley": "hidden magical shopping street in London",
            "Gringotts": "wizarding bank in Diagon Alley, run by goblins",
        }
    }


def fake_llm_chapter_6(state: PlaceState) -> dict:
    # Only one card changes; the other places are kept by the reducer, not by the LLM.
    return {"where_is_where": {"Gringotts": "wizarding bank; vault 713 was emptied"}}


# --------------------------------------------------------------------------------------
# Example 4: Overwrite -> skip the reducer once and set the value directly
# --------------------------------------------------------------------------------------
def start_new_book(state: AppendState) -> dict:
    return {"notes": Overwrite(["new book, empty memory"])}


# --------------------------------------------------------------------------------------
# Example 5: parallel nodes writing the same key
# Without a reducer LangGraph cannot choose between the two values and raises an error.
# With a reducer both values are combined.
# --------------------------------------------------------------------------------------
def who_node(state: dict) -> dict:
    return {"notes": ["WHO IS WHO updated"]}


def where_node(state: dict) -> dict:
    return {"notes": ["WHERE IS WHERE updated"]}


def run_in_parallel(state_type):
    """START fans out to who_node and where_node, which run in the same step."""
    graph = StateGraph(state_type)
    graph.add_node("who_node", who_node)
    graph.add_node("where_node", where_node)
    graph.add_edge(START, "who_node")
    graph.add_edge(START, "where_node")
    graph.add_edge("who_node", END)
    graph.add_edge("where_node", END)
    return graph.compile().invoke({"notes": []})


def main() -> None:
    print("1. No reducer (replace)")
    state = run_in_order(ReplaceState, [write_chapter_1, write_chapter_2], {"notes": []})
    print("   ", state["notes"], "<- chapter 1 is gone\n")

    print("2. operator.add (append)")
    state = run_in_order(AppendState, [write_chapter_1, write_chapter_2], {"notes": []})
    print("   ", state["notes"], "<- both chapters kept\n")

    print("3. Custom upsert reducer (LLM returns only changes)")
    start = {"where_is_where": {"Privet Drive": "quiet street where the Dursleys live"}}
    state = run_in_order(
        PlaceState, [fake_llm_chapter_4, fake_llm_chapter_5, fake_llm_chapter_6], start
    )
    for name, card in state["where_is_where"].items():
        print(f"    {name} | {card}")
    print()

    print("4. Overwrite (bypass the reducer once)")
    state = run_in_order(AppendState, [write_chapter_1, start_new_book], {"notes": ["old"]})
    print("   ", state["notes"], "<- old notes cleared even though the key appends\n")

    print("5. Parallel nodes writing the same key")
    try:
        run_in_parallel(ReplaceState)
    except Exception as error:
        print(f"    without reducer: {type(error).__name__}: {str(error).splitlines()[0]}")
    state = run_in_parallel(AppendState)
    print("    with operator.add:", state["notes"])


if __name__ == "__main__":
    main()
