from pathlib import Path

import pytest
from openai import OpenAI
from test_character_ingest import RecordingWriter, make_extraction

from pov_retell.config import Settings
from pov_retell.infrastructure.llm import OpenRouterClient
from pov_retell.ingest.graph.extract_character.model import CharacterRecord
from pov_retell.ingest.pipeline import ingest_book


@pytest.mark.openrouter
def test_real_summaries_and_character_extraction_preserve_a_revealed_identity(
    tmp_path: Path,
) -> None:
    import json

    make_extraction(
        tmp_path,
        [
            [
                "Mara's friend Jo spoke to the masked captain. "
                "The masked captain was a cautious human woman with a scar on her left cheek."
            ],
            ["The masked captain removed her mask and revealed she was Mara. Jo recognized Mara."],
        ],
    )
    settings = Settings()  # type: ignore[call-arg]
    writer = RecordingWriter()
    with OpenAI(
        api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=45,
        max_retries=0,
    ) as transport:
        result = ingest_book(
            "sample",
            OpenRouterClient(
                settings,
                client=transport,
                model=settings.OPENROUTER_EXTRACT_CHARACTER_MODEL,
                max_tokens_setting="OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS",
            ),
            writer,
            summary_llm=OpenRouterClient(
                settings,
                client=transport,
                model=settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL,
                max_tokens_setting="OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS",
                reasoning=settings.OPENROUTER_SUMMARIZE_CHAPTER_REASONING,
            ),
            extracted_dir=tmp_path / "extracted",
            ingest_dir=tmp_path / "ingest",
            on_step=print,
        )
    records = [
        CharacterRecord.model_validate(value)
        for value in json.loads(result.characters_file.read_text())
    ]
    assert {record.candidate_name for record in records} == {"Mara", "Jo"}
    mara = next(record for record in records if record.candidate_name == "Mara")
    assert any("captain" in alias.casefold() for alias in mara.aliases)
    assert "scar" in (mara.attributes.physical_description or "").casefold()
    assert "cautious" in mara.attributes.personality_traits
    assert (result.characters_file.parent / "summaries/u02.summary.json").exists()
    assert writer.saved is not None and len(writer.saved[2]) == 2
