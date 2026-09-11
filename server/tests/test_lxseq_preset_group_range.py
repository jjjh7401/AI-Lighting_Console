"""t351 — 범위 술어를 하나로 합치고, 그룹 단위 대조를 **생산 경로에** 배선한다.

이 카드가 고치러 온 두 가지:

1. **술어가 둘이었다.** `design.capability_verdict.range_verdict`(t344) 와
   `lxseq.preset_parser._bm_out_of_range_segments`(t229) 가 각자 `min`/`max` 로
   포함 검사를 계산했다. 같은 판정이 두 자리에 있으면 갈리는 날 한쪽만 고쳐진다.
   → 술어를 축 자신에게 옮겼다(`AxisRange.window` -> `AxisWindow`).
2. **둘 다 생산 호출자가 0 이었다.** `classify_storability(capabilities=...)` 는
   `parse_preset_csv` 가 인자 없이 부르고 있었고(`preset_parser.py:882`),
   `range_verdict` 는 자신의 판정 문서가 호출자 0 을 적어 두었다. 부품은 초록인데
   경로가 안 이어져 있었다(같은 형태를 t343->t229 가 이미 한 번 겪었다).
   → `parse_preset_csv(capabilities_for=...)` + `import_lxseq_presets` 배선.

## 왜 그룹 단위인가 — 실측이 그것을 요구한다

정본 시트에서 `BM.01 Zoom 45°` 의 `TargetGroup` 은 `MOVER-ALL` 이고, 그 그룹은
**기종이 둘**이다(`LXSEQ_RIG_01_ShowBase_r3.patch.csv` · `.group.csv` 실측
2026-09-11, `awk` 로 전수):

    MOVER-ALL = MOVER-U + MOVER-D          (group.csv 7·10·13 행의 합집합 표기)
    MOVER-U   Robe MegaPointe  Mode 1 39ch  FID 501-508
    MOVER-D   Robe Spiider     Mode 1 49ch  FID 521-528

그래서 「이 값을 낼 수 있는가」는 한 축으로 답할 수 없다. 채택한 규칙은 **교집합**
이고 하나라도 못 내면 보류한다 — 근거는 `GroupCapabilities` 독스트링에 있다.

## 조인 키는 FID 다 — 이름이 아니다

시트는 `Robe MegaPointe`, 콘솔 라이브러리 실측은 `Robin MegaPointe` 였다
(2026-09-10, FixtureType 11). **두 이름이 같다는 것은 안 쟀다.** 그래서 조인은
FID 로 하고, 아래 가짜 콘솔은 그 차이를 **일부러 그대로 재현한다**(콘솔 쪽 이름을
`Robin` 으로 답한다) — 이름으로 조인하는 회귀가 들어오면 여기서 빨개진다.

## 이 파일의 값들이 어디서 왔는지 (섞지 말 것)

* **실측 replay** — Robin MegaPointe(FixtureType 11, Mode 1) Zoom
  `PHYSICALFROM=42.0 PHYSICALTO=1.8`, Frost1 `0.0~1.0`. 2026-09-10, onPC /
  응답기 1.6.5, 읽기 전용. `test_capability_read.py` · `test_capability_verdict.py`
  의 고정값과 **같은 표본**이다.
* **구성된 대조군** — Robe Spiider 의 Zoom `50.0 -> 5.0`. 🔴 **이것은 실측이
  아니다.** 이 저장소에 Spiider 의 물리 범위 판독 기록은 없다. 기종이 섞인 그룹의
  교집합이 실제로 좁혀지는지 재기 위한 **모양**이며, Spiider 의 줌이 그렇다는
  주장이 아니다(형제 `test_capability_verdict.py` 의 `Pan Only` 와 같은 규율).
  실측이 들어오면 이 상수를 그것으로 갈아끼운다.

콘솔·네트워크 접촉 0. 아래 모든 dispatch 는 `action="preview"` 이며 발화 포트는
발화가 오면 실패한다 — 콘솔 쓰기 0 을 검사가 지킨다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from server.design.capability_join import (
    FixtureCapability,
    FixtureTypeRef,
    RigCapabilities,
    read_rig_capabilities,
)
from server.design.capability_verdict import (
    VERDICT_HELD,
    VERDICT_OK,
    GroupCapabilities,
    group_capabilities,
    group_capability_source,
    range_verdict,
)
from server.llm.types import ToolCall
from server.lxseq.position_derive import group_members_from_sheets
from server.lxseq.preset_parser import (
    HOLD_VALUE_OUT_OF_RANGE,
    classify_storability,
    parse_preset_csv,
)
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.prechk.capability_read import (
    NORMALIZED_AXIS_MAX,
    AxisRange,
    AxisWindow,
    AxisWindowPart,
    ModeCapabilities,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3"
BM = RIG / (STEM + ".preset-bm.csv")
PATCH = RIG / (STEM + ".patch.csv")
GROUP = RIG / (STEM + ".group.csv")
TOOL = "import_lxseq_presets"

_TYPES_ROOT = "Patch/FixtureTypes"
_FIXTURE_ROOT = "Patch/Stages/1/Fixtures"

#: 실측 replay (2026-09-10). Zoom 의 두 끝이 **역순**인 것이 이 파일의 핵심 고정값이다.
MEGAPOINTE_ZOOM = AxisRange(
    attribute="Zoom",
    channel_name="Main Module_Zoom",
    dmx_from=0,
    dmx_to=16777216,
    physical_from=42.0,
    physical_to=1.8,
)
MEGAPOINTE_FROST = AxisRange(
    attribute="Frost1",
    channel_name="Main Module_Frost1",
    physical_from=0.0,
    physical_to=1.0,
)

#: 🔴 **구성된 대조군, 실측 아님** (모듈 독스트링 참조). MegaPointe 보다 좁은 하한을
#: 갖도록 골랐다 — 교집합이 실제로 좁아지는지 재려면 두 창이 달라야 한다.
SPIIDER_ZOOM = AxisRange(
    attribute="Zoom",
    channel_name="Main Module_Zoom",
    physical_from=50.0,
    physical_to=5.0,
)

MEGAPOINTE_TYPE = "Robin MegaPointe"  # 콘솔이 답한 철자 (시트는 'Robe MegaPointe')
SPIIDER_TYPE = "Robe Spiider"


def _caps(*axes: AxisRange) -> ModeCapabilities:
    return ModeCapabilities(attempted=True, mode_found=True, channel_count=32, axes=tuple(axes))


def _fixture(fid: int, type_name: str, *axes: AxisRange, gaps: tuple[str, ...] = ()):
    return FixtureCapability(
        fid=fid,
        type_slot=0,
        type_name=type_name,
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=None,
        channel_count=32,
        axes=tuple(axes),
        gaps=gaps,
    )


def _rig(*fixtures: FixtureCapability) -> RigCapabilities:
    return RigCapabilities(fixtures={f.fid: f for f in fixtures})


# ── Part 1: 술어가 하나다 ──────────────────────────────────────────────


class TestTheContainmentPredicateLivesOnTheAxis:
    """포함 검사가 축 자신에게 있고, 두 소비자가 **그것을** 부른다."""

    def test_the_window_sorts_for_comparison_without_touching_the_axis(self):
        """정렬은 파생값에서만 일어난다 — 축은 읽은 방향 그대로 남는다."""
        window = MEGAPOINTE_ZOOM.window()
        assert (window.low, window.high) == (1.8, 42.0)
        assert (MEGAPOINTE_ZOOM.physical_from, MEGAPOINTE_ZOOM.physical_to) == (42.0, 1.8)

    def test_the_window_carries_the_dmx_direction_separately(self):
        """🔴 이 카드의 요구 그 자체: 정렬해도 DMX 0 쪽을 **버리지 않는다**."""
        assert MEGAPOINTE_ZOOM.window().descending is True
        ascending = AxisRange(
            attribute="Pan", channel_name="c", physical_from=-270.0, physical_to=270.0
        )
        assert ascending.window().descending is False

    @pytest.mark.parametrize("value", [1.8, 5.0, 20.0, 42.0])
    def test_a_descending_axis_contains_its_own_interval(self, value: float):
        assert MEGAPOINTE_ZOOM.window().contains(value) is True

    @pytest.mark.parametrize("value", [1.7, 42.1, 45.0, -3.0])
    def test_values_outside_either_end_are_not_contained(self, value: float):
        assert MEGAPOINTE_ZOOM.window().contains(value) is False

    def test_an_unmeasured_axis_has_no_window_at_all(self):
        """``None`` 은 「범위 밖이 아니다」가 아니라 「대조할 수 없다」다."""
        assert AxisRange(attribute="Zoom", channel_name="c", physical_from=42.0).window() is None
        assert AxisRange(attribute="Zoom", channel_name="c").window() is None

    def test_the_normalized_threshold_needs_both_ends_inside(self):
        """-180~180(팬 모양)을 정규화로 읽으면 그 축이 검사에서 통째로 빠진다."""
        assert MEGAPOINTE_FROST.window().normalized is True
        assert MEGAPOINTE_ZOOM.window().normalized is False
        pan = AxisRange(attribute="Pan", channel_name="c", physical_from=-180.0, physical_to=180.0)
        assert pan.window().normalized is False
        assert NORMALIZED_AXIS_MAX == 1.0

    def test_range_verdict_still_holds_and_passes_through_the_shared_predicate(self):
        """합치기가 판정을 바꾸지 않았다 — 두 갈래를 값으로 고정한다."""
        assert range_verdict(MEGAPOINTE_ZOOM, 20.0).status == VERDICT_OK
        held = range_verdict(MEGAPOINTE_ZOOM, 45.0)
        assert held.status == VERDICT_HELD
        assert (held.low, held.high) == (1.8, 42.0)
        assert held.descending is True

    def test_range_verdict_reads_that_predicate_and_not_a_copy(self, monkeypatch):
        """치환으로 잰다 — 사본을 쓰고 있으면 안 움직인다."""
        monkeypatch.setattr(AxisRange, "window", lambda _self: None)
        assert range_verdict(MEGAPOINTE_ZOOM, 20.0).status != VERDICT_OK

    def test_the_bm_predicate_reads_that_predicate_and_not_a_copy(self, monkeypatch):
        """같은 치환으로 파서 쪽도 잰다 — 두 소비자가 **한** 술어를 쓴다는 증명이다."""
        before = classify_storability("preset-bm", "Zoom 45°", capabilities=_caps(MEGAPOINTE_ZOOM))
        assert HOLD_VALUE_OUT_OF_RANGE in [r.hold_class for r in before[1]]
        monkeypatch.setattr(AxisRange, "window", lambda _self: None)
        after = classify_storability("preset-bm", "Zoom 45°", capabilities=_caps(MEGAPOINTE_ZOOM))
        assert HOLD_VALUE_OUT_OF_RANGE not in [r.hold_class for r in after[1]]


class TestTheHoldDetailKeepsTheDmxZeroEnd:
    """🔴 정렬된 `1.8~42.0` 만 적으면 어느 끝이 DMX 0 인지가 문면에서 사라진다.

    감독이 고칠 방향(좁은 쪽인가 넓은 쪽인가)을 문면에서 읽을 수 있어야 한다.
    """

    def _detail(self, value: str, capabilities) -> str:
        _storable, reasons = classify_storability("preset-bm", value, capabilities=capabilities)
        return next(r for r in reasons if r.hold_class == HOLD_VALUE_OUT_OF_RANGE).detail

    def test_a_descending_axis_names_the_dmx_zero_end(self):
        detail = self._detail("Zoom 45°", _caps(MEGAPOINTE_ZOOM))
        assert "1.8~42.0" in detail  # 대조 구간은 그대로 실린다
        assert "DMX 0 이 42.0 쪽" in detail, detail

    def test_an_ascending_axis_names_the_other_end(self):
        """대조군 — 방향이 반대면 문면의 끝도 반대여야 한다. 이것이 없으면 위
        검사는 상수를 하나 박아 둔 것과 구별되지 않는다."""
        rising = AxisRange(
            attribute="Zoom", channel_name="Main Module_Zoom", physical_from=1.8, physical_to=42.0
        )
        detail = self._detail("Zoom 45°", _caps(rising))
        assert "DMX 0 이 1.8 쪽" in detail, detail

    def test_a_direction_that_is_not_settled_is_not_asserted(self):
        """교집합에서 방향이 갈리면 아무 말도 하지 않는다 — 안 잰 방향을 단정하는
        것보다 침묵이 낫다."""
        mixed = GroupCapabilities(
            group_name="MIXED",
            per_type={
                MEGAPOINTE_TYPE: _caps(MEGAPOINTE_ZOOM),  # 42.0 -> 1.8 (내림)
                SPIIDER_TYPE: _caps(
                    AxisRange(
                        attribute="Zoom", channel_name="c", physical_from=5.0, physical_to=50.0
                    )
                ),  # 오름
            },
        )
        assert mixed.window("Zoom").descending is None
        assert "DMX 0" not in self._detail("Zoom 45°", mixed)


# ── Part 2: 그룹 단위 교집합 ───────────────────────────────────────────


class TestAHomogeneousGroup:
    """기종이 하나인 그룹 — 교집합은 그 기종의 창과 같아야 한다."""

    GROUP = "MOVER-U"

    def _source(self) -> GroupCapabilities:
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(502, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
        )
        return group_capabilities(rig, self.GROUP, [501, 502])

    def test_the_window_equals_the_single_types_window(self):
        window = self._source().window("Zoom")
        assert (window.low, window.high) == (1.8, 42.0)
        assert window.descending is True

    def test_the_same_type_on_many_fids_folds_into_one_part(self):
        """능력은 기종의 성질이다 — 같은 기종의 fid 를 여러 번 세지 않는다."""
        source = self._source()
        assert source.type_names == (MEGAPOINTE_TYPE,)
        assert len(source.window("Zoom").parts) == 1

    def test_45_degrees_is_held_and_the_detail_names_the_type(self):
        """🔴 이 검사가 t351 의 첫 술어를 잡았다. 「부품 1개면 채널 이름」으로
        가르면 기종이 하나뿐인 그룹의 창이 `(채널 'Robin MegaPointe')` 로 나갔다 —
        기종 이름을 채널이라고 부른 것이다. 역할을 **선언**으로 바꿔 고쳤다.
        """
        _storable, reasons = classify_storability(
            "preset-bm", "Zoom 45°", capabilities=self._source()
        )
        detail = next(r for r in reasons if r.hold_class == HOLD_VALUE_OUT_OF_RANGE).detail
        assert MEGAPOINTE_TYPE in detail, detail
        assert "채널" not in detail, (
            "그룹 창의 이름은 기종이다 — 채널이라고 부르면 감독이 콘솔 채널을 찾는다: " + detail
        )

    def test_20_degrees_is_not_held(self):
        assert classify_storability("preset-bm", "Zoom 20°", capabilities=self._source()) == (
            True,
            (),
        )


class TestAMixedGroupWhereOneTypeRejects:
    """🔴 이 카드의 결정이 걸리는 자리 — 그룹에 기종이 섞였고 한쪽만 못 낸다."""

    def _source(self) -> GroupCapabilities:
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),  # 1.8 ~ 42.0
            _fixture(521, SPIIDER_TYPE, SPIIDER_ZOOM),  # 5.0 ~ 50.0 (구성)
        )
        return group_capabilities(rig, "MOVER-ALL", [501, 521])

    def test_the_window_is_the_intersection_not_the_union(self):
        """합집합(1.8~50.0)이면 절반만 낼 수 있는 값이 통과한다 — 콘솔은 그 값을
        잘라 받고 되읽기는 슬롯 점유만 확인하므로 절단이 아무 신호도 안 낸다."""
        window = self._source().window("Zoom")
        assert (window.low, window.high) == (5.0, 42.0)

    def test_a_value_only_the_wide_type_can_reach_is_held(self):
        """45° 는 Spiider(구성 50.0 상한) 는 낼 수 있고 MegaPointe 는 못 낸다."""
        _storable, reasons = classify_storability(
            "preset-bm", "Zoom 45°", capabilities=self._source()
        )
        classes = [r.hold_class for r in reasons]
        assert HOLD_VALUE_OUT_OF_RANGE in classes
        detail = next(r for r in reasons if r.hold_class == HOLD_VALUE_OUT_OF_RANGE).detail
        assert MEGAPOINTE_TYPE in detail, detail
        assert SPIIDER_TYPE not in detail, (
            "낼 수 있는 기종을 거절자로 적으면 감독이 엉뚱한 장비를 고친다: " + detail
        )

    def test_a_value_only_the_narrow_type_can_reach_is_also_held(self):
        """반대쪽 — 3° 는 MegaPointe 는 낼 수 있고 Spiider(구성 5.0 하한) 는 못 낸다.
        한쪽만 쏘면 술어가 「늘 넓은 기종을 지목」해도 통과한다."""
        _storable, reasons = classify_storability(
            "preset-bm", "Zoom 3°", capabilities=self._source()
        )
        detail = next(r for r in reasons if r.hold_class == HOLD_VALUE_OUT_OF_RANGE).detail
        assert SPIIDER_TYPE in detail, detail
        assert MEGAPOINTE_TYPE not in detail, detail

    def test_a_value_inside_the_intersection_is_accepted(self):
        """대조군 — 교집합 안이면 안 걸린다. 없으면 위 둘은 술어가 늘 걸려도 통과한다."""
        assert classify_storability("preset-bm", "Zoom 20°", capabilities=self._source()) == (
            True,
            (),
        )

    @pytest.mark.parametrize("value", ["Zoom 5°", "Zoom 42°"])
    def test_both_intersection_ends_are_inclusive(self, value: str):
        assert classify_storability("preset-bm", value, capabilities=self._source()) == (True, ())


class TestTheGroupJudgementsThreeBoundaries:
    """판정이 **하지 않는** 것 — 셋 다 문턱이고 넘는 쪽·안 넘는 쪽을 함께 쏜다."""

    def test_a_type_without_the_axis_at_all_does_not_reach_this_rung(self):
        """경계 1 — 축 부재는 t348 의 `axis_absent` 몫이다. 여기서 같이 들면 한
        사실에 사유가 둘이 되고 감독은 무엇을 고쳐야 하는지 못 읽는다."""
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(521, SPIIDER_TYPE, MEGAPOINTE_FROST),  # Zoom 축이 없다
        )
        source = group_capabilities(rig, "MOVER-ALL", [501, 521])
        window = source.window("Zoom")
        assert [part.name for part in window.parts] == [MEGAPOINTE_TYPE]
        assert (window.low, window.high) == (1.8, 42.0)

    def test_an_unmeasured_axis_does_not_narrow_the_window(self):
        """경계 2 — 못 읽은 범위로 막으면 미판독이 결함으로 바뀐다."""
        half = AxisRange(attribute="Zoom", channel_name="c", physical_from=100.0)
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(521, SPIIDER_TYPE, half),
        )
        source = group_capabilities(rig, "MOVER-ALL", [501, 521])
        assert [part.name for part in source.window("Zoom").parts] == [MEGAPOINTE_TYPE]

    def test_a_group_where_nothing_is_measurable_has_no_window(self):
        """반대쪽 — 기여하는 축이 하나도 없으면 ``None`` 이고, 소비자는 그것을
        통과로 처리하면 안 된다."""
        rig = _rig(_fixture(501, MEGAPOINTE_TYPE, AxisRange(attribute="Zoom", channel_name="c")))
        source = group_capabilities(rig, "MOVER-U", [501])
        assert source.window("Zoom") is None
        assert classify_storability("preset-bm", "Zoom 45°", capabilities=source) == (True, ())

    def test_a_normalized_axis_is_excluded_from_a_degree_comparison(self):
        """경계 3 — 도 값과 0~1 축은 단위가 달라 대조 자체가 성립하지 않는다."""
        normalized = AxisRange(
            attribute="Zoom", channel_name="c", physical_from=0.0, physical_to=1.0
        )
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(521, SPIIDER_TYPE, normalized),
        )
        source = group_capabilities(rig, "MOVER-ALL", [501, 521])
        excluded = source.window("Zoom", exclude_normalized=True)
        assert [part.name for part in excluded.parts] == [MEGAPOINTE_TYPE]
        # 문턱의 반대쪽: 제외하지 않으면 그 축이 교집합을 1.0 으로 접는다.
        kept = source.window("Zoom", exclude_normalized=False)
        assert kept.high == 1.0
        assert kept.empty is True  # 5.0 ... 아니라 max(0.0, 1.8)=1.8 > 1.0


class TestTheGroupJudgementDisclosesWhatItCouldNotRead:
    def test_fids_absent_from_the_capability_read_are_named(self):
        """조용히 줄어든 그룹은 「장비가 적은 그룹」과 바이트 동일하다."""
        rig = _rig(_fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM))
        source = group_capabilities(rig, "MOVER-ALL", [501, 521, 522])
        assert source.missing_fids == (521, 522)
        assert source.whole is False

    def test_a_full_read_says_so(self):
        rig = _rig(_fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM))
        assert group_capabilities(rig, "MOVER-U", [501]).whole is True

    def test_an_unknown_group_is_not_an_empty_group(self):
        """이름을 모르는 것과 축을 못 읽은 것은 다른 사실이고, 감독에게 할 말도 다르다."""
        resolve = group_capability_source(_rig(), {"MOVER-U": (501,)})
        assert resolve("NOPE") is None
        assert resolve("MOVER-U") is not None


class TestAnEmptyIntersectionHoldsEverything:
    def test_disjoint_ranges_leave_no_common_value(self):
        """두 기종의 범위가 안 겹치면 그 그룹이 공통으로 낼 수 있는 각도가 없다."""
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),  # 1.8 ~ 42.0
            _fixture(
                521,
                SPIIDER_TYPE,
                AxisRange(attribute="Zoom", channel_name="c", physical_from=60.0, physical_to=90.0),
            ),
        )
        source = group_capabilities(rig, "MOVER-ALL", [501, 521])
        window = source.window("Zoom")
        assert window.empty is True
        _storable, reasons = classify_storability("preset-bm", "Zoom 20°", capabilities=source)
        detail = next(r for r in reasons if r.hold_class == HOLD_VALUE_OUT_OF_RANGE).detail
        assert SPIIDER_TYPE in detail, detail


class TestTheWindowPartsCountContract:
    """`AxisWindow.parts` 의 **개수**가 이름의 뜻을 정한다 — 두 생산자의 불변식."""

    def test_a_single_mode_read_produces_exactly_one_part_named_by_channel(self):
        window = _caps(MEGAPOINTE_ZOOM).window("Zoom")
        assert len(window.parts) == 1
        assert window.parts[0].name == "Main Module_Zoom"

    def test_a_two_type_group_produces_two_parts_named_by_type(self):
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(521, SPIIDER_TYPE, SPIIDER_ZOOM),
        )
        window = group_capabilities(rig, "MOVER-ALL", [501, 521]).window("Zoom")
        assert {part.name for part in window.parts} == {MEGAPOINTE_TYPE, SPIIDER_TYPE}

    def test_excluding_names_only_the_parts_that_cannot_reach_the_value(self):
        window = AxisWindow(
            attribute="Zoom",
            low=5.0,
            high=42.0,
            parts=(
                AxisWindowPart(name="wide", low=1.8, high=42.0),
                AxisWindowPart(name="narrow", low=5.0, high=50.0),
            ),
        )
        assert window.excluding(45.0) == ("wide",)
        assert window.excluding(3.0) == ("narrow",)
        assert window.excluding(20.0) == ()


# ── 주입이 없으면 예전과 같다 ──────────────────────────────────────────


class TestWithoutInjectionNothingChanges:
    """새 인자가 기본값으로 조용히 기존 판정을 바꾸지 않는다 — 정본 시트 전수로 잰다."""

    def test_every_row_matches_the_no_argument_result(self):
        text = BM.read_text(encoding="utf-8")
        plain = parse_preset_csv(text)
        explicit = parse_preset_csv(text, capabilities_for=None)
        assert plain == explicit

    def test_a_resolver_that_never_resolves_changes_nothing(self):
        """호출가능을 넘겨도 그것이 ``None`` 만 돌려주면 결과가 같아야 한다."""
        text = BM.read_text(encoding="utf-8")
        assert parse_preset_csv(text) == parse_preset_csv(text, capabilities_for=lambda _g: None)

    def test_the_resolver_is_asked_with_the_sheets_target_group(self):
        """어떤 이름으로 물었는지를 값으로 잰다 — 그룹이 아닌 것으로 물으면
        엉뚱한 기종의 범위로 막는다."""
        asked: list[str] = []
        parse_preset_csv(
            BM.read_text(encoding="utf-8"),
            capabilities_for=lambda name: asked.append(name) or None,
        )
        assert asked == ["MOVER-ALL", "MOVER-ALL", "MOVER-U", "KEY", "MOVER-U"]

    def test_a_sheet_without_a_target_group_column_never_asks(self):
        """dim·col 시트에는 그룹이 없다 — 그룹을 모르면 아무 판독도 붙이지 않는다."""
        asked: list[str] = []
        parse_preset_csv(
            (RIG / (STEM + ".preset-dim.csv")).read_text(encoding="utf-8"),
            capabilities_for=lambda name: asked.append(name) or None,
        )
        assert asked == []


# ── 생산 경로: 툴을 두드린다 ───────────────────────────────────────────

#: 정본 패치 시트 실측 — MOVER-U 는 FID 501-508, MOVER-D 는 521-528.
_MOVER_U_FIDS = tuple(range(501, 509))
_MOVER_D_FIDS = tuple(range(521, 529))

#: 타입 슬롯 -> (콘솔이 답하는 이름, 채널 슬롯 -> (속성, PHYSICALFROM, PHYSICALTO)).
#: 슬롯 11 은 실측 replay, 슬롯 12 는 구성된 대조군(모듈 독스트링).
_TYPES = {
    11: (MEGAPOINTE_TYPE, {1: ("Pan", -270.0, 270.0), 2: ("Zoom", 42.0, 1.8)}),
    12: (SPIIDER_TYPE, {1: ("Pan", -270.0, 270.0), 2: ("Zoom", 50.0, 5.0)}),
}
_FIXTURES: dict[int, tuple[int, int]] = {
    **{slot: (11, fid) for slot, fid in enumerate(_MOVER_U_FIDS, start=1)},
    **{slot: (12, fid) for slot, fid in enumerate(_MOVER_D_FIDS, start=9)},
}


class _FakeConsole:
    """타입 라이브러리 + 픽스처 트리 + 프리셋 풀을 답하는 가짜 포트.

    형제 `test_capability_verdict.py::_FakeConsole` 과 같은 모양이고, 여기서는 프리셋
    풀 경로까지 답해 `import_lxseq_presets` 의 정상 경로가 끝까지 돈다.

    **발화하면 실패한다.** `action="preview"` 이므로 이 포트의 `execute` 는 절대
    불려서는 안 되고, 그것이 「콘솔 쓰기 0」을 문장이 아니라 값으로 지킨다.
    """

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:  # pragma: no cover - 발화 금지
        self.executed.append(command)
        raise AssertionError("preview 경로에서 발화가 나갔다: " + command)

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        parts = path.split("/")
        if path.endswith("PresetPools"):
            return dict(
                ok=True,
                node=dict(childCount=1),
                children=[dict(i=4, name="Beam")],
                truncated=False,
            )
        if path.endswith("PresetPools/4"):
            return dict(ok=True, node=dict(childCount=0), children=[], truncated=False)
        if path == _TYPES_ROOT:
            children = [dict(i=slot, name=name) for slot, (name, _) in _TYPES.items()]
            return dict(ok=True, node=dict(childCount=len(children)), children=children)
        if path == _FIXTURE_ROOT:
            children = [dict(i=slot, name="fixture " + str(slot)) for slot in _FIXTURES]
            return dict(ok=True, node=dict(childCount=len(children)), children=children)
        if len(parts) >= 4 and parts[3] == "DMXModes":
            type_slot = int(parts[2])
            if type_slot not in _TYPES:
                return dict(ok=False)
            channels = _TYPES[type_slot][1]
            if len(parts) == 4:
                return dict(ok=True, children=[dict(i=1, name="Mode 1")])
            if len(parts) == 6 and parts[5] == "DMXChannels":
                return dict(
                    ok=True,
                    children=[
                        dict(i=slot, name="Main Module_" + spec[0])
                        for slot, spec in channels.items()
                    ],
                )
            if len(parts) == 7:
                spec = channels.get(int(parts[6]))
                if spec is None:
                    return dict(ok=True, children=[])
                return dict(ok=True, children=[dict(i=1, name=spec[0])])
            if len(parts) == 8:
                return dict(ok=True, children=[dict(i=1, name=channels[int(parts[6])][0] + " 1")])
        return dict(ok=False)

    def query_property(self, path: str, name: str) -> dict:
        if path.startswith(_FIXTURE_ROOT) and name == "FID":
            slot = int(path.split("/")[-1])
            entry = _FIXTURES.get(slot)
            if entry is None:
                return dict(ok=False)
            return dict(ok=True, value=str(entry[1]))
        return dict(ok=True, value="32")

    def query_properties(self, path: str, property_names) -> dict:
        parts = path.split("/")
        if path.startswith(_FIXTURE_ROOT):
            slot = int(parts[-1])
            type_slot = _FIXTURES[slot][0]
            values = {
                "Patch": "1.001",
                "FixtureType": "FixtureType " + str(type_slot),
                "Mode": "1 Mode 1",
                "Name": "fixture " + str(slot),
            }
            return dict(
                ok=True,
                reads=[dict(n=name, ok=True, v=values.get(name, "")) for name in property_names],
            )
        attribute, physical_from, physical_to = _TYPES[int(parts[2])][1][int(parts[6])]
        values = {
            "ATTRIBUTE": attribute,
            "DMXFROM": "0",
            "DMXTO": "255",
            "PHYSICALFROM": str(physical_from),
            "PHYSICALTO": str(physical_to),
            "DEFAULT": "0",
        }
        return dict(ok=True, reads=[dict(n=key, ok=True, v=value) for key, value in values.items()])


def _dispatch(*, with_sheets: bool):
    port = _FakeConsole()
    registry = build_toolset(execution_port=port, state_port=port, property_port=port)
    arguments: dict[str, object] = dict(
        file_content_base64=base64.b64encode(BM.read_bytes()).decode("ascii"),
        action="preview",
    )
    if with_sheets:
        arguments["patch_content_base64"] = base64.b64encode(PATCH.read_bytes()).decode("ascii")
        arguments["group_content_base64"] = base64.b64encode(GROUP.read_bytes()).decode("ascii")
    execution = registry.dispatch(ToolCall(id="t351", name=TOOL, arguments=arguments))
    return json.loads(execution.result.content), port


def _held_classes(payload: dict, preset_id: str) -> list[str]:
    for row in payload["held"] + payload["already_present"]:
        if row["preset_id"] == preset_id:
            return list(row["classes"])
    return []


def _held_details(payload: dict, preset_id: str) -> list[str]:
    for row in payload["held"] + payload["already_present"]:
        if row["preset_id"] == preset_id:
            return list(row["details"])
    return []


class TestTheRungFiresThroughTheProductionPath:
    """🔴 「부품은 초록인데 경로가 안 이어졌다」가 이 카드가 고치러 온 결함이라,
    능력을 직접 넣어주는 시험은 여기서 **충분하지 않다.** 정본 시트 셋을 그대로
    툴에 넘겨 `import_lxseq_presets` 를 두드린다.
    """

    def test_bm01_is_held_with_the_range_class(self):
        payload, _port = _dispatch(with_sheets=True)
        assert HOLD_VALUE_OUT_OF_RANGE in _held_classes(payload, "BM.01"), payload["held"]

    def test_the_detail_names_the_fixture_type_that_cannot_reach_45_degrees(self):
        payload, _port = _dispatch(with_sheets=True)
        detail = " / ".join(_held_details(payload, "BM.01"))
        assert MEGAPOINTE_TYPE in detail, detail
        # 구간은 **교집합**이다(5.0~42.0) — MegaPointe 단독 창(1.8~42.0)이 아니다.
        # 하한이 1.8 로 나오면 그룹 대조가 아니라 한 기종만 보고 있다는 뜻이다.
        assert "45" in detail and "5.0~42.0" in detail, detail
        assert "1.8" not in detail, detail

    def test_without_the_two_sheets_the_rung_does_not_fire(self):
        """대조군 — 배선이 없으면 안 걸린다. 이것이 없으면 위 둘은 다른 사유가
        우연히 그 클래스를 낸 것과 구별되지 않는다."""
        payload, _port = _dispatch(with_sheets=False)
        assert HOLD_VALUE_OUT_OF_RANGE not in _held_classes(payload, "BM.01")
        assert payload["capability"]["ok"] is False
        assert payload["capability"]["gap"] == "sheets_absent"

    def test_the_payload_says_the_comparison_actually_ran(self):
        """「범위 밖 0건」이 「대조해서 0건」과 「대조를 안 해서 0건」 두 뜻을 갖지
        않게 하는 절이다."""
        payload, _port = _dispatch(with_sheets=True)
        capability = payload["capability"]
        assert capability["ok"] is True
        assert capability["whole"] is True, capability
        assert set(capability["types_read"]) == {MEGAPOINTE_TYPE, SPIIDER_TYPE}
        assert capability["fixtures_read"] == 16

    def test_the_join_is_on_fid_not_on_the_sheets_type_name(self):
        """시트는 `Robe MegaPointe`, 콘솔은 `Robin MegaPointe` — 이름으로 조인하는
        회귀가 들어오면 기종이 하나도 안 붙어 이 검사가 빨개진다."""
        sheet_types = set()
        for line in PATCH.read_text(encoding="utf-8").splitlines()[1:]:
            columns = line.split(",")
            if len(columns) > 3 and columns[1] in ("MOVER-U", "MOVER-D"):
                sheet_types.add(columns[2])
        assert sheet_types == {"Robe MegaPointe", "Robe Spiider"}
        assert MEGAPOINTE_TYPE not in sheet_types  # 콘솔 이름은 시트에 없다
        payload, _port = _dispatch(with_sheets=True)
        assert MEGAPOINTE_TYPE in payload["capability"]["types_read"]

    def test_the_preview_path_writes_nothing_to_the_console(self):
        _payload, port = _dispatch(with_sheets=True)
        assert port.executed == []

    def test_bm02s_20_degrees_still_passes_the_range_rung(self):
        """대조군 — 교집합(5.0~42.0) 안이면 이 사유가 안 붙는다."""
        payload, _port = _dispatch(with_sheets=True)
        assert HOLD_VALUE_OUT_OF_RANGE not in _held_classes(payload, "BM.02")

    def test_bm04s_percent_frost_is_not_flagged_by_the_range_rung(self):
        """`Frost 30%` 는 퍼센트다 — 방향 미측정(t235)이라 도로 옮기지 않는다."""
        payload, _port = _dispatch(with_sheets=True)
        assert HOLD_VALUE_OUT_OF_RANGE not in _held_classes(payload, "BM.04")


class TestTheOfflineHalfOfTheChain:
    """사슬 1 단(그룹 명단)은 **오프라인**이다 — 시트 둘로만 선다."""

    def test_mover_all_expands_to_both_mover_groups(self):
        members = group_members_from_sheets(
            PATCH.read_text(encoding="utf-8"), GROUP.read_text(encoding="utf-8")
        )
        assert members["MOVER-ALL"] == tuple(sorted(_MOVER_U_FIDS + _MOVER_D_FIDS))
        assert members["MOVER-U"] == _MOVER_U_FIDS
        assert members["MOVER-D"] == _MOVER_D_FIDS

    def test_every_target_group_the_bm_sheet_names_is_resolvable_offline(self):
        members = group_members_from_sheets(
            PATCH.read_text(encoding="utf-8"), GROUP.read_text(encoding="utf-8")
        )
        wanted = {
            record.target_group
            for record in parse_preset_csv(BM.read_text(encoding="utf-8")).records
            if record.target_group
        }
        assert wanted == {"MOVER-ALL", "MOVER-U", "KEY"}
        assert wanted <= set(members), wanted - set(members)


class TestTheMoverAllZoomCeiling:
    """Part 3 — `MOVER-ALL` 이 공통으로 낼 수 있는 줌 상한을 값으로 남긴다.

    🔴 이 숫자는 **절반만 실측이다.** MegaPointe 상한 42.0 은 실측 replay 이고,
    Spiider 쪽은 구성된 대조군이므로 아래 교집합 상한은 「실측 두 기종의 교집합」이
    **아니다.** Spiider 판독이 들어오면 이 검사의 기대값이 바뀐다 — 그때 바뀌는
    것이 정상이고, 그 사실을 검사 이름과 이 문장이 나른다.
    """

    def test_the_intersection_ceiling_comes_from_the_narrower_type(self):
        rig = _rig(
            _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
            _fixture(521, SPIIDER_TYPE, SPIIDER_ZOOM),
        )
        window = group_capabilities(rig, "MOVER-ALL", [501, 521]).window("Zoom")
        assert window.high == 42.0  # MegaPointe 실측 상한이 이긴다
        assert window.low == 5.0  # 구성된 Spiider 하한이 이긴다

    def test_the_sheets_45_degrees_is_above_that_ceiling(self):
        """BM.01 은 시트를 고쳐야 하는 행이다 — 이 카드는 시트를 **안 고친다**."""
        assert 45.0 > 42.0
        assert "Zoom 45°" in BM.read_text(encoding="utf-8")

    def test_adding_a_type_can_only_lower_the_ceiling_never_raise_it(self):
        """🔴 **이 단조성이 BM.01 판정을 Spiider 실측 없이도 참으로 만든다.**

        교집합 상한은 `min(part.high)` 이므로 기종을 더 넣으면 낮아지거나 그대로다 —
        절대 올라가지 않는다. 그러므로 MegaPointe 실측 상한 42.0 은 `MOVER-ALL` 의
        **상한의 상한**이고, Spiider 를 실제로 재도 45° 가 교집합 안으로 들어올 수는
        없다. 「Spiider 를 안 재서 판정을 못 한다」가 아니라 「안 재도 이 방향은
        정해진다」다.

        이 성질이 깨지면(교집합을 합집합으로 바꾸는 회귀) BM.01 판정의 근거가
        사라진다 — 그래서 값으로 고정한다.
        """
        alone = group_capabilities(
            _rig(_fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM)), "MOVER-U", [501]
        ).window("Zoom")
        for other_high, other_low in ((90.0, 60.0), (50.0, 5.0), (10.0, 2.0)):
            widened = group_capabilities(
                _rig(
                    _fixture(501, MEGAPOINTE_TYPE, MEGAPOINTE_ZOOM),
                    _fixture(
                        521,
                        SPIIDER_TYPE,
                        AxisRange(
                            attribute="Zoom",
                            channel_name="c",
                            physical_from=other_high,
                            physical_to=other_low,
                        ),
                    ),
                ),
                "MOVER-ALL",
                [501, 521],
            ).window("Zoom")
            assert widened.high <= alone.high, (other_high, other_low, widened.high)
            assert widened.contains(45.0) is False


class TestTheJoinRunsThroughTheRealJoinNotAHandBuiltRig:
    """`_rig(...)` 로 손으로 세운 판독만 쓰면 조인 자체는 안 재진다."""

    def test_the_real_join_produces_the_two_types_from_the_fake_console(self):
        console = _FakeConsole()
        caps = read_rig_capabilities(
            console,
            console,
            root=_TYPES_ROOT,
            fixtures=[
                FixtureTypeRef(fid=fid, type_raw="FixtureType 11", mode_raw="1 Mode 1")
                for fid in _MOVER_U_FIDS
            ]
            + [
                FixtureTypeRef(fid=fid, type_raw="FixtureType 12", mode_raw="1 Mode 1")
                for fid in _MOVER_D_FIDS
            ],
            type_names={slot: name for slot, (name, _) in _TYPES.items()},
        )
        source = group_capabilities(caps, "MOVER-ALL", _MOVER_U_FIDS + _MOVER_D_FIDS)
        assert source.type_names == tuple(sorted((MEGAPOINTE_TYPE, SPIIDER_TYPE)))
        assert source.whole is True
        window = source.window("Zoom")
        assert (window.low, window.high) == (5.0, 42.0)
        assert window.descending is True  # 두 기종이 다 내림이므로 방향이 정해진다
