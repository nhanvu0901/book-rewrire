"""The OpenRouter client, tested with a fake `openai` client: no network or key."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from pov_retell.book.models import MapResponse
from pov_retell.config import Settings
from pov_retell.infrastructure.llm import LLMError, OpenRouterClient

GOOD = '{"items": [{"cand_id": "c1", "role": "front", "unit_kind": "front", "title": "T"}]}'


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "OPENROUTER_API_KEY": SecretStr(""),
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
        "OPENROUTER_MODEL": "openai/gpt-4o-mini",
        "OPENROUTER_MAX_TOKENS": 8192,
        "BOOK_CLONE_DATA_DIR": "/tmp/book-clone-test",
        "NEO4J_PASSWORD": SecretStr(""),
        "NEO4J_USER": "neo4j",
        "NEO4J_HTTP_PORT": 7475,
        "NEO4J_BOLT_PORT": 7688,
    }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[call-arg]


class FakeOpenAI:
    """Stands in for `openai.OpenAI`: replies are scripted, requests are recorded."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> Any:
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        message = SimpleNamespace(content=self.replies.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make(replies: list[str]) -> tuple[OpenRouterClient, FakeOpenAI]:
    fake = FakeOpenAI(replies)
    return OpenRouterClient(settings(), client=fake), fake  # type: ignore[arg-type]


def test_the_request_asks_for_json() -> None:
    client, fake = make([GOOD])
    assert client.complete_json("classify", MapResponse).items[0].cand_id == "c1"
    request = fake.requests[0]
    assert request["model"] == "openai/gpt-4o-mini"
    assert request["response_format"] == {"type": "json_object"}
    assert "extra_body" not in request
    assert request["messages"] == [{"role": "user", "content": "classify"}]


def test_a_wrong_answer_is_retried_with_the_error_in_the_message() -> None:
    client, fake = make(["not json at all", '{"items": [{"cand_id": "c1"}]}', GOOD])
    assert client.complete_json("classify", MapResponse).items
    assert len(fake.requests) == 3  # the first answer plus two retries
    second = fake.requests[1]["messages"]
    assert second[1] == {"role": "assistant", "content": "not json at all"}
    assert "Rejected:" in second[2]["content"] and "json" in second[2]["content"].lower()
    assert "role" in fake.requests[2]["messages"][-1]["content"]  # names the missing field


def test_output_token_limit_comes_from_settings() -> None:
    fake = FakeOpenAI([GOOD])
    client = OpenRouterClient(settings(OPENROUTER_MAX_TOKENS=32768), client=fake)  # type: ignore[arg-type]
    client.complete_json("classify", MapResponse)
    assert fake.requests[0]["max_tokens"] == 32768


def test_truncated_output_is_reported_without_retrying_the_same_token_limit() -> None:
    client, fake = make([GOOD])
    original = fake.chat.completions.create

    def truncated(**kwargs: Any) -> Any:
        response = original(**kwargs)
        response.choices[0].finish_reason = "length"
        return response

    fake.chat.completions.create = truncated
    with pytest.raises(LLMError, match="truncated.*OPENROUTER_MAX_TOKENS"):
        client.complete_json("classify", MapResponse)
    assert len(fake.requests) == 1


def test_a_check_failure_is_retried_too() -> None:
    client, fake = make([GOOD, GOOD])

    def check(value: MapResponse) -> None:
        if len(fake.requests) < 2:
            raise ValueError("missing ids: c2")

    client.complete_json("classify", MapResponse, check)
    assert "missing ids: c2" in fake.requests[1]["messages"][-1]["content"]


def test_it_gives_up_after_two_retries() -> None:
    client, fake = make(["nope", "still nope", "never"])
    with pytest.raises(LLMError, match="no valid answer after 3 attempts"):
        client.complete_json("classify", MapResponse)
    assert len(fake.requests) == 3


def test_upstream_error_body_is_reported_without_crashing() -> None:
    fake = FakeOpenAI([])
    fake.chat.completions.create = lambda **_: SimpleNamespace(
        choices=None,
        error={"code": 503, "message": "Service temporarily overloaded"},
    )
    client = OpenRouterClient(settings(), client=fake)  # type: ignore[arg-type]
    with pytest.raises(LLMError, match="Service temporarily overloaded"):
        client.complete_json("classify", MapResponse)


def test_no_provider_specific_thinking_option_is_sent() -> None:
    client, fake = make(["bad", "bad", GOOD])
    client.complete_json("classify", MapResponse)
    assert all("extra_body" not in r for r in fake.requests)


def test_a_missing_key_is_a_clear_error() -> None:
    with pytest.raises(LLMError, match="OPENROUTER_API_KEY"):
        OpenRouterClient(settings())


def test_the_real_client_uses_the_openrouter_endpoint() -> None:
    configured = settings(OPENROUTER_API_KEY=SecretStr("sk-test"))
    with patch("pov_retell.infrastructure.llm.OpenAI") as constructor:
        OpenRouterClient(configured)
    constructor.assert_called_once_with(api_key="sk-test", base_url="https://openrouter.ai/api/v1")


def test_the_api_key_never_shows_up_when_settings_are_printed() -> None:
    configured = settings(OPENROUTER_API_KEY=SecretStr("sk-super-secret"))
    assert "sk-super-secret" not in repr(configured) and "sk-super-secret" not in str(configured)
    assert configured.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
    assert configured.OPENROUTER_MODEL == "openai/gpt-4o-mini"
