"""카드 t402 — 감독 지시(2026-09-13) "각 부분마다 변조를 주어야 한다"의
실측 결함.

재현: 확정 구간(`role` 이 명시된 경로, 카드 t393)에서 같은 역할이 반복되면
(코러스 25회 등) `_section_palette_choice` -> `_arc_palette` 이 매번 바이트
동일한 팔레트를 낸다 — 회차를 구분하지 않기 때문이다.

`_build_unified_song_plan` 을 확정 구간으로 직접 몰아 재현한다 — 웹소켓
통합 하네스 없이도 결정 층 자체의 결함이라 이 폭으로 충분하다.
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _arc_accent_weight,
    _arc_palette,
    _build_unified_song_plan,
    _confirmed_section_names,
    _infer_confirmed_role,
)


def _confirmed_sections(d_levels: list[int]) -> list[PositionSheetSection]:
    """카드 t393 확정 구간 합성과 같은 모양 -- 이름 비고 role 명시, mood 공백."""
    roles = [_infer_confirmed_role(i, d_levels) for i in range(len(d_levels))]
    names = _confirmed_section_names(roles)
    sections = []
    start_ms = 0
    for name, role, level in zip(names, roles, d_levels, strict=True):
        sections.append(
            PositionSheetSection(name=name, start_ms=start_ms, mood="", d_level=level, role=role)
        )
        start_ms += 4000
    return sections


# 실측(카드 지시문): "Club Diver.mp3" 39구간 중 코러스 25회 -- D 레벨은 여기서
# 코러스를 최고치로, 나머지를 낮게 흉내만 낸다(형태 재현).
def _club_diver_shape() -> list[int]:
    d_levels = [2]  # intro
    d_levels += [3, 4, 3, 4, 3, 4, 3]  # verse x7
    for _ in range(25):
        d_levels.append(5)  # chorus x25
    d_levels += [2, 1, 2, 1, 2]  # bridge x5
    d_levels.append(5)  # finale
    return d_levels


class TestArcPaletteVariesByOccurrence:
    """t402 — 같은 역할의 반복 회차가 서로 다른 팔레트를 낸다, 메인 컬러는
    항상 남는다."""

    def test_first_and_second_chorus_occurrence_differ(self):
        base = ("블루",)
        first = _arc_palette(base, "chorus", occurrence=1)
        second = _arc_palette(base, "chorus", occurrence=2)
        assert first != second, "회차가 달라져도 팔레트가 바이트 동일하다 — t402 결함 재현"

    def test_main_colour_is_always_present_across_occurrences(self):
        base = ("블루",)
        for occurrence in range(1, 6):
            colors = _arc_palette(base, "chorus", occurrence=occurrence)
            assert "블루" in colors, f"회차 {occurrence} 에서 메인 컬러가 사라졌다"

    def test_occurrence_one_is_byte_identical_to_the_old_default(self):
        """회귀 없음 — occurrence 생략(기본값 1)은 고치기 전과 동일해야 한다."""
        base = ("블루",)
        assert _arc_palette(base, "chorus") == _arc_palette(base, "chorus", occurrence=1)

    def test_rotation_cycles_back_in_hue_and_weight_separates_the_states(self):
        """카드 t406 핫픽스로 갱신 — 색상 회전(hue)은 회전 주기 2 그대로다
        (아크가 2색뿐이고, 색 문자열은 콘솔 범례 조회가 걸려야 해서 무게
        수식어를 섞지 않는다 — 코디네이터 지시). 원래 이 테스트는 "회차
        3이 회차 1과 바이트 동일하다"를 A-B-A-B 결함(t402/t406 이전)의
        재현으로 검증했는데, 색만 보면 그 동일함은 지금도 유지된다 —
        상태를 가르는 것은 이제 `_arc_accent_weight`(별도 채널)다."""
        base = ("블루",)
        first = _arc_palette(base, "chorus", occurrence=1)
        third = _arc_palette(base, "chorus", occurrence=3)
        # 카드 t409 — 첫 칸은 항상 감독의 메인 컬러(반환값 순서가 바뀌었다).
        assert first == third == ("블루", "warm white")
        # 색은 같아도 무게 라벨이 갈라 회차를 구분한다.
        assert _arc_accent_weight("chorus", 1) != _arc_accent_weight("chorus", 3)


class TestBuildUnifiedSongPlanVariesRepeatedRoles:
    """t402 통합 — 확정 구간 39개(클럽 다이버 모양)를 실제로 계획에 태워
    코러스 25회가 더 이상 팔레트 1종으로 뭉개지지 않는지 확인한다."""

    def _plan(self, d_levels: list[int]):
        sections = _confirmed_sections(d_levels)
        profile = MusicProfile()
        return _build_unified_song_plan(
            sections=sections,
            profile=profile,
            rig=build_rig_profile(patch=[], groups={}, coords=[]),
            records=(),
            timing=TimingPlan.manual_go(),
            sequence_no=120,
        )

    def test_before_fix_all_25_choruses_share_one_palette(self):
        plan = self._plan(_club_diver_shape())
        chorus_labels = {
            f"Chorus {n}" for n in range(1, 26)
        }  # _confirmed_section_names 이 붙인 이름과 같은 형태
        chorus_palettes = [
            tuple(decision.palette.colors)
            for decision in plan.sections
            if decision.section.label in chorus_labels
        ]
        distinct = set(chorus_palettes)
        assert len(distinct) > 1, (
            f"코러스 25구간이 여전히 팔레트 {len(distinct)}종뿐이다 — t402 결함 재현"
        )

    def test_finale_and_intro_are_unaffected_singleton_roles(self):
        """싱글턴 역할(intro·finale)은 회차가 항상 1 — 회귀 없이 기존 팔레트."""
        plan = self._plan(_club_diver_shape())
        # intro is section 1, finale is the last section.
        assert plan.sections[0].section.label.startswith("Intro")
        assert plan.sections[-1].section.label == "Finale"
