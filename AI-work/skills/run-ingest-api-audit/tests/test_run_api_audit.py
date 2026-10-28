import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import OpenAI
from pydantic import SecretStr
from test_llm import settings

from pov_retell.infrastructure.llm import LLMError, OpenRouterClient

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_api_audit.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("run_api_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_truncated_response_is_saved_before_production_client_raises(tmp_path: Path) -> None:
    audit = load_module()
    recorder = audit.Recorder(tmp_path, secrets=["test-key"])
    recorder.phase = "extract_character"
    recorder.step("extract_characters u02")

    def reply(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "id": "gen_failure",
                "model": "example/model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "length",
                        "message": {"role": "assistant", "content": '{"characters":['},
                    }
                ],
                "usage": {
                    "completion_tokens": 64,
                    "completion_tokens_details": {"reasoning_tokens": 60},
                },
            },
        )

    with httpx.Client(
        transport=httpx.MockTransport(reply),
        event_hooks={
            "request": [recorder.on_request],
            "response": [recorder.on_response],
        },
    ) as http:
        with OpenAI(
            api_key="test-key",
            base_url="https://example.invalid/v1",
            http_client=http,
            max_retries=0,
        ) as transport:
            client = OpenRouterClient(settings(), client=transport)
            with pytest.raises(LLMError, match="truncated"):
                client.complete_text("Source text", system_prompt="Summarize")
    saved = json.loads((tmp_path / "http/http_0001.response.json").read_text())
    assert saved["response"]["id"] == "gen_failure"
    assert saved["response"]["usage"]["completion_tokens_details"]["reasoning_tokens"] == 60
    assert saved["chapter_id"] == "u02" and saved["phase"] == "extract_character"
    assert saved["response"]["choices"][0]["message"]["content"] == '{"characters":['
    all_text = "\n".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    assert "test-key" not in all_text and "Bearer" not in all_text


def test_dry_run_uses_no_api_or_database_and_refuses_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit = load_module()

    def unexpected_api(**kwargs: Any) -> None:
        raise AssertionError("Dry runs must not construct an API client")

    monkeypatch.setattr(audit, "OpenAI", unexpected_api)
    monkeypatch.setattr(audit, "Settings", lambda: settings())
    output = tmp_path / "audit"
    assert audit.main(["--smoke", "--output", str(output)]) == 0
    status = json.loads((output / "progress.json").read_text())
    assert status["status"] == "planned" and status["http_calls"] == 0
    assert status["expected_chapters"] == 2
    assert not (output / "characters.json").exists()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["extract_character"] == {
        "provider": "open-inference/fp4",
        "allow_fallbacks": False,
        "reasoning": "enabled",
        "structured_outputs": True,
    }
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        audit.main(["--smoke", "--output", str(output)])
    assert (output / "manifest.json").read_bytes() == before


def test_failure_report_preserves_unknown_usage_and_redacts_secrets(tmp_path: Path) -> None:
    audit = load_module()
    recorder = audit.Recorder(tmp_path, secrets=["secret-value"])
    recorder.phase = "summarize_chapter"
    recorder.step("summarize_chapter u01")
    recorder.fail(RuntimeError("Provider failed for secret-value"))
    failure = json.loads((tmp_path / "failure.json").read_text())
    assert failure["error_type"] == "RuntimeError"
    assert failure["last_http"] is None
    assert "secret-value" not in json.dumps(failure)
    status = json.loads((tmp_path / "progress.json").read_text())
    assert status["status"] == "failed" and status["phase"] == "summarize_chapter"


