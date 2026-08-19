"""진행 스트리밍 — 턴이 **도는 동안** 사용자에게 신호가 간다.

측정된 문제: 한 턴은 모델 호출을 최대 24회(``DEFAULT_MAX_MODEL_CALLS``) 돌고
도구 하나도 짧지 않다 — ``server/audit_logs/probe-*.jsonl`` 실측에서 콘솔 왕복
p90이 67.3ms이고 ``get_spatial_context`` 1회가 240~420왕복 = 16~28초였다. CLI
모델 호출 1회도 ~12초다(``server/llm/claude_code_adapter.py``
``_DEFAULT_PROFILE`` 주석: 다단 도구 턴이 "~70초+ 무응답"으로 쌓여 사용자가
서버가 죽은 줄 안다). 그런데 종전에는 그 사이 프레임이 **0개**였다.

여기서 재는 것은 두 가지다:

1. 루프가 돌 때 진행 한 줄이 **순서대로** 나온다 (콜백 더블로 확인).
2. 콜백을 주지 않으면 **아무 일도 일어나지 않는다** — 기존 호출자의 동작 불변.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from server.llm.types import ModelTurn, ToolCall, ToolDefinition, Usage
from server.orchestrator.runner import (
    _TOOL_TASKS,
    DEFAULT_MAX_MODEL_CALLS,
    PROGRESS_MODEL_CALL,
    PROGRESS_TOOL_DONE,
    PROGRESS_TOOL_START,
    Orchestrator,
    progress_task_name,
)
from server.orchestrator.tools import ToolExecution, ToolResult

TOOLS_SOURCE = Path(__file__).resolve().parents[1] / "orchestrator" / "tools.py"


def _registered_tool_names() -> set[str]:
    """``ToolDefinition(name=...)``\\ 이 실제로 여는 도구 이름 전부 (AST 열거)."""
    tree = ast.parse(TOOLS_SOURCE.read_text(encoding="utf-8"))
    return {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ToolDefinition"
        for keyword in node.keywords
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant)
    }


class ScriptedProvider:
    """정해진 도구 호출 묶음들을 차례로 내고, 그다음 글로 끝내는 모델."""

    def __init__(self, rounds: tuple[tuple[str, ...], ...]) -> None:
        self._rounds = rounds
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools):
        self.calls += 1
        if self.calls <= len(self._rounds):
            names = self._rounds[self.calls - 1]
            return ModelTurn(
                text="",
                tool_calls=tuple(
                    ToolCall(id=f"c{self.calls}-{i}", name=name, arguments={})
                    for i, name in enumerate(names)
                ),
                stop_reason="tool_use",
                usage=Usage(),
                provider="scripted",
            )
        return ModelTurn(
            text="끝냈습니다",
            tool_calls=(),
            stop_reason="end",
            usage=Usage(),
            provider="scripted",
        )


class EchoRegistry:
    """무엇을 불러도 성공을 내는 등록부 — 이 파일이 재는 것은 배출 순서다."""

    def definitions(self):
        return (
            ToolDefinition(name="query_state", description="콘솔 상태", parameters={}),
            ToolDefinition(name="get_spatial_context", description="무대 좌표", parameters={}),
            ToolDefinition(name="run_commands", description="명령 실행", parameters={}),
        )

    def dispatch(self, call, context):
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"ok": True}, ensure_ascii=False),
                is_error=False,
            )
        )


class Recorder:
    """진행 싱크 더블 — 받은 (phase, detail, seq)를 도착 순서로 쌓는다."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, int]] = []

    def __call__(self, *, phase: str, detail: str, seq: int) -> None:
        self.events.append((phase, detail, seq))


def _run(rounds, *, progress=None, max_model_calls=DEFAULT_MAX_MODEL_CALLS):
    provider = ScriptedProvider(rounds)
    result = Orchestrator(
        provider=provider,
        registry=EchoRegistry(),
        system_prefix="",
        max_model_calls=max_model_calls,
        progress=progress,
    ).handle_instruction("무대 좌표 읽고 그대로 걸어줘")
    return provider, result


