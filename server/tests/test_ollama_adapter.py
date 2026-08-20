"""로컬 Ollama 프로바이더 (SPEC-COPILOT-LOCALLM-001).

이 축이 지키는 것 넷 — 각각 가드를 지우면 RED가 되어야 한다:

  * **프리픽스가 첫 메시지다.** 로컬 성능의 전부가 프리픽스 캐시이고
    (실측 2026-08-20: 콜드 54초 → 웜 0.25초), 순서를 바꾸면 매 턴이 콜드가
    된다. 그래서 "system이 0번"은 취향이 아니라 계약이다.
  * **선택 가능한 공급자다.** config에 등록되고 factory가 만들 수 있다.
  * **키가 없다.** 키 주입 경로가 예외 대신 빈 목록을 낸다 — 이것이 깨지면
    로컬을 고르는 순간 기동이 죽는다(실제로 죽었다).
  * **도구 미지원 모델은 조용히 실패하지 않는다.** 닫힌 ERROR_KINDS 안에서
    재시도 불가로 분류된다.
"""

from __future__ import annotations

import pytest

from server.deploy.keystore import inject_key_for_provider
from server.llm.config import SUPPORTED_PROVIDERS, OllamaSettings, ProviderConfig
from server.llm.errors import ProviderError
from server.llm.ollama_adapter import OllamaAdapter
from server.llm.types import ToolDefinition, ToolResult, ToolResultsMessage, UserMessage

_TOOL = ToolDefinition(
    name="get_rig_context",
    description="read the rig",
    parameters={"type": "object", "properties": {}},
)


def _reply(content="답했습니다", tool_calls=None):
    return {
        "message": {"content": content, "tool_calls": tool_calls or []},
        "prompt_eval_count": 28100,
        "eval_count": 12,
        "done": True,
    }


class _Recorder:
    """Transport double — records the request body, returns a scripted reply."""

    def __init__(self, reply=None, lines=None):
        self.reply = reply if reply is not None else _reply()
        self.lines = lines
        self.bodies: list[dict] = []

    def __call__(self, body):
        self.bodies.append(body)
        return self.lines if body.get("stream") else self.reply


class TestThePrefixLeadsEveryRequest:
    def test_the_system_prefix_is_the_first_message(self):
        transport = _Recorder()
        OllamaAdapter("m", transport=transport).complete(
            system_prefix="RULEBOOK", conversation=[UserMessage(text="안녕")], tools=()
        )
        messages = transport.bodies[0]["messages"]
        assert messages[0] == {"role": "system", "content": "RULEBOOK"}
        assert messages[1]["role"] == "user"

    def test_a_tool_result_round_trip_keeps_the_prefix_first(self):
        transport = _Recorder()
        OllamaAdapter("m", transport=transport).complete(
            system_prefix="RULEBOOK",
            conversation=[
                UserMessage(text="리그 봐줘"),
                ToolResultsMessage(
                    results=(ToolResult(tool_call_id="c", name="get_rig_context", content="{}"),)
                ),
            ],
            tools=[_TOOL],
        )
        messages = transport.bodies[0]["messages"]
        assert messages[0]["role"] == "system"
        assert [m["role"] for m in messages[1:]] == ["user", "tool"]

    def test_keep_alive_is_always_sent(self):
        # 언로드는 다음 턴을 조용히 콜드 스타트로 되돌린다 — 데몬 기본값에
        # 맡기면 그 순간이 언제인지 이 앱이 알 수 없다.
        transport = _Recorder()
        OllamaAdapter("m", keep_alive="90m", transport=transport).complete(
            system_prefix="P", conversation=[UserMessage(text="x")], tools=()
        )
        assert transport.bodies[0]["keep_alive"] == "90m"

    def test_reasoning_is_off(self):
        # gemma4:12b에서 추론 채널이 사용자 답변으로 새는 것을 관측했다.
        transport = _Recorder()
        OllamaAdapter("m", transport=transport).complete(
            system_prefix="P", conversation=[UserMessage(text="x")], tools=()
        )
        assert transport.bodies[0]["think"] is False


