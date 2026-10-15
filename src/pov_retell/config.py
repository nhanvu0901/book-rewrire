"""Settings: read from ~/.config/book-clone/secrets.env, then from the environment.

The API key is a SecretStr so it prints as '**********' even if someone logs the settings.
Phase A runs without any key: only `--map llm` needs one.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETS_PATH = Path.home() / ".config" / "book-clone" / "secrets.env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(SECRETS_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,  # a blank "NAME=" copied from .env.example keeps the default
    )

    DEEPSEEK_API_KEY: SecretStr = SecretStr("")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"
    # Everything we write lives under here; the source books go in <dir>/books/.
    BOOK_CLONE_DATA_DIR: Path = Path.home() / ".local" / "share" / "book-clone"

    @property
    def books_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "books"

    @property
    def extracted_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "extracted"
