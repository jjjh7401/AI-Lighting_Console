"""Local Ollama provider adapter (SPEC-COPILOT-LOCALLM-001).

Talks to a locally running Ollama daemon over its HTTP API. No API key, no
network egress, no per-token cost — the trade is that the model runs on this
machine and a cold prompt is paid once per model load.

Three properties of the local path shape this adapter:

* **Prefix caching is the whole performance story.** Measured 2026-08-20 on an
  M5 Pro with the app's real 40 KB rulebook plus 33 tool schemas (~28,100
  tokens): the first call pays 54 s (gemma4:26b) / 90 s (gemma4:12b) of prompt
  evaluation, and every later call with the SAME leading prefix pays ~0.25 s.
  So the system prefix is sent as the FIRST message on every request and never
  reordered — a reordered prefix is a cache miss and a minute of latency.
* **The daemon must stay loaded.** ``keep_alive`` is sent explicitly rather
  than left to the daemon default, because an unload silently converts the next
  turn back into a cold start.
* **Tool support is a per-model capability, not a family one.** ``gemma3`` has
  no tools and Ollama rejects the request outright; that is surfaced as a
  non-retryable error, because no amount of retrying adds a capability the
  weights do not have.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from server.llm.errors import ProviderError
from server.llm.types import (
    ConversationItem,
    ModelTurn,
    ToolCall,
    ToolDefinition,
    ToolResultsMessage,
    Usage,
    UserMessage,
)

PROVIDER_NAME = "ollama"

#: How long the daemon keeps the model resident after a call. Long enough that
#: an operator's think-time between instructions does not trigger a reload and
#: hand them a cold prompt mid-show.
DEFAULT_KEEP_ALIVE = "60m"

DEFAULT_HOST = "http://127.0.0.1:11434"

#: Ollama's own wording when a model has no tool support. Matched so the
#: failure is classified as a request this model cannot serve — an operator
#: action (pick another model), not a transient fault worth retrying.
_NO_TOOLS_MARKER = "does not support tools"


def _messages(system_prefix: str, conversation: Sequence[ConversationItem]) -> list[dict[str, Any]]:
    """Neutral conversation -> Ollama chat messages, prefix FIRST.

    The prefix's position is load-bearing (see the module docstring): prompt
    caching matches on a leading token prefix, so emitting it anywhere else
    turns every turn into a cold evaluation.
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prefix}]
    for item in conversation:
        if isinstance(item, UserMessage):
            message: dict[str, Any] = {"role": "user", "content": item.text}
            if item.images:
                message["images"] = [image.content_base64 for image in item.images]
            messages.append(message)
        elif isinstance(item, ToolResultsMessage):
            for result in item.results:
                messages.append(
                    {"role": "tool", "tool_name": result.name, "content": result.content}
                )
        elif isinstance(item, ModelTurn):
            entry: dict[str, Any] = {"role": "assistant", "content": item.text or ""}
            if item.tool_calls:
                entry["tool_calls"] = [
                    {"function": {"name": call.name, "arguments": call.arguments}}
                    for call in item.tool_calls
                ]
            messages.append(entry)
        else:  # pragma: no cover - defensive
            raise TypeError(f"unsupported conversation item: {type(item).__name__}")
    return messages


