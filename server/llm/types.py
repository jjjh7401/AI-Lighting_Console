"""Provider-neutral LLM interface types (REQ-MVP-038).

Everything above this layer — the orchestrator, safety gate (M4), and UI (M5) —
speaks ONLY these types. Tool calling, system-prompt placement, and response
parsing are provider concerns hidden behind :class:`LLMProvider`; upper layers
never branch on provider identity.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolDefinition:
    """A neutral tool declaration (JSON-schema parameters).

    Adapters convert this to the provider wire format (Anthropic ``input_schema``
    / Gemini function declarations).
    """

    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolResult:
    """The outcome of one executed tool call, fed back to the model."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class Usage:
    """Token accounting for one model turn (cache fields feed AC-MVP-014 part 2)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class UserMessage:
    """A user-authored conversation item (instruction or injected context)."""

    text: str


@dataclass(frozen=True)
class ToolResultsMessage:
    """All tool results for one assistant turn, delivered as ONE message."""

    results: tuple[ToolResult, ...]


@dataclass(frozen=True)
class ModelTurn:
    """One parsed model response, provider-neutral.

    ``provider_payload`` is the opaque raw content used to echo this turn back
    verbatim to the SAME provider on the next request (e.g. Anthropic content
    blocks including thinking blocks). Adapters of a different provider ignore
    it and reconstruct from the neutral fields.
    """

    text: str
    tool_calls: tuple[ToolCall, ...]
    stop_reason: str  # "end" | "tool_use" | provider-specific passthrough
    usage: Usage
    provider: str
    provider_payload: Any = field(default=None, compare=False)


ConversationItem = UserMessage | ModelTurn | ToolResultsMessage


# @MX:ANCHOR: [AUTO] the provider-neutral completion interface — orchestrator (M3),
#   safety gate (M4), and both adapters all bind to exactly this surface
# @MX:REASON: REQ-MVP-038 requires upper layers to work without knowing the active
#   provider; widening or bypassing this interface re-couples them to one SDK
@runtime_checkable
class LLMProvider(Protocol):
    """Provider-neutral completion interface (single active provider at runtime)."""

    @property
    def name(self) -> str:
        """Provider identifier ("anthropic" | "gemini")."""
        ...

    @property
    def model_id(self) -> str:
        """The pinned model id from configuration (REQ-MVP-006)."""
        ...

    @property
    def supports_prompt_caching(self) -> bool:
        """Whether the fixed-prefix caching path is active (REQ-MVP-041)."""
        ...

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        """Run one completion over the fixed prefix + conversation + tools."""
        ...
