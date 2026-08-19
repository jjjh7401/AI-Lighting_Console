"""질문 통로 — **답이 글로 오는가.**

[round24 후속] 승인 브리지를 그대로 재사용했다가 실물에서 무너졌다. 그쪽은
`approved: bool`을 나르도록 만들어졌으므로 도구가 받은 값은 사용자가 고른 문구가
아니라 ``True``였다. `ask_user`는 `isinstance(answer, str)`로 걸러 「아직 답을 못
받았다」로 읽었고, 모델은 카드로 답을 받고도 최종 본문에 *"이 채팅에 「…으로
진행해줘」라고 답변해 주세요"*라고 다시 물었다.

카드가 뜨고 `question_resolved` 반향까지 나갔기 때문에 **겉보기로는 되는 것처럼
보였다** — 반향은 WS 처리기가 내는 것이라 기다리던 쪽이 무엇을 받았는지와 무관하다.
그래서 여기서는 반향이 아니라 **`ask()`의 반환값**만 본다.
"""

from __future__ import annotations

import threading

import pytest

from server.web.question import (
    UNANSWERED,
    QuestionChannel,
    QuestionOption,
    QuestionRequest,
)

_ASK = QuestionRequest(
    prompt="'Clay Paky Sharpy'이(가) 없습니다. 어떻게 할까요?",
    why="콘솔은 명령줄로 타입을 추가하지 못합니다.",
    steps=("Menu > Patch", "Insert New Fixture"),
    options=(QuestionOption(label="콘솔에서 직접 고르겠다"),),
)


class Recorder:
    """UI 대신 물음을 받아 두고, 원하는 때 답한다."""

    def __init__(self, channel: QuestionChannel) -> None:
        self.channel = channel
        self.seen: list[tuple[str, QuestionRequest]] = []
        self.arrived = threading.Event()

    def notify(self, request_id: str, request: QuestionRequest) -> None:
        self.seen.append((request_id, request))
        self.arrived.set()

    def answer_with(self, answer: str) -> bool:
        assert self.arrived.wait(2), "물음이 UI까지 오지 않았다"
        return self.channel.resolve(self.seen[-1][0], answer=answer)


@pytest.fixture()
def channel() -> QuestionChannel:
    return QuestionChannel(timeout_seconds=2.0)


def _ask_in_background(channel: QuestionChannel, request=_ASK) -> list:
    box: list = []
    thread = threading.Thread(target=lambda: box.append(channel.ask(request)))
    thread.start()
    return [thread, box]


class TestTheAnswerIsText:
    def test_the_words_the_user_chose_come_back(self, channel: QuestionChannel):
        # [HARD] 이 한 줄이 실물 사고 전부다 — True가 오면 도구는 답을 못 알아본다.
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, box = _ask_in_background(channel)

        assert recorder.answer_with("콘솔에서 직접 고르겠다") is True
        thread.join(2)

        assert box == ["콘솔에서 직접 고르겠다"]

    def test_a_freeform_answer_survives_intact(self, channel: QuestionChannel):
        # 선택지에 없는 사정을 적는 경우가 실물에서 흔하다.
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, box = _ask_in_background(channel)
        recorder.answer_with("Sharpy 250W Beam으로 6대, FID 201부터")
        thread.join(2)

        assert box == ["Sharpy 250W Beam으로 6대, FID 201부터"]

    def test_the_question_reaches_the_ui_whole(self, channel: QuestionChannel):
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, _ = _ask_in_background(channel)
        recorder.answer_with("x")
        thread.join(2)

        _request_id, seen = recorder.seen[0]
        assert seen.steps == _ASK.steps
        assert seen.prompt == _ASK.prompt


class TestNotAnsweringIsNotDenying:
    def test_a_timeout_reads_as_unanswered(self):
        channel = QuestionChannel(timeout_seconds=0.05)
        channel.bind(lambda request_id, request: None)

        assert channel.ask(_ASK) == UNANSWERED

    def test_a_disconnect_releases_the_waiter(self, channel: QuestionChannel):
        # [HARD] 연결이 끊겼는데 계속 붙잡고 있으면 대화가 통째로 멈춘다.
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, box = _ask_in_background(channel)
        assert recorder.arrived.wait(2)

        channel.unbind()
        thread.join(2)

        assert box == [UNANSWERED]
        assert not thread.is_alive()

    def test_asking_with_nobody_watching_does_not_hang(self, channel: QuestionChannel):
        # 아무도 안 보는 물음을 600초 붙잡으면 배치 경로가 죽는다.
        assert channel.ask(_ASK) == UNANSWERED

    def test_a_publisher_that_raises_does_not_hang(self, channel: QuestionChannel):
        def broken(request_id: str, request: QuestionRequest) -> None:
            raise RuntimeError("소켓이 죽었다")

        channel.bind(broken)

        assert channel.ask(_ASK) == UNANSWERED


class TestResolvingOnce:
    def test_an_unknown_id_is_refused(self, channel: QuestionChannel):
        assert channel.resolve("question-999", answer="아무거나") is False

    def test_a_second_answer_is_refused(self, channel: QuestionChannel):
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, box = _ask_in_background(channel)
        request_id = (recorder.arrived.wait(2), recorder.seen[-1][0])[1]

        assert channel.resolve(request_id, answer="첫 답") is True
        thread.join(2)

        assert channel.resolve(request_id, answer="늦은 답") is False
        assert box == ["첫 답"]

    def test_ids_do_not_repeat(self, channel: QuestionChannel):
        # 같은 id가 두 번 나오면 늦은 답이 엉뚱한 물음을 푼다.
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        for index in range(3):
            recorder.arrived.clear()
            thread, _ = _ask_in_background(channel)
            assert recorder.answer_with(f"답{index}") is True
            thread.join(2)

        ids = [request_id for request_id, _ in recorder.seen]
        assert len(set(ids)) == 3


