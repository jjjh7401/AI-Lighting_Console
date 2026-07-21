"""Google Gemini provider adapter (REQ-MVP-038/039/041 — config-pinned model).

Wire contract (google-genai SDK):

* The fixed rulebook prefix goes through **explicit context caching** when the
  configuration enables it AND the model accepts the cache (minimum cacheable
  token thresholds are model-dependent — research.md section F "verify at
  implementation"). Cache creation is attempted ONCE; on failure the adapter
  records the trade-off and falls back to the uncached ``system_instruction``
  path (REQ-MVP-041 explicit trade-off).
* Neutral tool definitions become ``FunctionDeclaration`` entries; neutral JSON
  schema types are uppercased to the Gemini ``Type`` enum values.
* Gemini function calls may carry no id — the adapter assigns synthetic,
  turn-stable ids (``<name>-<index>``).
* Every SDK exception is normalized to :class:`ProviderError` (REQ-MVP-044
  forward design).

Live-console-style unknowns (rest verified with a real API key at M6): the
``role="tool"`` function-response convention and per-model cache thresholds
are recorded as gaps in progress.md.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from typing import Any

from server.llm.config import GeminiSettings
from server.llm.errors import ProviderError, normalize_gemini_error
from server.llm.types import (
    ConversationItem,
    ModelTurn,
    ToolCall,
    ToolDefinition,
    ToolResultsMessage,
    Usage,
    UserMessage,
)

PROVIDER_NAME = "gemini"

logger = logging.getLogger(__name__)

# Candidate.finish_reason values that mean the candidate's parts are a
# genuine, complete answer. Anything else (SAFETY/RECITATION block,
# MAX_TOKENS truncation, MALFORMED_FUNCTION_CALL, etc.) means the parts do
# NOT represent what they appear to — an empty/partial `parts` list under one
# of those reasons must surface as an error, never as a silently "successful"
# empty turn (M6c-3 Finding 1). FINISH_REASON_UNSPECIFIED and a missing
# attribute (older/mocked responses) are treated as "no signal" and pass
# through unchanged for backward compatibility.
_OK_FINISH_REASONS = frozenset({"STOP", "FINISH_REASON_UNSPECIFIED"})

# Substring that identifies a stale/expired CachedContent handle (REQ-MVP TTL
# expiry, live-observed at DEPLOY-001 M16): the SDK raises APIError 403
# PERMISSION_DENIED / 404 whose detail names the missing CachedContent. Keyed on
# the marker (not the bare status code) so an ordinary 403 auth denial / 404
# model-not-found does NOT trigger a needless cache regeneration.
_CACHE_MISS_MARKER = "CachedContent not found"

# Case-insensitive markers that identify a missing/invalid-credential
# ValueError from ``genai.Client()`` construction (google-genai raises
# ``ValueError("No API key was provided ...")`` when no key is in env).
_MISSING_KEY_MARKERS = ("api key", "api_key", "credential")


def _is_cache_miss(exc: Exception) -> bool:
    """True when a generate() failure means the CachedContent handle is stale.

    A 403/404 APIError whose detail names the missing CachedContent (TTL
    expiry). Detection is marker-precise so a genuine 403 auth denial or a 404
    model-not-found is NOT mistaken for a recoverable cache miss (REQ-DEPLOY-031).
    """
    from google.genai import errors as genai_errors

    if not isinstance(exc, genai_errors.APIError):
        return False
    code = getattr(exc, "code", None) or 0
    if code not in (403, 404):
        return False
    return _CACHE_MISS_MARKER in str(exc)


def _is_missing_key_error(exc: ValueError) -> bool:
    """True when a client-construction ValueError is credential-related.

    Narrow: only a message naming an API key / credential counts, so an
    unrelated construction ValueError re-raises unchanged (REQ-DEPLOY-031).
    """
    text = str(exc).lower()
    return any(marker in text for marker in _MISSING_KEY_MARKERS)


def _to_gemini_schema(schema: dict) -> dict:
    """Convert neutral JSON schema to Gemini schema (uppercased type values)."""
    converted: dict = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            converted[key] = value.upper()
        elif key == "properties" and isinstance(value, dict):
            converted[key] = {name: _to_gemini_schema(sub) for name, sub in value.items()}
        elif key == "items" and isinstance(value, dict):
            converted[key] = _to_gemini_schema(value)
        else:
            converted[key] = value
    return converted


class GeminiAdapter:
    """LLMProvider implementation backed by the official ``google-genai`` SDK."""

    def __init__(self, settings: GeminiSettings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client  # injected in tests; lazily constructed in production
        self._cache_name: str | None = None
        self._cache_attempted = False
        self._cached_tools: tuple[ToolDefinition, ...] = ()
        self.cache_status = "uninitialized"
        # @MX:ANCHOR: [AUTO] serializes the whole check-then-set cache attempt
        #   — production wiring shares ONE GeminiAdapter instance across every
        #   ChatSession (server/web/serve.py build_runtime builds the provider
        #   once; server/web/app.py injects the same deps.provider into every
        #   session), and ChatSession.run_instruction runs on a worker thread
        #   via asyncio.to_thread (server/web/session.py), so complete() ->
        #   _ensure_cache() can genuinely be entered concurrently from two OS
        #   threads on their first turn.
        # @MX:REASON: [AUTO] without the lock, a second concurrent caller
        #   could observe self._cache_attempted already True (set eagerly,
        #   before the network call lands) and return a stale self._cache_name
        #   (still None) instead of the real result — or, if scheduled
        #   earlier, both callers could race client.caches.create() and create
        #   duplicate cache entries. Guarding the full method body makes the
        #   second caller WAIT for the first attempt's real result instead of
        #   racing or returning early, matching the module docstring's
        #   "attempted ONCE" single-attempt semantics.
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_id(self) -> str:
        return self._settings.model

    @property
    def supports_prompt_caching(self) -> bool:
        return self._settings.context_caching

    def _ensure_client(self) -> Any:
        if self._client is None:
            from google import genai

            # Credentials resolve from the environment (GEMINI_API_KEY /
            # GOOGLE_API_KEY) — never from the provider config file.
            try:
                self._client = genai.Client()
            except ValueError as exc:
                # @MX:NOTE: [AUTO] a client-construction ValueError from
                #   google-genai means missing/invalid credentials ("No API key
                #   was provided ...") — normalize to ProviderError(kind="auth")
                #   so the session classifier routes it to the Korean auth
                #   message instead of the 'unexpected' bucket (REQ-DEPLOY-031).
                #   Non-credential ValueErrors re-raise unchanged (narrow scope).
                if _is_missing_key_error(exc):
                    raise ProviderError(
                        kind="auth",
                        provider=PROVIDER_NAME,
                        retryable=False,
                        raw_detail=repr(exc),
                    ) from exc
                raise
        return self._client

    # -- context caching (REQ-MVP-041, capability-gated) -----------------------

    def _ensure_cache(
        self, client: Any, system_prefix: str, tools: Sequence[ToolDefinition]
    ) -> str | None:
        if not self._settings.context_caching:
            self.cache_status = "disabled"
            return None
        with self._lock:
            if self._cache_attempted:
                return self._cache_name
            self._cache_attempted = True
            try:
                from google.genai import types as gtypes

                # API constraint (live-verified at M6b-1): a generate request
                # that uses cached_content must NOT set
                # system_instruction/tools — so BOTH are baked into the
                # CachedContent (fixed prefix + fixed toolset, REQ-MVP-007
                # discipline).
                cache_kwargs: dict[str, Any] = {
                    "system_instruction": system_prefix,
                    "ttl": f"{self._settings.cache_ttl_seconds}s",
                }
                if tools:
                    cache_kwargs["tools"] = [self._tool_config(tools)]
                cache = client.caches.create(
                    model=self._settings.model,
                    config=gtypes.CreateCachedContentConfig(**cache_kwargs),
                )
                self._cache_name = cache.name
                self._cached_tools = tuple(tools)
                self.cache_status = "cached"
            except Exception as exc:  # capability gate: fall back, record trade-off
                self._cache_name = None
                self.cache_status = f"uncached: {exc}"
                logger.warning(
                    "gemini context cache unavailable — running the UNCACHED path "
                    "(higher cost/latency accepted per REQ-MVP-041): %s",
                    exc,
                )
            return self._cache_name

    # -- request construction --------------------------------------------------

    def _tool_config(self, tools: Sequence[ToolDefinition]) -> Any:
        from google.genai import types as gtypes

        declarations = [
            gtypes.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=_to_gemini_schema(tool.parameters),
            )
            for tool in tools
        ]
        return gtypes.Tool(function_declarations=declarations)

    def _to_contents(self, conversation: Sequence[ConversationItem]) -> list[Any]:
        from google.genai import types as gtypes

        contents: list[Any] = []
        for item in conversation:
            if isinstance(item, UserMessage):
                contents.append(
                    gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=item.text)])
                )
            elif isinstance(item, ModelTurn):
                if item.provider == PROVIDER_NAME and item.provider_payload is not None:
                    contents.append(item.provider_payload)  # verbatim echo
                    continue
                parts: list[Any] = []
                if item.text:
                    parts.append(gtypes.Part.from_text(text=item.text))
                for call in item.tool_calls:
                    parts.append(
                        gtypes.Part.from_function_call(name=call.name, args=call.arguments)
                    )
                contents.append(gtypes.Content(role="model", parts=parts))
            elif isinstance(item, ToolResultsMessage):
                parts = [
                    gtypes.Part.from_function_response(
                        name=result.name,
                        response={"result": result.content, "is_error": result.is_error},
                    )
                    for result in item.results
                ]
                contents.append(gtypes.Content(role="tool", parts=parts))
            else:  # pragma: no cover - defensive
                raise TypeError(f"unsupported conversation item: {type(item).__name__}")
        return contents

    # -- response parsing --------------------------------------------------------

    def _parse_response(self, response: Any) -> ModelTurn:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            raise ProviderError(
                kind="malformed_response",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=f"response without candidates: {response!r}",
            )
        candidate = candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason is not None and finish_reason not in _OK_FINISH_REASONS:
            raise ProviderError(
                kind="malformed_response",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=(
                    f"candidate blocked/truncated: finish_reason={finish_reason!r} "
                    f"(not a genuine empty success)"
                ),
            )
        content = candidate.content
        parts = getattr(content, "parts", None) or []
        texts: list[str] = []
        tool_calls: list[ToolCall] = []
        for index, part in enumerate(parts):
            text = getattr(part, "text", None)
            if text:
                texts.append(text)
            function_call = getattr(part, "function_call", None)
            if function_call is not None:
                call_id = getattr(function_call, "id", None) or f"{function_call.name}-{index}"
                tool_calls.append(
                    ToolCall(
                        id=call_id,
                        name=function_call.name,
                        arguments=dict(function_call.args or {}),
                    )
                )
        usage_metadata = getattr(response, "usage_metadata", None)
        return ModelTurn(
            text="\n".join(texts),
            tool_calls=tuple(tool_calls),
            stop_reason="tool_use" if tool_calls else "end",
            usage=Usage(
                input_tokens=getattr(usage_metadata, "prompt_token_count", 0) or 0,
                output_tokens=getattr(usage_metadata, "candidates_token_count", 0) or 0,
                cache_read_tokens=getattr(usage_metadata, "cached_content_token_count", 0) or 0,
            ),
            provider=PROVIDER_NAME,
            provider_payload=content,
        )

    # -- LLMProvider interface ---------------------------------------------------

    def _build_generate_config(
        self,
        system_prefix: str,
        tools: Sequence[ToolDefinition],
        tools_tuple: tuple[ToolDefinition, ...],
        cache_name: str | None,
    ) -> tuple[bool, dict[str, Any]]:
        # The cached path is valid ONLY when this call's toolset is the cached
        # one (or empty — the cache's tools then apply). A different toolset
        # takes the uncached path: with cached_content the request may not
        # carry tools, so using the cache would silently swap the tools.
        use_cache = cache_name is not None and (
            not tools_tuple or tools_tuple == self._cached_tools
        )
        config_kwargs: dict[str, Any] = {}
        if use_cache:
            config_kwargs["cached_content"] = cache_name
        else:
            config_kwargs["system_instruction"] = system_prefix
            if tools_tuple:
                config_kwargs["tools"] = [self._tool_config(tools)]
        return use_cache, config_kwargs

    def _regenerate_cache(
        self, client: Any, system_prefix: str, tools: Sequence[ToolDefinition]
    ) -> str | None:
        # @MX:NOTE: [AUTO] latch-reset carve-out — the "attempted ONCE" latch
        #   (self._cache_attempted) is deliberately cleared here so a PROVEN-stale
        #   cache handle can be rebuilt after a 403/404 CachedContent-not-found.
        #   This is the ONE sanctioned reset; it runs under self._lock (matching
        #   the initial attempt), then RELEASES the lock before calling
        #   _ensure_cache — which re-acquires the same non-reentrant Lock — so
        #   there is no deadlock and the single-attempt semantics hold per
        #   regeneration. Returns the fresh cache name (or None if regeneration
        #   itself failed, in which case the retry takes the uncached path).
        with self._lock:
            self._cache_attempted = False
            self._cache_name = None
        return self._ensure_cache(client, system_prefix, tools)

    def _generate_with_cache_recovery(
        self,
        client: Any,
        system_prefix: str,
        tools: Sequence[ToolDefinition],
        tools_tuple: tuple[ToolDefinition, ...],
        contents: list[Any],
        cache_name: str | None,
    ) -> Any:
        from google.genai import types as gtypes

        use_cache, config_kwargs = self._build_generate_config(
            system_prefix, tools, tools_tuple, cache_name
        )
        try:
            return client.models.generate_content(
                model=self._settings.model,
                contents=contents,
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )
        except ProviderError:
            raise
        except Exception as exc:
            # A stale CachedContent (TTL expiry) surfaces here as a 403/404
            # "CachedContent not found". Regenerate the cache and retry EXACTLY
            # ONCE (REQ-DEPLOY-031 / AC-DEPLOY-022 ①). Any other failure — or a
            # retry that also fails — normalizes; there is no infinite retry.
            if not (use_cache and _is_cache_miss(exc)):
                raise normalize_gemini_error(exc) from exc
            fresh_cache = self._regenerate_cache(client, system_prefix, tools)
            _, retry_kwargs = self._build_generate_config(
                system_prefix, tools, tools_tuple, fresh_cache
            )
            try:
                return client.models.generate_content(
                    model=self._settings.model,
                    contents=contents,
                    config=gtypes.GenerateContentConfig(**retry_kwargs),
                )
            except ProviderError:
                raise
            except Exception as retry_exc:
                raise normalize_gemini_error(retry_exc) from retry_exc

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        client = self._ensure_client()
        cache_name = self._ensure_cache(client, system_prefix, tools)
        tools_tuple = tuple(tools)
        contents = self._to_contents(conversation)
        response = self._generate_with_cache_recovery(
            client, system_prefix, tools, tools_tuple, contents, cache_name
        )
        return self._parse_response(response)
