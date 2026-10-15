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

    # Neo4j of the "book-clone-dev" compose project. The host ports are NOT 7474/7687 on purpose:
    # the other stack ("book-clone") owns those. docker/compose.yml reads the same two names.
    NEO4J_HTTP_PORT: int = 7475  # Neo4j Browser
    NEO4J_BOLT_PORT: int = 7688  # what the Python driver connects to
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("")  # no default: put it in secrets.env

    @property
    def books_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "books"

    @property
    def extracted_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "extracted"

    @property
    def checkpoint_db(self) -> Path:
        """Where `pov ingest --checkpoint sqlite` keeps its checkpoints."""
        return self.BOOK_CLONE_DATA_DIR / "checkpoints.sqlite"

    @property
    def neo4j_uri(self) -> str:
        return f"bolt://localhost:{self.NEO4J_BOLT_PORT}"

    @property
    def neo4j_browser_url(self) -> str:
        return f"http://localhost:{self.NEO4J_HTTP_PORT}"
