"""Anthropic adapter tests (M3 — REQ-MVP-038/041, AC-MVP-013/014 seed, REQ-MVP-044 seed).

All tests run against an injected fake client — no network, no API key. The
fake records the exact ``messages.create`` kwargs so the tests pin the wire
contract: pinned model id, cache_control on the fixed system prefix, neutral
tool-schema conversion, verbatim assistant echo, and structured error
normalization (raw SDK errors never escape the adapter un-normalized).
"""

from __future__ import annotations

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from server.llm.anthropic_adapter import AnthropicAdapter
from server.llm.config import AnthropicSettings
from server.llm.errors import ProviderError
from server.llm.types import (
    ModelTurn,
    ToolCall,
    ToolDefinition,
    ToolResult,
    ToolResultsMessage,
    Usage,
    UserMessage,
)

_PREFIX = "RULEBOOK PREFIX (fixed)"

_TOOL = ToolDefinition(
    name="run_commands",
    description="Execute MA3 command lines.",
    parameters={
        "type": "object",
        "properties": {"commands": {"type": "array", "items": {"type": "string"}}},
        "required": ["commands"],
    },
)


def _settings(**overrides) -> AnthropicSettings:
    return AnthropicSettings(model="claude-opus-4-8", **overrides)


def _text_response(text: str = "done") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=10,
            cache_read_input_tokens=90,
            cache_creation_input_tokens=0,
        ),
    )


def _tool_use_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="running"),
            SimpleNamespace(
                type="tool_use",
                id="toolu_01",
                name="run_commands",
                input={"commands": ["Store Cue 5"]},
            ),
        ],
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, *responses):
        self.messages = FakeMessages(responses)


def _complete(adapter_client, conversation=None, tools=(_TOOL,), settings=None):
    adapter = AnthropicAdapter(settings or _settings(), client=adapter_client)
    turn = adapter.complete(
        system_prefix=_PREFIX,
        conversation=conversation or [UserMessage(text="보컬 그룹 만들어줘")],
        tools=tools,
    )
    return adapter, turn


class TestRequestConstruction:
    def test_model_id_is_pinned_from_settings(self):
        client = FakeClient(_text_response())
        _complete(client)
        assert client.messages.calls[0]["model"] == "claude-opus-4-8"

    def test_system_prefix_carries_cache_control(self):
        # REQ-MVP-007/041 — prompt caching on the fixed rulebook prefix.
        client = FakeClient(_text_response())
        _complete(client)
        system = client.messages.calls[0]["system"]
        assert system == [{"type": "text", "text": _PREFIX, "cache_control": {"type": "ephemeral"}}]

    def test_caching_disabled_sends_plain_system_string(self):
        client = FakeClient(_text_response())
        adapter, _ = _complete(client, settings=_settings(prompt_caching=False))
        assert client.messages.calls[0]["system"] == _PREFIX
        assert adapter.supports_prompt_caching is False

    def test_neutral_tools_converted_to_anthropic_schema(self):
        client = FakeClient(_text_response())
        _complete(client)
        tools = client.messages.calls[0]["tools"]
        assert tools == [
            {
                "name": "run_commands",
                "description": "Execute MA3 command lines.",
                "input_schema": _TOOL.parameters,
            }
        ]

    def test_adaptive_thinking_and_effort_are_passed(self):
        client = FakeClient(_text_response())
        _complete(client)
        call = client.messages.calls[0]
        assert call["thinking"] == {"type": "adaptive"}
        assert call["output_config"] == {"effort": "high"}

    def test_user_message_becomes_user_role(self):
        client = FakeClient(_text_response())
        _complete(client)
        messages = client.messages.calls[0]["messages"]
        assert messages == [{"role": "user", "content": "보컬 그룹 만들어줘"}]

    def test_own_assistant_turn_is_echoed_verbatim(self):
        # Anthropic requires echoing prior assistant content blocks unchanged.
        payload = [SimpleNamespace(type="text", text="earlier")]
        prior = ModelTurn(
            text="earlier",
            tool_calls=(),
            stop_reason="end",
            usage=Usage(),
            provider="anthropic",
            provider_payload=payload,
        )
        client = FakeClient(_text_response())
        _complete(client, conversation=[UserMessage(text="hi"), prior, UserMessage(text="next")])
        messages = client.messages.calls[0]["messages"]
        assert messages[1] == {"role": "assistant", "content": payload}

    def test_foreign_assistant_turn_is_reconstructed_neutrally(self):
        prior = ModelTurn(
            text="from gemini",
            tool_calls=(ToolCall(id="g-0", name="query_state", arguments={"path": "X"}),),
            stop_reason="tool_use",
            usage=Usage(),
            provider="gemini",
            provider_payload=object(),
        )
        client = FakeClient(_text_response())
        _complete(client, conversation=[UserMessage(text="hi"), prior])
        assistant = client.messages.calls[0]["messages"][1]
        assert assistant["role"] == "assistant"
        types = [block["type"] for block in assistant["content"]]
        assert types == ["text", "tool_use"]

    def test_tool_results_form_a_single_user_message(self):
        results = ToolResultsMessage(
            results=(
                ToolResult(tool_call_id="toolu_01", name="run_commands", content="ok"),
                ToolResult(
                    tool_call_id="toolu_02", name="query_state", content="bad", is_error=True
                ),
            )
        )
        client = FakeClient(_text_response())
        _complete(client, conversation=[UserMessage(text="hi"), results])
        message = client.messages.calls[0]["messages"][1]
        assert message["role"] == "user"
        assert [block["type"] for block in message["content"]] == ["tool_result"] * 2
        assert message["content"][1]["is_error"] is True


