"""Neo4j connection errors at the CLI boundary."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.config import Settings

runner = CliRunner()


def use_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **values: Any) -> None:
    """Make the CLI ignore the real .env, so these tests never depend on your machine."""

    def make_settings() -> Settings:
        configured: dict[str, Any] = {
            "OPENROUTER_API_KEY": SecretStr(""),
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_MODEL": "openai/gpt-4o-mini",
            "OPENROUTER_MAX_TOKENS": 8192,
            "BOOK_CLONE_DATA_DIR": tmp_path,
            "NEO4J_PASSWORD": SecretStr(""),
            "NEO4J_USER": "neo4j",
            "NEO4J_HTTP_PORT": 7475,
            "NEO4J_BOLT_PORT": 7688,
        }
        return Settings(_env_file=None, **(configured | values))  # type: ignore[call-arg]

    monkeypatch.setattr(cli, "Settings", make_settings)


def test_ingest_requires_a_neo4j_password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    use_settings(monkeypatch, tmp_path)
    result = runner.invoke(cli.app, ["ingest", "sample"])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD" in result.output


def test_status_without_a_password_says_where_to_put_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(monkeypatch, tmp_path)
    result = runner.invoke(cli.app, ["neo4j-status"])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD" in result.output and ".env" in result.output


def test_status_says_when_neo4j_is_not_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(
        monkeypatch, tmp_path, NEO4J_PASSWORD=SecretStr("not-used-1234"), NEO4J_BOLT_PORT=1
    )
    result = runner.invoke(cli.app, ["neo4j-status"])
    assert result.exit_code == 1 and "cannot reach Neo4j" in result.output
    assert "not-used-1234" not in result.output  # the password is never printed
