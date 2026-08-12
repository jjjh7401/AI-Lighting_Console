"""Claude Code subscription adapter.

Uses the locally installed ``claude`` CLI rather than Anthropic's API.  The CLI
owns the browser OAuth session in the macOS Keychain; this process neither reads
nor stores its token.  The CLI is deliberately invoked with its own tools
disabled.  MA3 commands are returned as structured proposals and stay inside the
existing safety-gate tool loop.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
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

PROVIDER_NAME = "claude_code"
_MODEL_ALIASES = frozenset({"opus", "sonnet", "fable"})


def _conversation_text(conversation: Sequence[ConversationItem]) -> str:
    """Render neutral conversation items for the stateless Claude CLI call."""
    lines: list[str] = []
    for item in conversation:
        if isinstance(item, UserMessage):
            lines.append(f"사용자: {item.text}")
        elif isinstance(item, ToolResultsMessage):
            for result in item.results:
                lines.append(
                    f"도구 결과 ({result.name}, "
                    f"{'오류' if result.is_error else '성공'}): {result.content}"
                )
        else:
            if item.text:
                lines.append(f"어시스턴트: {item.text}")
            for call in item.tool_calls:
                lines.append(
                    f"제안한 도구 호출: {call.name} "
                    f"{json.dumps(call.arguments, ensure_ascii=False)}"
                )
    return "\n".join(lines)


class ClaudeCodeAdapter:
    """LLMProvider backed by a locally authenticated Claude Code subscription."""

    def __init__(
        self,
        model: str,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        if model not in _MODEL_ALIASES:
            raise ValueError(f"unsupported Claude Code model alias: {model!r}")
        self._model = model
        self._runner = runner or subprocess.run

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def supports_prompt_caching(self) -> bool:
        return False

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["text", "tool_calls"],
            "properties": {
                "text": {"type": "string"},
                "tool_calls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "arguments"],
                        "properties": {
                            "name": {"type": "string"},
                            "arguments": {"type": "object"},
                        },
                    },
                },
            },
        }

    @staticmethod
    def _tool_instructions(tools: Sequence[ToolDefinition]) -> str:
        if not tools:
            return "도구는 사용할 수 없습니다."
        definitions = [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in tools
        ]
        return (
            "아래 앱 도구만 필요할 때 tool_calls에 넣으세요. 실제 실행은 앱의 안전 게이트가 "
            "처리합니다. Claude Code 자체 도구는 절대 사용하지 마세요.\n"
            + json.dumps(definitions, ensure_ascii=False)
        )

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        command = [
            "claude",
            "--print",
            "--model",
            self._model,
            "--tools",
            "",
            "--no-session-persistence",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(self._schema(), separators=(",", ":")),
            "--system-prompt",
            f"{system_prefix}\n\n{self._tool_instructions(tools)}",
            _conversation_text(conversation),
        ]
        try:
            result = self._runner(command, capture_output=True, text=True, timeout=120, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                kind="connection",
                provider=PROVIDER_NAME,
                retryable=True,
                raw_detail="Claude Code timed out",
            ) from exc
        except OSError as exc:
            raise ProviderError(
                kind="connection",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=repr(exc),
            ) from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Claude Code failed").strip()
            kind = "auth" if "login" in detail.lower() or "auth" in detail.lower() else "server"
            raise ProviderError(
                kind=kind,
                provider=PROVIDER_NAME,
                retryable=kind == "server",
                raw_detail=detail,
            )
        try:
            envelope = json.loads(result.stdout)
            structured_output = envelope["structured_output"]
            payload = (
                json.loads(structured_output)
                if isinstance(structured_output, str)
                else structured_output
            )
            text = payload["text"]
            calls = tuple(
                ToolCall(
                    id=f"claude-code-{index}",
                    name=call["name"],
                    arguments=dict(call["arguments"]),
                )
                for index, call in enumerate(payload["tool_calls"])
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(
                kind="malformed_response",
                provider=PROVIDER_NAME,
                retryable=False,
                raw_detail=repr(exc),
            ) from exc
        return ModelTurn(
            text=text,
            tool_calls=calls,
            stop_reason="tool_use" if calls else "end",
            usage=Usage(),
            provider=PROVIDER_NAME,
            provider_payload=None,
        )
