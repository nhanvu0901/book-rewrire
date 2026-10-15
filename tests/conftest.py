"""Shared fixtures. Tests never read the user's real secrets.env or data directory."""

import os

import pytest
import samples

from pov_retell.models import BookFormat


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """The local_books tests read real books from disk, so they only run when asked for."""
    if os.environ.get("POV_LOCAL_BOOKS") == "1":
        return
    skip = pytest.mark.skip(reason="opt-in: run with POV_LOCAL_BOOKS=1 (make test-books)")
    for item in items:
        if "local_books" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def sample_bytes() -> dict[BookFormat, bytes]:
    return {
        "html": samples.render_html(),
        "epub": samples.render_epub(),
        "txt": samples.render_txt(),
    }
