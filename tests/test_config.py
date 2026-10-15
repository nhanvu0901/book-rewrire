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
