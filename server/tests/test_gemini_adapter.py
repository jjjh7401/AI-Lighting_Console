"""Gemini adapter tests (M3 — REQ-MVP-038/039/041, research.md section F verification tasks).

All tests run against an injected fake client — no network, no API key
(AC-MVP-026 mocked-boot path). Capability-gated caching (REQ-MVP-041): the
adapter attempts explicit context-cache creation once; on failure (below the
model's minimum cacheable tokens, unsupported, etc.) it falls back to the
uncached path and records the trade-off.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors as genai_errors

from server.llm.config import GeminiSettings
from server.llm.errors import ProviderError
from server.llm.gemini_adapter import GeminiAdapter, _to_gemini_schema
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


def _response_with_finish_reason(
    finish_reason: str, *, text: str | None = "완료"
) -> SimpleNamespace:
    parts = [SimpleNamespace(text=text, function_call=None)] if text else []
    content = SimpleNamespace(role="model", parts=parts)
    candidate = SimpleNamespace(content=content, finish_reason=finish_reason)
    return SimpleNamespace(candidates=[candidate], usage_metadata=None)


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
        # Incrementing handle name so a regenerate-after-miss retry can be
        # distinguished from the original cache (the 1st create is still
        # rulebook-1, preserving every single-create assertion in this file).
        return SimpleNamespace(name=f"cachedContents/rulebook-{len(self.calls)}")


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

    def test_cache_miss_regenerates_and_retries_once(self):
        # REQ-DEPLOY-031 / AC-DEPLOY-022 ①: a TTL-expired CachedContent surfaces
        # on generate as a 403 PERMISSION_DENIED "CachedContent not found". The
        # adapter regenerates the cache and retries ONCE instead of failing the
        # call terminally.
        cache_miss = genai_errors.APIError(403, {"error": {"message": "CachedContent not found"}})
        client = FakeClient(cache_miss, _text_response("복구됨"))
        adapter, turn = _complete(client)
        assert turn.text == "복구됨"  # retry succeeded — NOT a terminal failure
        assert len(client.caches.calls) == 2  # cache regenerated after the miss
        # First attempt used the stale handle; the retry used the FRESH one.
        assert client.models.calls[0]["config"].cached_content == "cachedContents/rulebook-1"
        assert client.models.calls[1]["config"].cached_content == "cachedContents/rulebook-2"
        assert adapter.cache_status == "cached"

    def test_cache_miss_404_variant_also_regenerates_and_retries(self):
        # AC-DEPLOY-022 ① "(및 404)": a 404 CachedContent-not-found recovers too.
        cache_miss = genai_errors.APIError(404, {"error": {"message": "CachedContent not found"}})
        client = FakeClient(cache_miss, _text_response("복구됨"))
        _, turn = _complete(client)
        assert turn.text == "복구됨"
        assert len(client.caches.calls) == 2
        assert client.models.calls[1]["config"].cached_content == "cachedContents/rulebook-2"

    def test_cache_miss_retry_that_also_fails_is_not_retried_again(self):
        # Single-retry guard (no infinite recursion): if the regenerated-cache
        # retry ALSO raises, the adapter normalizes and raises — it does NOT loop.
        miss1 = genai_errors.APIError(403, {"error": {"message": "CachedContent not found"}})
        miss2 = genai_errors.APIError(403, {"error": {"message": "CachedContent not found"}})
        client = FakeClient(miss1, miss2)
        with pytest.raises(ProviderError) as excinfo:
            _complete(client)
        assert excinfo.value.kind == "auth"  # 403 → auth via normalize_gemini_error
        assert len(client.models.calls) == 2  # exactly one retry, then give up
        assert len(client.caches.calls) == 2  # regenerated once

    def test_non_cache_miss_403_is_not_treated_as_a_cache_miss(self):
        # A 403 that is a genuine auth denial (NOT "CachedContent not found") must
        # normalize straight to auth — never trigger a needless regenerate/retry.
        denied = genai_errors.APIError(403, {"error": {"message": "denied"}})
        client = FakeClient(denied)
        with pytest.raises(ProviderError) as excinfo:
            _complete(client)
        assert excinfo.value.kind == "auth"
        assert len(client.models.calls) == 1  # no retry
        assert len(client.caches.calls) == 1  # no regeneration

    def test_cache_miss_regeneration_failure_falls_back_to_uncached_retry(self):
        # If regeneration itself fails, the retry takes the UNCACHED path
        # (system_instruction + tools) rather than reusing a stale/none handle.
        cache_miss = genai_errors.APIError(403, {"error": {"message": "CachedContent not found"}})

        class OneGoodThenBrokenCaches(FakeCaches):
            def create(self, **kwargs):
                if len(self.calls) >= 1:  # 2nd create (regeneration) fails
                    self.calls.append(kwargs)
                    raise genai_errors.APIError(400, {"error": {"message": "too small"}})
                return super().create(**kwargs)

        client = FakeClient(cache_miss, _text_response("복구됨"))
        client.caches = OneGoodThenBrokenCaches()
        _, turn = _complete(client)
        assert turn.text == "복구됨"
        retry_config = client.models.calls[1]["config"]
        assert retry_config.cached_content is None
        assert retry_config.system_instruction == _PREFIX

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


class TestContextCachingConcurrencySafety:
    """MEDIUM backlog item (M6c 종합, server/llm/gemini_adapter.py:101) —
    _ensure_cache() did a lock-free check-then-set on self._cache_attempted.
    Production concurrency: ONE GeminiAdapter instance is shared across every
    ChatSession (server/web/serve.py build_runtime builds the provider once;
    server/web/app.py injects the SAME deps.provider into every new
    ChatSession), and ChatSession.run_instruction runs on a worker thread via
    asyncio.to_thread (server/web/session.py docstring) — so two concurrent
    WebSocket sessions' first turn can call complete() -> _ensure_cache() on
    the SAME adapter instance from two OS threads at once."""

    def test_ensure_cache_invoked_at_most_once_under_concurrent_calls(self):
        class SlowCaches(FakeCaches):
            def create(self, **kwargs):
                # Widen the check-then-set race window so two concurrently
                # invoked _ensure_cache() calls reliably interleave inside
                # the critical section (mirrors the analogous fix/test in
                # server/orchestrator/fallback.py + test_fallback_detector.py).
                time.sleep(0.05)
                return super().create(**kwargs)

        client = FakeClient()
        client.caches = SlowCaches()
        adapter = GeminiAdapter(_settings(), client=client)

        results: list[str | None] = []
        errors: list[BaseException] = []

        def worker():
            try:
                results.append(adapter._ensure_cache(client, _PREFIX, (_TOOL,)))
            except BaseException as exc:  # pragma: no cover - diagnostic only
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"_ensure_cache raised under concurrency: {errors}"
        assert all(not t.is_alive() for t in threads), "_ensure_cache call hung (deadlock)"
        assert len(client.caches.calls) == 1, (
            f"client.caches.create invoked {len(client.caches.calls)} times under "
            f"concurrent _ensure_cache() calls, expected at most once (single-attempt "
            f"semantics, module docstring 'Cache creation is attempted ONCE'): "
            f"{client.caches.calls}"
        )
        # Both concurrent callers must observe the SAME final cache name —
        # no caller races the create() call and none is left with a stale
        # local value diverging from adapter._cache_name.
        assert results == [adapter._cache_name, adapter._cache_name]


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


class TestFinishReasonInspection:
    """M6c-3 Finding 1 (HIGH) — a blocked/truncated candidate must surface as
    an error, never as a silently "successful" empty/partial turn."""

    def test_normal_stop_finish_reason_parses_as_before(self):
        # No-regression case: an explicit finish_reason="STOP" behaves exactly
        # like the pre-existing (finish_reason-less) response fixtures.
        _, turn = _complete(FakeClient(_response_with_finish_reason("STOP", text="완료")))
        assert turn.text == "완료"
        assert turn.tool_calls == ()
        assert turn.stop_reason == "end"

    def test_missing_finish_reason_attribute_is_backward_compatible(self):
        # Older mocks / SDK responses without the attribute at all: getattr
        # falls back to None and parsing proceeds unchanged.
        _, turn = _complete(FakeClient(_text_response("완료")))
        assert turn.text == "완료"

    @pytest.mark.parametrize(
        "finish_reason",
        ["SAFETY", "RECITATION", "MAX_TOKENS", "MALFORMED_FUNCTION_CALL", "PROHIBITED_CONTENT"],
    )
    def test_non_stop_finish_reason_surfaces_as_provider_error(self, finish_reason):
        # A safety/recitation block or a truncated function call has an EMPTY
        # or partial `parts` list — without the finish_reason check this
        # would silently parse as a successful empty turn.
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(_response_with_finish_reason(finish_reason, text=None)))
        error = excinfo.value
        assert error.kind == "malformed_response"
        assert error.provider == "gemini"
        assert error.retryable is False
        assert finish_reason in error.raw_detail


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


def _httpx_request() -> httpx.Request:
    return httpx.Request("POST", "https://generativelanguage.googleapis.com")


class TestConnectivityErrorClassification:
    """M6c-3 Finding 2 (HIGH) — the google-genai SDK (httpx-based) raises
    httpx.ConnectError/httpx.TimeoutException on real network failures; these
    are NOT subclasses of the Python builtin ConnectionError/TimeoutError, so
    they must be classified alongside (not instead of) the builtins."""

    @pytest.mark.parametrize(
        "exc",
        [
            ConnectionError("builtin connection error"),
            TimeoutError("builtin timeout"),
            httpx.ConnectError("connect failed", request=_httpx_request()),
            httpx.TimeoutException("timed out", request=_httpx_request()),
        ],
    )
    def test_connectivity_exceptions_classify_as_retryable_connection(self, exc):
        with pytest.raises(ProviderError) as excinfo:
            _complete(FakeClient(exc))
        error = excinfo.value
        assert error.kind == "connection"
        assert error.retryable is True
        assert error.provider == "gemini"


class TestBootWithoutKeys:
    def test_injected_client_boot_does_not_touch_env(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        adapter = GeminiAdapter(_settings(), client=FakeClient(_text_response()))
        assert adapter.name == "gemini"
        assert adapter.model_id == "gemini-2.5-pro"


class TestMissingKeyClassification:
    """REQ-DEPLOY-031 / AC-DEPLOY-022 ②: a client-construction "No API key"
    ValueError (raised by google-genai's ``genai.Client()`` when no
    GEMINI_API_KEY/GOOGLE_API_KEY is in env) is normalized at the adapter to
    ProviderError(kind="auth") — so the session classifier routes it to the
    Korean auth message instead of the 'unexpected' internal-error bucket."""

    def test_missing_key_raises_provider_auth_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        # No client injected → _ensure_client() builds a real genai.Client(),
        # which raises ValueError("No API key ...") with no key in env.
        adapter = GeminiAdapter(_settings(context_caching=False))
        with pytest.raises(ProviderError) as excinfo:
            adapter.complete(
                system_prefix=_PREFIX,
                conversation=[UserMessage(text="hi")],
                tools=(),
            )
        error = excinfo.value
        assert error.kind == "auth"
        assert error.provider == "gemini"
        assert error.retryable is False
        assert error.raw_detail  # repr(exc) preserved for the audit log only

    def test_non_key_valueerror_from_client_construction_is_not_swallowed(self, monkeypatch):
        # Narrowness guard: a client-construction ValueError that is NOT
        # credential-related re-raises unchanged (never masqueraded as auth).
        from google import genai as genai_mod

        def _boom(*args, **kwargs):
            raise ValueError("some unrelated config problem")

        monkeypatch.setattr(genai_mod, "Client", _boom)
        adapter = GeminiAdapter(_settings(context_caching=False))
        with pytest.raises(ValueError) as excinfo:
            adapter.complete(
                system_prefix=_PREFIX,
                conversation=[UserMessage(text="hi")],
                tools=(),
            )
        assert "unrelated config problem" in str(excinfo.value)
        assert not isinstance(excinfo.value, ProviderError)


class TestSchemaConversionDropsKeysGeminiRejects:
    """Live-observed 2026-08-03: one unsupported keyword kills the whole request.

    Gemini's function-declaration schema subset rejects `additionalProperties`
    with 400 INVALID_ARGUMENT ("Unknown name ... Cannot find field"), and the
    failure is per-REQUEST, not per-tool: eleven tool schemas carried it and
    EVERY turn died — the cached path and the uncached fallback alike, so the
    app answered "AI 서비스가 요청을 거부했습니다" to every instruction.

    The neutral schema keeps the keyword for providers that accept it (Anthropic
    takes full JSON Schema); the stripping is Gemini-local.
    """

    def test_additional_properties_is_stripped_at_the_top_level(self):
        converted = _to_gemini_schema(
            {"type": "object", "properties": {}, "additionalProperties": False}
        )
        assert "additionalProperties" not in converted

    def test_additional_properties_is_stripped_from_nested_properties(self):
        # The live failure named BOTH a top-level `parameters` and a nested
        # `parameters.properties[...]` occurrence, so depth matters.
        converted = _to_gemini_schema(
            {
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "object",
                        "properties": {"fid": {"type": "integer"}},
                        "additionalProperties": False,
                    }
                },
            }
        )
        assert "additionalProperties" not in converted["properties"]["spec"]

    def test_additional_properties_is_stripped_from_array_items(self):
        converted = _to_gemini_schema(
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
        )
        assert "additionalProperties" not in converted["items"]

    def test_the_conversion_still_does_its_original_job(self):
        # Non-vacuity: stripping must not have replaced the uppercasing.
        converted = _to_gemini_schema(
            {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            }
        )
        assert converted["type"] == "OBJECT"
        assert converted["properties"]["path"]["type"] == "STRING"
        assert converted["required"] == ["path"]

    def test_no_shipped_tool_schema_reaches_gemini_with_a_rejected_keyword(self):
        # The regression that matters: assert over the REAL toolset, so a tool
        # added later with `additionalProperties` cannot resurrect the outage.
        import json

        from server.orchestrator.tools import build_toolset

        class _Port:
            def execute(self, command):
                raise AssertionError("no console in a schema test")

            def ping(self):
                return True

            def query_state(self, path):
                return {}

            def read_property(self, path, name):
                return {}

        registry = build_toolset(execution_port=_Port(), state_port=_Port())
        definitions = (
            registry.tool_definitions()
            if hasattr(registry, "tool_definitions")
            else registry.definitions()
        )
        assert definitions, "the toolset must not be empty or this proves nothing"
        carried = [
            tool.name
            for tool in definitions
            if "additionalProperties" in json.dumps(tool.parameters)
        ]
        assert carried, "non-vacuity: some shipped schema must still USE the keyword"
        leaked = [
            tool.name
            for tool in definitions
            if "additionalProperties" in json.dumps(_to_gemini_schema(tool.parameters))
        ]
        assert leaked == []