def test_complete_graph_workflow_records_all_responses_with_mock_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit = load_module()
    configured = settings(OPENROUTER_API_KEY=SecretStr("test-key"))
    monkeypatch.setattr(audit, "Settings", lambda: configured)
    replies = [
        "Mara and the captain were introduced.",
        "Mara | - | friend of Jo\nthe masked captain | - | cautious woman",
        "The Gate | - | stone gate",
        "The captain revealed she was Mara.",
        "Mara | the masked captain | cautious woman and friend of Jo",
        "The Gate | - | stone gate\nGreat Hall | - | hall inside the gate",
        "The masked captain revealed she was Mara.",
        json.dumps(
            {
                "characters": [
                    {"character_id": "new_1", "candidate_name": "Mara"},
                    {"character_id": "new_2", "candidate_name": "Jo"},
                ]
            }
        ),
        json.dumps(
            {
                "relationships": [
                    {
                        "op": "start",
                        "source_id": "char_001",
                        "target_id": "char_002",
                        "kind": "friend of",
                        "paragraph_ids": ["u01_p001"],
                    }
                ]
            }
        ),
        json.dumps(
            {
                "locations": [
                    {
                        "location_id": "new_1",
                        "name": "the stone gate",
                        "aliases": [],
                        "kind": "stone gate",
                        "part_of": None,
                    }
                ]
            }
        ),
        json.dumps(
            {
                "segments": [
                    {
                        "start": "u01_p001",
                        "end": "u01_p001",
                        "location_id": "loc_001",
                        "present_ids": ["char_001", "char_002"],
                        "mentioned_ids": [],
                        "viewpoint_ids": ["char_002"],
                        "time": {"relation": "continues", "anchor": None, "note": None},
                        "label": "Jo meets the masked captain at the stone gate",
                    }
                ]
            }
        ),
        json.dumps({"characters": [{"character_id": "char_001", "candidate_name": "Mara"}]}),
        json.dumps({"relationships": []}),
        json.dumps(
            {
                "locations": [
                    {
                        "location_id": "new_1",
                        "name": "the inner courtyard",
                        "aliases": [],
                        "kind": "walled courtyard",
                        "part_of": "loc_001",
                    }
                ]
            }
        ),
        json.dumps(
            {
                "segments": [
                    {
                        "start": "u02_p001",
                        "end": "u02_p001",
                        "location_id": "loc_002",
                        "present_ids": ["char_001", "char_002"],
                        "mentioned_ids": [],
                        "viewpoint_ids": ["char_002"],
                        "time": {"relation": "continues", "anchor": None, "note": None},
                        "label": "The masked captain reveals she is Mara",
                    }
                ]
            }
        ),
    ]

    def reply(request: httpx.Request) -> httpx.Response:
        content = replies.pop(0)
        return httpx.Response(
            200,
            json={
                "id": f"fixture-{len(replies)}",
                "model": "fixture/model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
                "usage": {"completion_tokens": 10},
            },
        )

    original = httpx.Client

    class LocalClient(original):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["transport"] = httpx.MockTransport(reply)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(audit.httpx, "Client", LocalClient)
    output = tmp_path / "complete"
    assert audit.main(["--smoke", "--live", "--output", str(output)]) == 0
    assert replies == []
    state = json.loads((output / "progress.json").read_text())
    assert state["status"] == "completed"
    assert state["quality_status"] == "not_reviewed"
    assert state["summary_files"] == state["character_snapshots"] == 2
    assert (output / "summaries/book_memory.json").exists()
    assert (output / "relationships.json").exists()
    assert (output / "locations.json").exists()
    assert (output / "chapters/u01.scenes.json").exists()
    assert (output / "chapters/u02.scenes.json").exists()
    assert state["http_calls"] == 15
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["neo4j_writes"] is False
    assert manifest["summary_reasoning"] == "medium"
    assert manifest["extract_character"] == {
        "provider": "open-inference/fp4",
        "allow_fallbacks": False,
        "reasoning": "enabled",
        "structured_outputs": True,
    }
    summary_req = json.loads((output / "http/http_0001.request.json").read_text())["request"]
    assert summary_req["response_format"] is None
    assert summary_req["provider"] is None
    assert summary_req["reasoning"] == {"effort": "medium"}
    extract_req = json.loads((output / "http/http_0008.request.json").read_text())["request"]
    assert extract_req["response_format"]["type"] == "json_schema"
    assert extract_req["response_format"]["json_schema"]["strict"] is True
    assert extract_req["provider"] == {
        "only": ["open-inference/fp4"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }
    assert extract_req["reasoning"] == {"enabled": True}
    assert len(list((output / "http").glob("*.response.json"))) == 15
