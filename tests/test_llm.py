"""The OpenRouter client, tested with a fake `openai` client: no network or key."""

import json
import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from pov_retell.book.models import MapResponse
from pov_retell.config import ReasoningMode, Settings
from pov_retell.infrastructure.llm import LLMError, OpenRouterClient, strict_json_schema
from pov_retell.ingest.graph.extract_character.model import ExtractCharacterResponse
from pov_retell.ingest.graph.extract_character.prompt.extract_character import PROMPT_EXTRACT_CHAR

GOOD = '{"items": [{"cand_id": "c1", "role": "front", "unit_kind": "front", "title": "T"}]}'
GOOD_CHAR = '{"characters": [{"character_id": "new_1", "candidate_name": "Mara"}]}'


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "OPENROUTER_API_KEY": SecretStr(""),
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
        "OPENROUTER_MODEL": "openai/gpt-4o-mini",
        "OPENROUTER_SUMMARIZE_CHAPTER_MODEL": "example/summary",
        "OPENROUTER_SUMMARIZE_CHAPTER_REASONING": "medium",
        "OPENROUTER_EXTRACT_CHARACTER_MODEL": "example/characters",
        "OPENROUTER_MAX_TOKENS": 8192,
        "OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS": 4096,
        "OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS": 16384,
        "OPENROUTER_EXTRACT_CHARACTER_PROVIDER": "open-inference/fp4",
        "OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS": False,
        "OPENROUTER_EXTRACT_CHARACTER_REASONING": "enabled",
        "OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS": True,
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


def test_text_completion_uses_system_instructions_without_json_or_sampling_options() -> None:
    fake = FakeOpenAI(["  Mara arrived.\n"])
    client = OpenRouterClient(
        settings(),
        client=fake,
        model="test/summarize",  # type: ignore[arg-type]
    )
    assert client.complete_text("Mara arrived at noon.", system_prompt="Summarize in English.") == (
        "Mara arrived."
    )
    request = fake.requests[0]
    assert request["model"] == "test/summarize"
    assert request["messages"] == [
        {"role": "system", "content": "Summarize in English."},
        {"role": "user", "content": "Mara arrived at noon."},
    ]
    assert "response_format" not in request
    assert "temperature" not in request


@pytest.mark.parametrize("reply", ["", " \n\t"])
def test_text_completion_rejects_empty_output(reply: str) -> None:
    client, fake = make([reply])
    with pytest.raises(LLMError, match="empty text"):
        client.complete_text("Mara arrived.", system_prompt="Summarize in English.")
    assert len(fake.requests) == 1


def test_a_wrong_answer_is_retried_with_the_error_in_the_message() -> None:
    client, fake = make(["not json at all", '{"items": [{"cand_id": "c1"}]}', GOOD])
    assert client.complete_json("classify", MapResponse).items
    assert len(fake.requests) == 3  # the first answer plus two retries
    second = fake.requests[1]["messages"]
    assert second[1] == {"role": "assistant", "content": "not json at all"}
    assert "Rejected:" in second[2]["content"] and "json" in second[2]["content"].lower()
    assert "role" in fake.requests[2]["messages"][-1]["content"]  # names the missing field


def test_model_override_is_used_for_the_request_and_validation_retry() -> None:
    fake = FakeOpenAI(["invalid", GOOD])
    client = OpenRouterClient(
        settings(),
        client=fake,
        model="example/characters",  # type: ignore[arg-type]
    )
    client.complete_json("classify", MapResponse)
    assert [request["model"] for request in fake.requests] == [
        "example/characters",
        "example/characters",
    ]


def test_output_token_limit_comes_from_settings() -> None:
    fake = FakeOpenAI([GOOD])
    client = OpenRouterClient(settings(OPENROUTER_MAX_TOKENS=32768), client=fake)  # type: ignore[arg-type]
    client.complete_json("classify", MapResponse)
    assert fake.requests[0]["max_tokens"] == 32768


def test_output_token_limit_can_come_from_a_graph_setting() -> None:
    fake = FakeOpenAI([GOOD])
    client = OpenRouterClient(
        settings(OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS=65536),
        client=fake,  # type: ignore[arg-type]
        max_tokens_setting="OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS",
    )
    client.complete_json("classify", MapResponse)
    assert fake.requests[0]["max_tokens"] == 65536