class TestSessions:
    def test_one_session_disconnecting_leaves_another_waiting(self):
        channel = QuestionChannel(timeout_seconds=2.0)
        seen: dict[str, str] = {}
        channel.bind(lambda rid, req: seen.__setitem__("a", rid), session_key="a")
        channel.bind(lambda rid, req: seen.__setitem__("b", rid), session_key="b")

        box: list = []
        thread = threading.Thread(target=lambda: box.append(channel.ask(_ASK, session_key="b")))
        thread.start()
        while "b" not in seen:
            pass

        channel.unbind(session_key="a")
        assert channel.resolve(seen["b"], answer="b의 답") is True
        thread.join(2)

        assert box == ["b의 답"]

    def test_it_finds_the_ui_bound_to_the_current_turn(self):
        """[HARD] 세션 키를 상수로 박으면 카드가 **아예 안 뜬다.**

        실측: `ask()`가 `DEFAULT_SESSION_KEY`로 찾는데 UI는 실제 세션 키로
        바인딩되어 있었다. 붙어 있는 UI를 못 찾아 즉시 미응답이 났고, 사용자는
        질문 한 번 못 받은 채 "응답을 받지 못했습니다"만 읽었다.
        """
        from server.safety.session_context import (
            SessionKey,
            bind_session_key,
            reset_session_key,
        )

        channel = QuestionChannel(timeout_seconds=1.0)
        key = SessionKey("turn-7")
        recorder = Recorder(channel)
        channel.bind(recorder.notify, session_key=key)

        box: list = []

        def run() -> None:
            token = bind_session_key(key)
            try:
                box.append(channel.ask(_ASK))
            finally:
                reset_session_key(token)

        thread = threading.Thread(target=run)
        thread.start()
        assert recorder.answer_with("붙어 있는 UI로 갔다") is True
        thread.join(2)

        assert box == ["붙어 있는 UI로 갔다"]

    def test_a_question_goes_only_to_its_own_session(self):
        channel = QuestionChannel(timeout_seconds=1.0)
        reached: list[str] = []
        channel.bind(lambda rid, req: reached.append("a"), session_key="a")
        channel.bind(lambda rid, req: reached.append("b"), session_key="b")

        channel.ask(_ASK, session_key="b")

        assert reached == ["b"]


class TestMultiSelect:
    """한 문장이 여러 계열을 지정하는 물음 — **하나만 받고 나머지를 버리지 않는다.**

    실측: «포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을 설정해줘»가 단일 선택
    카드를 만나면 그중 하나만 답이 되고 나머지 계열은 조용히 사라진다. ``multi``는
    카드 개수가 아니라 답 하나의 **모양**을 넓히는 필드다 — UI가 체크박스 + 「확인」으로
    렌더하고, 고른 라벨을 ``", "``로 이어 하나의 답으로 보낸다.
    """

    def test_it_defaults_to_single_select(self):
        """기본값이 참으로 새면 기존 카드 전부가 「확인」을 한 번 더 요구하게 된다."""
        assert QuestionRequest(prompt="무엇을 할까요?").multi is False
        assert _ASK.to_dict()["multi"] is False

    def test_the_default_payload_keeps_every_pre_existing_field(self):
        """additive여야 한다 — 구버전 UI가 읽던 키를 하나도 바꾸지 않는다."""
        payload = _ASK.to_dict()

        assert payload == {
            "prompt": _ASK.prompt,
            "why": _ASK.why,
            "steps": list(_ASK.steps),
            "commands": [],
            # `selected`는 additive다 — 기본값 False라 단일 선택 카드의 뜻은 그대로다.
            "options": [{"label": "콘솔에서 직접 고르겠다", "description": "", "selected": False}],
            "multi": False,
        }

    def test_it_serializes_multi_for_the_ui(self):
        request = QuestionRequest(
            prompt="어느 계열을 설정할까요?",
            options=(
                QuestionOption(label="기본 포지션 프리셋"),
                QuestionOption(label="기본 컬러 프리셋"),
            ),
            multi=True,
        )

        assert request.to_dict()["multi"] is True

    def test_the_wire_event_carries_multi(self):
        """``to_dict()``가 맞아도 이벤트가 떨어뜨리면 UI는 단일 선택으로 렌더한다."""
        from server.web.messages import question_request_event

        event = question_request_event(
            request_id="q9",
            request=QuestionRequest(prompt="어느 계열을?", multi=True),
        )

        assert event["multi"] is True
        assert event["type"] == "question_request"

    def test_the_channel_returns_the_joined_answer_verbatim(self):
        """콤마+공백 결합은 **답 형식**이다 — 통로는 그것을 다듬지 않는다."""
        channel = QuestionChannel(timeout_seconds=2.0)
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        request = QuestionRequest(
            prompt="어느 계열을 설정할까요?",
            options=(
                QuestionOption(label="기본 포지션 프리셋"),
                QuestionOption(label="기본 컬러 프리셋"),
            ),
            multi=True,
        )
        thread, box = _ask_in_background(channel, request)

        assert recorder.answer_with("기본 포지션 프리셋, 기본 컬러 프리셋") is True
        thread.join(2)

        assert box == ["기본 포지션 프리셋, 기본 컬러 프리셋"]
        assert recorder.seen[-1][1].multi is True
