"""라이브러리에 없는 타입을 만났을 때 — **도구가 직접 묻고, 기다리고, 잇는가.**

[round24 후속] 앞선 판은 모델에게 "ask_user를 불러라"고 **지시**했다. 실측 전사에서
모델은 그 지시를 산문으로 옮겨 적고 턴을 끝냈다 — 질문 카드는 뜨지 않았고, 사용자가
나중에 "선택했어"라고 하자 그때는 원래 과제(6대 패치)를 잊은 뒤였다.

그래서 지시를 검사하지 않는다. **구멍을 발견한 자리가 실제로 물었는가**, 답을 받은 뒤
**라이브러리 변화를 감지해 원래 과제로 이어지는가**만 본다.
"""

from __future__ import annotations

import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import (
    ANSWER_CANCEL,
    ANSWER_PICK_ON_CONSOLE,
    ANSWER_SUPPLY_FILE,
    build_toolset,
)
from server.vwx.typemap import FIXTURE_TYPE_LIBRARY_ROOT
from server.web.question import UNANSWERED

_PRESENT = ("Robin MMX Spot", "Robin LEDBeam 350")


def _tree(names):
    return {
        "ok": True,
        "path": FIXTURE_TYPE_LIBRARY_ROOT,
        "truncated": False,
        "node": {"childCount": len(names)},
        "children": [
            {"class": "FixtureType", "i": index + 1, "name": name}
            for index, name in enumerate(names)
        ],
    }


class RollingStatePort:
    """읽을 때마다 다음 장면을 내는 상태 포트 — 사용자가 콘솔 앞에서 고르는 흐름."""

    def __init__(self, *scenes: tuple[str, ...]) -> None:
        self._scenes = list(scenes)
        self.reads = 0

    def query_state(self, path: str) -> dict:
        self.reads += 1
        scene = self._scenes[min(self.reads - 1, len(self._scenes) - 1)]
        return _tree(scene)


class RecordingQuestionPort:
    """물어본 내용을 붙잡아 두고 정해진 답을 내는 질문 통로.

    **실물 `QuestionChannel`과 같은 이름·같은 반환형이어야 한다.** 앞선 판에서
    이 대역이 승인 브리지의 `request_approval`을 흉내 내며 문자열을 냈고, 실물은
    불리언을 냈다 — 테스트는 다 통과했는데 앱은 답을 못 알아봤다.
    """

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


def _resolve(state_port, question_port, requested="Clay Paky Sharpy"):
    registry = build_toolset(
        execution_port=None,
        state_port=state_port,
        question_port=question_port,
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="resolve_fixture_type",
            arguments={"instrument_type": requested},
        )
    )
    return json.loads(execution.result.content)


