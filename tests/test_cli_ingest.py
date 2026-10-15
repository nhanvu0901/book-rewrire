"""The ingest commands that need no running Neo4j: the diagram and the friendly errors."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.config import Settings

runner = CliRunner()


def use_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **values: Any) -> None:
    """Make the CLI ignore the real secrets.env, so these tests never depend on your machine."""

    def make_settings() -> Settings:
        return Settings(_env_file=None, BOOK_CLONE_DATA_DIR=tmp_path, **values)  # type: ignore[call-arg]

    monkeypatch.setattr(cli, "Settings", make_settings)


def test_graph_prints_the_mermaid_diagram() -> None:
    result = runner.invoke(cli.app, ["graph"])
    assert result.exit_code == 0
    assert result.output.startswith("---\nconfig:") and "graph TD;" in result.output
    for node in (
        "load_extracted",
        "validate",
        "write_paragraphs",
        "verify",
        "analysis_placeholder",
    ):
        assert node in result.output


def test_ingest_without_a_password_says_where_to_put_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(monkeypatch, tmp_path)
    result = runner.invoke(cli.app, ["ingest", "some-book"])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD" in result.output and "secrets.env" in result.output


def test_ingest_and_status_say_when_neo4j_is_not_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(
        monkeypatch, tmp_path, NEO4J_PASSWORD=SecretStr("not-used-1234"), NEO4J_BOLT_PORT=1
    )
    for command in (["ingest", "some-book"], ["neo4j-status"]):
        result = runner.invoke(cli.app, command)
        assert result.exit_code == 1 and "cannot reach Neo4j" in result.output
        assert "not-used-1234" not in result.output  # the password is never printed


def test_resume_needs_a_persistent_checkpointer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(monkeypatch, tmp_path)
    result = runner.invoke(cli.app, ["ingest", "some-book", "--resume"])
    assert result.exit_code == 1 and "--checkpoint sqlite" in result.output
