"""Settings: read from the repository's .env file and environment variables.

The API key is a SecretStr so it prints as '**********' even if someone logs the settings.
Extract needs an OpenRouter key; reading an extraction and checking Neo4j do not.
"""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, PositiveInt, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_str(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _validate_provider_list(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and not [tag.strip() for tag in stripped.split(",") if tag.strip()]:
        raise ValueError("provider list contains no provider tags")
    return stripped


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ProviderSetting = Annotated[str, BeforeValidator(_validate_provider_list)]
ReasoningMode = Annotated[
    Literal["none", "enabled", "low", "medium", "high"],
    BeforeValidator(_strip_str),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENROUTER_API_KEY: SecretStr
    OPENROUTER_BASE_URL: str
    OPENROUTER_MODEL: str
    OPENROUTER_SUMMARIZE_CHAPTER_MODEL: ModelName
    OPENROUTER_EXTRACT_CHARACTER_MODEL: ModelName
    # Output-token limits, including reasoning tokens. Each must fit its model's limit.
    OPENROUTER_MAX_TOKENS: PositiveInt
    OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS: PositiveInt
    OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS: PositiveInt
    # Extract client routing, reasoning and structured output options.
    OPENROUTER_EXTRACT_CHARACTER_PROVIDER: ProviderSetting
    OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS: bool
    OPENROUTER_EXTRACT_CHARACTER_REASONING: ReasoningMode
    OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS: bool
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
