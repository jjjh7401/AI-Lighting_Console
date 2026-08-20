"""답변 스트리밍 (SPEC-COPILOT-STREAM-001).

측정(2026-08-20, 실기): 좌표 판독 턴 18.5초 가운데 **마지막 모델 호출이
6~10초**를 쓰는데 그동안 화면에는 진행 한 줄만 있었다. 이 축은 그 침묵을
글자로 채운다.

여기서 지키는 성질 넷 — 각각 가드를 지우면 RED가 되어야 한다:

  * **부가 채널이다.** 싱크가 없거나 프로바이더가 스트리밍을 모르면 종전
    경로가 그대로 쓰이고 결과 턴은 동일하다.
  * **판정을 바꾸지 않는다.** 같은 대화에 대해 스트리밍 턴과 버퍼링 턴의
    text·tool_calls가 같다.
  * **실패해도 답을 잃지 않는다.** 스트리밍 호출이 터지면 같은 턴을 버퍼링
    경로로 한 번 더 부른다.
  * **싱크가 던져도 턴은 산다.** 진행 배출과 같은 규율이다.
"""

from __future__ import annotations

from server.llm.types import ModelTurn, ToolCall, Usage
from server.orchestrator.runner import Orchestrator
from server.orchestrator.tools import build_toolset


class _Port:
    def __getattr__(self, name):
        def call(*args, **kwargs):
            return []

        return call


def _turn(text: str, calls: tuple[ToolCall, ...] = ()) -> ModelTurn:
    return ModelTurn(
        text=text,
        tool_calls=calls,
        stop_reason="tool_use" if calls else "end",
        usage=Usage(),
        provider="scripted",
        provider_payload=None,
    )


class BufferedProvider:
    """스트리밍을 모르는 프로바이더 — 종전 계약 그대로."""

    name = "scripted"
    model_id = "scripted-model"
    supports_prompt_caching = False

    def __init__(self, turns: list[ModelTurn]) -> None:
        self.turns = list(turns)
        self.complete_calls = 0

    def complete(self, *, system_prefix, conversation, tools=()) -> ModelTurn:
        self.complete_calls += 1
        return self.turns.pop(0)


class StreamingProvider(BufferedProvider):
    """조각을 흘리는 프로바이더. 조각의 합은 turn.text와 같아야 한다."""

    def __init__(self, turns: list[ModelTurn], *, pieces: int = 3, explode: bool = False) -> None:
        super().__init__(turns)
        self.pieces = pieces
        self.explode = explode
        self.stream_calls = 0

    def complete_stream(self, *, system_prefix, conversation, tools=(), on_text) -> ModelTurn:
        self.stream_calls += 1
        if self.explode:
            raise RuntimeError("stream transport died")
        turn = self.turns.pop(0)
        text = turn.text
        if text:
            size = max(len(text) // self.pieces, 1)
            for start in range(0, len(text), size):
                on_text(text[start : start + size])
        return turn


def _orchestrator(provider, sink=None):
    return Orchestrator(
        provider=provider,
        registry=build_toolset(execution_port=_Port(), state_port=_Port()),
        system_prefix="",
        answer=sink,
    )


class _Recorder:
    def __init__(self) -> None:
        self.deltas: list[tuple[str, int]] = []

    def __call__(self, *, delta: str, seq: int) -> None:
        self.deltas.append((delta, seq))

    @property
    def text(self) -> str:
        return "".join(delta for delta, _ in self.deltas)


class TestTheChannelIsAdditive:
    def test_without_a_sink_the_streaming_path_is_not_taken(self):
        provider = StreamingProvider([_turn("끝냈습니다")])
        result = _orchestrator(provider).handle_instruction("아무거나")
        assert provider.stream_calls == 0
        assert provider.complete_calls == 1
        assert result.text == "끝냈습니다"

    def test_a_provider_without_streaming_still_answers(self):
        provider = BufferedProvider([_turn("끝냈습니다")])
        recorder = _Recorder()
        result = _orchestrator(provider, recorder).handle_instruction("아무거나")
        assert recorder.deltas == []
        assert result.text == "끝냈습니다"


class TestTheStreamedTurnIsTheSameTurn:
    def test_the_deltas_reassemble_into_the_final_text(self):
        provider = StreamingProvider([_turn("무대 좌표를 읽어 배치를 정리했습니다")])
        recorder = _Recorder()
        result = _orchestrator(provider, recorder).handle_instruction("배치 알려줘")
        assert recorder.text == result.text
        assert provider.stream_calls == 1

    def test_seq_starts_at_one_and_increases(self):
        provider = StreamingProvider([_turn("한 줄 답")], pieces=3)
        recorder = _Recorder()
        _orchestrator(provider, recorder).handle_instruction("아무거나")
        seqs = [seq for _, seq in recorder.deltas]
        assert seqs == list(range(1, len(seqs) + 1))

    def test_a_tool_turn_still_drives_the_loop(self):
        provider = StreamingProvider(
            [
                _turn("", (ToolCall(id="c1", name="query_state", arguments={"path": "x"}),)),
                _turn("정리했습니다"),
            ]
        )
        recorder = _Recorder()
        result = _orchestrator(provider, recorder).handle_instruction("상태 봐줘")
        assert provider.stream_calls == 2
        assert result.text == "정리했습니다"
        assert recorder.text == "정리했습니다"


class TestFailureNeverCostsTheAnswer:
    def test_a_broken_stream_falls_back_to_the_buffered_call(self):
        provider = StreamingProvider([_turn("끝냈습니다")], explode=True)
        recorder = _Recorder()
        result = _orchestrator(provider, recorder).handle_instruction("아무거나")
        assert provider.stream_calls == 1
        assert provider.complete_calls == 1  # 같은 턴을 버퍼링으로 다시
        assert result.text == "끝냈습니다"

    def test_a_throwing_sink_does_not_kill_the_turn(self):
        def hostile(*, delta: str, seq: int) -> None:
            raise RuntimeError("socket closed")

        provider = StreamingProvider([_turn("끝냈습니다")])
        result = _orchestrator(provider, hostile).handle_instruction("아무거나")
        assert result.text == "끝냈습니다"
        assert result.status == "ok"
