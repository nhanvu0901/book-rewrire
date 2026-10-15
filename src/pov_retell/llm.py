"""A minimal DeepSeek client: ask for JSON, validate it with Pydantic, retry with the error.

Why so small: phase A only needs ONE kind of call, "classify these candidates". The rules that
matter are the same for every later LLM step too:

- thinking is ALWAYS disabled (DeepSeek turns it on by default and it would bill reasoning
  tokens we never read), so the client has no switch for it at all;
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
MAX_TOKENS = 8192


class LLMError(RuntimeError):
    """The LLM call failed or kept returning unusable answers."""


class JsonLLM(Protocol):
    """What the rest of the code needs from an LLM. Tests pass a fake that implements this."""

    def complete_json(
        self, prompt: str, schema: type[T], check: Callable[[T], None] | None = None
    ) -> T: ...


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None, client: OpenAI | None = None) -> None:
        settings = settings or Settings()
        self.model = settings.DEEPSEEK_MODEL
        if client is None:
            key = settings.DEEPSEEK_API_KEY.get_secret_value()
            if not key:
                raise LLMError(
                    "DEEPSEEK_API_KEY is not set (put it in ~/.config/book-clone/secrets.env)"
                )
            client = OpenAI(api_key=key, base_url=settings.DEEPSEEK_BASE_URL)
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
                extra_body={
                    "thinking": {"type": "disabled"}
                },  # never enabled, see module docstring
                max_tokens=MAX_TOKENS,
                temperature=0,
            )
        except OpenAIError as exc:
            raise LLMError(f"DeepSeek request failed: {exc}") from exc
        return response.choices[0].message.content or ""