class TestTheToolLoopStreamsInOrder:
    def test_every_phase_arrives_and_the_order_is_the_loop_order(self):
        recorder = Recorder()
        _run((("query_state",), ("run_commands",)), progress=recorder)
        phases = [phase for phase, _, _ in recorder.events]
        # 모델 호출 3회(도구 2라운드 + 마지막 글), 그 사이에 도구 2건.
        assert phases == [
            PROGRESS_MODEL_CALL,
            PROGRESS_TOOL_START,
            PROGRESS_TOOL_DONE,
            PROGRESS_MODEL_CALL,
            PROGRESS_TOOL_START,
            PROGRESS_TOOL_DONE,
            PROGRESS_MODEL_CALL,
        ]

    def test_the_model_call_line_lands_before_the_call_not_after(self):
        """모델을 부른 **뒤에** 알리면 늦는다 — 기다림은 부르는 순간 시작된다."""
        seen: list[str] = []
        provider = ScriptedProvider((("query_state",),))
        original = provider.complete

        def watched(**kwargs):
            seen.append("model")
            return original(**kwargs)

        provider.complete = watched  # type: ignore[method-assign]

        def sink(*, phase, detail, seq):
            if phase == PROGRESS_MODEL_CALL:
                seen.append("progress")

        Orchestrator(
            provider=provider,
            registry=EchoRegistry(),
            system_prefix="",
            progress=sink,
        ).handle_instruction("아무거나")
        # 첫 쌍이 progress -> model 이어야 한다(그 반대면 늦은 통보다).
        assert seen[:2] == ["progress", "model"]

    def test_tool_start_precedes_dispatch_and_tool_done_follows_it(self):
        order: list[str] = []

        class WatchedRegistry(EchoRegistry):
            def dispatch(self, call, context):
                order.append("dispatch")
                return super().dispatch(call, context)

        def sink(*, phase, detail, seq):
            if phase in (PROGRESS_TOOL_START, PROGRESS_TOOL_DONE):
                order.append(phase)

        Orchestrator(
            provider=ScriptedProvider((("get_spatial_context",),)),
            registry=WatchedRegistry(),
            system_prefix="",
            progress=sink,
        ).handle_instruction("좌표 읽어줘")
        assert order == [PROGRESS_TOOL_START, "dispatch", PROGRESS_TOOL_DONE]

    def test_seq_is_monotonic_from_one_within_the_turn(self):
        recorder = Recorder()
        _run((("query_state", "get_spatial_context"), ("run_commands",)), progress=recorder)
        seqs = [seq for _, _, seq in recorder.events]
        assert seqs == list(range(1, len(seqs) + 1))

    def test_a_second_turn_restarts_the_sequence(self):
        """``seq``\\ 는 **턴 안에서만** 단조증가한다 — 턴 경계에서 1로 돌아간다."""
        recorder = Recorder()
        orchestrator = Orchestrator(
            provider=ScriptedProvider((("query_state",),)),
            registry=EchoRegistry(),
            system_prefix="",
            progress=recorder,
        )
        orchestrator.handle_instruction("첫 턴")
        first_turn = len(recorder.events)
        assert first_turn == 4  # 모델 2회 + 도구 1건의 시작/완료
        # 같은 대본은 이미 소진돼 둘째 턴은 곧바로 마지막 글을 낸다 — 그래도
        # 첫 배출은 다시 1이어야 한다.
        orchestrator.handle_instruction("둘째 턴")
        assert [seq for _, _, seq in recorder.events[first_turn:]] == [1]

    def test_every_detail_is_a_korean_user_phrase(self):
        recorder = Recorder()
        _run((("query_state", "get_spatial_context"), ("run_commands",)), progress=recorder)
        assert recorder.events, "배출이 0건이면 판정이 공허하다"
        for phase, detail, _ in recorder.events:
            assert detail.strip(), phase
            # 영어 도구 이름은 조명 감독의 어휘가 아니다 — 그대로 새면 안 된다.
            assert "query_state" not in detail
            assert "get_spatial_context" not in detail
            assert "run_commands" not in detail
            assert any("\uac00" <= ch <= "\ud7a3" for ch in detail), detail

    def test_each_dispatched_tool_gets_its_own_named_task(self):
        recorder = Recorder()
        _run((("query_state", "get_spatial_context"),), progress=recorder)
        started = [detail for phase, detail, _ in recorder.events if phase == PROGRESS_TOOL_START]
        assert started == [
            f"{progress_task_name('query_state')}…",
            f"{progress_task_name('get_spatial_context')}…",
        ]

    def test_the_loop_limit_wrap_up_call_is_also_announced(self):
        """마무리 정리 호출도 모델 호출이다 — 그 동안도 화면이 정지해서는 안 된다."""
        recorder = Recorder()
        rounds = tuple(("query_state",) for _ in range(4))
        _run(rounds, progress=recorder, max_model_calls=2)
        phase, detail, _ = recorder.events[-1]
        assert (phase, detail) == (PROGRESS_MODEL_CALL, "마무리 정리 중…")

    def test_an_unlisted_tool_still_gets_a_korean_line(self):
        """표에 없는 도구도 **말은 남긴다** — 조용한 공백이 더 나쁘다."""
        detail = progress_task_name("some_future_tool")
        assert "some_future_tool" in detail
        assert any("\uac00" <= ch <= "\ud7a3" for ch in detail)


