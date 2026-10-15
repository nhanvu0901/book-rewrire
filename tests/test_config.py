"""Settings: defaults, env files, secrets."""

from pathlib import Path

import pytest

from pov_retell.config import Settings


def test_defaults_need_no_file_and_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOK_CLONE_DATA_DIR", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.DEEPSEEK_API_KEY.get_secret_value() == ""
    assert settings.books_dir == settings.BOOK_CLONE_DATA_DIR / "books"
    assert settings.extracted_dir == settings.BOOK_CLONE_DATA_DIR / "extracted"


def test_values_come_from_the_env_file_and_blanks_keep_the_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / "secrets.env"
    env_file.write_text(
        "DEEPSEEK_API_KEY=sk-test\nDEEPSEEK_MODEL=deepseek-v4-pro\nDEEPSEEK_BASE_URL=\n"
        f"BOOK_CLONE_DATA_DIR={tmp_path}\nSOMETHING_ELSE=ignored\n"
    )
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert settings.DEEPSEEK_API_KEY.get_secret_value() == "sk-test"
    assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com"  # blank line: default stays
    assert settings.BOOK_CLONE_DATA_DIR == tmp_path


def test_neo4j_defaults_do_not_collide_with_the_other_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("NEO4J_BOLT_PORT", "NEO4J_HTTP_PORT", "NEO4J_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    # the "book-clone" stack owns 7474 and 7687; docker/compose.yml uses the same defaults
    assert (settings.NEO4J_HTTP_PORT, settings.NEO4J_BOLT_PORT) == (7475, 7688)
    assert settings.neo4j_uri == "bolt://localhost:7688"
    assert settings.neo4j_browser_url == "http://localhost:7475"
    assert settings.NEO4J_PASSWORD.get_secret_value() == ""  # no default password anywhere


def test_the_neo4j_password_is_a_secret(tmp_path: Path) -> None:
    env_file = tmp_path / "secrets.env"
    env_file.write_text("NEO4J_PASSWORD=hunter2-hunter2\nNEO4J_BOLT_PORT=9999\n")
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert "hunter2" not in repr(settings) and "hunter2" not in str(settings)
    assert settings.NEO4J_PASSWORD.get_secret_value() == "hunter2-hunter2"
    assert settings.neo4j_uri == "bolt://localhost:9999"
    assert settings.checkpoint_db == settings.BOOK_CLONE_DATA_DIR / "checkpoints.sqlite"
