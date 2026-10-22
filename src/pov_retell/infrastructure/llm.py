"""A minimal OpenRouter client: ask for JSON, validate it with Pydantic, retry with the error.

Why so small: phase A only needs ONE kind of call, "classify these candidates". The rules that
matter are the same for every later LLM step too:

- `json_object` mode, then Pydantic validation: the model's answer is untrusted input;
- a wrong answer is retried at most twice, and the retry message carries the exact error, so
  the model can fix it instead of repeating it.
"""

from collections.abc import Callable
from typing import Protocol, TypeVar

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from pov_retell.config import Settings

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 2  # extra attempts after the first answer


class LLMError(RuntimeError):
    """The LLM call failed or kept returning unusable answers."""


class JsonLLM(Protocol):
    """What the rest of the code needs from an LLM. Tests pass a fake that implements this."""

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T: ...


class OpenRouterClient:
    def __init__(self, settings: Settings | None = None, client: OpenAI | None = None) -> None:
        settings = settings or Settings()  # type: ignore[call-arg]  # required fields come from .env
        self.model = settings.OPENROUTER_MODEL
        self.max_tokens = settings.OPENROUTER_MAX_TOKENS
        if client is None:
            key = settings.OPENROUTER_API_KEY.get_secret_value()
            if not key:
                raise LLMError("OPENROUTER_API_KEY is not set (put it in .env)")
            client = OpenAI(api_key=key, base_url=settings.OPENROUTER_BASE_URL)
        self._client = client

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T:
        """Return the answer parsed as `schema`; `check` may raise ValueError to reject it."""
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": prompt}]
        error = ""
        for _ in range(1 + MAX_RETRIES):
            reply = self._ask(messages)
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

    def _ask(self, messages: list[ChatCompletionMessageParam]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                temperature=0,
            )
        except OpenAIError as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc
        if not response.choices:
            error = getattr(response, "error", None)
            message = error.get("message") if isinstance(error, dict) else "no choices returned"
            raise LLMError(f"OpenRouter request failed: {message}")
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise LLMError(
                f"OpenRouter response was truncated at OPENROUTER_MAX_TOKENS={self.max_tokens}; "
                "increase this value in .env or reduce the requested output"
            )
        return choice.message.content or ""
