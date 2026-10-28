"""OpenRouter requests for JSON extraction and plain-text summarization."""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from langsmith.wrappers import wrap_openai
from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from pov_retell.config import ReasoningMode, Settings

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 2  # extra attempts after the first answer


class LLMError(RuntimeError):
    """The LLM call failed or kept returning unusable answers."""


def _enforce_strict_objects(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            props = node.get("properties", {})
            node["additionalProperties"] = False
            node["required"] = list(props.keys())
        for value in node.values():
            _enforce_strict_objects(value)
    elif isinstance(node, list):
        for item in node:
            _enforce_strict_objects(item)


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build a strict JSON Schema from `model` (excluding `exclude=True` fields)."""
    schema = model.model_json_schema(mode="serialization")
    _enforce_strict_objects(schema)
    return schema


def _extract_error_message(error_obj: Any) -> str | None:
    if isinstance(error_obj, dict):
        msg = error_obj.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        code = error_obj.get("code")
        if code is not None:
            return f"error code {code}"
    elif error_obj is not None:
        msg = getattr(error_obj, "message", None)
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        text = str(error_obj).strip()
        if text:
            return text
    return None


class JsonLLM(Protocol):
    """What the rest of the code needs from an LLM. Tests pass a fake that implements this."""

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T: ...


class TextLLM(Protocol):
    def complete_text(self, text: str, *, system_prompt: str) -> str: ...


class SummarizeLLM(TextLLM, JsonLLM, Protocol):
    """What the summarize_chapter graph needs: plain text summaries and JSON card updates."""


class OpenRouterClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
        *,
        model: str | None = None,
        max_tokens_setting: str = "OPENROUTER_MAX_TOKENS",
        provider: str = "",
        allow_fallbacks: bool = True,
        reasoning: ReasoningMode = "none",
        structured_outputs: bool = False,
    ) -> None:
        settings = settings or Settings()  # type: ignore[call-arg]  # required fields come from .env
        self.model = settings.OPENROUTER_MODEL if model is None else model
        self.max_tokens_setting = max_tokens_setting
        self.max_tokens: int = getattr(settings, max_tokens_setting)
        self.providers = [tag.strip() for tag in provider.split(",") if tag.strip()]
        self.allow_fallbacks = allow_fallbacks
        self.reasoning: ReasoningMode = reasoning
        self.structured_outputs = structured_outputs
        if client is None:
            key = settings.OPENROUTER_API_KEY.get_secret_value()
            if not key:
                raise LLMError("OPENROUTER_API_KEY is not set (put it in .env)")
            client = wrap_openai(OpenAI(api_key=key, base_url=settings.OPENROUTER_BASE_URL))
        self._client = client

    def complete_text(self, text: str, *, system_prompt: str) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        reasoning = self._reasoning_options()
        extra_body = {"reasoning": reasoning} if reasoning is not None else None
        reply = self._ask(messages, json_mode=False, extra_body=extra_body).strip()
        if not reply:
            raise LLMError("OpenRouter returned an empty text response")
        return reply

    def _reasoning_options(self) -> dict[str, Any] | None:
        if self.reasoning == "enabled":
            return {"enabled": True}
        if self.reasoning in ("low", "medium", "high"):
            return {"effort": self.reasoning}
        return None

    def _json_request_options(
        self, schema: type[BaseModel]
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if self.structured_outputs:
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": strict_json_schema(schema),
                },
            }
        else:
            response_format = {"type": "json_object"}

        extra_body: dict[str, Any] = {}
        if self.providers:
            provider_body: dict[str, Any] = {
                "only": list(self.providers),
                "allow_fallbacks": self.allow_fallbacks,
            }
            if self.structured_outputs:
                provider_body["require_parameters"] = True
            extra_body["provider"] = provider_body
        elif self.structured_outputs:
            extra_body["provider"] = {"require_parameters": True}

        reasoning = self._reasoning_options()
        if reasoning is not None:
            extra_body["reasoning"] = reasoning

        return response_format, (extra_body or None)

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        """Return the answer parsed as `schema`; `check` may raise ValueError to reject it."""
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": prompt}]
        response_format, extra_body = self._json_request_options(schema)
        error = ""
        for _ in range(1 + MAX_RETRIES):
            reply = self._ask(
                messages,
                response_format=response_format,
                extra_body=extra_body,
            )
            try:
                value = schema.model_validate_json(reply)
                if check is not None:
                    check(value)
                return value
            except (ValidationError, ValueError) as exc:
                error = str(exc)
                messages += [
                    {"role": "assistant", "content": reply or "(empty)"},
                    {"role": "user", "content": f"Rejected: {error}\nReturn corrected JSON only."},
                ]
        raise LLMError(f"no valid answer after {1 + MAX_RETRIES} attempts: {error}")

    def _ask(
        self,
        messages: list[ChatCompletionMessageParam],
        *,
        json_mode: bool = True,
        response_format: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        try:
            if json_mode:
                fmt: Any = response_format or {"type": "json_object"}
                if extra_body is not None:
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format=fmt,
                        max_tokens=self.max_tokens,
                        temperature=0,
                        extra_body=extra_body,
                    )
                else:
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format=fmt,
                        max_tokens=self.max_tokens,
                        temperature=0,
                    )
            elif extra_body is not None:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    extra_body=extra_body,
                )
            else:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                )
        except OpenAIError as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc
        if not response.choices:
            error = getattr(response, "error", None)
            message = error.get("message") if isinstance(error, dict) else "no choices returned"
            raise LLMError(f"OpenRouter request failed: {message}")
        choice = response.choices[0]
        choice_error = getattr(choice, "error", None)
        finish_reason = getattr(choice, "finish_reason", None)
        if choice_error is not None or finish_reason == "error":
            detail = (
                _extract_error_message(choice_error)
                or _extract_error_message(getattr(response, "error", None))
                or "provider returned finish_reason=error"
            )
            raise LLMError(f"OpenRouter generation failed: {detail}")
        if finish_reason == "length":
            raise LLMError(
                f"OpenRouter response was truncated at "
                f"{self.max_tokens_setting}={self.max_tokens}; "
                "increase this value in .env or reduce the requested output"
            )
        return choice.message.content or ""
