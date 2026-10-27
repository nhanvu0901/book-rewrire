"""Run isolated summary/character API diagnostics without writing to Neo4j."""

import argparse
import hashlib
import json
import os
import re
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from openai import OpenAI

from pov_retell.config import Settings
from pov_retell.infrastructure.llm import OpenRouterClient
from pov_retell.ingest.graph.extract_character.graph import (
    build_extract_character_graph,
    extract_character_recursion_limit,
)
from pov_retell.ingest.graph.summarize_chapter.graph import (
    build_summarize_chapter_graph,
    summarize_chapter_recursion_limit,
)
from pov_retell.ingest.model import Chapter
from pov_retell.ingest.source import load_chapters

REPO = Path(__file__).resolve().parents[4]


def now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class Recorder:
    def __init__(self, output: Path, *, secrets: list[str]) -> None:
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.secrets = [value for value in secrets if value]
        self.phase = "setup"
        self.chapter_id: str | None = None
        self.http_calls = 0
        self.last_http: dict[str, Any] | None = None
        self.state: dict[str, Any] = {
            "status": "running",
            "pid": os.getpid(),
            "started_at": now(),
            "quality_status": "not_reviewed",
        }
        self.save_progress()

    def redact(self, text: str) -> str:
        for value in self.secrets:
            text = text.replace(value, "[REDACTED]")
        return text

    def save(self, path: Path, value: Any) -> None:
        clean = json.loads(self.redact(json.dumps(value, ensure_ascii=False)))
        write_json(path, clean)

    def save_progress(self) -> None:
        self.state.update(
            {
                "updated_at": now(),
                "phase": self.phase,
                "chapter_id": self.chapter_id,
                "http_calls": self.http_calls,
                "last_http": self.last_http,
                "summary_files": len(list((self.output / "summaries").glob("*.summary.json"))),
                "character_snapshots": len(
                    list((self.output / "chapters").glob("*.characters.json"))
                ),
            }
        )
        self.save(self.output / "progress.json", self.state)

    def step(self, message: str) -> None:
        match = re.search(r"\bu\d+\b", message)
        if match:
            self.chapter_id = match[0]
        elif message in ("summarize_book", "save_book_memory"):
            self.chapter_id = None
        self.state["step"] = message
        event = {"time": now(), "phase": self.phase, "chapter_id": self.chapter_id, "step": message}
        with (self.output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(self.redact(json.dumps(event)) + "\n")
        line = self.redact(f"{event['time']} {message}")
        with (self.output / "run.log").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        print(line, flush=True)
        self.save_progress()

    def on_request(self, request: httpx.Request) -> None:
        self.http_calls += 1
        request.extensions["audit_call"] = self.http_calls
        payload = json.loads(request.content)
        messages = payload.get("messages", [])
        last = messages[-1].get("content", "") if messages else ""
        captured = {
            "time": now(),
            "call": self.http_calls,
            "phase": self.phase,
            "chapter_id": self.chapter_id,
            "step": self.state.get("step"),
            "attempt_kind": "repair"
            if isinstance(last, str) and (last.startswith("Rejected:") or "\n\nRejected:" in last)
            else "initial",
            "request": {
                key: payload.get(key)
                for key in (
                    "model",
                    "max_tokens",
                    "temperature",
                    "response_format",
                    "provider",
                    "reasoning",
                )
            },
            "request_bytes": len(request.content),
            "request_sha256": hashlib.sha256(request.content).hexdigest(),
        }
        self.save(self.output / "http" / f"http_{self.http_calls:04d}.request.json", captured)
        self.save_progress()

    def on_response(self, response: httpx.Response) -> None:
        response.read()
        try:
            body: Any = response.json()
        except ValueError:
            body = {"unparsed_text": response.text}
        number = response.request.extensions["audit_call"]
        artifact = f"http/http_{number:04d}.response.json"
        self.save(
            self.output / artifact,
            {
                "time": now(),
                "call": number,
                "phase": self.phase,
                "chapter_id": self.chapter_id,
                "status_code": response.status_code,
                "response": body,
            },
        )
        data = body if isinstance(body, dict) else {}
        choices = data.get("choices") or []
        choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        self.last_http = {
            "artifact": artifact,
            "status_code": response.status_code,
            "response_id": data.get("id"),
            "returned_model": data.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "usage": data.get("usage"),
        }
        self.save_progress()

    def fail(self, error: BaseException) -> None:
        failure = {
            "time": now(),
            "phase": self.phase,
            "chapter_id": self.chapter_id,
            "step": self.state.get("step"),
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": "".join(traceback.format_exception(error)),
            "last_http": self.last_http,
        }
        self.save(self.output / "failure.json", failure)
        self.state.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error=str(error),
            ended_at=now(),
        )
        self.save_progress()
        self.step(f"ERROR {type(error).__name__}: {error}")


