"""라이브러리에 없는 타입을 **어떻게 올릴 것인가** — 막다른 길이 없는가.

지금까지 ``fixture_type_not_in_library``는 *"GDTF 라이브러리 임포트를 먼저 수행하라"*
는 문장 하나로 끝났다. 조작자는 무엇을·어디서·어디에·언제인지 듣지 못했다.

이 파일이 지키는 것은 넷이다.

1. **빈 계획을 내지 않는다.** 자동화 못 하는 갈래라도 사람이 밟을 길은 늘 있다.
2. **MVR이 답을 갖고 있으면 그것이 첫 갈래다.** 도면이 실제로 쓴 **그 버전**이라
   이름으로 검색해 받는 것보다 정확하다 — 그리고 파일이 지금 손에 있다.
3. **놓을 자리를 말한다.** 실물 디스크 확인:
   ``~/MALightingTechnology/gma3_library/fixturetypes`` · ``.../mvr``
   (후자는 ``patch_mvr.html``이 명시한다).
4. **언제인지 말한다.** round20 세션 GO 조건 ①이 세션 중 GDTF 임포트를 금지한다 —
   모든 단계 문장이 「세션 착수 전」을 달고 나가야 한다.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from server.vwx import typesource as ts
from server.vwx.intake import FixtureRequest, LibraryOption, assess
from server.vwx.mvr import bundled_fixture_type_bytes
from server.vwx.mvr import read as read_mvr

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vwx"
DEMOSHOW = FIXTURES / "demoshow_grandma3.mvr"

#: 실물 MVR이 동봉한 다섯 종 중 셋만 콘솔에 있다고 가정한다.
KNOWN_ON_CONSOLE = ("MAC Encore Performance CLD", "Mac Aura XB")


@pytest.fixture(scope="module")
def mvr_bytes() -> bytes:
    return DEMOSHOW.read_bytes()


@pytest.fixture(scope="module")
def rows(mvr_bytes: bytes):
    return list(read_mvr(mvr_bytes).records)


class TestThereIsAlwaysAWayForward:
    """막다른 길을 내지 않는다."""

    def test_an_unknown_type_still_gets_a_plan(self):
        steps = ts.plan_for_missing_type("Clay Paky Sharpy")
        assert steps

    def test_every_step_tells_the_operator_what_to_do(self):
        for step in ts.plan_for_missing_type("Clay Paky Sharpy"):
            assert step.action.strip()

    def test_every_step_says_when(self):
        """세션 중 임포트 금지 — 이 말이 빠지면 조작자가 세션을 깨뜨린다."""
        for step in ts.plan_for_missing_type("Clay Paky Sharpy"):
            assert "세션 착수 전" in step.action

    def test_the_console_editor_is_last(self):
        """채널 배치를 손으로 정의하는 것은 마지막 수단이다."""
        steps = ts.plan_for_missing_type("Clay Paky Sharpy")
        assert steps[-1].source == ts.SOURCE_CONSOLE_EDITOR

    def test_without_a_file_nothing_claims_to_be_available(self):
        """[비공허] 손에 없는 것을 있다고 하지 않는다."""
        steps = ts.plan_for_missing_type("Clay Paky Sharpy")
        assert not any(step.available_now for step in steps)
        assert all(step.payload is None for step in steps)


class TestTheMvrAnswersFirst:
    """MVR이 그 타입을 담고 있으면 그것이 첫 갈래이고, 파일이 실제로 나온다."""

    def test_a_bundled_type_is_the_first_choice(self, mvr_bytes: bytes):
        steps = ts.plan_for_missing_type(
            "Rush Par 2 RGBW Zoom",
            gdtf_spec="Martin@Rush Par 2 RGBW Zoom",
            mvr_bytes=mvr_bytes,
        )
        assert steps[0].source == ts.SOURCE_BUNDLED_IN_MVR
        assert steps[0].available_now is True

    def test_the_payload_is_a_real_gdtf(self, mvr_bytes: bytes):
        """바이트를 실제로 열어 본다 — 「있다」고만 하고 깨진 것을 주면 더 나쁘다."""
        payload = bundled_fixture_type_bytes(mvr_bytes, "Martin@Rush Par 2 RGBW Zoom")
        assert payload is not None
        with zipfile.ZipFile(__import__("io").BytesIO(payload)) as gdtf:
            assert "description.xml" in gdtf.namelist()

    def test_a_type_the_mvr_does_not_carry_falls_through(self, mvr_bytes: bytes):
        """[비공허] MVR을 줬다고 아무 타입이나 있다고 하지 않는다."""
        steps = ts.plan_for_missing_type(
            "Clay Paky Sharpy", gdtf_spec="Clay Paky@Sharpy", mvr_bytes=mvr_bytes
        )
        assert steps[0].source != ts.SOURCE_BUNDLED_IN_MVR
        assert bundled_fixture_type_bytes(mvr_bytes, "Clay Paky@Sharpy") is None

    def test_a_name_without_a_spec_cannot_reach_the_bundle(self, mvr_bytes: bytes):
        """MVR 안의 키는 `제조사@이름`이다 — 이름만으로는 못 찾고, 찾은 척도 안 한다."""
        steps = ts.plan_for_missing_type("Rush Par 2 RGBW Zoom", mvr_bytes=mvr_bytes)
        assert steps[0].source != ts.SOURCE_BUNDLED_IN_MVR

    def test_the_suggested_path_is_the_library_folder(self, mvr_bytes: bytes):
        steps = ts.plan_for_missing_type(
            "Rush Par 2 RGBW Zoom",
            gdtf_spec="Martin@Rush Par 2 RGBW Zoom",
            mvr_bytes=mvr_bytes,
        )
        assert "gma3_library" in steps[0].install_hint
        assert steps[0].install_hint.endswith(".gdtf")


class TestPlanningForAWholeDrawing:
    """도면 전체에서 모자란 타입만 골라낸다."""

    def test_only_the_missing_types_are_planned(self, rows, mvr_bytes: bytes):
        plans = ts.plan_for_rows(rows, KNOWN_ON_CONSOLE, mvr_bytes=mvr_bytes)
        planned = {p.instrument_type for p in plans}
        assert planned == {"Rush Par 2 RGBW Zoom", "Led Tile RGB8 Wall", "LED steps small"}

    def test_a_fully_stocked_console_needs_nothing(self, rows, mvr_bytes: bytes):
        """[비공허] 전부 있으면 계획이 비어야 한다."""
        every = {(row["Instrument Type"]) for row in rows}
        assert ts.plan_for_rows(rows, sorted(every), mvr_bytes=mvr_bytes) == ()

    def test_each_type_appears_once(self, rows, mvr_bytes: bytes):
        """176행에 타입은 5종뿐 — 행마다 한 줄씩 내면 읽히지 않는다."""
        plans = ts.plan_for_rows(rows, KNOWN_ON_CONSOLE, mvr_bytes=mvr_bytes)
        names = [p.instrument_type for p in plans]
        assert len(names) == len(set(names))

    def test_all_three_come_from_the_bundle(self, rows, mvr_bytes: bytes):
        """이 MVR은 자기가 쓰는 타입을 전부 싣는다 — 사람이 구할 것이 없다."""
        plans = ts.plan_for_rows(rows, KNOWN_ON_CONSOLE, mvr_bytes=mvr_bytes)
        assert all(p.source == ts.SOURCE_BUNDLED_IN_MVR for p in plans)
        assert all(p.payload for p in plans)

    def test_without_the_mvr_the_same_types_need_a_person(self, rows):
        """[비공허] 같은 도면이라도 MVR 바이트가 없으면 사람이 가져와야 한다."""
        plans = ts.plan_for_rows(rows, KNOWN_ON_CONSOLE)
        assert plans
        assert not any(p.available_now for p in plans)


class TestIntakeOffersItInsteadOfADeadEnd:
    """인테이크가 「없는 타입」을 조달 단계와 함께 낸다."""

    LIBRARY = (LibraryOption("Mac Aura XB", "Martin@Mac Aura XB", {"Standard (14 ch)": 14}),)

    def test_an_unknown_type_gets_both_a_question_and_a_plan(self, mvr_bytes: bytes):
        request = FixtureRequest(
            instrument_type="Rush Par 2 RGBW Zoom", gdtf_fixture="Martin@Rush Par 2 RGBW Zoom"
        )
        result = assess(request, self.LIBRARY, mvr_bytes=mvr_bytes)
        assert result.ready is False
        assert any(q.field == "instrument_type" for q in result.questions)
        assert result.provisioning
        assert result.provisioning[0].source == ts.SOURCE_BUNDLED_IN_MVR

    def test_a_known_type_needs_no_plan(self):
        """[비공허] 있는 타입에 조달 계획을 붙이지 않는다."""
        result = assess(FixtureRequest(instrument_type="Mac Aura XB"), self.LIBRARY)
        assert result.provisioning == ()

    def test_an_ambiguous_name_asks_rather_than_provisions(self):
        """후보가 있으면 그건 「없는 타입」이 아니라 「고르지 못한 타입」이다."""
        library = (
            LibraryOption("Mac Aura XB", modes={"A": 1}),
            LibraryOption("Mac Aura PXL", modes={"B": 1}),
        )
        result = assess(FixtureRequest(instrument_type="Mac Aura"), library)
        assert result.provisioning == ()
        assert any(q.field == "instrument_type" for q in result.questions)
