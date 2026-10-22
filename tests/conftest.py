"""Shared fixtures. Opt-in integration tests alone use Neo4j or OpenRouter."""

import os

import pytest
import samples

from pov_retell.book.models import BookFormat

# Tests that touch things outside the repo only run when asked for: marker -> switch.
OPT_IN = {
    "neo4j": "POV_NEO4J",
    "openrouter": "POV_OPENROUTER",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip tests that need Neo4j or a paid OpenRouter request by default."""
    for marker, switch in OPT_IN.items():
        if os.environ.get(switch) == "1":
            continue
        skip = pytest.mark.skip(reason=f"opt-in: run with {switch}=1 (see the Makefile)")
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def sample_bytes() -> dict[BookFormat, bytes]:
    return {
        "html": samples.render_html(),
        "epub": samples.render_epub(),
        "txt": samples.render_txt(),
    }
