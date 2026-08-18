"""`resolve_fixture_type` — 이름이 비슷하면 **묻고**, 없다고 단정하지 않는다.

실기 2026-08-18: 사용자가 «robe esprite 20대»를 요청했고 콘솔에는 «Robin Esprite»가
실재했는데, 도구가 "라이브러리에 없습니다"로 판정해 필요 없는 GUI 절차(Insert New
Fixture …)를 안내했다. 제조사 표기(Robe)와 콘솔 제품명(Robin …)이 다른 것은 실물에서
흔하다 — 그 자리는 부재가 아니라 **확인**이다.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.web.question import UNANSWERED

LIBRARY = (
    "Robin Esprite",
    "Robin Forte HP",
    "Robin LEDBeam 350",
    "Robin Spiider",
    "Xtylos",
    "Sharpy Plus",
)


class LibraryPort:
    """`Patch/FixtureTypes` 얕은 열거만 답하는 포트."""

    def __init__(self, names=LIBRARY) -> None:
        self.names = tuple(names)

    def query_state(self, path: str) -> dict:
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(self.names)},
            "children": [
                {"i": index + 1, "name": name, "class": "FixtureType"}
                for index, name in enumerate(self.names)
            ],
        }


class NoExec:
    """이 도구는 아무것도 실행하지 않는다 — 부르면 시험이 실패한다."""

    def execute(self, command: str):
        raise AssertionError(f"resolve_fixture_type이 명령을 실행했다: {command}")


class Picks:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


def _resolve(requested: str, *, question_port=None, names=LIBRARY):
    registry = build_toolset(
        execution_port=NoExec(),
        state_port=LibraryPort(names),
        question_port=question_port,
    )
    execution = registry.dispatch(
        ToolCall(
            id="r1",
            name="resolve_fixture_type",
            arguments={"instrument_type": requested},
        )
    )
    return json.loads(execution.result.content), execution


class TestTheManufacturerNameGap:
    def test_robe_esprite_resolves_to_robin_esprite_without_a_card(self):
        """[HARD] 그 사고의 처방 — 예전에는 status=absent로 GUI 절차를 안내했다.

        후보가 하나면 카드를 세우지 않는다: 다음 단계인 모드 선택 카드가 콘솔
        이름을 제목에 실어 보여 주므로, 확인 카드 두 장은 같은 것을 두 번 묻는다.
        """
        port = Picks("무엇이든")
        payload, _execution = _resolve("robe esprite", question_port=port)

        assert payload["status"] == "present"
        assert payload["resolved"] == "Robin Esprite"
        assert payload["matched_by"] == "name"
        assert port.asked == [], "후보가 하나인데 물었다 — 카드가 한 장 더 늘었다"

    def test_the_guidance_makes_the_model_name_the_type_it_used(self):
        # 조용히 다른 이름으로 진행하면 조명감독이 알 수 없다.
        payload, _execution = _resolve("robe esprite", question_port=Picks("x"))

        assert "Robin Esprite" in payload["guidance"]

    def test_an_exact_name_never_asks(self):
        port = Picks("Sharpy Plus")
        payload, _execution = _resolve("Sharpy Plus", question_port=port)

        assert payload["status"] == "present"
        assert port.asked == []

    def test_several_candidates_ask_which_one(self):
        # 'robin'은 네 제품에 공통 — 하나로 좁히지 않고 사용자가 고른다.
        port = Picks("Robin Spiider")
        payload, _execution = _resolve("robin 무빙", question_port=port)

        labels = [option.label for option in port.asked[0].options]
        assert labels[:4] == [
            "Robin Esprite",
            "Robin Forte HP",
            "Robin LEDBeam 350",
            "Robin Spiider",
        ]
        assert labels[-1] == "이 중에 없습니다"
        assert payload["resolved"] == "Robin Spiider"
        assert payload["confirmed_by_user"] is True


class TestItStillReportsARealAbsence:
    def test_an_unrelated_type_is_absent_with_the_console_procedure(self):
        payload, _execution = _resolve("Martin Mac Aura XB", question_port=Picks("x"))

        assert payload["status"] == "absent"
        assert payload["can_the_server_add_it"] is False

    def test_answering_not_in_the_list_falls_through_to_the_absence_path(self):
        # 후보를 보여 줬는데 사용자가 "이 중에 없다"면 라이브러리 추가 경로다.
        port = Picks("이 중에 없습니다")
        payload, _execution = _resolve("robin 무빙", question_port=port)

        assert payload["status"] == "absent"
        assert payload["candidates"][0] == "Robin Esprite"

    def test_an_unanswered_card_never_picks_a_candidate(self):
        port = Picks(UNANSWERED)
        payload, _execution = _resolve("robin 무빙", question_port=port)

        assert payload["status"] == "ambiguous"
        assert "resolved" not in payload
