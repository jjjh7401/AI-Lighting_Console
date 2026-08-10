"""사람이 답한 왕복은 **폭주 가드에 청구하지 않는다.**

[round24 후속] :data:`DEFAULT_MAX_MODEL_CALLS`\\ 는 모델이 혼자 도는 것을 막는 비용
가드다. 그런데 질문 카드 왕복까지 거기에 청구되어, 실측에서 질문 3회를 거치자 12회
한도가 말라 ``status=loop_limit`` · 본문 **0자**로 끝났다 — 사용자는 대화를 끝까지
따라왔는데 답을 한 글자도 못 받았다.

사람 왕복은 폭주할 수 없다. 사람이 스스로 멈추기 때문이다.
"""

from __future__ import annotations

import json

from server.llm.types import ModelTurn, ToolCall, ToolDefinition, Usage
from server.orchestrator.runner import DEFAULT_MAX_MODEL_CALLS, Orchestrator
from server.orchestrator.tools import ToolExecution, ToolResult

_ROUNDS = DEFAULT_MAX_MODEL_CALLS + 5


class LoopingProvider:
    """``rounds``\\ 번 도구를 부르고 그다음 글로 끝내는 모델."""

    def __init__(self, rounds: int) -> None:
        self.rounds = rounds
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools):
        self.calls += 1
        if self.calls <= self.rounds:
            return ModelTurn(
                text="",
                tool_calls=(ToolCall(id=f"c{self.calls}", name="ask_user", arguments={}),),
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


class OneToolRegistry:
    """물음 하나만 아는 등록부 — 답을 받았는지 여부를 그대로 낸다."""

    def __init__(self, *, awaited_human: bool) -> None:
        self.awaited_human = awaited_human

    def definitions(self):
        # 비어 있으면 `not tools`가 늘 참이라 마무리 호출과 구별되지 않는다.
        return (ToolDefinition(name="ask_user", description="사용자에게 묻는다", parameters={}),)

    def dispatch(self, call, context):
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"answered": self.awaited_human}, ensure_ascii=False),
                is_error=False,
            ),
            awaited_human=self.awaited_human,
        )


def _run(*, rounds: int, awaited_human: bool):
    return Orchestrator(
        provider=LoopingProvider(rounds),
        registry=OneToolRegistry(awaited_human=awaited_human),
        system_prefix="",
    ).handle_instruction("Sharpy 6대 추가해줘")


class TestTheGuardStillStopsRunaways:
    """가드를 없앤 것이 아니다 — 사람이 낀 회차만 뺀다."""

    def test_a_model_looping_alone_is_cut_off(self):
        # [HARD] 이 줄이 무너지면 폭주 비용을 아무것도 못 막는다.
        assert _run(rounds=_ROUNDS, awaited_human=False).status == "loop_limit"

    def test_a_short_autonomous_run_still_finishes(self):
        result = _run(rounds=2, awaited_human=False)

        assert result.status == "ok"
        assert result.text == "끝냈습니다"

    def test_an_unanswered_question_is_still_charged(self):
        # 답이 안 온 물음은 사람이 멈춘 것이 아니라 그냥 모델의 회차다.
        assert _run(rounds=_ROUNDS, awaited_human=False).status == "loop_limit"


class TestHumanRoundTripsAreNotCharged:
    def test_many_questions_still_reach_a_final_answer(self):
        # [HARD] 실물 사고 그대로 — 질문을 거듭하면 본문 0자로 끝났다.
        result = _run(rounds=_ROUNDS, awaited_human=True)

        assert result.status == "ok"

    def test_the_user_is_never_left_without_words(self):
        assert _run(rounds=_ROUNDS, awaited_human=True).text == "끝냈습니다"


class TestTheUserAlwaysGetsWords:
    """한도에 걸려도 **말은 남긴다** — 가드는 도구 루프를 끊는 것이다."""

    class _Provider(LoopingProvider):
        """도구만 부르다 끝나는 모델 — 스스로는 글을 한 번도 내지 않는다."""

        def __init__(self) -> None:
            super().__init__(rounds=10_000)
            self.toolless_calls = 0

        def complete(self, *, system_prefix, conversation, tools):
            if not tools:
                self.toolless_calls += 1
                return ModelTurn(
                    text="여기까지 확인했고, 남은 일은 이렇습니다.",
                    tool_calls=(),
                    stop_reason="end",
                    usage=Usage(),
                    provider="scripted",
                )
            return super().complete(
                system_prefix=system_prefix, conversation=conversation, tools=tools
            )

    def _run(self, provider):
        return Orchestrator(
            provider=provider,
            registry=OneToolRegistry(awaited_human=False),
            system_prefix="",
        ).handle_instruction("Sharpy 6대 추가해줘")

    def test_a_loop_limit_still_says_something(self):
        # [HARD] 실측: 사용자가 카드 셋에 답하며 끝까지 따라왔는데 본문 0자였다.
        provider = self._Provider()
        result = self._run(provider)

        assert result.status == "loop_limit"
        assert result.text == "여기까지 확인했고, 남은 일은 이렇습니다."

    def test_the_closing_call_gets_no_tools(self):
        # 도구를 주면 그 자리에서 루프가 되살아나 가드가 무의미해진다.
        provider = self._Provider()
        self._run(provider)

        assert provider.toolless_calls == 1

    def test_it_asks_only_once(self):
        provider = self._Provider()
        self._run(provider)

        assert provider.toolless_calls == 1, "마무리 호출이 늘면 그것도 루프다"

    def test_a_model_that_already_spoke_is_not_asked_again(self):
        # 이미 낸 글이 있으면 덧붙일 이유가 없다.
        class Spoke(LoopingProvider):
            def __init__(self) -> None:
                super().__init__(rounds=10_000)
                self.toolless_calls = 0

            def complete(self, *, system_prefix, conversation, tools):
                if not tools:
                    self.toolless_calls += 1
                    return ModelTurn(
                        text="덧붙임",
                        tool_calls=(),
                        stop_reason="end",
                        usage=Usage(),
                        provider="scripted",
                    )
                self.calls += 1
                return ModelTurn(
                    text="진행 중입니다",
                    tool_calls=(ToolCall(id=f"c{self.calls}", name="ask_user", arguments={}),),
                    stop_reason="tool_use",
                    usage=Usage(),
                    provider="scripted",
                )

        provider = Spoke()
        result = self._run(provider)

        assert provider.toolless_calls == 0
        assert result.text == "진행 중입니다"

    def test_a_failing_closing_call_does_not_kill_the_turn(self):
        class Broken(LoopingProvider):
            def __init__(self) -> None:
                super().__init__(rounds=10_000)

            def complete(self, *, system_prefix, conversation, tools):
                if not tools:
                    raise RuntimeError("공급자가 죽었다")
                return super().complete(
                    system_prefix=system_prefix, conversation=conversation, tools=tools
                )

        result = self._run(Broken())

        assert result.status == "loop_limit"
        assert result.text == ""
