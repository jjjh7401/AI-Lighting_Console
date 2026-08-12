"""Mutable provider selection boundary for the local settings UI."""

from __future__ import annotations

from collections.abc import Sequence

from server.llm.types import ConversationItem, LLMProvider, ModelTurn, ToolDefinition


class ProviderSlot:
    """Delegates each new model call to the currently selected provider.

    A selection change affects the next turn without rebuilding the safety gate
    or WebSocket server.  The operation is one pointer replacement, so a turn
    already in progress remains coherent on its original provider.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def model_id(self) -> str:
        return self._provider.model_id

    @property
    def supports_prompt_caching(self) -> bool:
        return self._provider.supports_prompt_caching

    def select(self, provider: LLMProvider) -> None:
        self._provider = provider

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        return self._provider.complete(
            system_prefix=system_prefix, conversation=conversation, tools=tools
        )
