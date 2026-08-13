"""Claude Code adapter regression tests for app-integrated tool routing."""

from __future__ import annotations

import json
import subprocess

from server.llm.claude_code_adapter import ClaudeCodeAdapter
from server.llm.types import ToolDefinition, UserMessage

_SPATIAL_TOOL = ToolDefinition(
    name="get_spatial_context",
    description="Read fixture FIDs and 3D coordinates.",
    parameters={"type": "object", "additionalProperties": False, "properties": {}},
)


def test_spatial_tool_contract_is_present_in_the_claude_system_prompt() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"structured_output": {"text": "", "tool_calls": []}}),
            stderr="",
        )

    adapter = ClaudeCodeAdapter("sonnet", runner=runner)
    adapter.complete(
        system_prefix="rulebook",
        conversation=[UserMessage(text="3D 레이아웃")],
        tools=[_SPATIAL_TOOL],
    )

    system_prompt = calls[0][calls[0].index("--system-prompt") + 1]
    assert "앱 내 도구" in system_prompt
    assert "도구가 연결되지 않았다" in system_prompt
    assert "첫 호출은 반드시 `get_spatial_context`" in system_prompt
    assert '"name": "get_spatial_context"' in system_prompt


def test_ask_user_one_at_a_time_contract_is_in_the_system_prompt() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"structured_output": {"text": "", "tool_calls": []}}),
            stderr="",
        )

    adapter = ClaudeCodeAdapter("sonnet", runner=runner)
    adapter.complete(
        system_prefix="rulebook",
        conversation=[UserMessage(text="배치")],
        tools=[_SPATIAL_TOOL],
    )

    system_prompt = calls[0][calls[0].index("--system-prompt") + 1]
    assert "ask_user" in system_prompt
    assert "한 번에" in system_prompt  # one question at a time, not a prose wall


def test_reasoning_scratchpad_is_present_but_optional_for_speed() -> None:
    schema = ClaudeCodeAdapter("opus")._schema()
    # reasoning stays first (generation order → chain-of-thought when the model
    # uses it) but is NOT required, so no long scratchpad is forced on every
    # call — keeping multi-step tool turns from stacking into a long hang.
    assert list(schema["properties"])[0] == "reasoning"
    assert "reasoning" not in schema["required"]
    assert set(schema["required"]) == {"text", "tool_calls"}


def test_speed_first_model_makes_reasoning_optional() -> None:
    schema = ClaudeCodeAdapter("fable")._schema()
    # fable is speed-first: the scratchpad exists but is NOT required, so an
    # obvious request is answered fast without forced deliberation.
    assert "reasoning" in schema["properties"]
    assert "reasoning" not in schema["required"]
    assert set(schema["required"]) == {"text", "tool_calls"}


def test_reasoning_is_parsed_away_and_only_text_and_calls_surface() -> None:
    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        payload = {"reasoning": "의도 분석…", "text": "높이를 바꾸겠습니다", "tool_calls": []}
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps({"structured_output": payload}), stderr=""
        )

    adapter = ClaudeCodeAdapter("opus", runner=runner)
    turn = adapter.complete(
        system_prefix="rulebook", conversation=[UserMessage(text="hi")], tools=[_SPATIAL_TOOL]
    )
    assert turn.text == "높이를 바꾸겠습니다"
    assert turn.tool_calls == ()


def _prompt_for(model: str) -> str:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"structured_output": {"text": "", "tool_calls": []}}),
            stderr="",
        )

    ClaudeCodeAdapter(model, runner=runner).complete(
        system_prefix="rulebook", conversation=[UserMessage(text="배치")], tools=[_SPATIAL_TOOL]
    )
    return calls[0][calls[0].index("--system-prompt") + 1]


def test_reasoning_first_directive_is_in_the_system_prompt() -> None:
    system_prompt = _prompt_for("opus")
    assert "reasoning" in system_prompt
    assert "의도" in system_prompt


def test_speed_first_model_directive_favors_speed() -> None:
    system_prompt = _prompt_for("fable")
    assert "속도" in system_prompt  # the fast model is told to stay fast
