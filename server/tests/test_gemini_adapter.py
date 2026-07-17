"""Gemini adapter tests (M3 — REQ-MVP-038/039/041, research.md section F verification tasks).

All tests run against an injected fake client — no network, no API key
(AC-MVP-026 mocked-boot path). Capability-gated caching (REQ-MVP-041): the
adapter attempts explicit context-cache creation once; on failure (below the
model's minimum cacheable tokens, unsupported, etc.) it falls back to the
uncached path and records the trade-off.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from server.llm.config import GeminiSettings
from server.llm.errors import ProviderError
from server.llm.gemini_adapter import GeminiAdapter
from server.llm.types import (
    ToolDefinition,
    ToolResult,
    ToolResultsMessage,
    UserMessage,
)

_PREFIX = "RULEBOOK PREFIX (fixed)"

_TOOL = ToolDefinition(
    name="query_state",
    description="Query the console object tree.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)


def _settings(**overrides) -> GeminiSettings:
    return GeminiSettings(model="gemini-2.5-pro", **overrides)


def _text_response(text: str = "done") -> SimpleNamespace:
    part = SimpleNamespace(text=text, function_call=None)
    content = SimpleNamespace(role="model", parts=[part])
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=content)],
        usage_metadata=SimpleNamespace(
            prompt_token_count=200,
            candidates_token_count=20,
            cached_content_token_count=150,
        ),
    )


def _function_call_response() -> SimpleNamespace:
    call = SimpleNamespace(id=None, name="query_state", args={"path": "DataPool/Groups"})
    part = SimpleNamespace(text=None, function_call=call)
    content = SimpleNamespace(role="model", parts=[part])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)], usage_metadata=None)


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeCaches:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(name="cachedContents/rulebook-1")


class FakeClient:
    def __init__(self, *responses, cache_error: Exception | None = None):
        self.models = FakeModels(responses)
        self.caches = FakeCaches(error=cache_error)


def _complete(client, conversation=None, tools=(_TOOL,), settings=None):
    adapter = GeminiAdapter(settings or _settings(), client=client)
    turn = adapter.complete(
        system_prefix=_PREFIX,
        conversation=conversation or [UserMessage(text="그룹 상태 알려줘")],
        tools=tools,
    )
    return adapter, turn


class TestRequestConstruction:
    def test_model_id_comes_from_config_pin(self):
        client = FakeClient(_text_response())
        _complete(client)
        assert client.models.calls[0]["model"] == "gemini-2.5-pro"

    def test_tools_converted_to_function_declarations(self):
        # Uncached path: the request itself carries the converted tools. On
        # the cached path the SAME conversion lands in the CachedContent (see
        # TestContextCaching — cached requests may not carry tools).
        client = FakeClient(_text_response())
        _complete(client, settings=_settings(context_caching=False))
        config = client.models.calls[0]["config"]
        declaration = config.tools[0].function_declarations[0]
        assert declaration.name == "query_state"
        assert declaration.description == "Query the console object tree."
        assert str(declaration.parameters.type).endswith("OBJECT")

    def test_user_message_becomes_user_content(self):
        client = FakeClient(_text_response())
        _complete(client)
        contents = client.models.calls[0]["contents"]
        assert contents[0].role == "user"
        assert contents[0].parts[0].text == "그룹 상태 알려줘"

    def test_tool_results_sent_as_function_response_parts(self):
        results = ToolResultsMessage(
            results=(ToolResult(tool_call_id="query_state-0", name="query_state", content="{}"),)
        )
        client = FakeClient(_text_response())
        _complete(client, conversation=[UserMessage(text="hi"), results])
        contents = client.models.calls[0]["contents"]
        response_part = contents[1].parts[0]
        assert response_part.function_response.name == "query_state"


class TestContextCaching:
    """REQ-MVP-041 — capability-gated caching with explicit uncached fallback."""

    def test_cache_created_once_and_reused(self):
        client = FakeClient(_text_response(), _text_response())
        adapter, _ = _complete(client)
        adapter.complete(system_prefix=_PREFIX, conversation=[UserMessage(text="2")], tools=())
        assert len(client.caches.calls) == 1
        assert adapter.cache_status == "cached"
        for call in client.models.calls:
            assert call["config"].cached_content == "cachedContents/rulebook-1"
            assert call["config"].system_instruction is None

    def test_cache_failure_falls_back_to_uncached_path(self):
        # e.g. below the model's minimum cacheable token threshold.
        client = FakeClient(
            _text_response(),
            _text_response(),
            cache_error=genai_errors.APIError(400, {"error": {"message": "too small"}}),
        )
        adapter, _ = _complete(client)
        adapter.complete(system_prefix=_PREFIX, conversation=[UserMessage(text="2")], tools=())
        assert len(client.caches.calls) == 1  # not retried every turn
        assert adapter.cache_status.startswith("uncached")
        for call in client.models.calls:
            assert call["config"].system_instruction == _PREFIX
            assert call["config"].cached_content is None

    def test_caching_disabled_by_config_never_creates_cache(self):
        client = FakeClient(_text_response())
        adapter, _ = _complete(client, settings=_settings(context_caching=False))
        assert client.caches.calls == []
        assert adapter.supports_prompt_caching is False
        assert client.models.calls[0]["config"].system_instruction == _PREFIX

    def test_cached_requests_never_carry_tools_or_system_instruction(self):
        # Live-API reproduction (M6b-1 smoke, 400 INVALID_ARGUMENT):
        # "CachedContent can not be used with GenerateContent request setting
        # system_instruction, tools or tool_config." — a cached request must
        # carry cached_content ONLY; tools live inside the cache.
        client = FakeClient(_text_response())
        _complete(client)  # tools=(_TOOL,) with cache creation succeeding
        config = client.models.calls[0]["config"]
        assert config.cached_content == "cachedContents/rulebook-1"
        assert config.tools is None
        assert config.system_instruction is None

    def test_cache_creation_bakes_the_tools_into_the_cached_content(self):
        # The API's proposed fix: move system_instruction AND tools into the
        # CachedContent — the fixed toolset is part of the fixed prefix.
        client = FakeClient(_text_response())
        _complete(client)
        cache_config = client.caches.calls[0]["config"]
        assert cache_config.system_instruction == _PREFIX
        declaration = cache_config.tools[0].function_declarations[0]
        assert declaration.name == "query_state"

    def test_mismatched_tools_bypass_the_cache_for_that_call(self):
        # A call whose toolset differs from the cached one cannot use the
        # cache (its tools would be silently replaced by the cached tools) —
        # it takes the uncached path with its own tools instead.
        other_tool = ToolDefinition(
            name="run_commands",
            description="Run commands.",
            parameters={"type": "object", "properties": {"commands": {"type": "array"}}},
        )
        client = FakeClient(_text_response(), _text_response())
        adapter, _ = _complete(client)  # cache created with (_TOOL,)
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="2")],
            tools=(other_tool,),
        )
        second = client.models.calls[1]["config"]
        assert second.cached_content is None
        assert second.system_instruction == _PREFIX
        assert second.tools[0].function_declarations[0].name == "run_commands"


class TestResponseParsing:
    def test_text_turn_parsed(self):
        _, turn = _complete(FakeClient(_text_response("완료")))
        assert turn.text == "완료"
        assert turn.tool_calls == ()
        assert turn.stop_reason == "end"
        assert turn.provider == "gemini"

    def test_function_call_parsed_with_synthetic_id(self):
        _, turn = _complete(FakeClient(_function_call_response()))
        assert turn.stop_reason == "tool_use"
        call = turn.tool_calls[0]
        assert call.name == "query_state"
        assert call.arguments == {"path": "DataPool/Groups"}
        assert call.id  # synthetic id assigned when the SDK provides none

    def test_usage_maps_cached_tokens(self):
        _, turn = _complete(FakeClient(_text_response()))
        assert turn.usage.input_tokens == 200
        assert turn.usage.output_tokens == 20
        assert turn.usage.cache_read_tokens == 150

    def test_missing_usage_defaults_to_zero(self):
        _, turn = _complete(FakeClient(_function_call_response()))
        assert turn.usage.input_tokens == 0

    def test_empty_candidates_raise_malformed_response(self):
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(SimpleNamespace(candidates=[], usage_metadata=None)))
        assert excinfo.value.kind == "malformed_response"


class TestErrorNormalization:
    """REQ-MVP-044 seed — Gemini SDK errors become structured internal errors."""

    @pytest.mark.parametrize(
        ("exc", "kind", "retryable"),
        [
            (genai_errors.APIError(429, {"error": {"message": "rate"}}), "rate_limit", True),
            (genai_errors.APIError(401, {"error": {"message": "key"}}), "auth", False),
            (genai_errors.APIError(403, {"error": {"message": "denied"}}), "auth", False),
            (genai_errors.APIError(400, {"error": {"message": "bad"}}), "invalid_request", False),
            (genai_errors.APIError(503, {"error": {"message": "down"}}), "server", True),
            (RuntimeError("surprise"), "unknown", False),
        ],
    )
    def test_sdk_errors_are_normalized(self, exc, kind, retryable):
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(exc))
        error = excinfo.value
        assert error.kind == kind
        assert error.retryable is retryable
        assert error.provider == "gemini"
        assert error.raw_detail


class TestBootWithoutKeys:
    def test_injected_client_boot_does_not_touch_env(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        adapter = GeminiAdapter(_settings(), client=FakeClient(_text_response()))
        assert adapter.name == "gemini"
        assert adapter.model_id == "gemini-2.5-pro"
