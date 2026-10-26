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
        "OPENROUTER_SUMMARIZE_CHAPTER_MODEL=example/summary\n"
        "OPENROUTER_EXTRACT_CHARACTER_MODEL=example/characters\n"
        "OPENROUTER_MAX_TOKENS=8192\n"
        "OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS=4096\n"
        "OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS=16384\n"
        "OPENROUTER_EXTRACT_CHARACTER_PROVIDER=open-inference/fp4\n"
        "OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS=false\n"
        "OPENROUTER_EXTRACT_CHARACTER_REASONING=enabled\n"
        "OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS=true\n"
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
    assert settings.OPENROUTER_MODEL == "openai/gpt-4o-mini"
    assert settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL == "example/summary"
    assert settings.OPENROUTER_EXTRACT_CHARACTER_MODEL == "example/characters"
    assert settings.OPENROUTER_MAX_TOKENS == 8192
    assert settings.OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS == 4096
    assert settings.OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS == 16384
    assert settings.OPENROUTER_EXTRACT_CHARACTER_PROVIDER == "open-inference/fp4"
    assert settings.OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS is False
    assert settings.OPENROUTER_EXTRACT_CHARACTER_REASONING == "enabled"
    assert settings.OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS is True
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


@pytest.mark.parametrize("include_legacy_model", [False, True])
def test_settings_load_env_file_with_optional_legacy_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, include_legacy_model: bool
) -> None:
    legacy_key = "_".join(("OPENROUTER", "CHARACTER", "ATTRIBUTES", "MODEL"))
    for name in {*Settings.model_fields, legacy_key}:
        monkeypatch.delenv(name, raising=False)
    contents = env_text(tmp_path)
    if include_legacy_model:
        contents += f"{legacy_key}=legacy/unused\n"
    env_file = tmp_path / ".env"
    env_file.write_text(contents)

    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]

    assert settings.OPENROUTER_EXTRACT_CHARACTER_MODEL == "example/characters"
    assert settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL == "example/summary"
    assert legacy_key not in settings.model_dump()


@pytest.mark.parametrize(
    "field",
    [
        "OPENROUTER_SUMMARIZE_CHAPTER_MODEL",
        "OPENROUTER_EXTRACT_CHARACTER_MODEL",
    ],
)
@pytest.mark.parametrize("value", ["", "   "])
def test_graph_model_names_cannot_be_blank(tmp_path: Path, field: str, value: str) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(env_text(tmp_path))
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env_file, **{field: value})  # type: ignore[call-arg]
    assert any(error["loc"] == (field,) for error in exc.value.errors())


@pytest.mark.parametrize("reasoning", ["none", "enabled", "low", "medium", "high"])
def test_extract_character_reasoning_accepts_supported_modes(
    tmp_path: Path, reasoning: str
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(env_text(tmp_path))
    settings = Settings(
        _env_file=env_file,
        OPENROUTER_EXTRACT_CHARACTER_REASONING=reasoning,  # type: ignore[arg-type]
        OPENROUTER_EXTRACT_CHARACTER_PROVIDER="",
    )  # type: ignore[call-arg]
    assert settings.OPENROUTER_EXTRACT_CHARACTER_REASONING == reasoning
    assert settings.OPENROUTER_EXTRACT_CHARACTER_PROVIDER == ""


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("OPENROUTER_EXTRACT_CHARACTER_REASONING", "maybe"),
        ("OPENROUTER_EXTRACT_CHARACTER_REASONING", ""),
        ("OPENROUTER_EXTRACT_CHARACTER_PROVIDER", " , "),
        ("OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS", "maybe"),
        ("OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS", "maybe"),
    ],
)
def test_extract_character_client_settings_reject_invalid_values(
    tmp_path: Path, field: str, value: str
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(env_text(tmp_path))
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env_file, **{field: value})  # type: ignore[call-arg]
    assert any(error["loc"] == (field,) for error in exc.value.errors())
