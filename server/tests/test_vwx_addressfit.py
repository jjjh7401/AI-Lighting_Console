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
from server.vwx.addressfit import Occupant, Placement, evaluate, first_free
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


class TestTheRequestedAddressIsNeverMovedSilently:
    """[t15 HIGH-1] 요청받은 첫 자리를 말없이 다른 유니버스로 옮기지 않는다.

    실측: `evaluate("1.500", count=1, width=32)` 가 `ok=True` 로 `2.1` 을 냈다.
    폭이 CSV `Ch` 보다 넓어지는 것은 `mode_overrides` 에서 정상인데, 512 천장을
    보는 유일한 거부(파서)는 CSV 폭으로만 돌아 그 사이가 무검사였다.

    여기서 만드는 것은 **새 천장이 아니다**. `UNIVERSE_CHANNELS` 주석대로 큰 주소를
    거절하지는 않는다. 금지하는 것은 *바꿔치기* 다 — 요청받은 자리에 실측 폭이 안
    들어가면 옮기지 말고 그대로 두고 사실을 말한다. 판단은 부르는 쪽 몫이다.
    """

    def test_a_first_placement_that_overruns_is_not_relocated(self):
        fit = evaluate("1.500", count=1, width=32, occupants=())

        assert fit.ok is False
        assert fit.placements[0] == Placement(universe=1, address=500)
        assert fit.error

    def test_the_width_that_fits_is_untouched(self):
        fit = evaluate("1.500", count=1, width=8, occupants=())

        assert fit.ok is True
        assert fit.placements == (Placement(universe=1, address=500),)
        assert fit.error is None

    def test_an_address_already_past_the_ceiling_is_refused_but_not_moved(self):
        """이름이 약속하는 것을 **전부** 단언한다 — 자리와 판정 둘 다.

        이전 이름(`..._keeps_its_address`)은 자리만 봤다. 그러면 `ok` 가 무엇이든
        통과해서, ASSUMPTION-33 트립와이어처럼 읽히지만 실제로는 아무 판정도
        지키지 않는다(t15 리뷰 MED-1).
        """
        fit = evaluate("1.513", count=1, width=8, occupants=())

        assert fit.placements[0].universe == 1
        assert fit.placements[0].address == 513
        assert fit.ok is False
        assert fit.error

    def test_a_single_channel_high_up_is_also_refused(self):
        """폭 1채널짜리도 끝을 넘으면 거절이다 — 옮길 뒷자리가 없어도 마찬가지다.

        이 단언이 이 변경의 정직한 얼굴이다: 「옮기기를 막는 것」이라 설명했지만
        여기에는 옮길 일이 애초에 없다. 그런데도 거절한다 — 512 를 넘는 채널은
        유니버스에 존재하지 않기 때문이다. 감독 결정으로 유지한다(t15).
        """
        fit = evaluate("1.600", count=1, width=1, occupants=())

        assert fit.ok is False
        assert fit.placements[0].address == 600

    def test_an_occupant_inside_the_true_span_is_seen(self):
        """[거짓 음성] 감긴 뒤의 자리로 검사하면 진짜 발자국 안의 장비를 놓친다."""
        squatter = Occupant(universe=1, address=505, name="이미 여기 있음")

        fit = evaluate("1.500", count=1, width=32, occupants=(squatter,))

        assert squatter in fit.collisions

    def test_an_occupant_in_another_universe_is_not_claimed_as_a_clash(self):
        """[거짓 양성] 감긴 자리로 검사하면 남의 유니버스 장비를 겹친다고 한다."""
        elsewhere = Occupant(universe=2, address=1, name="다른 선반")

        fit = evaluate("1.500", count=1, width=32, occupants=(elsewhere,))

        assert elsewhere not in fit.collisions

    def test_a_continuation_still_crosses_into_the_next_universe(self):
        """여럿을 이어 깔 때의 선반 넘김은 **원래 설계된 동작**이라 그대로 둔다.

        고친 것은 첫 자리뿐이다. 이어 붙일 앞자리가 있는 두 번째부터는 넘기는 것이
        맞다 — 이 단언은 그 구분이 지켜지는지를 본다(첫 자리는 요청대로, 뒤는 이어서).
        """
        fit = evaluate("1.500", count=3, width=8, occupants=())

        assert fit.placements[0] == Placement(universe=1, address=500)
        assert fit.placements[1].universe == 2
        assert fit.placements[1].address == 1

    def test_a_run_that_never_reaches_the_end_stays_in_one_universe(self):
        fit = evaluate("1.1", count=3, width=8, occupants=())

        assert [p.universe for p in fit.placements] == [1, 1, 1]

    def test_the_last_channel_of_the_universe_is_usable(self):
        """경계를 양쪽에서 못 박는다 — 512 는 **쓸 수 있는** 마지막 칸이다.

        `505 + 8 - 1 = 512`. 여기서 거절하면 콘솔이 받는 자리를 서버가 막는 것이라
        ASSUMPTION-33 위반이다. 이 단언이 없으면 `>` 를 `>=` 로 바꿔도 아무도 모른다.
        """
        fit = evaluate("1.505", count=1, width=8, occupants=())

        assert fit.ok is True
        assert fit.error is None
        assert fit.placements == (Placement(universe=1, address=505),)

    def test_one_channel_past_the_end_is_refused(self):
        """반대쪽 못 — `506 + 8 - 1 = 513` 은 한 칸 넘는다. 옮기지 않고 사실을 낸다."""
        fit = evaluate("1.506", count=1, width=8, occupants=())

        assert fit.ok is False
        assert fit.placements[0] == Placement(universe=1, address=506)
        assert "513" in (fit.error or "")

    def test_a_width_that_exactly_fills_the_universe_is_usable(self):
        """`1.1` 에 512채널 — 유니버스를 꽉 채운다. 넘지 않았으므로 통과다."""
        fit = evaluate("1.1", count=1, width=512, occupants=())

        assert fit.ok is True
        assert fit.placements == (Placement(universe=1, address=1),)


