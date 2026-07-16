"""Anthropic provider adapter (REQ-MVP-038/041 — claude-opus-4-8, prompt caching).

Wire contract (anthropic SDK, Messages API):

* The fixed rulebook prefix is sent as a ``system`` text block carrying
  ``cache_control: {"type": "ephemeral"}`` — the prompt-caching breakpoint
  (REQ-MVP-007/041). With caching disabled it degrades to a plain string.
* Neutral tool definitions become Anthropic ``tools`` entries (``input_schema``).
* Prior assistant turns produced by THIS provider are echoed back verbatim via
  ``provider_payload`` (required for tool-use loops and thinking blocks);
  foreign turns are reconstructed from the neutral fields.
* Every SDK exception is normalized to :class:`ProviderError` before it leaves
  this module (REQ-MVP-044 forward design — raw SDK errors never surface).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from server.llm.config import AnthropicSettings
from server.llm.errors import ProviderError, normalize_anthropic_error
from server.llm.types import (
    ConversationItem,
    ModelTurn,
    ToolCall,
    ToolDefinition,
    ToolResultsMessage,
    Usage,
    UserMessage,
)

PROVIDER_NAME = "anthropic"


class AnthropicAdapter:
    """LLMProvider implementation backed by the official ``anthropic`` SDK."""

    def __init__(self, settings: AnthropicSettings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client  # injected in tests; lazily constructed in production

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_id(self) -> str:
        return self._settings.model

    @property
    def supports_prompt_caching(self) -> bool:
        return self._settings.prompt_caching

    def _ensure_client(self) -> Any:
        if self._client is None:
            import anthropic

            # Credentials resolve from the environment (ANTHROPIC_API_KEY) —
            # never from the provider config file (Secured constraint).
            self._client = anthropic.Anthropic()
        return self._client

    # -- request construction -------------------------------------------------

    def _system_param(self, system_prefix: str) -> Any:
        if not self._settings.prompt_caching:
            return system_prefix
        return [
            {
                "type": "text",
                "text": system_prefix,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    @staticmethod
    def _tool_param(tool: ToolDefinition) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    @staticmethod
    def _assistant_content(turn: ModelTurn) -> Any:
        if turn.provider == PROVIDER_NAME and turn.provider_payload is not None:
            return turn.provider_payload  # verbatim echo (thinking/tool_use blocks)
        content: list[dict] = []
        if turn.text:
            content.append({"type": "text", "text": turn.text})
        for call in turn.tool_calls:
            content.append(
                {"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments}
            )
        return content

    def _messages_param(self, conversation: Sequence[ConversationItem]) -> list[dict]:
        messages: list[dict] = []
        for item in conversation:
            if isinstance(item, UserMessage):
                messages.append({"role": "user", "content": item.text})
            elif isinstance(item, ModelTurn):
                messages.append({"role": "assistant", "content": self._assistant_content(item)})
            elif isinstance(item, ToolResultsMessage):
                blocks = [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_call_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                    for result in item.results
                ]
                messages.append({"role": "user", "content": blocks})
            else:  # pragma: no cover - defensive
                raise TypeError(f"unsupported conversation item: {type(item).__name__}")
        return messages

    # -- response parsing ------------------------------------------------------

    def _parse_response(self, response: Any) -> ModelTurn:
        content = getattr(response, "content", None)
        if content is None:
            raise ProviderError(
                kind="malformed_response",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=f"response without content blocks: {response!r}",
            )
        texts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                texts.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "end_turn":
            neutral_stop = "end"
        elif stop_reason == "tool_use":
            neutral_stop = "tool_use"
        else:
            neutral_stop = stop_reason or "end"
        usage = getattr(response, "usage", None)
        return ModelTurn(
            text="\n".join(texts),
            tool_calls=tuple(tool_calls),
            stop_reason=neutral_stop,
            usage=Usage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
            provider=PROVIDER_NAME,
            provider_payload=content,
        )

    # -- LLMProvider interface -------------------------------------------------

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        request: dict[str, Any] = {
            "model": self._settings.model,
            "max_tokens": self._settings.max_tokens,
            "system": self._system_param(system_prefix),
            "messages": self._messages_param(conversation),
        }
        if tools:
            request["tools"] = [self._tool_param(tool) for tool in tools]
        if self._settings.thinking == "adaptive":
            request["thinking"] = {"type": "adaptive"}
        if self._settings.effort:
            request["output_config"] = {"effort": self._settings.effort}
        client = self._ensure_client()
        try:
            response = client.messages.create(**request)
        except ProviderError:
            raise
        except Exception as exc:
            raise normalize_anthropic_error(exc) from exc
        return self._parse_response(response)
