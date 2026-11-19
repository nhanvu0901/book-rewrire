"""Last two nodes of a chapter: save the JSON files, then write the graph snapshot."""

from pov_retell.ingest import storage
from pov_retell.ingest.graph.extract_story import snapshot
from pov_retell.ingest.graph.extract_story.context import StoryRuntime
from pov_retell.ingest.graph.extract_story.state import StoryState, current_chapter
from pov_retell.ingest.graph.extract_story.steps.registry import STEPS


def save_json(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    runtime.context.report(
        f"save_characters_json {chapter.unit_id}: {len(state['characters'])} characters"
    )
    files = [("identity_redirects.json", state["identity_redirects"])]
    for step in STEPS:
        files.extend(step.files(state))
    for path, value in files:
        storage.save_json(state["output_dir"] / path, value)
    return {}


def save_graph(state: StoryState, runtime: StoryRuntime) -> StoryState:
    chapter = current_chapter(state)
    writer = runtime.context.writer
    if writer is not None:
        runtime.context.report(f"save_graph {chapter.unit_id}")
        writer.write_chapter(state["book_id"], state["run_id"], snapshot.chapter_snapshot(state))
    return {"chapter_index": state["chapter_index"] + 1}
