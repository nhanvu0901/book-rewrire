"""Opt-in test that sends a real request to OpenRouter and may incur a small charge."""

import pytest

from pov_retell.book.models import MapResponse
from pov_retell.config import Settings
from pov_retell.infrastructure.llm import OpenRouterClient


@pytest.mark.openrouter
def test_openrouter_returns_a_valid_structure_map_response() -> None:
    settings = Settings()  # type: ignore[call-arg]  # reads the repository's .env
    if not settings.OPENROUTER_API_KEY.get_secret_value():
        pytest.fail("Set OPENROUTER_API_KEY in .env before running the real OpenRouter test")

    client = OpenRouterClient(settings)
    response = client.complete_json(
        "Return JSON only. Classify this single book-structure candidate: "
        "cand_id=cand_001, text='TITLE PAGE', kind=heading. "
        "Return exactly one item with cand_id='cand_001', role='front', "
        "unit_kind='front', title='Title Page', parent_cand_id=null. "
        "The JSON object must have an 'items' array.",
        MapResponse,
    )

    assert len(response.items) == 1
    assert response.items[0].cand_id == "cand_001"
    assert response.items[0].role == "front"
    assert response.items[0].unit_kind == "front"
    assert response.items[0].title