def test_truncation_names_the_setting_that_limited_the_output() -> None:
    fake = FakeOpenAI([GOOD])
    original = fake.chat.completions.create

    def truncated(**kwargs: Any) -> Any:
        response = original(**kwargs)
        response.choices[0].finish_reason = "length"
        return response

    fake.chat.completions.create = truncated
    client = OpenRouterClient(
        settings(),
        client=fake,  # type: ignore[arg-type]
        max_tokens_setting="OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS",
    )
    with pytest.raises(LLMError, match="OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS=4096"):
        client.complete_text("Mara arrived.", system_prompt="Summarize in English.")


@pytest.mark.parametrize("text_mode", [False, True])
def test_truncated_output_is_reported_without_retrying_the_same_token_limit(
    text_mode: bool,
) -> None:
    client, fake = make([GOOD])
    original = fake.chat.completions.create

    def truncated(**kwargs: Any) -> Any:
        response = original(**kwargs)
        response.choices[0].finish_reason = "length"
        return response

    fake.chat.completions.create = truncated
    with pytest.raises(LLMError, match="truncated.*OPENROUTER_MAX_TOKENS"):
        if text_mode:
            client.complete_text("Mara arrived.", system_prompt="Summarize in English.")
        else:
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


@pytest.mark.parametrize(
    ("reasoning", "expected_reasoning"),
    [
        ("none", None),
        ("enabled", {"enabled": True}),
        ("low", {"effort": "low"}),
        ("medium", {"effort": "medium"}),
        ("high", {"effort": "high"}),
    ],
)
def test_extract_client_sends_strict_json_schema_pinned_provider_and_reasoning(
    reasoning: ReasoningMode, expected_reasoning: dict[str, Any] | None
) -> None:
    fake = FakeOpenAI([GOOD_CHAR])
    configured = settings(
        OPENROUTER_EXTRACT_CHARACTER_MODEL="z-ai/glm-5.3-flash",
        OPENROUTER_EXTRACT_CHARACTER_REASONING=reasoning,
    )
    client = OpenRouterClient(
        configured,
        client=fake,  # type: ignore[arg-type]
        model=configured.OPENROUTER_EXTRACT_CHARACTER_MODEL,
        max_tokens_setting="OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS",
        provider=configured.OPENROUTER_EXTRACT_CHARACTER_PROVIDER,
        allow_fallbacks=configured.OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS,
        reasoning=configured.OPENROUTER_EXTRACT_CHARACTER_REASONING,
        structured_outputs=configured.OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS,
    )
    response = client.complete_json("extract", ExtractCharacterResponse)
    assert response.characters[0].candidate_name == "Mara"

    request = fake.requests[0]
    assert request["model"] == "z-ai/glm-5.3-flash"
    assert request["max_tokens"] == 16384
    assert request["temperature"] == 0
    assert request["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "ExtractCharacterResponse",
            "strict": True,
            "schema": strict_json_schema(ExtractCharacterResponse),
        },
    }
    expected_extra_body: dict[str, Any] = {
        "provider": {
            "only": ["open-inference/fp4"],
            "allow_fallbacks": False,
            "require_parameters": True,
        }
    }
    if expected_reasoning is not None:
        expected_extra_body["reasoning"] = expected_reasoning
    assert request["extra_body"] == expected_extra_body


def test_structured_outputs_false_with_empty_provider_equals_todays_request() -> None:
    fake = FakeOpenAI([GOOD_CHAR])
    client = OpenRouterClient(
        settings(),
        client=fake,  # type: ignore[arg-type]
        model="z-ai/glm-5.3-flash",
        max_tokens_setting="OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS",
        provider="",
        allow_fallbacks=False,
        reasoning="none",
        structured_outputs=False,
    )
    client.complete_json("extract", ExtractCharacterResponse)
    request = fake.requests[0]
    assert request == {
        "model": "z-ai/glm-5.3-flash",
        "messages": [{"role": "user", "content": "extract"}],
        "response_format": {"type": "json_object"},
        "max_tokens": 16384,
        "temperature": 0,
    }