class TestAnOverrunAsksInsteadOfErroring:
    """t15 리뷰 HIGH-1. 폭이 안 들어가는 것과 주소를 못 읽는 것은 다른 일이다.

    처음 고쳤을 때 초과 판정이 `fit.error` 를 세웠고, 그 앞의 「error 면
    unreadable_request 로 즉시 반환」 분기에 걸렸다. 결과가 셋 다 틀렸다 —
    멀쩡히 읽힌 주소에 「못 읽었다」 라벨, 질문카드 0개, `is_error=True`.
    이 모듈이 생긴 이유가 「산문으로 묻고 턴을 끝내면 사용자가 처음부터 다시
    친다」였는데 그 실수를 되살린 것이다.
    """

    def test_it_is_not_filed_as_an_unreadable_address(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)

        payload = _resolve(port, address="1.500", count=1, width=20, occupants=())

        assert payload["status"] == "does_not_fit"
        assert payload["status"] != "unreadable_request"

    def test_it_actually_asks_the_user(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)

        _resolve(port, address="1.500", count=1, width=20, occupants=())

        assert len(port.asked) == 1

    def test_it_does_not_blame_an_occupant_that_does_not_exist(self):
        port = RecordingQuestionPort(ANSWER_CANCEL)

        payload = _resolve(port, address="1.500", count=1, width=20, occupants=())

        assert payload["collisions"] == []
        assert payload["reason"]

    def test_a_genuinely_unreadable_address_still_says_so(self):
        """대조군 — 이 갈래까지 같이 옮기면 진짜 파싱 실패가 질문카드로 샌다."""
        port = RecordingQuestionPort(ANSWER_CANCEL)

        payload = _resolve(port, address="세 점 일", count=1, width=8, occupants=())

        assert payload["status"] == "unreadable_request"
        assert port.asked == []