class TestItIsSelectable:
    def test_ollama_is_a_supported_provider(self):
        assert "ollama" in SUPPORTED_PROVIDERS

    def test_the_factory_builds_it_from_config(self):
        from server.llm.config import (
            AnthropicSettings,
            ClaudeCodeSettings,
            FallbackSettings,
            GeminiSettings,
        )
        from server.llm.factory import build_provider

        provider = build_provider(
            ProviderConfig(
                active="ollama",
                anthropic=AnthropicSettings(model="claude-opus-4-8"),
                claude_code=ClaudeCodeSettings(model="sonnet"),
                gemini=GeminiSettings(model="gemini-3.5-flash"),
                ollama=OllamaSettings(model="gemma4:26b", keep_alive="30m"),
                fallback=FallbackSettings(),
            )
        )
        assert provider.name == "ollama"
        assert provider.model_id == "gemma4:26b"

    def test_the_shipped_config_carries_a_local_model(self):
        from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config

        config = load_provider_config(DEFAULT_CONFIG_PATH)
        # 기본값은 여전히 Gemini다 — 로컬은 골라서 쓰는 백업이다.
        assert config.active == "gemini"
        assert config.ollama.model.strip()


class TestItNeedsNoKey:
    @pytest.mark.parametrize("provider", ["ollama", "claude_code"])
    def test_injecting_a_keyless_provider_is_a_no_op_not_a_crash(self, provider):
        # 이 가드가 없으면 로컬을 고르는 순간 기동이 KeyError로 죽는다.
        assert inject_key_for_provider(provider, environ={}) == []


class TestFailuresAreClassified:
    def test_a_model_without_tools_is_a_non_retryable_invalid_request(self):
        transport = _Recorder(reply={"error": "registry/gemma3:12b does not support tools"})
        with pytest.raises(ProviderError) as caught:
            OllamaAdapter("gemma3:12b", transport=transport).complete(
                system_prefix="P", conversation=[UserMessage(text="x")], tools=[_TOOL]
            )
        assert caught.value.kind == "invalid_request"
        assert caught.value.retryable is False

    def test_an_unreadable_tool_call_is_refused_rather_than_guessed(self):
        transport = _Recorder(reply=_reply(tool_calls=[{"function": {"arguments": {}}}]))
        with pytest.raises(ProviderError) as caught:
            OllamaAdapter("m", transport=transport).complete(
                system_prefix="P", conversation=[UserMessage(text="x")], tools=[_TOOL]
            )
        assert caught.value.kind == "malformed_response"


class TestStreamingMatchesTheBufferedTurn:
    def test_the_deltas_reassemble_into_the_turn_text(self):
        lines = [
            {"message": {"content": "무대 "}},
            {"message": {"content": "좌표를 "}},
            {"message": {"content": "읽었습니다"}, "done": True, "eval_count": 9},
        ]
        seen: list[str] = []
        turn = OllamaAdapter("m", transport=_Recorder(lines=lines)).complete_stream(
            system_prefix="P",
            conversation=[UserMessage(text="x")],
            tools=(),
            on_text=seen.append,
        )
        assert "".join(seen) == turn.text == "무대 좌표를 읽었습니다"

    def test_a_streamed_tool_call_survives_into_the_turn(self):
        lines = [
            {
                "message": {
                    "tool_calls": [{"function": {"name": "get_rig_context", "arguments": {}}}]
                }
            },
            {"message": {"content": ""}, "done": True},
        ]
        turn = OllamaAdapter("m", transport=_Recorder(lines=lines)).complete_stream(
            system_prefix="P",
            conversation=[UserMessage(text="x")],
            tools=[_TOOL],
            on_text=lambda _d: None,
        )
        assert [call.name for call in turn.tool_calls] == ["get_rig_context"]
        assert turn.stop_reason == "tool_use"
