"""헤드룸 4축 + G5 경고 4조건 시험 — SPEC-LDDESIGN-001 M4
(REQ-LDDESIGN-047, 050~052, 카드 t437).

두 개의 날조 대조군(fabricated control)을 포함한다
(``verification-claim-integrity`` "양팔 대조"):

- ``TestG5ChorusOneCondition`` — REQ-051 조건 2의 OR 로직을, 일부러
  AND 로 구현한 지역 재구현과 나란히 돌려 실제 구현이 그 차이를
  구분해 냄을 보인다.
- ``TestBridgeReducedSectionUnitComparison`` — REQ-047 의 "구간 단위
  비교"를, 일부러 큐-대-큐(직전 큐와만 비교)로 구현한 지역 재구현과
  나란히 돌려 구간 단위 비교만이 브릿지 2큐 분할을 오탐하지 않음을
  보인다.
"""

from __future__ import annotations

from server.concept.cue_model import CueState
from server.concept.headroom import (
    SectionCueSnapshot,
    bridge_reduced,
    compute_cue_headroom,
    g5_warnings,
)


def _state(dim=None, color=None, pos="home", motion=0) -> CueState:
    return CueState(dim=dim or {}, color=color, pos=pos, motion=motion)


class TestComputeCueHeadroom:
    """REQ-050 — 매 구간 큐마다 4축(미사용 그룹·유보색·유보 효과·남은
    상승 단계)을 계산한다."""

    def test_four_axes_computed_against_known_state(self) -> None:
        state = _state(dim={"KEY": 75, "FOH": 75, "BACK": 75}, motion=1)
        headroom = compute_cue_headroom(
            state,
            reserved_colors_remaining=("흰색",),
            reserved_effects=("STROBE",),
        )
        # 기본 GROUP_ROSTER 는 11개 — 켜진 3개를 빼면 미사용 8개.
        assert headroom.unused_groups == 8
        assert headroom.reserved_colors == ("흰색",)
        assert headroom.reserved_effects == ("STROBE",)
        assert headroom.remaining.motion == 3 - 1
        assert headroom.remaining.dimmer == 100 - 75

    def test_all_off_state_has_full_headroom(self) -> None:
        state = _state()
        headroom = compute_cue_headroom(state)
        assert headroom.unused_groups == 11
        assert headroom.remaining.motion == 3
        assert headroom.remaining.dimmer == 100


class TestBridgeReducedSectionUnitComparison:
    """REQ-047 — 브릿지 비교 기준은 그 직전 "브릿지가 아닌" 구간이다
    (구간 단위 비교, 큐 단위가 아니다)."""

    def _snap(
        self,
        *,
        section: str,
        is_bridge: bool,
        groups_on: int,
        top_dimmer: int,
    ) -> SectionCueSnapshot:
        return SectionCueSnapshot(
            section=section,
            occurrence=1,
            is_bridge=is_bridge,
            groups_on=groups_on,
            top_dimmer=top_dimmer,
            effects_on=frozenset(),
            color=None,
        )

    def test_single_bridge_reduced_relative_to_prior_non_bridge(self) -> None:
        snapshots = [
            self._snap(section="Final Chorus", is_bridge=False, groups_on=10, top_dimmer=100),
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30),
        ]
        assert bridge_reduced(snapshots) is True

    def test_single_bridge_not_reduced_is_flagged(self) -> None:
        snapshots = [
            self._snap(section="Final Chorus", is_bridge=False, groups_on=2, top_dimmer=20),
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30),
        ]
        assert bridge_reduced(snapshots) is False

    def test_no_preceding_non_bridge_is_skipped_not_flagged(self) -> None:
        snapshots = [self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30)]
        assert bridge_reduced(snapshots) is True

    def test_bridge_split_into_two_cues_does_not_false_warn(self) -> None:
        """REQ-047 의 동기가 된 실측 결함 — 브릿지가 끄기 큐(빠르게
        낮춤)와 켜기 큐(30% 로 안정) 두 개로 나뉘면, 두 번째 큐가 첫
        번째 큐보다 살짝 높을 수 있다. 구간 단위(직전 "브릿지가 아닌"
        구간과 비교)로는 여전히 "감소"이지만, 순진한 큐-대-큐(직전 큐와
        비교) 로직으로는 두 번째 큐가 "증가"로 보여 오탐한다.
        """
        snapshots = [
            self._snap(section="Final Chorus", is_bridge=False, groups_on=10, top_dimmer=100),
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=20),  # 끄기 큐
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30),  # 켜기 큐
        ]

        # 정상 경로 — 구간 단위 비교는 두 브릿지 큐 모두 직전 "브릿지
        # 아닌" 구간(Final Chorus)보다 낮으므로 감소로 정확히 판정한다.
        assert bridge_reduced(snapshots) is True

        # 날조 대조군 — 일부러 큐-대-큐(직전 큐와만 비교)로 재구현하면,
        # 두 번째 브릿지 큐(30)가 첫 번째 브릿지 큐(20)보다 커서
        # "감소 아님"으로 오탐한다. 이 대조군이 실패(False)를 내야
        # 정상 경로의 True 가 공허하지 않음이 증명된다.
        def _cue_to_cue_reduced(snaps: list[SectionCueSnapshot]) -> bool:
            ok = True
            for i, snap in enumerate(snaps):
                if not snap.is_bridge or i == 0:
                    continue
                prev = snaps[i - 1]
                if not (snap.top_dimmer < prev.top_dimmer and snap.groups_on < prev.groups_on):
                    ok = False
            return ok

        assert _cue_to_cue_reduced(snapshots) is False

    def test_two_bridges_each_compare_to_the_same_prior_non_bridge(self) -> None:
        snapshots = [
            self._snap(section="Final Chorus", is_bridge=False, groups_on=10, top_dimmer=100),
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30),
            self._snap(section="Bridge", is_bridge=True, groups_on=2, top_dimmer=30),
        ]
        assert bridge_reduced(snapshots) is True


