"""t229 — bm 의 **범위 축**: 도로 적힌 시트 값이 그 기종이 낼 수 있는 각도인가.

이 회차가 잇는 것은 `server/prechk/capability_read.py` 와 `classify_storability`
사이의 **첫 소비 경로**다. 그 판독기는 t343 이 넣었고 이 카드 전까지 비테스트
호출자가 0건이었다 — 부품은 초록인데 경로가 안 이어져 있었다.

## 왜 새 사유 클래스인가

기존 bm 보류는 두 축이었다:

    어휘 축   그 속성을 콘솔에 쏠 수 있는가        (probe_rejected · out_of_scope · unknown)
    구조 축   이 값을 (속성, 값) 으로 가를 수 있는가 (value_not_machine_readable)

BM.01 의 `Zoom 45°` 는 **둘 다 통과한다.** Zoom 은 쏠 수 있고 조각도 읽힌다.
그런데 실측한 Robin MegaPointe(FixtureType 11, Mode 1)의 줌은 **1.8~42.0도**이므로
45도는 그 기종이 못 낸다. 두 축으로는 이것이 안 잡히고, 어휘가 열리는 날 조용히
나간다 — 콘솔은 값을 잘라서 받고, 되읽기는 슬롯 점유만 확인한다.

## 이 검사가 지키는 네 개의 문턱

`_bm_out_of_range_segments` 는 조각마다 넷을 다 통과해야 걸린다. 넷 중 하나라도
느슨해지면 **틀린 사유로 막거나 추측한 값으로 막는다** — 안 막는 것보다 나쁘다:

    1. 조각이 읽힌다        못 읽은 조각은 구조 축이 이미 든다
    2. 도 표기가 있다        퍼센트는 방향이 미측정이다(t235) — 옮기면 추측이다
    3. 축이 measurable      미판독을 결함으로 바꾸지 않는다
    4. 축이 0~1 이 아니다    단위가 다른 짝을 「범위 밖」이라 부르지 않는다

각 문턱마다 **넘는 쪽과 안 넘는 쪽을 둘 다** 쏜다. 한쪽만 쏘면 술어가 항상
빈손이어도 통과한다.

## 주입이지 조회가 아니다

`classify_storability` 는 능력 판독을 **받기만** 한다. `capabilities=None` 이면
이 축은 존재하지 않는 것과 같고, 그것을 다섯 행 **전수**로 잰다(아래
`TestWithoutCapabilitiesNothingChanges`) — 새 인자가 기본값으로 조용히 기존
판정을 바꾸지 않는다는 것이 이 카드의 hard 요구다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq import preset_parser as parser_module
from server.lxseq.preset_parser import (
    HOLD_FAMILY_OUT_OF_SCOPE,
    HOLD_PROBE_REJECTED,
    HOLD_VALUE_NOT_MACHINE_READABLE,
    HOLD_VALUE_OUT_OF_RANGE,
    PresetHoldReason,
    classify_storability,
    parse_preset_csv,
)
from server.prechk.capability_read import AxisRange, ModeCapabilities

BM = Path("src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv")

#: 실측 축 둘(2026-09-10, onPC / 응답기 1.6.5, 읽기 전용 — `test_capability_read.py`
#: 의 고정값과 같은 표본). Zoom 의 두 끝이 **역순**인 것이 이 파일의 핵심이다.
_ZOOM = AxisRange(
    attribute="Zoom",
    channel_name="Main Module_Zoom",
    dmx_from=0,
    dmx_to=16777216,
    physical_from=42.0,
    physical_to=1.8,
)
_FROST1 = AxisRange(
    attribute="Frost1",
    channel_name="Main Module_Frost1",
    dmx_from=0,
    dmx_to=3487029,
    physical_from=0.0,
    physical_to=1.0,
    default=0.0,
)


def _caps(*axes: AxisRange) -> ModeCapabilities:
    """축 목록만 실은 판독 결과. 콘솔을 부르지 않고 손으로 세운다."""
    return ModeCapabilities(attempted=True, mode_found=True, channel_count=32, axes=tuple(axes))


MEGAPOINTE = _caps(_ZOOM, _FROST1)


def _classify(value: str, capabilities: ModeCapabilities | None = MEGAPOINTE):
    return classify_storability("preset-bm", value, capabilities=capabilities)


def _classes(value: str, capabilities: ModeCapabilities | None = MEGAPOINTE) -> list[str]:
    return [reason.hold_class for reason in _classify(value, capabilities)[1]]


def _rows() -> dict[str, str]:
    """정본 시트의 ID -> Value 원문."""
    result = parse_preset_csv(BM.read_text(encoding="utf-8"))
    assert result.sheet_kind == "preset-bm"
    return {record.preset_id: record.value_raw for record in result.records}


class TestTheCanonicalSheetAgainstTheMeasuredFixture:
    """정본 시트 두 행이 이 축의 관측 창이다 — 하나는 걸리고 하나는 안 걸린다."""

    def test_bm01_is_held_because_45_degrees_is_outside_1_8_to_42(self):
        """🔴 이 카드의 발견 그 자체. 어휘·구조 축은 둘 다 통과하는 값이다."""
        storable, reasons = _classify(_rows()["BM.01"])
        assert storable is False
        assert HOLD_VALUE_OUT_OF_RANGE in [r.hold_class for r in reasons]

    def test_bm01_keeps_the_reasons_it_already_had(self):
        """사유는 **누적된다.** 새 축이 기존 두 사유를 밀어내면 한 원인을 풀었을 때
        그 행이 열릴 것처럼 보인다 — `classify_storability` 독스트링의 계약이다."""
        assert _classes(_rows()["BM.01"]) == [
            HOLD_PROBE_REJECTED,
            HOLD_FAMILY_OUT_OF_SCOPE,
            HOLD_VALUE_OUT_OF_RANGE,
        ]

    def test_bm02s_20_degrees_does_not_trip_the_new_rung(self):
        """대조군. BM.02 는 Gobo(범위 밖)에 여전히 막히므로 storable 로 묻지 않고
        **새 사유의 부재**를 묻는다 — 다른 축의 상태를 이 검사의 근거로 쓰지 않는다."""
        classes = _classes(_rows()["BM.02"])
        assert HOLD_VALUE_OUT_OF_RANGE not in classes
        assert classes == [HOLD_FAMILY_OUT_OF_SCOPE]

    def test_the_hold_detail_names_the_value_the_interval_and_the_channel(self):
        """감독이 **무엇을 고쳐야 하는지** 사유 문면에서 읽을 수 있어야 한다."""
        reason = next(
            r for r in _classify(_rows()["BM.01"])[1] if r.hold_class == HOLD_VALUE_OUT_OF_RANGE
        )
        assert "Zoom 45°" in reason.detail
        assert "1.8~42.0" in reason.detail
        assert "Main Module_Zoom" in reason.detail

    def test_the_hold_does_not_offer_to_clamp(self):
        """값을 잘라 맞추는 것은 조용히 틀린 값을 보내는 것이다. 문면이 그것을
        제안하지 않고, 이 축의 처방은 시트 수정 또는 기종 변경 둘뿐이다."""
        reason = next(
            r for r in _classify(_rows()["BM.01"])[1] if r.hold_class == HOLD_VALUE_OUT_OF_RANGE
        )
        assert "잘라 맞추지 않는다" in reason.detail


class TestTheDescendingAxisBoundary:
    """역방향 축(42.0 -> 1.8)에서 포함 검사가 **정렬된** 구간으로 걸리는가.

    정렬 없이 `physical_from <= v <= physical_to` 로 쓰면 42.0 >= 1.8 이라
    **모든 값이 범위 밖**이 된다 — 술어가 항상 걸리는 쪽으로 고장 난다.
    두 끝을 포함으로 잡고, 그 바로 밖 둘도 함께 쏜다.
    """

    @pytest.mark.parametrize("value", ["Zoom 42°", "Zoom 1.8°", "Zoom 20°"])
    def test_inside_the_interval_including_both_ends(self, value: str):
        assert _classify(value) == (True, ())

    @pytest.mark.parametrize("value", ["Zoom 42.1°", "Zoom 1.7°", "Zoom 45°"])
    def test_outside_the_interval_on_either_side(self, value: str):
        assert _classes(value) == [HOLD_VALUE_OUT_OF_RANGE]

    def test_the_direction_is_not_normalized_away_in_the_payload(self):
        """판독기는 방향을 보존한다(`AxisRange.descending`). 정렬은 **이 검사
        안에서만** 일어나고 축 자신은 그대로여야 한다 — 판독기의 계약이다."""
        assert _ZOOM.descending is True
        assert (_ZOOM.physical_from, _ZOOM.physical_to) == (42.0, 1.8)


class TestTheDegreeMarkerIsRequired:
    """🔴 표기가 없으면 읽지 않는다. 퍼센트를 물리값으로 옮기려면 콘솔 `At` 매핑의
    방향을 알아야 하는데 역방향 축에서 그것은 **안 쟀다**(t235). 재지 않은 방향으로
    옮기면 뒤집힌 값이 조용히 범위 안에 들어온다.
    """

    @pytest.mark.parametrize("value", ["Zoom 45 deg", "Zoom 45DEG", "Zoom 45 degrees"])
    def test_the_written_forms_of_degree_are_read(self, value: str):
        assert _classes(value) == [HOLD_VALUE_OUT_OF_RANGE]

    def test_a_percent_value_out_of_the_degree_interval_is_not_flagged(self):
        """95 는 1.8~42.0 밖이지만 **퍼센트**다. 걸리면 퍼센트를 도로 읽은 것이다."""
        assert _classify("Zoom 95%") == (True, ())

    def test_frost_30_percent_is_not_flagged(self):
        """정본 BM.04. Frost 는 어휘로 막히지만 범위 축은 **걸지 않는다**."""
        classes = _classes(_rows()["BM.04"])
        assert HOLD_VALUE_OUT_OF_RANGE not in classes
        assert classes == [HOLD_PROBE_REJECTED]

    def test_a_bare_number_is_not_read_as_degrees(self):
        assert _classify("Zoom 95") == (True, ())

    def test_a_word_that_merely_starts_with_deg_is_not_a_degree(self):
        """`deg` 를 접두로만 보면 `45 degauss` 가 도가 된다 — 그것은 추측이다."""
        assert _classify("Zoom 95 degauss") == (True, ())


class TestAnUnmeasuredAxisIsNotADefect:
    """미판독을 결함으로 바꾸지 않는다 — 부재와 미판독은 다른 상태다."""

    def test_an_axis_with_no_physical_range_does_not_flag(self):
        half_read = _caps(AxisRange(attribute="Zoom", channel_name="Main Module_Zoom"))
        assert half_read.axis("Zoom").measurable is False
        assert _classify("Zoom 45°", half_read) == (True, ())

    def test_an_axis_missing_from_the_read_does_not_flag(self):
        assert _caps(_FROST1).axis("Zoom") is None
        assert _classify("Zoom 45°", _caps(_FROST1)) == (True, ())

    def test_one_end_read_is_still_not_measurable(self):
        one_end = _caps(
            AxisRange(attribute="Zoom", channel_name="Main Module_Zoom", physical_from=42.0)
        )
        assert _classify("Zoom 45°", one_end) == (True, ())


class TestANormalizedAxisIsNotComparedWithDegrees:
    """`Frost1` 은 `PHYSICALFROM=0.0 PHYSICALTO=1.0` 이다(실측). 도 값이 그 축과
    어긋나는 것은 **단위가 다른 탓**이지 값이 틀린 탓이 아니다.
    """

    def test_a_degree_value_against_a_0_to_1_axis_does_not_flag(self):
        """Zoom 을 정규화 모양으로 세워 어휘 축을 섞지 않고 이 문턱만 본다."""
        normalized = _caps(
            AxisRange(
                attribute="Zoom",
                channel_name="Main Module_Zoom",
                physical_from=0.0,
                physical_to=1.0,
            )
        )
        assert _classify("Zoom 45°", normalized) == (True, ())

    def test_the_same_value_flags_once_the_axis_leaves_the_0_to_1_shape(self):
        """문턱의 반대쪽 — 상한이 1.0 을 넘으면 같은 값이 걸린다. 이것이 없으면
        위 검사는 술어가 항상 빈손이어도 통과한다."""
        widened = _caps(
            AxisRange(
                attribute="Zoom",
                channel_name="Main Module_Zoom",
                physical_from=0.0,
                physical_to=1.1,
            )
        )
        assert _classes("Zoom 45°", widened) == [HOLD_VALUE_OUT_OF_RANGE]

    def test_a_negative_lower_end_is_not_treated_as_normalized(self):
        """0~1 판정은 두 끝이 **다** 그 구간 안일 때만이다. -180~180(팬 모양)을
        정규화로 읽으면 그 축 전체가 검사에서 빠진다."""
        pan_shaped = _caps(
            AxisRange(
                attribute="Zoom",
                channel_name="Main Module_Zoom",
                physical_from=-180.0,
                physical_to=180.0,
            )
        )
        assert _classify("Zoom 45°", pan_shaped) == (True, ())
        assert _classes("Zoom 200°", pan_shaped) == [HOLD_VALUE_OUT_OF_RANGE]


class TestTheSheetToConsoleVocabularyIsTheOneTable:
    """시트 토큰과 콘솔 이름이 갈리는 자리(`Frost` -> `Frost1`)에서 축을 찾는가.

    둘째 매핑 표를 만들면 두 어휘의 연결 지점이 둘이 되고, 한쪽만 고치는 날이 온다.
    문장으로 두지 않고 **표를 비워서** 잰다 — 사본을 쓰고 있으면 안 움직인다.
    """

    #: 콘솔 이름으로만 존재하는 축이고, 0~1 모양이 아니다.
    WIDE_FROST = AxisRange(
        attribute="Frost1",
        channel_name="Main Module_Frost1",
        physical_from=0.0,
        physical_to=100.0,
    )

    def test_a_sheet_token_finds_its_console_named_axis(self):
        classes = _classes("Frost 900°", _caps(self.WIDE_FROST))
        assert HOLD_VALUE_OUT_OF_RANGE in classes

    def test_emptying_the_one_table_loses_that_axis(self, monkeypatch):
        """치환으로 잰다 — 이 술어가 실제로 그 표를 부른다는 증명이다."""
        monkeypatch.setattr(parser_module, "_SHEET_TO_CONSOLE_ATTRIBUTE", {})
        classes = _classes("Frost 900°", _caps(self.WIDE_FROST))
        assert HOLD_VALUE_OUT_OF_RANGE not in classes

    def test_a_token_absent_from_the_table_uses_the_sheet_spelling(self):
        """`Zoom` 은 두 어휘가 같은 자리다(실측: FixtureType 11 채널 28
        `ATTRIBUTE=Zoom`). 표에 없는 토큰에 대해 둘째 표를 세우지 않는다."""
        assert "Zoom" not in parser_module._SHEET_TO_CONSOLE_ATTRIBUTE
        assert _classes("Zoom 45°") == [HOLD_VALUE_OUT_OF_RANGE]


class TestTheClassifierActuallyCallsThisPredicate:
    """「같은 술어를 쓴다」를 문장이 아니라 치환으로 잰다 — 사본이면 안 움직인다."""

    def test_blinding_the_predicate_opens_bm01s_new_reason(self, monkeypatch):
        assert HOLD_VALUE_OUT_OF_RANGE in _classes(_rows()["BM.01"])
        monkeypatch.setattr(parser_module, "_bm_out_of_range_segments", lambda _v, _c: ())
        assert HOLD_VALUE_OUT_OF_RANGE not in _classes(_rows()["BM.01"])

    def test_making_the_predicate_all_seeing_holds_a_value_that_was_storable(self, monkeypatch):
        assert _classify("Zoom 20°") == (True, ())
        monkeypatch.setattr(parser_module, "_bm_out_of_range_segments", lambda _v, _c: ("x",))
        assert _classes("Zoom 20°") == [HOLD_VALUE_OUT_OF_RANGE]


class TestWithoutCapabilitiesNothingChanges:
    """🔴 이 카드의 hard 요구. 인자를 주지 않은 호출은 이 축이 생기기 전과 **같다.**

    기대값은 **손으로 적었다**(변경 전 `classify_storability` 출력 전수). 술어의
    출력을 그대로 받아 적으면 술어가 무엇을 하든 통과하는 검사가 된다.
    """

    PROBE = "라이브 프로브가 거절한 속성: "
    PROBE_TAIL = " (server/looks/schema.py 의 M0 프로브 판정)"
    SCOPE = "풀 계열이 범위 밖인 속성: "
    SCOPE_TAIL = " (server/looks/schema.py 의 범위 선언)"

    #: 변경 전 다섯 행의 사유 튜플 전수. 문면까지 포함한다 — 클래스만 고정하면
    #: 사유 문면이 조용히 바뀌는 회귀가 통과한다.
    EXPECTED = {
        "BM.01": (
            PresetHoldReason(HOLD_PROBE_REJECTED, PROBE + "Prism" + PROBE_TAIL),
            PresetHoldReason(HOLD_FAMILY_OUT_OF_SCOPE, SCOPE + "Gobo" + SCOPE_TAIL),
        ),
        "BM.02": (PresetHoldReason(HOLD_FAMILY_OUT_OF_SCOPE, SCOPE + "Gobo" + SCOPE_TAIL),),
        "BM.03": (PresetHoldReason(HOLD_PROBE_REJECTED, PROBE + "Prism" + PROBE_TAIL),),
        "BM.04": (PresetHoldReason(HOLD_PROBE_REJECTED, PROBE + "Frost" + PROBE_TAIL),),
        "BM.05": (
            PresetHoldReason(HOLD_FAMILY_OUT_OF_SCOPE, SCOPE + "Gobo" + SCOPE_TAIL),
            PresetHoldReason(
                HOLD_VALUE_NOT_MACHINE_READABLE,
                "성분으로 못 가르는 조각: 예비"
                " — 속성 이름으로 시작하는 조각만 옮긴다(버리지 않고 보고한다)",
            ),
        ),
    }

    @pytest.mark.parametrize("preset_id", ["BM.01", "BM.02", "BM.03", "BM.04", "BM.05"])
    def test_the_reason_tuple_is_unchanged_for_every_canonical_row(self, preset_id: str):
        storable, reasons = classify_storability("preset-bm", _rows()[preset_id])
        assert storable is False
        assert reasons == self.EXPECTED[preset_id]

    def test_the_default_is_none_not_a_shared_capability_object(self):
        """기본값이 판독 객체면 파서가 콘솔 상태에 묶인다. 다섯 행 전수와 별개로
        기본값 자체를 본다 — 위 검사는 「지금 아무 축도 안 걸린다」와도 양립한다."""
        import inspect

        default = inspect.signature(classify_storability).parameters["capabilities"].default
        assert default is None

    @pytest.mark.parametrize("value", ["Zoom 45°", "Zoom 42.1°", "Frost 900°"])
    def test_values_that_the_new_rung_flags_are_untouched_without_the_injection(self, value: str):
        assert HOLD_VALUE_OUT_OF_RANGE not in _classes(value, None)


class TestTheOtherSheetsAreUntouched:
    """범위 축은 bm 전용이다. dim·col 에 능력 판독을 주어도 판정이 안 바뀐다."""

    @pytest.mark.parametrize(
        ("kind", "value"),
        [
            ("preset-dim", "85%"),
            ("preset-dim", "Zoom 45°"),
            ("preset-col", "R255 G180 B60"),
            ("preset-col", "Zoom 45°"),
        ],
    )
    def test_dim_and_col_ignore_the_capability_argument(self, kind: str, value: str):
        assert classify_storability(kind, value) == classify_storability(
            kind, value, capabilities=MEGAPOINTE
        )