class TestWithoutASinkNothingChanges:
    """콜백 미주입 = 진행 스트리밍 이전 동작. 기존 호출자·테스트 호환성의 근거."""

    def test_the_turn_result_is_identical_with_and_without_a_sink(self):
        rounds = (("query_state",), ("run_commands",))
        bare_provider, bare = _run(rounds)
        _, streamed = _run(rounds, progress=Recorder())
        assert bare.status == streamed.status == "ok"
        assert bare.text == streamed.text == "끝냈습니다"
        assert bare.model_calls == streamed.model_calls == 3
        assert bare.command_outcomes == streamed.command_outcomes
        # 배출이 모델 호출이나 디스패치를 추가로 유발하지 않는다.
        assert bare_provider.calls == 3

    def test_the_default_orchestrator_takes_no_sink(self):
        # 인자를 주지 않고도 구성된다 — 이 축의 모든 기존 호출자가 그렇게 부른다.
        _, result = _run((("query_state",),))
        assert result.status == "ok"


class TestTheDisplayNeverBreaksTheTurn:
    """진행 표시 때문에 실제 작업이 무너지면 개선이 아니라 새 고장이다."""

    def test_a_throwing_sink_is_swallowed_and_the_turn_completes(self):
        calls = {"n": 0}

        def exploding(*, phase, detail, seq):
            calls["n"] += 1
            raise RuntimeError("소켓이 끊겼다")

        _, result = _run((("query_state",), ("run_commands",)), progress=exploding)
        assert result.status == "ok"
        assert result.text == "끝냈습니다"
        # 첫 배출에서 멈추지 않았다 — 매번 다시 시도하고 매번 삼킨다.
        assert calls["n"] >= 7

    def test_a_throwing_sink_does_not_stall_the_sequence(self):
        seen: list[int] = []

        def flaky(*, phase, detail, seq):
            seen.append(seq)
            if phase == PROGRESS_TOOL_START:
                raise RuntimeError("한 줄만 실패")

        _run((("query_state",), ("run_commands",)), progress=flaky)
        assert seen == list(range(1, len(seen) + 1))


class TestTheTaskTableCoversTheRealToolset:
    """도구 표가 실제 등록부와 벌어지면 사용자는 영어 이름을 보게 된다.

    등록부에 도구가 새로 붙는 것은 흔한 일이고, 그때 표를 갱신하지 않으면
    진행 한 줄이 ``도구 실행(compose_fx)``\\ 처럼 새 나간다 — 조용히 나빠지는
    쪽이라 사람 눈으로는 잡히지 않는다. 그래서 여기서 잠근다.
    """

    def test_every_registered_tool_name_has_a_korean_task_name(self):
        names = _registered_tool_names()
        assert len(names) >= 30, "도구 이름을 못 모으면 0건 판정이 공허하다"
        assert sorted(n for n in names if n not in _TOOL_TASKS) == []

    def test_the_table_holds_no_name_the_registry_does_not_offer(self):
        """반대 방향도 잠근다 — 사라진 도구의 문구가 표에 남아 썩지 않게."""
        assert sorted(set(_TOOL_TASKS) - _registered_tool_names()) == []