def smoke_chapters() -> list[Chapter]:
    texts = [
        "At the stone gate, Mara's friend Jo met the masked captain. "
        "The narrator called the captain cautious. "
        "The captain was a human woman with a scar on her left cheek. "
        "Mara had dark hair. Nobody yet knew who the captain was.",
        "Inside the inner courtyard behind the stone gate, the masked captain removed her mask "
        "and revealed that she was Mara. "
        "Jo recognized Mara. The scar on Mara's left cheek was visible.",
    ]
    return [
        Chapter(f"u{i:02d}", f"[u{i:02d}_p001] {text}", {f"u{i:02d}_p001": text})
        for i, text in enumerate(texts, 1)
    ]


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Value must be positive")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--smoke", action="store_true", help="Use two synthetic chapters")
    scope.add_argument("--book-id", help="Use an existing extracted book")
    parser.add_argument("--max-chapters", type=positive, help="Use the first N validated chapters")
    parser.add_argument("--output", type=Path, required=True, help="Fresh diagnostic directory")
    parser.add_argument("--live", action="store_true", help="Actually call configured APIs")
    parser.add_argument("--timeout-seconds", type=positive, default=120)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(output, secrets=[])
    try:
        settings = Settings()
        key = settings.OPENROUTER_API_KEY.get_secret_value()
        recorder.secrets = [key] if key else []
        book_id = args.book_id or "api-smoke"
        title, chapters = (
            ("The Masked Captain", smoke_chapters())
            if args.smoke
            else load_chapters(settings.extracted_dir, book_id)
        )
        if args.max_chapters:
            chapters = chapters[: args.max_chapters]
        recorder.state["expected_chapters"] = len(chapters)
        recorder.save(
            output / "manifest.json",
            {
                "created_at": now(),
                "book_id": book_id,
                "live": args.live,
                "scope": "smoke" if args.smoke else "book",
                "chapter_ids": [c.unit_id for c in chapters],
                "source_sha256": hashlib.sha256(
                    "\n".join(c.text for c in chapters).encode()
                ).hexdigest(),
                "models": {
                    "summarize_chapter": settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL,
                    "extract_character": settings.OPENROUTER_EXTRACT_CHARACTER_MODEL,
                },
                "max_tokens": {
                    "summarize_chapter": settings.OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS,
                    "extract_character": settings.OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS,
                },
                "summary_reasoning": settings.OPENROUTER_SUMMARIZE_CHAPTER_REASONING,
                "extract_character": {
                    "provider": settings.OPENROUTER_EXTRACT_CHARACTER_PROVIDER,
                    "allow_fallbacks": settings.OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS,
                    "reasoning": settings.OPENROUTER_EXTRACT_CHARACTER_REASONING,
                    "structured_outputs": settings.OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS,
                },
                "sdk_retries": 0,
                "timeout_seconds": args.timeout_seconds,
                "neo4j_writes": False,
                "repo_root": str(REPO),
            },
        )
        if not args.live:
            recorder.state.update(status="planned", ended_at=now())
            recorder.step("Dry run only; no API requests or Neo4j writes")
            return 0
        with httpx.Client(
            timeout=args.timeout_seconds,
            event_hooks={
                "request": [recorder.on_request],
                "response": [recorder.on_response],
            },
        ) as http:
            with OpenAI(
                api_key=key,
                base_url=settings.OPENROUTER_BASE_URL,
                http_client=cast(Any, http),
                timeout=args.timeout_seconds,
                max_retries=0,
            ) as transport:
                recorder.phase = "summarize_chapter"
                recorder.chapter_id = None
                recorder.step(
                    "Build summarize_chapter graph: model="
                    + settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL
                )
                summary_graph = build_summarize_chapter_graph(
                    OpenRouterClient(
                        settings,
                        client=transport,
                        model=settings.OPENROUTER_SUMMARIZE_CHAPTER_MODEL,
                        max_tokens_setting="OPENROUTER_SUMMARIZE_CHAPTER_MAX_TOKENS",
                        reasoning=settings.OPENROUTER_SUMMARIZE_CHAPTER_REASONING,
                    ),
                    recorder.step,
                )
                summaries = summary_graph.invoke(
                    {
                        "title": title,
                        "chapters": chapters,
                        "output_dir": output,
                    },
                    {"recursion_limit": summarize_chapter_recursion_limit(len(chapters))},
                )
                recorder.phase = "extract_character"
                recorder.chapter_id = None
                recorder.step(
                    "Build extract_character graph: model="
                    + settings.OPENROUTER_EXTRACT_CHARACTER_MODEL
                )
                character_graph = build_extract_character_graph(
                    OpenRouterClient(
                        settings,
                        client=transport,
                        model=settings.OPENROUTER_EXTRACT_CHARACTER_MODEL,
                        max_tokens_setting="OPENROUTER_EXTRACT_CHARACTER_MAX_TOKENS",
                        provider=settings.OPENROUTER_EXTRACT_CHARACTER_PROVIDER,
                        allow_fallbacks=settings.OPENROUTER_EXTRACT_CHARACTER_ALLOW_FALLBACKS,
                        reasoning=settings.OPENROUTER_EXTRACT_CHARACTER_REASONING,
                        structured_outputs=settings.OPENROUTER_EXTRACT_CHARACTER_STRUCTURED_OUTPUTS,
                    ),
                    recorder.step,
                )
                character_graph.invoke(
                    {
                        "book_id": book_id,
                        "run_id": output.name,
                        "title": title,
                        "chapters": chapters,
                        "summaries": summaries["summaries"],
                        "output_dir": output,
                    },
                    {"recursion_limit": extract_character_recursion_limit(len(chapters))},
                )
        recorder.phase = "done"
        recorder.chapter_id = None
        recorder.state.update(status="completed", ended_at=now())
        recorder.step(
            "Completed API workflow; factual quality requires parent review; no Neo4j writes"
        )
        return 0
    except (Exception, KeyboardInterrupt) as error:
        recorder.fail(error)
        return 130 if isinstance(error, KeyboardInterrupt) else 1


if __name__ == "__main__":
    sys.exit(main())
