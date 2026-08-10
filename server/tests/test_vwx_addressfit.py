"""주소가 겹치면 **묻고 새 자리를 받아 이어간다.**

[round24 후속] 실측: `claypaky sharpy 250 6대를 3.001부터 패치해줘`에 앱은 3.001이
이미 찬 것을 정확히 찾아냈다. 그러고는 산문으로 "결정해 주세요"라고 쓰고 턴을
끝냈다 — 사용자는 처음부터 다시 쳐야 했고, 그때 앱은 원래 과제를 잊은 뒤였다.
없는 픽스처 타입 때와 **같은 실수**다.

여기서는 "충돌을 찾았는가"가 아니라 **"찾은 다음 대화가 이어지는가"**를 본다.
"""

from __future__ import annotations

import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import (
    ANSWER_CANCEL,
    ANSWER_TYPE_ADDRESS,
    ANSWER_USE_SUGGESTED,
    build_toolset,
)
from server.vwx.addressfit import Occupant, evaluate, first_free
from server.web.question import UNANSWERED

#: 실측 리그를 본뜬 자리 — 유니버스 3에 16채널 간격으로 20대.
_CROWDED = tuple(
    Occupant(universe=3, address=1 + index * 16, name=f"RLB350M1 {index + 1}")
    for index in range(20)
)


class TestTheVerdict:
    def test_a_crowded_span_is_refused(self):
        fit = evaluate("3.001", count=6, width=14, occupants=_CROWDED)

        assert fit.ok is False
        assert fit.collisions

    def test_an_empty_universe_is_accepted(self):
        fit = evaluate("9.1", count=6, width=14, occupants=_CROWDED)

        assert fit.ok is True
        assert [spot.text for spot in fit.placements] == [
            "9.1",
            "9.15",
            "9.29",
            "9.43",
            "9.57",
            "9.71",
        ]

    def test_the_span_covers_every_channel_it_takes(self):
        # [HARD] 마지막 장비의 꼬리를 빼먹으면 그 뒤 장비와 겹친 채로 통과한다.
        fit = evaluate("9.1", count=2, width=14, occupants=())

        assert fit.span_text == "9.1 ~ 9.28"

    def test_a_fixture_starting_inside_the_span_is_a_collision(self):
        # 폭을 몰라도 확정인 축 — 남의 시작점이 내 구간 안에 있다.
        fit = evaluate("5.1", count=1, width=14, occupants=(Occupant(universe=5, address=10),))

        assert fit.ok is False

    def test_a_fixture_just_past_the_span_is_not(self):
        fit = evaluate("5.1", count=1, width=14, occupants=(Occupant(universe=5, address=15),))

        assert fit.ok is True

    def test_another_universe_is_not_a_collision(self):
        fit = evaluate("5.1", count=1, width=14, occupants=(Occupant(universe=6, address=1),))

        assert fit.ok is True

    def test_an_unreadable_address_is_refused_not_guessed(self):
        # [HARD] 못 읽은 주소를 1.1로 채우면 엉뚱한 자리를 검사하고 통과시킨다.
        fit = evaluate("셋점일", count=1, width=14, occupants=())

        assert fit.ok is False
        assert fit.error

    def test_an_unknown_width_is_refused(self):
        fit = evaluate("1.1", count=1, width=0, occupants=())

        assert fit.ok is False
        assert "채널 폭" in (fit.error or "")

    def test_the_blind_spot_is_always_stated(self):
        # [HARD] 못 보는 축을 안 적으면 "충돌 없음"이 안전 확정으로 읽힌다.
        assert "믿을 수 없다" in evaluate("9.1", count=1, width=14, occupants=()).blind_spot


class TestTheSuggestion:
    def test_it_finds_an_empty_universe(self):
        found = first_free(count=6, width=14, occupants=_CROWDED)

        assert found is not None
        assert found.ok is True
        assert found.requested.endswith(".1")

    def test_it_never_suggests_an_occupied_universe(self):
        found = first_free(count=6, width=14, occupants=_CROWDED)

        assert found is not None
        assert not found.requested.startswith("3.")

    def test_nowhere_to_go_is_reported_as_such(self):
        # 자리가 없으면 없다고 해야 한다 — 아무 데나 제안하면 남의 장비를 덮는다.
        packed = tuple(Occupant(universe=u, address=1) for u in range(1, 40))
        assert first_free(count=1, width=14, occupants=packed, universes_to_scan=8) is None


class RecordingQuestionPort:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


class FakePorts:
    """콘솔 대신 정해진 픽스처 목록을 내는 포트."""

    def __init__(self, occupants) -> None:
        self.occupants = list(occupants)

    def query_state(self, path: str) -> dict:
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(self.occupants)},
            "children": [
                {"class": "Fixture", "i": index + 1, "name": occupant.name}
                for index, occupant in enumerate(self.occupants)
            ],
        }

    def query_property(self, path: str, property_name: str) -> dict:
        index = int(path.rsplit("/", 1)[-1]) - 1
        if not 0 <= index < len(self.occupants):
            return {"ok": False}
        occupant = self.occupants[index]
        value = {
            "Patch": f"{occupant.universe}.{occupant.address:03d}",
            "Name": occupant.name or "",
            "FixtureType": occupant.fixture_type or "RLB",
            "Mode": "Mode 0",
            "FID": str(index + 1),
        }.get(property_name)
        return {"ok": True, "value": value} if value is not None else {"ok": False}


