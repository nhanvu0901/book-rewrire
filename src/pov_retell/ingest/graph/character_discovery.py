from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest import extrac_character
from pov_retell.ingest.models.character_discovery import CharacterDiscoveryState


def build_character_graph(
    llm: JsonLLM,
    extracted_dir: Path,
    ingest_dir: Path,
    on_step: Callable[[str], None] | None = None,
) -> CompiledStateGraph[
    CharacterDiscoveryState, Any, CharacterDiscoveryState, CharacterDiscoveryState
]:
    def report(message: str) -> None:
        if on_step is not None:
            on_step(message)

    def load_chapters(state: CharacterDiscoveryState) -> CharacterDiscoveryState:
        report("load_chapters")
        title, chapters = extrac_character.load_chapters(extracted_dir, state["book_id"])
        extrac_character.validate_directory_name(state["run_id"])
        output_dir = ingest_dir / state["book_id"] / state["run_id"]
        output_dir.mkdir(parents=True, exist_ok=False)
        report(f"Run {state['run_id']}: {output_dir}")
        return {
            "title": title,
            "chapters": chapters,
            "chapter_index": 0,
            "characters": [],
            "next_character_number": 1,
            "output_dir": output_dir,
        }

    def extract_characters(state: CharacterDiscoveryState) -> CharacterDiscoveryState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"extract_characters {chapter.unit_id}")
        return {
            "proposed": extrac_character.extract_characters(
                llm, state["title"], chapter, state["characters"], state["next_character_number"]
            )
        }

    def validate_characters(state: CharacterDiscoveryState) -> CharacterDiscoveryState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_characters {chapter.unit_id}")
        characters, next_number = extrac_character.validate_characters(
            state["proposed"],
            state["characters"],
            state["next_character_number"],
        )
        return {"characters": characters, "next_character_number": next_number}

    def save_json(state: CharacterDiscoveryState) -> CharacterDiscoveryState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"save_characters_json {chapter.unit_id}: {len(state['characters'])} characters")
        extrac_character.save_records(
            state["output_dir"] / "chapters" / f"{chapter.unit_id}.characters.json",
            state["characters"],
        )
        extrac_character.save_records(state["output_dir"] / "characters.json", state["characters"])
        return {"chapter_index": state["chapter_index"] + 1}

    def next_step(state: CharacterDiscoveryState) -> Literal["next_chapter", "done"]:
        return "next_chapter" if state["chapter_index"] < len(state["chapters"]) else "done"

    graph = StateGraph(CharacterDiscoveryState)
    for node in (load_chapters, extract_characters, validate_characters, save_json):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "load_chapters")
    graph.add_edge("load_chapters", "extract_characters")
    graph.add_edge("extract_characters", "validate_characters")
    graph.add_edge("validate_characters", "save_json")
    graph.add_conditional_edges(
        "save_json", next_step, {"next_chapter": "extract_characters", "done": END}
    )
    return graph.compile()
