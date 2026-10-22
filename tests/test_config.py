"""Settings come from one .env file, without code defaults."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from pov_retell.config import ENV_FILE, Settings


def env_text(data_dir: Path, password: str = "") -> str:
    return (
        "OPENROUTER_API_KEY=\n"
        "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1\n"
        "OPENROUTER_MODEL=openai/gpt-4o-mini\n"
        "OPENROUTER_MAX_TOKENS=8192\n"
        f"BOOK_CLONE_DATA_DIR={data_dir}\n"
        f"NEO4J_PASSWORD={password}\n"
        "NEO4J_USER=neo4j\n"
        "NEO4J_HTTP_PORT=7475\n"
        "NEO4J_BOLT_PORT=7688\n"
    )


def test_no_values_are_supplied_by_python_when_env_file_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert len(exc.value.errors()) == len(Settings.model_fields)


def test_values_come_from_one_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(env_text(tmp_path / "data") + "SOMETHING_ELSE=ignored\n")
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert settings.OPENROUTER_API_KEY.get_secret_value() == ""
    assert settings.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
    assert settings.BOOK_CLONE_DATA_DIR == tmp_path / "data"
    assert settings.books_dir == tmp_path / "data" / "books"
    assert settings.extracted_dir == tmp_path / "data" / "extracted"
    assert settings.neo4j_uri == "bolt://localhost:7688"
    assert settings.neo4j_browser_url == "http://localhost:7475"


def test_the_neo4j_password_is_a_secret(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(env_text(tmp_path, "hunter2-hunter2").replace("7688", "9999"))
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert "hunter2" not in repr(settings) and "hunter2" not in str(settings)
    assert settings.NEO4J_PASSWORD.get_secret_value() == "hunter2-hunter2"
    assert settings.neo4j_uri == "bolt://localhost:9999"


def test_default_env_path_points_to_repository() -> None:
    assert ENV_FILE == Path(__file__).resolve().parents[1] / ".env"