class TestResponseParsing:
    def test_text_turn_parsed(self):
        _, turn = _complete(FakeClient(_text_response("완료했습니다")))
        assert turn.text == "완료했습니다"
        assert turn.tool_calls == ()
        assert turn.stop_reason == "end"
        assert turn.provider == "anthropic"

    def test_tool_use_turn_parsed_to_neutral_tool_calls(self):
        _, turn = _complete(FakeClient(_tool_use_response()))
        assert turn.stop_reason == "tool_use"
        assert turn.tool_calls == (
            ToolCall(id="toolu_01", name="run_commands", arguments={"commands": ["Store Cue 5"]}),
        )

    def test_usage_maps_cache_tokens(self):
        # AC-MVP-014 part 2 evidence surface: cache_read tokens visible neutrally.
        _, turn = _complete(FakeClient(_text_response()))
        assert turn.usage == Usage(
            input_tokens=100, output_tokens=10, cache_read_tokens=90, cache_write_tokens=0
        )

    def test_provider_payload_carries_raw_content(self):
        response = _text_response()
        _, turn = _complete(FakeClient(response))
        assert turn.provider_payload is response.content

    def test_malformed_response_raises_provider_error(self):
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(SimpleNamespace(spam=1)))
        assert excinfo.value.kind == "malformed_response"


def _http_error(cls, status: int):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request)
    return cls("boom detail", response=response, body=None)


class TestErrorNormalization:
    """REQ-MVP-044 seed — SDK errors become structured internal errors."""

    @pytest.mark.parametrize(
        ("exc_factory", "kind", "retryable"),
        [
            (lambda: _http_error(anthropic.RateLimitError, 429), "rate_limit", True),
            (lambda: _http_error(anthropic.AuthenticationError, 401), "auth", False),
            (lambda: _http_error(anthropic.BadRequestError, 400), "invalid_request", False),
            (lambda: _http_error(anthropic.InternalServerError, 500), "server", True),
            (
                lambda: anthropic.APIConnectionError(
                    request=httpx.Request("POST", "https://api.anthropic.com")
                ),
                "connection",
                True,
            ),
            (lambda: ValueError("surprise"), "unknown", False),
        ],
    )
    def test_sdk_errors_are_normalized(self, exc_factory, kind, retryable):
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(exc_factory()))
        error = excinfo.value
        assert error.kind == kind
        assert error.retryable is retryable
        assert error.provider == "anthropic"
        assert error.raw_detail  # original detail preserved for diagnostics logs
