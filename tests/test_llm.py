"""The DeepSeek client, tested with a fake `openai` client: no network, no key, no money."""

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from pov_retell.config import Settings
from pov_retell.llm import DeepSeekClient, LLMError
from pov_retell.models import MapResponse

GOOD = '{"items": [{"cand_id": "c1", "role": "front", "unit_kind": "front", "title": "T"}]}'


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


def make(replies: list[str]) -> tuple[DeepSeekClient, FakeOpenAI]:
    fake = FakeOpenAI(replies)
    settings = Settings(_env_file=None, DEEPSEEK_MODEL="deepseek-v4-pro")  # type: ignore[call-arg]
    return DeepSeekClient(settings, client=fake), fake  # type: ignore[arg-type]


def test_the_request_asks_for_json_with_thinking_disabled() -> None:
    client, fake = make([GOOD])
    assert client.complete_json("classify", MapResponse).items[0].cand_id == "c1"
    request = fake.requests[0]
    assert request["model"] == "deepseek-v4-pro"
    assert request["response_format"] == {"type": "json_object"}
    assert request["extra_body"] == {"thinking": {"type": "disabled"}}
    assert request["messages"] == [{"role": "user", "content": "classify"}]


def test_a_wrong_answer_is_retried_with_the_error_in_the_message() -> None:
    client, fake = make(["not json at all", '{"items": [{"cand_id": "c1"}]}', GOOD])
    assert client.complete_json("classify", MapResponse).items
    assert len(fake.requests) == 3  # the first answer plus two retries
    second = fake.requests[1]["messages"]
    assert second[1] == {"role": "assistant", "content": "not json at all"}
    assert "Rejected:" in second[2]["content"] and "json" in second[2]["content"].lower()
    assert "role" in fake.requests[2]["messages"][-1]["content"]  # names the missing field


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


def test_thinking_is_never_enabled_in_any_request() -> None:
    client, fake = make(["bad", "bad", GOOD])
    client.complete_json("classify", MapResponse)
    assert all(r["extra_body"] == {"thinking": {"type": "disabled"}} for r in fake.requests)


def test_a_missing_key_is_a_clear_error() -> None:
    settings = Settings(_env_file=None, DEEPSEEK_API_KEY=SecretStr(""))  # type: ignore[call-arg]
    with pytest.raises(LLMError, match="DEEPSEEK_API_KEY"):
        DeepSeekClient(settings)


def test_the_api_key_never_shows_up_when_settings_are_printed() -> None:
    settings = Settings(_env_file=None, DEEPSEEK_API_KEY=SecretStr("sk-super-secret"))  # type: ignore[call-arg]
    assert "sk-super-secret" not in repr(settings) and "sk-super-secret" not in str(settings)
    assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com"
    assert settings.DEEPSEEK_MODEL == "deepseek-v4-pro"