def test_extract_character_response_strict_schema_matches_prompt_output_example() -> None:
    schema = strict_json_schema(ExtractCharacterResponse)
    objects_checked = 0

    def walk(node: Any) -> None:
        nonlocal objects_checked
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                objects_checked += 1
                props = node.get("properties", {})
                assert node.get("additionalProperties") is False
                assert node.get("required") == list(props.keys())
                assert "identity_context" not in props
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    assert objects_checked == 3

    match = re.search(r"OUTPUT\n.*?\n(\{\{.*?\}\})\n\nIf this chapter", PROMPT_EXTRACT_CHAR, re.S)
    assert match is not None
    prompt_example = json.loads(match.group(1).replace("{{", "{").replace("}}", "}"))

    assert set(schema["properties"].keys()) == set(prompt_example.keys())
    candidate_schema = schema["$defs"]["CharacterCandidate"]
    attributes_schema = schema["$defs"]["CharacterAttributes"]
    for example_record in prompt_example["characters"]:
        assert set(candidate_schema["properties"].keys()) == set(example_record.keys())
        assert set(attributes_schema["properties"].keys()) == set(
            example_record["attributes"].keys()
        )


def test_summary_client_request_remains_unchanged() -> None:
    fake = FakeOpenAI(["Chapter summary text."])
    configured = settings()
    summary_client = OpenRouterClient(
        configured,
        client=fake,  # type: ignore[arg-type]
        model=configured.OPENROUTER_SUMMARIZE_CHAPTER_MODEL,
        max_tokens_setting="OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS",
    )
    assert summary_client.complete_text("Chapter body.", system_prompt="Summarize.") == (
        "Chapter summary text."
    )
    request = fake.requests[0]
    assert request == {
        "model": "example/summary",
        "messages": [
            {"role": "system", "content": "Summarize."},
            {"role": "user", "content": "Chapter body."},
        ],
        "max_tokens": 4096,
    }


@pytest.mark.parametrize(
    ("reasoning", "expected"),
    [
        ("enabled", {"enabled": True}),
        ("low", {"effort": "low"}),
        ("medium", {"effort": "medium"}),
        ("high", {"effort": "high"}),
    ],
)
def test_text_completion_sends_configured_reasoning(
    reasoning: ReasoningMode, expected: dict[str, Any]
) -> None:
    fake = FakeOpenAI(["Chapter summary."])
    client = OpenRouterClient(settings(), client=fake, reasoning=reasoning)  # type: ignore[arg-type]

    client.complete_text("Chapter body.", system_prompt="Summarize.")

    assert fake.requests[0]["extra_body"] == {"reasoning": expected}
    assert "response_format" not in fake.requests[0]


def test_finish_reason_error_raises_llm_error_without_retry_loop() -> None:
    fake = FakeOpenAI([""])
    original = fake.chat.completions.create

    def errored(**kwargs: Any) -> Any:
        response = original(**kwargs)
        response.choices[0].finish_reason = "error"
        response.choices[0].error = {
            "code": 504,
            "message": "Upstream idle timeout exceeded",
        }
        return response

    fake.chat.completions.create = errored
    client = OpenRouterClient(settings(), client=fake)  # type: ignore[arg-type]
    with pytest.raises(
        LLMError, match="OpenRouter generation failed: Upstream idle timeout exceeded"
    ):
        client.complete_json("extract", ExtractCharacterResponse)
    assert len(fake.requests) == 1


def test_choice_error_object_without_error_finish_reason_raises_llm_error_immediately() -> None:
    fake = FakeOpenAI([""])
    original = fake.chat.completions.create

    def errored(**kwargs: Any) -> Any:
        response = original(**kwargs)
        response.choices[0].finish_reason = "stop"
        response.choices[0].error = {"code": 502, "message": "Provider disconnected mid-stream"}
        return response

    fake.chat.completions.create = errored
    client = OpenRouterClient(settings(), client=fake)  # type: ignore[arg-type]
    with pytest.raises(
        LLMError, match="OpenRouter generation failed: Provider disconnected mid-stream"
    ):
        client.complete_json("extract", ExtractCharacterResponse)
    assert len(fake.requests) == 1