def _resolve(question_port, *, address="3.001", count=6, width=14, occupants=_CROWDED):
    ports = FakePorts(occupants)
    registry = build_toolset(
        execution_port=None,
        state_port=ports,
        property_port=ports,
        question_port=question_port,
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="resolve_patch_address",
            arguments={
                "address": address,
                "count": count,
                "channels_per_fixture": width,
            },
        )
    )
    return json.loads(execution.result.content)


class TestItAsksInsteadOfNarrating:
    def test_a_clash_actually_reaches_the_user(self):
        # [HARD] 실측에서 앱은 충돌을 찾고도 산문만 쓰고 끝냈다.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        payload = _resolve(port)

        assert payload["status"] == "occupied"
        assert len(port.asked) == 1, "찾기만 하고 안 물으면 대화가 거기서 끊긴다"

    def test_the_question_names_what_it_would_have_hit(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(port)

        request = port.asked[0]
        assert "겹칩니다" in request.prompt
        assert any("겹치는 장비" in step for step in request.steps)

    def test_a_free_address_asks_nothing(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)
        payload = _resolve(port, address="9.1")

        assert port.asked == []
        assert payload["status"] == "free"


class TestTheAnswerContinuesTheWork:
    def test_taking_the_suggestion_settles_on_a_real_address(self):
        payload = _resolve(RecordingQuestionPort(ANSWER_USE_SUGGESTED))

        assert payload["status"] == "free"
        assert payload["address"] == payload["suggestion"]
        assert payload["placements"]

    def test_the_settled_result_tells_the_caller_to_proceed(self):
        # [HARD] 답을 받고도 "결정해 주세요"로 끝나면 고친 것이 없다.
        payload = _resolve(RecordingQuestionPort(ANSWER_USE_SUGGESTED))

        assert "다시 묻지 마라" in payload["guidance"]

    def test_a_typed_address_is_accepted_when_it_is_free(self):
        payload = _resolve(RecordingQuestionPort("9.1"))

        assert payload["status"] == "free"
        assert payload["address"] == "9.1"

    def test_a_typed_address_is_rechecked_not_trusted(self):
        # [HARD] 사용자가 준 자리도 겹칠 수 있다. 확인 없이 받으면 이 도구가
        # 존재할 이유가 사라진다.
        payload = _resolve(RecordingQuestionPort("3.017"))

        assert payload["status"] == "still_occupied"
        assert "겹친 채로 진행하지 마라" in payload["guidance"]

    def test_an_unreadable_typed_address_is_not_repaired(self):
        payload = _resolve(RecordingQuestionPort("사번 유니버스"))

        assert payload["status"] == "unreadable_answer"
        assert "임의로 고쳐 쓰지 마라" in payload["guidance"]

    def test_cancelling_ends_it(self):
        payload = _resolve(RecordingQuestionPort(ANSWER_CANCEL))

        assert payload["answer"] == ANSWER_CANCEL
        assert "끝내라" in payload["guidance"]

    def test_no_answer_is_never_turned_into_an_address(self):
        payload = _resolve(RecordingQuestionPort(UNANSWERED))

        assert payload["answer"] is None
        assert payload["status"] == "occupied"
        assert "지어내지 말고" in payload["guidance"]


class TestTheOfferedAnswersAreHandled:
    def test_the_labels_offered_are_the_labels_compared(self):
        # [HARD] 표시 문구와 판정 상수가 어긋나면 무엇을 골라도 조용히 아무 일도
        # 일어나지 않는다.
        port = RecordingQuestionPort(ANSWER_CANCEL)
        _resolve(port)

        offered = {option.label for option in port.asked[0].options}
        assert offered == {ANSWER_USE_SUGGESTED, ANSWER_TYPE_ADDRESS, ANSWER_CANCEL}

    @pytest.mark.parametrize("label", [ANSWER_USE_SUGGESTED, ANSWER_CANCEL])
    def test_every_offered_answer_reaches_a_verdict(self, label):
        payload = _resolve(RecordingQuestionPort(label))

        assert payload["guidance"]
        assert payload["status"] in {"free", "occupied", "still_occupied"}


class TestWhatItRefusesToDo:
    def test_a_guessed_width_is_refused(self):
        ports = FakePorts(_CROWDED)
        registry = build_toolset(
            execution_port=None, state_port=ports, property_port=ports, question_port=None
        )
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="resolve_patch_address",
                arguments={"address": "3.001", "count": 6},
            )
        )

        assert execution.result.is_error
        assert "추측하지 마라" in execution.result.content

    def test_without_a_question_channel_it_still_refuses_to_patch(self):
        payload = _resolve(None)

        assert payload["status"] == "occupied"
        assert "명령을 보내지 마라" in payload["guidance"]

    def test_the_blind_spot_travels_with_every_verdict(self):
        for address in ("3.001", "9.1"):
            payload = _resolve(RecordingQuestionPort(ANSWER_CANCEL), address=address)
            assert payload["blind_spot"]