def _tools(tools: Sequence[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


class OllamaAdapter:
    """LLMProvider implementation backed by a local Ollama daemon."""

    def __init__(
        self,
        model: str,
        *,
        host: str = DEFAULT_HOST,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        timeout_seconds: float = 600.0,
        transport: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._keep_alive = keep_alive
        self._timeout = timeout_seconds
        #: Injected in tests. Production uses urllib so this adapter adds no
        #: dependency for a daemon that is already local.
        self._transport = transport

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def supports_prompt_caching(self) -> bool:
        # The daemon caches the leading prefix itself; there is no explicit
        # cache object for this adapter to create, name or expire.
        return True

    # -- request bodies --------------------------------------------------------

    def _body(
        self,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition],
        *,
        stream: bool,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._model,
            "stream": stream,
            "keep_alive": self._keep_alive,
            "messages": _messages(system_prefix, conversation),
            # Reasoning stays OFF: the orchestrator judges a turn by its tool
            # calls and its prose, and a thinking channel that leaks into
            # `content` reaches the operator as noise (observed on gemma4:12b,
            # 2026-08-20).
            "think": False,
        }
        if tools:
            body["tools"] = _tools(tools)
        return body

    def _http_error(self, error: urllib.error.HTTPError) -> ProviderError:
        detail = error.read().decode("utf-8", "replace")
        return ProviderError(
            # Inside the closed ERROR_KINDS set on purpose: a model without
            # tool support makes THIS request invalid, and widening the set
            # would add a kind the Korean error catalog does not translate.
            kind=("invalid_request" if _NO_TOOLS_MARKER in detail else "server"),
            provider=PROVIDER_NAME,
            retryable=error.code >= 500 and _NO_TOOLS_MARKER not in detail,
            raw_detail=detail,
        )

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        if self._transport is not None:
            return self._transport(body)
        request = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise self._http_error(error) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ProviderError(
                kind="connection",
                provider=PROVIDER_NAME,
                retryable=True,
                raw_detail=repr(error),
            ) from error

    def _post_stream(self, body: dict[str, Any]) -> Iterator[dict[str, Any]]:
        if self._transport is not None:
            yield from self._transport(body)
            return
        request = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                for raw in response:
                    line = raw.strip()
                    if line:
                        yield json.loads(line)
        except urllib.error.HTTPError as error:
            raise self._http_error(error) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ProviderError(
                kind="connection",
                provider=PROVIDER_NAME,
                retryable=True,
                raw_detail=repr(error),
            ) from error

    # -- reply parsing ---------------------------------------------------------

    def _parse_reply(self, payload: dict[str, Any]) -> ModelTurn:
        """One Ollama reply -> a neutral turn. Shared by both call shapes.

        The streaming path accumulates deltas into this same envelope rather
        than parsing separately, so tool-call reading and usage mapping have
        exactly one implementation and cannot drift between the two paths.
        """
        if payload.get("error"):
            detail = str(payload["error"])
            raise ProviderError(
                kind=("invalid_request" if _NO_TOOLS_MARKER in detail else "malformed_response"),
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=detail,
            )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ProviderError(
                kind="malformed_response",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=f"reply without a message object: {payload!r}",
            )
        calls: list[ToolCall] = []
        for index, entry in enumerate(message.get("tool_calls") or []):
            function = entry.get("function") if isinstance(entry, dict) else None
            if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                raise ProviderError(
                    kind="malformed_response",
                    provider=PROVIDER_NAME,
                    retryable=False,
                    raw_detail=f"unreadable tool call at {index}: {entry!r}",
                )
            arguments = function.get("arguments")
            calls.append(
                ToolCall(
                    id=str(entry.get("id") or f"{function['name']}-{index}"),
                    name=function["name"],
                    arguments=dict(arguments) if isinstance(arguments, dict) else {},
                )
            )
        return ModelTurn(
            text=message.get("content") or "",
            tool_calls=tuple(calls),
            stop_reason="tool_use" if calls else "end",
            usage=Usage(
                input_tokens=int(payload.get("prompt_eval_count") or 0),
                output_tokens=int(payload.get("eval_count") or 0),
            ),
            provider=PROVIDER_NAME,
            provider_payload=None,
        )

    # -- LLMProvider interface -------------------------------------------------

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        return self._parse_reply(
            self._post(self._body(system_prefix, conversation, tools, stream=False))
        )

    def complete_stream(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
        on_text: Callable[[str], None],
    ) -> ModelTurn:
        """Same turn as :meth:`complete`, with prose handed over as it arrives.

        Ollama streams newline-delimited JSON objects carrying the same message
        shape as a non-streaming reply, one delta at a time. The deltas are
        accumulated back into one envelope and handed to :meth:`_parse_reply`,
        so the streamed turn and the buffered turn are the same object.
        """
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        final: dict[str, Any] = {}
        for line in self._post_stream(self._body(system_prefix, conversation, tools, stream=True)):
            if line.get("error"):
                raise ProviderError(
                    kind="malformed_response",
                    provider=PROVIDER_NAME,
                    retryable=False,
                    raw_detail=str(line["error"]),
                )
            message = line.get("message") or {}
            piece = message.get("content") or ""
            if piece:
                text_parts.append(piece)
                on_text(piece)
            tool_calls.extend(message.get("tool_calls") or [])
            if line.get("done"):
                final = line
        return self._parse_reply(
            {**final, "message": {"content": "".join(text_parts), "tool_calls": tool_calls}}
        )