class TestItAsksInsteadOfNarrating:
    """**모델이 옮겨 적기를 기다리지 않는다** — 도구가 그 자리에서 묻는다."""

    def test_a_missing_type_actually_reaches_the_user(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)
        payload = _resolve(RollingStatePort(_PRESENT), port)

        assert payload["asked"] is True
        assert len(port.asked) == 1, "물었다고 하고 안 물으면 앞선 판과 똑같다"

    def test_the_question_carries_the_console_steps(self):
        # 절차 없이 "라이브러리에 없다"만 오면 사용자는 무엇을 할지 모른다.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(RollingStatePort(_PRESENT), port)

        request = port.asked[0]
        assert request.steps, "절차가 비면 카드가 아니라 오류 메시지다"
        assert any("Patch" in step for step in request.steps)

    def test_the_requested_name_is_in_the_question(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(RollingStatePort(_PRESENT), port, requested="Clay Paky Sharpy")

        assert "Clay Paky Sharpy" in port.asked[0].prompt

    def test_a_present_type_asks_nothing(self):
        # 있는 타입까지 물으면 통로가 소음이 된다.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        payload = _resolve(RollingStatePort(_PRESENT), port, requested="Robin MMX Spot")

        assert port.asked == []
        assert payload.get("asked") is not True
        assert payload["status"] == "present"


class TestItWaitsForTheConsole:
    """「고르겠다」를 받으면 **그 자리에서 기다린다** — 다음 메시지를 기다리지 않는다."""

    def test_a_type_that_appears_is_detected_and_named(self, monkeypatch):
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        state = RollingStatePort(_PRESENT, _PRESENT, (*_PRESENT, "Sharpy 250W Beam"))
        payload = _resolve(state, RecordingQuestionPort(ANSWER_PICK_ON_CONSOLE))

        assert payload["added"] == ["Sharpy 250W Beam"]
        assert payload["resolved"] == "Sharpy 250W Beam"

    def test_the_status_flips_so_the_caller_can_proceed(self, monkeypatch):
        # [HARD] status가 absent로 남으면 모델은 "아직 없다"고 읽고 멈춘다 —
        # 사용자는 방금 넣었는데. 이어가려면 판정 자체가 바뀌어야 한다.
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        state = RollingStatePort(_PRESENT, (*_PRESENT, "Sharpy 250W Beam"))
        payload = _resolve(state, RecordingQuestionPort(ANSWER_PICK_ON_CONSOLE))

        assert payload["status"] == "present"

    def test_the_user_picking_a_different_name_is_taken_as_given(self, monkeypatch):
        # 실측: 'Clay Paky Sharpy'를 청했는데 콘솔에는 'Sharpy 250W Beam'이 들어왔다.
        # 이름이 다르다고 되물으면 안 된다 — 실물을 아는 쪽은 사용자다.
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        state = RollingStatePort(_PRESENT, (*_PRESENT, "Sharpy 250W Beam"))
        payload = _resolve(state, RecordingQuestionPort(ANSWER_PICK_ON_CONSOLE))

        assert payload["resolved"] == "Sharpy 250W Beam"
        assert "되묻지" in payload["guidance"]

    def test_nothing_appearing_is_not_reported_as_success(self, monkeypatch):
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        payload = _resolve(
            RollingStatePort(_PRESENT), RecordingQuestionPort(ANSWER_PICK_ON_CONSOLE)
        )

        assert payload["added"] == []
        assert payload["status"] == "absent"

    def test_waiting_actually_polls_more_than_once(self, monkeypatch):
        # 한 번 보고 포기하면 사용자가 고를 시간이 없다.
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        state = RollingStatePort(_PRESENT)
        _resolve(state, RecordingQuestionPort(ANSWER_PICK_ON_CONSOLE))

        assert state.reads > 2


class TestTheOtherAnswers:
    def test_supplying_a_file_does_not_start_waiting(self, monkeypatch):
        # 파일을 주겠다는 답에 2분을 기다리면 대화가 멈춘 것처럼 보인다.
        calls: list[object] = []
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda s: calls.append(s))
        payload = _resolve(RollingStatePort(_PRESENT), RecordingQuestionPort(ANSWER_SUPPLY_FILE))

        assert calls == []
        assert "watch_state" not in payload

    def test_cancelling_ends_it(self):
        payload = _resolve(RollingStatePort(_PRESENT), RecordingQuestionPort(ANSWER_CANCEL))

        assert payload["answer"] == ANSWER_CANCEL
        assert "끝내라" in payload["guidance"]

    def test_no_answer_is_never_dressed_up_as_one(self):
        # [HARD] 미응답을 답으로 내면 모델이 지어낸 값으로 진행한다 — 이 통로가
        # 막으려던 바로 그 사고다.
        payload = _resolve(RollingStatePort(_PRESENT), RecordingQuestionPort(UNANSWERED))

        assert payload["answer"] is None
        assert payload["status"] == "absent"


class TestWithoutAQuestionChannel:
    def test_it_degrades_instead_of_crashing(self):
        # 질문 통로가 없는 실행 경로(배치·테스트)에서도 도구는 답을 내야 한다.
        payload = _resolve(RollingStatePort(_PRESENT), None)

        assert payload["asked"] is False
        assert payload["status"] == "absent"

    def test_it_still_refuses_to_send_commands(self):
        payload = _resolve(RollingStatePort(_PRESENT), None)

        assert "명령을 보내지 마라" in payload["guidance"]


class TestTheAnswersAreASharedVocabulary:
    def test_the_labels_offered_are_the_labels_compared(self):
        # [HARD] 표시 문구와 판정 상수가 어긋나면 사용자가 무엇을 골라도
        # 마지막 else로 떨어져 아무 일도 안 일어난다 — 조용히.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(RollingStatePort(_PRESENT), port)

        offered = {option.label for option in port.asked[0].options}
        assert offered == {ANSWER_PICK_ON_CONSOLE, ANSWER_SUPPLY_FILE, ANSWER_CANCEL}

    @pytest.mark.parametrize("label", [ANSWER_PICK_ON_CONSOLE, ANSWER_SUPPLY_FILE, ANSWER_CANCEL])
    def test_every_offered_answer_is_handled(self, label, monkeypatch):
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        payload = _resolve(RollingStatePort(_PRESENT), RecordingQuestionPort(label))

        assert payload["guidance"]
        assert "사용자 답:" not in payload["guidance"], (
            f"{label!r}이 아무 갈래에도 안 걸려 마지막 else로 떨어졌다"
        )