class TestG5IntroCondition:
    def test_warns_when_intro_has_every_group_on(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=11,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert any("Intro" in w for w in warnings)

    def test_no_warning_when_intro_partial(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=1,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert not any("Intro" in w for w in warnings)

    def test_none_intro_groups_on_never_warns(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert not any("Intro" in w for w in warnings)


class TestG5ChorusOneCondition:
    """REQ-051 조건 2 — BLIND/STROBE 켜짐 **또는** 색이 흰색(OR, AND
    아님)."""

    def _and_version(self, effects_on: frozenset[str], color: str | None) -> bool:
        """일부러 틀리게(AND) 재구현한 지역 대조군 — 실제 구현(OR)과
        결과가 갈리는 지점을 시험이 실제로 통과하는지 확인한다."""
        return bool(effects_on & {"BLIND", "STROBE"}) and color == "흰색"

    def test_effect_on_but_not_white_still_warns_or_not_and(self) -> None:
        effects_on = frozenset({"BLIND"})
        color = "파랑"
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=effects_on,
            chorus1_color=color,
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert any("Chorus 1" in w for w in warnings)
        # 날조 대조군 — AND 로 재구현하면 이 입력에서 경고가 나오지
        # 않는다(0.5 만 성립). 실제 함수가 이 차이를 구분함을 보인다.
        assert self._and_version(effects_on, color) is False

    def test_white_color_but_no_effect_still_warns(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="흰색",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert any("Chorus 1" in w for w in warnings)

    def test_neither_effect_nor_white_does_not_warn(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert not any("Chorus 1" in w for w in warnings)


class TestG5BridgeCondition:
    def test_warns_when_bridge_not_reduced(self) -> None:
        snapshots = [
            SectionCueSnapshot(
                section="Final Chorus",
                occurrence=1,
                is_bridge=False,
                groups_on=2,
                top_dimmer=20,
                effects_on=frozenset(),
                color=None,
            ),
            SectionCueSnapshot(
                section="Bridge",
                occurrence=1,
                is_bridge=True,
                groups_on=2,
                top_dimmer=30,
                effects_on=frozenset(),
                color=None,
            ),
        ]
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=snapshots,
            final_chorus_has_new_axis=True,
        )
        assert any("Bridge" in w for w in warnings)

    def test_no_warning_when_no_bridge(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert not any("Bridge" in w for w in warnings)


class TestG5FinalChorusCondition:
    def test_warns_when_no_new_axis(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=False,
        )
        assert any("Final Chorus" in w for w in warnings)

    def test_no_warning_when_new_axis_present(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=True,
        )
        assert not any("Final Chorus" in w for w in warnings)

    def test_none_means_not_applicable_and_does_not_warn(self) -> None:
        # Final Chorus 가 아예 없는 곡(n/a) — None 은 "새 축 없음"이
        # 아니라 "해당 없음"이다. 경고를 내면 n/a 곡마다 오탐한다.
        warnings = g5_warnings(
            intro_groups_on=None,
            total_groups=11,
            chorus1_effects_on=frozenset(),
            chorus1_color="노랑",
            bridge_snapshots=(),
            final_chorus_has_new_axis=None,
        )
        assert not any("Final Chorus" in w for w in warnings)


class TestG5NeverBlocks:
    """REQ-052 — 헤드룸 경고는 조립을 막지 않는다: 모든 조건이 동시에
    성립해도 예외 없이 튜플을 반환한다."""

    def test_all_four_conditions_at_once_returns_without_raising(self) -> None:
        snapshots = [
            SectionCueSnapshot(
                section="Final Chorus",
                occurrence=1,
                is_bridge=False,
                groups_on=2,
                top_dimmer=20,
                effects_on=frozenset(),
                color=None,
            ),
            SectionCueSnapshot(
                section="Bridge",
                occurrence=1,
                is_bridge=True,
                groups_on=2,
                top_dimmer=30,
                effects_on=frozenset(),
                color=None,
            ),
        ]
        warnings = g5_warnings(
            intro_groups_on=11,
            total_groups=11,
            chorus1_effects_on=frozenset({"BLIND", "STROBE"}),
            chorus1_color="흰색",
            bridge_snapshots=snapshots,
            final_chorus_has_new_axis=False,
        )
        assert len(warnings) == 4

    def test_degenerate_zero_total_groups_does_not_raise(self) -> None:
        warnings = g5_warnings(
            intro_groups_on=0,
            total_groups=0,
            chorus1_effects_on=frozenset(),
            chorus1_color=None,
            bridge_snapshots=(),
            final_chorus_has_new_axis=None,
        )
        assert isinstance(warnings, tuple)
