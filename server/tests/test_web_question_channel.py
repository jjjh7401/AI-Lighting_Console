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

    def test_a_disconnect_alone_does_not_decide_the_answer(self):
        """[HARD] 새로고침은 거절이 아니다 (t316).

        예전에는 ``unbind`` 가 곧바로 :data:`UNANSWERED` 를 냈다. 그러면 감독이
        답하려던 물음이 새로고침 한 번에 「답하지 않았다」로 **확정**되고, 그
        확정은 되돌릴 수 없다. 이제는 세워 두고, 상한이 그 기다림을 끝낸다 —
        아래 두 단언이 각각 그 절반이다.
        """
        channel = QuestionChannel(timeout_seconds=1.0)
        recorder = Recorder(channel)
        channel.bind(recorder.notify)
        thread, box = _ask_in_background(channel)
        assert recorder.arrived.wait(2)

        channel.unbind()
        # ① 끊겼다고 즉시 결정되지 않는다.
        thread.join(0.2)
        assert box == []
        # ② 그래도 무한히 붙잡지는 않는다 — 상한이 끝낸다.
        thread.join(3)
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


class TestASurvivedReload:
    """새로고침 한 번에 물음이 사라지지 않는가 (t316).

    실측 결함: 디자인 인터뷰 첫 카드가 뜬 상태에서 앱을 다시 열면
    ``button.question-option`` 이 3 → 0 이 됐다. 화면에서는 카드가 없고, 서버는
    답을 기다리는 중 — 감독의 세션이 통째로 막힌 채 아무 신호도 남지 않는다.
    """

    def test_the_card_comes_back_on_the_next_connection(self):
        # [HARD] 오늘 코드에서 실패한다: 예전 ``unbind`` 는 여기서 답을
        # UNANSWERED 로 확정해 버려, 되살릴 물음 자체가 남지 않았다.
        channel = QuestionChannel(timeout_seconds=5.0)
        first = Recorder(channel)
        channel.bind(first.notify, session_key="tab-1")

        box: list = []
        thread = threading.Thread(target=lambda: box.append(channel.ask(_ASK, session_key="tab-1")))
        thread.start()
        assert first.arrived.wait(2)
        request_id = first.seen[-1][0]

        # 새로고침: 옛 연결이 끊기고 새 연결이 붙는다(새 세션 키).
        channel.unbind(session_key="tab-1")
        second = Recorder(channel)
        channel.bind(second.notify, session_key="tab-2")

        assert [rid for rid, _ in second.seen] == [request_id]
        restored = second.seen[-1][1]
        assert restored.prompt == _ASK.prompt
        assert [option.label for option in restored.options] == [
            option.label for option in _ASK.options
        ]

        # 그리고 되살아난 카드는 실제로 답할 수 있다.
        assert channel.resolve(request_id, answer="콘솔에서 직접 고르겠다") is True
        thread.join(3)
        assert box == ["콘솔에서 직접 고르겠다"]

    def test_a_restored_card_answered_twice_is_refused(self):
        """중복 답은 **거절**이다 — 멱등이 아니라.

        두 번째 답을 조용히 받아들이면 감독은 자기 답이 반영됐다고 읽지만
        실제로는 아무것도 바뀌지 않는다. 거절은 UI 가 ``stale_question`` 으로
        말해 줄 수 있는 유일한 형태다(app.py ``question_answer`` 분기).
        """
        channel = QuestionChannel(timeout_seconds=5.0)
        first = Recorder(channel)
        channel.bind(first.notify, session_key="tab-1")

        box: list = []
        thread = threading.Thread(target=lambda: box.append(channel.ask(_ASK, session_key="tab-1")))
        thread.start()
        assert first.arrived.wait(2)
        request_id = first.seen[-1][0]

        # 새로고침 — 옛 탭은 그대로 열려 있고 새 탭이 같은 카드를 되받는다.
        second = Recorder(channel)
        channel.bind(second.notify, session_key="tab-2")
        assert [rid for rid, _ in second.seen] == [request_id]

        # 새 탭에서 답한다.
        assert channel.resolve(request_id, answer="새 탭의 답") is True
        thread.join(3)
        assert box == ["새 탭의 답"]

        # 옛 탭에 남아 있던 같은 카드를 눌러도 **덮어쓰지 않는다** — 거절이다.
        assert channel.resolve(request_id, answer="옛 탭의 늦은 답") is False

    def test_a_question_already_answered_is_not_asked_again(self):
        """[HARD] 다른 탭에서 이미 답한 물음을 되살리면 끝난 것을 다시 묻는다."""
        channel = QuestionChannel(timeout_seconds=5.0)
        first = Recorder(channel)
        channel.bind(first.notify, session_key="tab-1")

        box: list = []
        thread = threading.Thread(target=lambda: box.append(channel.ask(_ASK, session_key="tab-1")))
        thread.start()
        assert first.arrived.wait(2)
        request_id = first.seen[-1][0]

        assert channel.resolve(request_id, answer="이미 답했다") is True
        thread.join(3)
        assert box == ["이미 답했다"]

        second = Recorder(channel)
        channel.bind(second.notify, session_key="tab-2")
        assert second.seen == []
        # 두 번째 답은 거절된다 — 되살아난 카드를 다시 눌러도 마찬가지다.
        assert channel.resolve(request_id, answer="두 번째 답") is False

    def test_the_next_card_of_a_parked_interview_still_reaches_a_ui(self):
        """되살린 다음이 더 중요하다 — Q2 가 죽은 자리로 가면 인터뷰가 멈춘다.

        인터뷰는 카드를 **한 장씩** 묻는다(``_song_run_interview``). Q1 을
        되살려 답을 받아도 Q2 가 갈 곳이 없으면 감독의 화면은 그대로 빈다.
        """
        channel = QuestionChannel(timeout_seconds=5.0)
        first = Recorder(channel)
        channel.bind(first.notify, session_key="tab-1")

        answers: list = []

        def interview() -> None:
            answers.append(channel.ask(_ASK, session_key="tab-1"))
            answers.append(channel.ask(_ASK, session_key="tab-1"))

        thread = threading.Thread(target=interview)
        thread.start()
        assert first.arrived.wait(2)
        q1 = first.seen[-1][0]

        channel.unbind(session_key="tab-1")
        second = Recorder(channel)
        # 새 연결이 붙을 때 앱은 옛 세션의 보내는 자리도 살아 있는 소켓으로
        # 되돌린다(app.py ``live_target``). 여기서는 그 결과를 그대로 흉내낸다.
        channel.bind(second.notify, session_key="tab-2")
        assert [rid for rid, _ in second.seen] == [q1]

        first.arrived.clear()
        assert channel.resolve(q1, answer="Q1 답") is True
        # Q2 는 옛 세션이 묻지만, 보내는 자리가 살아 있어 화면에 닿는다.
        assert first.arrived.wait(2)
        assert len(first.seen) == 2
        q2 = first.seen[-1][0]
        assert q2 != q1
        assert channel.resolve(q2, answer="Q2 답") is True
        thread.join(3)
        assert answers == ["Q1 답", "Q2 답"]
