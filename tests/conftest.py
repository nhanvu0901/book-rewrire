"""Shared fixtures. Tests never read the user's real secrets.env or data directory."""

import os

import pytest
import samples

from pov_retell.models import BookFormat

# Tests that touch things outside the repo only run when asked for: marker -> switch.
OPT_IN = {"local_books": "POV_LOCAL_BOOKS", "neo4j": "POV_NEO4J"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """local_books reads real books from disk; neo4j writes to the dev Neo4j."""
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
