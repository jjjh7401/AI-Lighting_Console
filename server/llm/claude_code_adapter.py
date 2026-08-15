"""Claude Code subscription adapter.

Uses the locally installed ``claude`` CLI rather than Anthropic's API.  The CLI
owns the browser OAuth session in the macOS Keychain; this process neither reads
nor stores its token.  The CLI is deliberately invoked with its own tools
disabled.  MA3 commands are returned as structured proposals and stay inside the
existing safety-gate tool loop.
"""

from __future__ import annotations

import dataclasses
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

# REQ-IMGLAYOUT-006 / contract.md §2: this provider has no image transport, so
# an image-bearing turn must refuse honestly rather than silently drop the
# image and answer as if it were text-only.
_NO_IMAGE_SUPPORT_MESSAGE = (
    "현재 프로바이더(claude_code)는 이미지를 읽을 수 없습니다. "
    "provider.toml에서 anthropic 또는 gemini로 전환하세요."
)


def _has_images(conversation: Sequence[ConversationItem]) -> bool:
    return any(isinstance(item, UserMessage) and item.images for item in conversation)


@dataclasses.dataclass(frozen=True)
class _ModelProfile:
    """How to play to ONE model's strength when driving it via the CLI.

    The three Claude Code models trade reasoning depth against speed, so the
    same request should not be shaped identically for all of them:

    * reasoning-first (opus): a REQUIRED reasoning scratchpad and a deep
      intent-analysis directive — accept the latency, spend it on understanding.
    * balanced (sonnet): reasoning still required but lighter.
    * speed-first (fable): reasoning OPTIONAL and brief, so its low latency is
      not squandered on forced deliberation for simple asks.
    """

    reasoning_required: bool
    reasoning_hint: str
    directive: str


_DEFAULT_PROFILE = _ModelProfile(
    # Optional, not required: a required scratchpad forces a long chain-of-thought
    # on EVERY call and each Opus CLI call is ~12s, so a multi-step tool turn
    # stacked to ~70s+ of dead air (perceived as "server down"). Keep it as an
    # available, directive-encouraged field the model fills only when it helps.
    reasoning_required=False,
    reasoning_hint=(
        "사용자에게 보이지 않는 사고 공간. 먼저 사용자의 의도와 요청을 분석하고, "
        "이전 대화 맥락과 이미 주어진 값을 반영하고, 부족하거나 모호한 값을 짚고, "
        "어떤 도구를 어떤 순서로 부를지 계획한 뒤에 text와 tool_calls를 정한다."
    ),
    directive=(
        "답하기 전에 먼저 `reasoning`에서 사용자의 의도와 요청을 분석하고, 이전 대화 "
        "맥락과 이미 주어진 값을 반영하고, 부족하거나 모호한 값을 짚은 뒤 무엇을 할지 "
        "정하세요. 그 판단에 따라 `text`(사용자에게 보일 답)와 `tool_calls`를 채웁니다. "
        "`reasoning`은 사용자에게 표시되지 않습니다."
    ),
)

_MODEL_PROFILES: dict[str, _ModelProfile] = {
    # opus — reasoning-first: think deeply about intent, latency is acceptable.
    "opus": dataclasses.replace(
        _DEFAULT_PROFILE,
        directive=(
            "답하기 전에 먼저 `reasoning`에서 사용자의 의도·맥락·부족한 값을 충분히 "
            "깊게 분석하세요. 복잡하거나 다단계 요청일수록 단계적으로 따져 계획을 세운 "
            "뒤 `text`와 `tool_calls`를 정합니다. `reasoning`은 사용자에게 보이지 않으니 "
            "여기서 마음껏 추론하세요."
        ),
    ),
    # sonnet — balanced: reason, but concisely.
    "sonnet": _DEFAULT_PROFILE,
    # fable — speed-first: keep it lean so the fast model stays fast.
    "fable": _ModelProfile(
        reasoning_required=False,
        reasoning_hint=(
            "선택 사항인 짧은 메모 공간. 요청이 분명하면 비워 두고 바로 답하고, 모호할 "
            "때만 한두 줄로 무엇이 불확실한지 적는다."
        ),
        directive=(
            "이 모델은 속도가 강점입니다. 분명한 요청은 `reasoning` 없이 바로 `text`/"
            "`tool_calls`로 답하고, 모호할 때만 `reasoning`에 짧게 짚으세요. 불필요하게 "
            "길게 숙고하지 마세요."
        ),
    ),
}


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
        self._profile = _MODEL_PROFILES.get(model, _DEFAULT_PROFILE)
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

    def _schema(self) -> dict[str, Any]:
        # `reasoning` is a leading free-text field: under `--json-schema` the
        # model fills fields in order, so it restores the chain-of-thought that
        # structured-output otherwise suppresses. Whether it is REQUIRED is
        # per-model (profile): reasoning-first models must fill it, a speed-first
        # model may skip it for an obvious request. The field is parsed away and
        # never shown to the user.
        required = ["text", "tool_calls"]
        if self._profile.reasoning_required:
            required = ["reasoning", *required]
        return {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": self._profile.reasoning_hint,
                },
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

    def _tool_instructions(self, tools: Sequence[ToolDefinition]) -> str:
        if not tools:
            return "도구는 사용할 수 없습니다."
        definitions = [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in tools
        ]
        return (
            self._profile.directive + "\n"
            "아래 목록은 이 Copilot 세션에 이미 연결된 **앱 내 도구**입니다. "
            "MCP 연결이나 Claude Code 자체 도구가 아니며, `No such tool`, "
            "`도구가 연결되지 않았다`, `MCP가 없다`고 말해서는 안 됩니다. "
            "필요한 호출은 반드시 `tool_calls`에 넣으세요. 실제 실행은 앱의 안전 "
            "게이트가 처리하며, Claude Code 자체 도구는 절대 사용하지 마세요.\n"
            "사용자가 3D/레이아웃/공간 좌표에서 장비를 배치·이동·높이 변경하라고 "
            "요청하면 첫 호출은 반드시 `get_spatial_context`여야 합니다. "
            "특히 바닥 기준 높이 변경은 그 읽기 결과의 실제 FID만 `arrange_fixtures`의 "
            '`preset: "elevation"`, `height`로 넘기세요.\n'
            "확인할 값이 있으면 채팅 본문에 여러 질문이나 긴 표를 늘어놓지 말고 "
            "`ask_user` 도구를 쓰세요. 모르는 값이 여러 개면 `ask_user`를 **한 번에 "
            "하나씩** 여러 번 호출해 한 질문씩 받고, 모두 받은 뒤에 실행하세요. "
            "선택지는 `options`에 넣으면 버튼으로, 비우면 답 입력칸으로 표시됩니다.\n"
            + json.dumps(definitions, ensure_ascii=False)
        )

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        if _has_images(conversation):
            return ModelTurn(
                text=_NO_IMAGE_SUPPORT_MESSAGE,
                tool_calls=(),
                stop_reason="end",
                usage=Usage(),
                provider=PROVIDER_NAME,
                provider_payload=None,
            )
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
