from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pov_retell.infrastructure.llm import JsonLLM
from pov_retell.ingest.graph.extract_character import location, logic, relationship, scene_map
from pov_retell.ingest.graph.extract_character.model import ExtractCharacterState
from pov_retell.ingest.graph.summarize_chapter.logic import format_previous_context

EXTRACT_NODES_PER_CHAPTER = 9


def extract_character_recursion_limit(chapter_count: int) -> int:
    return max(25, chapter_count * (EXTRACT_NODES_PER_CHAPTER + 1) + 10)


def build_extract_character_graph(
    llm: JsonLLM,
    on_step: Callable[[str], None] | None = None,
) -> CompiledStateGraph[ExtractCharacterState, Any, ExtractCharacterState, ExtractCharacterState]:
    def report(message: str) -> None:
        if on_step is not None:
            on_step(message)

    def initialize(state: ExtractCharacterState) -> ExtractCharacterState:
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
        }

    def extract_characters(state: ExtractCharacterState) -> ExtractCharacterState:
        index = state["chapter_index"]
        chapter = state["chapters"][index]
        report(f"extract_characters {chapter.unit_id}")
        previous_summary = format_previous_context(state["summaries"][:index])
        return {
            "proposed": logic.extract_characters(
                llm,
                state["title"],
                chapter,
                state["characters"],
                state["next_character_number"],
                state["identity_redirects"],
                previous_summary,
            )
        }

    def validate_characters(state: ExtractCharacterState) -> ExtractCharacterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_characters {chapter.unit_id}")
        records, active, next_number, redirects = logic.validate_characters(
            state["proposed"],
            state["characters"],
            state["next_character_number"],
            state["identity_redirects"],
            chapter,
        )
        chapter_order = {c.unit_id: i for i, c in enumerate(state["chapters"])}
        rewritten_relationships = relationship.rewrite_relationships_for_redirects(
            state["relationships"],
            redirects,
            chapter_order,
        )
        return {
            "characters": records,
            "active_character_ids": active,
            "next_character_number": next_number,
            "identity_redirects": redirects,
            "relationships": rewritten_relationships,
        }

    def extract_relationships(state: ExtractCharacterState) -> ExtractCharacterState:
        index = state["chapter_index"]
        chapter = state["chapters"][index]
        report(f"extract_relationships {chapter.unit_id}")
        previous_summary = format_previous_context(state["summaries"][:index])
        return {
            "proposed_relationships": relationship.extract_relationships(
                llm,
                state["title"],
                chapter,
                state["characters"],
                state["active_character_ids"],
                state["relationships"],
                state["next_relationship_number"],
                state["identity_redirects"],
                previous_summary,
            )
        }

    def validate_relationships(state: ExtractCharacterState) -> ExtractCharacterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_relationships {chapter.unit_id}")
        records, next_number = relationship.validate_relationships(
            state["proposed_relationships"],
            state["relationships"],
            state["next_relationship_number"],
            state["characters"],
            state["identity_redirects"],
            chapter,
        )
        return {
            "relationships": records,
            "next_relationship_number": next_number,
        }

    def extract_locations(state: ExtractCharacterState) -> ExtractCharacterState:
        index = state["chapter_index"]
        chapter = state["chapters"][index]
        report(f"extract_locations {chapter.unit_id}")
        previous_summary = format_previous_context(state["summaries"][:index])
        return {
            "proposed_locations": location.extract_locations(
                llm,
                state["title"],
                chapter,
                state["locations"],
                state["next_location_number"],
                previous_summary,
            )
        }

    def validate_locations(state: ExtractCharacterState) -> ExtractCharacterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"validate_locations {chapter.unit_id}")
        records, next_number = location.validate_locations(
            state["proposed_locations"],
            state["locations"],
            state["next_location_number"],
        )
        return {
            "locations": records,
            "next_location_number": next_number,
        }

    def extract_scenes(state: ExtractCharacterState) -> ExtractCharacterState:
        index = state["chapter_index"]
        chapter = state["chapters"][index]
        report(f"extract_scenes {chapter.unit_id}")
        previous_summary = format_previous_context(state["summaries"][:index])
        return {
            "proposed_scenes": scene_map.extract_scene_map(
                llm,
                state["title"],
                chapter,
                state["chapters"][: index + 1],
                state["characters"],
                state["locations"],
                state["identity_redirects"],
                previous_summary,
            )
        }

    def validate_scenes(state: ExtractCharacterState) -> ExtractCharacterState:
        index = state["chapter_index"]
        chapter = state["chapters"][index]
        report(f"validate_scenes {chapter.unit_id}")
        records = scene_map.validate_scene_map(
            state["proposed_scenes"],
            chapter,
            state["chapters"][: index + 1],
            state["characters"],
            state["locations"],
            state["identity_redirects"],
        )
        return {"scenes": records}

    def save_json(state: ExtractCharacterState) -> ExtractCharacterState:
        chapter = state["chapters"][state["chapter_index"]]
        report(f"save_characters_json {chapter.unit_id}: {len(state['characters'])} characters")
        directory = state["output_dir"]
        records = [c.model_dump() for c in state["characters"]]
        rel_records = [r.model_dump() for r in state["relationships"]]
        loc_records = [loc.model_dump() for loc in state["locations"]]
        scene_records = [s.model_dump() for s in state["scenes"]]
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.proposed.json",
            state["proposed"].model_dump(),
        )
        logic.save_json(directory / "chapters" / f"{chapter.unit_id}.characters.json", records)
        logic.save_json(directory / "identity_redirects.json", state["identity_redirects"])
        logic.save_json(directory / "characters.json", records)
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.relationships.proposed.json",
            state["proposed_relationships"].model_dump(),
        )
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.relationships.json",
            rel_records,
        )
        logic.save_json(directory / "relationships.json", rel_records)
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.locations.proposed.json",
            state["proposed_locations"].model_dump(),
        )
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.locations.json",
            loc_records,
        )
        logic.save_json(directory / "locations.json", loc_records)
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.scenes.proposed.json",
            state["proposed_scenes"].model_dump(),
        )
        logic.save_json(
            directory / "chapters" / f"{chapter.unit_id}.scenes.json",
            scene_records,
        )
        return {"chapter_index": state["chapter_index"] + 1}

    def next_step(state: ExtractCharacterState) -> Literal["next_chapter", "done"]:
        return "next_chapter" if state["chapter_index"] < len(state["chapters"]) else "done"

    graph = StateGraph(ExtractCharacterState)
    for node in (
        initialize,
        extract_characters,
        validate_characters,
        extract_relationships,
        validate_relationships,
        extract_locations,
        validate_locations,
        extract_scenes,
        validate_scenes,
        save_json,
    ):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "extract_characters")
    graph.add_edge("extract_characters", "validate_characters")
    graph.add_edge("validate_characters", "extract_relationships")
    graph.add_edge("extract_relationships", "validate_relationships")
    graph.add_edge("validate_relationships", "extract_locations")
    graph.add_edge("extract_locations", "validate_locations")
    graph.add_edge("validate_locations", "extract_scenes")
    graph.add_edge("extract_scenes", "validate_scenes")
    graph.add_edge("validate_scenes", "save_json")
    graph.add_conditional_edges(
        "save_json", next_step, {"next_chapter": "extract_characters", "done": END}
    )
    return graph.compile()