class TestAnAnswerIsADecision:
    """받은 답을 **참고**로 두면 모델이 산문으로 다시 묻는다 — 실측 그대로."""

    def _ask(self, answer):
        registry = build_toolset(
            execution_port=None,
            state_port=RollingStatePort(_PRESENT),
            question_port=RecordingQuestionPort(answer),
        )
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="ask_user",
                arguments={
                    "prompt": "어느 타입인가?",
                    "options": [{"label": "Sharpy 250W Beam 사용"}],
                },
            )
        )
        return json.loads(execution.result.content)

    def test_the_result_tells_the_caller_to_act(self):
        payload = self._ask("Sharpy 250W Beam 사용")

        assert payload["answered"] is True
        assert "다시 묻지 마라" in payload["guidance"]

    def test_the_chosen_answer_is_quoted_back(self):
        # 무엇으로 정해졌는지가 결과 안에 없으면 모델이 되짚을 근거가 없다.
        payload = self._ask("Sharpy 250W Beam 사용")

        assert "Sharpy 250W Beam 사용" in payload["guidance"]

    def test_no_answer_is_not_turned_into_a_decision(self):
        payload = self._ask(UNANSWERED)

        assert payload["answered"] is False
        assert "지어내지 말고" in payload["guidance"]
        assert "결정이다" not in payload["guidance"]


class TestThroughTheRealChannel:
    """**대역이 아니라 실물 통로로** 도구를 통과시킨다.

    [round24 후속] 이 파일의 대역은 처음에 승인 브리지의 `request_approval`을 흉내
    내며 문자열을 냈고, 실물은 불리언을 냈다. 대역만 보는 테스트는 21건 전부
    통과했지만 앱에서는 도구가 답을 못 알아봤다. 대역의 모양을 검사해도 같은
    함정에 다시 빠진다 — 그래서 여기서는 진짜 `QuestionChannel`을 꽂는다.
    """

    def _run(self, answer: str, state_port):
        import threading

        from server.web.question import QuestionChannel

        channel = QuestionChannel(timeout_seconds=5.0)
        seen: list[str] = []

        def notify(request_id: str, request) -> None:
            seen.append(request_id)
            # UI가 답하는 자리 — 통지 안에서 바로 풀면 교착이므로 딴 갈래로 보낸다.
            threading.Timer(0.01, lambda: channel.resolve(request_id, answer=answer)).start()

        channel.bind(notify)
        registry = build_toolset(execution_port=None, state_port=state_port, question_port=channel)
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="resolve_fixture_type",
                arguments={"instrument_type": "Clay Paky Sharpy"},
            )
        )
        return json.loads(execution.result.content), seen

    def test_the_chosen_words_reach_the_tool(self):
        # [HARD] 이 한 줄이 실물 사고를 잡는다 — 불리언이 오면 여기서 깨진다.
        payload, seen = self._run(ANSWER_CANCEL, RollingStatePort(_PRESENT))

        assert len(seen) == 1
        assert payload["answer"] == ANSWER_CANCEL

    def test_the_console_branch_is_actually_entered(self, monkeypatch):
        # 답을 못 알아보면 마지막 else로 떨어져 감시가 아예 안 돈다 — 실측 그대로.
        monkeypatch.setattr("server.orchestrator.tools.time.sleep", lambda _: None)
        state = RollingStatePort(_PRESENT, (*_PRESENT, "Sharpy 250W Beam"))
        payload, _ = self._run(ANSWER_PICK_ON_CONSOLE, state)

        assert payload["watch_state"], "감시가 돌지 않았다 — 답이 갈래에 안 걸렸다"
        assert payload["resolved"] == "Sharpy 250W Beam"


class TestTheWaitIsAnnounced:
    def test_the_card_says_how_long_it_will_watch(self):
        # 답한 뒤 2분간 아무 표시가 없으면 사용자는 고장으로 읽는다.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(RollingStatePort(_PRESENT), port)

        console = next(
            option for option in port.asked[0].options if option.label == ANSWER_PICK_ON_CONSOLE
        )
        assert "분간" in console.description
        assert "멈춘 것이 아닙니다" in console.description

    def test_the_announced_wait_matches_the_real_one(self):
        # [HARD] 안내한 시간과 실제 대기가 어긋나면 안내가 거짓말이 된다.
        from server.orchestrator.tools import (
            _SELECTION_WATCH_MINUTES,
            SELECTION_WATCH_ATTEMPTS,
            SELECTION_WATCH_INTERVAL_SECONDS,
        )

        real_minutes = SELECTION_WATCH_ATTEMPTS * SELECTION_WATCH_INTERVAL_SECONDS / 60
        assert abs(real_minutes - _SELECTION_WATCH_MINUTES) < 0.5
