"""Settings: read from the repository's .env file and environment variables.

The API key is a SecretStr so it prints as '**********' even if someone logs the settings.
Extract needs an OpenRouter key; reading an extraction and checking Neo4j do not.
"""

from pathlib import Path

from pydantic import PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENROUTER_API_KEY: SecretStr
    OPENROUTER_BASE_URL: str
    OPENROUTER_MODEL: str
    OPENROUTER_MAX_TOKENS: PositiveInt
    # Everything we write lives under here; the source books go in <dir>/books/.
    BOOK_CLONE_DATA_DIR: Path

    # Neo4j of the "book-clone-dev" compose project. The host ports are NOT 7474/7687 on purpose:
    # the other stack ("book-clone") owns those. docker/compose.yml reads the same two names.
    NEO4J_HTTP_PORT: int  # Neo4j Browser
    NEO4J_BOLT_PORT: int  # what the Python driver connects to
    NEO4J_USER: str
    NEO4J_PASSWORD: SecretStr

    @property
    def books_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "books"

    @property
    def extracted_dir(self) -> Path:
        return self.BOOK_CLONE_DATA_DIR / "extracted"

    @property
    def neo4j_uri(self) -> str:
        return f"bolt://localhost:{self.NEO4J_BOLT_PORT}"

    @property
    def neo4j_browser_url(self) -> str:
        return f"http://localhost:{self.NEO4J_HTTP_PORT}"
