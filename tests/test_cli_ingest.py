"""Neo4j connection errors at the CLI boundary."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from pov_retell import cli
from pov_retell.config import Settings
from pov_retell.ingest.model import IngestResult

runner = CliRunner()


def use_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **values: Any) -> None:
    """Make the CLI ignore the real .env, so these tests never depend on your machine."""

    def make_settings() -> Settings:
        configured: dict[str, Any] = {
            "OPENROUTER_API_KEY": SecretStr(""),
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_MODEL": "openai/gpt-4o-mini",
            "OPENROUTER_SUMMARIZE_CHAPTER_MODEL": "example/summary",
            "OPENROUTER_SUMMARIZE_CHAPTER_REASONING": "medium",
            "OPENROUTER_EXTRACT_CHARACTER_MODEL": "example/characters",
            "OPENROUTER_MAX_TOKENS": 8192,
            "OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS": 4096,
            "OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS": 16384,
            "OPENROUTER_EXTRACT_CHARACTER_PROVIDER": "open-inference/fp4",
            "OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS": False,
            "OPENROUTER_EXTRACT_CHARACTER_REASONING": "enabled",
            "OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS": True,
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


def test_ingest_without_neo4j_never_connects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use_settings(monkeypatch, tmp_path, OPENROUTER_API_KEY=SecretStr("not-used"))
    calls: dict[str, Any] = {}

    def no_connect(settings: Settings) -> None:
        raise AssertionError("Neo4j must not be contacted")

    def fake_ingest(book_id: str, character_llm: Any, writer: Any, **kwargs: Any) -> Any:
        calls["writer"] = writer
        calls["character_llm"] = character_llm
        calls["summary_llm"] = kwargs.get("summary_llm")
        return IngestResult(
            book_id=book_id, run_id="run_x", characters_file=tmp_path, character_count=0
        )

    monkeypatch.setattr(cli, "connect", no_connect)
    monkeypatch.setattr(cli, "ingest_book", fake_ingest)
    result = runner.invoke(cli.app, ["ingest", "sample", "--no-neo4j"])
    assert result.exit_code == 0, result.output
    assert calls["writer"] is None
    assert calls["character_llm"].providers == ["open-inference/fp4"]
    assert calls["character_llm"].allow_fallbacks is False
    assert calls["character_llm"].reasoning == "enabled"
    assert calls["character_llm"].structured_outputs is True
    assert calls["summary_llm"].providers == []
    assert calls["summary_llm"].reasoning == "medium"
    assert calls["summary_llm"].structured_outputs is False
