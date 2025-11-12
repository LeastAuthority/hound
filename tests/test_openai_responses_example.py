"""Tests for the lightweight OpenAI Responses example + helper flow."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from examples import openai_responses_example as example
from llm.openai_provider import OpenAIProvider


class DummyProvider:
    """Simple provider used to intercept example calls."""

    def __init__(self, payload: str = '{"bullets": ["ok"]}'):
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    def raw(self, *, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.payload


def _stub_response(payload: dict) -> SimpleNamespace:
    """Return a Response-like stub exposing json()."""
    return SimpleNamespace(json=lambda payload=payload: payload)


@pytest.fixture()
def provider(monkeypatch) -> OpenAIProvider:
    """Instantiate OpenAIProvider with network calls patched out."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("llm.openai_provider.OpenAI") as mock_openai:
        mock_openai.return_value = MagicMock()
        provider = OpenAIProvider(
            config={"openai": {"api_key_env": "OPENAI_API_KEY"}},
            model_name="gpt-5-pro",
            timeout=5,
            retries=1,
        )
    return provider


def test_run_responses_job_handles_polling(monkeypatch, provider: OpenAIProvider):
    """Ensure _run_responses_job polls until completion and returns payload."""
    responses = [
        {"id": "job-1", "status": "queued"},
        {"id": "job-1", "status": "in_progress"},
        {
            "id": "job-1",
            "status": "completed",
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "Result text"},
                    ]
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        },
    ]

    def fake_safe_request(method: str, url: str, **_: object):
        if not responses:
            pytest.fail("Safe request called more times than responses provided")
        return _stub_response(responses.pop(0))

    provider._safe_request = fake_safe_request  # type: ignore[method-assign]
    monkeypatch.setattr("llm.openai_provider.time.sleep", lambda *_: None)

    result = provider._run_responses_job({"model": "gpt-5-pro", "input": "hi", "instructions": "sys"})

    assert result["status"] == "completed"
    assert example.DEFAULT_USER_PROMPT  # Sanity check - module import succeeded.
    text = provider._extract_output_text(result)
    assert text == "Result text"


def test_example_run_can_use_dummy_provider():
    """The example runner should accept an injected provider for tests."""
    dummy = DummyProvider(payload="demo")
    output = example.run_example(
        system_prompt="sys",
        user_prompt="usr",
        provider=dummy,
    )

    assert output == "demo"
    assert dummy.calls == [("sys", "usr")]


def test_example_main_prints_output(capsys):
    """The example CLI prints provider output when main() succeeds."""
    dummy = DummyProvider(payload="from-main")

    def builder():
        return dummy

    exit_code = example.main(builder=builder)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "from-main" in captured.out
