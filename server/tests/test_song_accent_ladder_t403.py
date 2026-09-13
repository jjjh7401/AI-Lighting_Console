"""카드 t403 -- 감독 지시(2026-09-13) "임팩트를 줄 곳에서 터뜨려야 한다"의
실측 결함.

재현: `_climax_section_index` 가 확정 구간의 표시 이름(``_confirmed_
section_names`` 가 붙인 "Chorus 1" 같은 이름)을 텍스트로 검색해 곡의 **첫**
코러스에서 오탐한다 -- 그 결과 `_accent_decision` 이 액센트를 곡 전체에서
딱 한 자리, 그것도 이른 자리에만 낸다.
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _build_unified_song_plan,
    _climax_section_index,
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


def _club_diver_shape() -> list[int]:
    d_levels = [2]
    d_levels += [3, 4, 3, 4, 3, 4, 3]
    for _ in range(25):
        d_levels.append(5)
    d_levels += [2, 1, 2, 1, 2]
    d_levels.append(5)
    return d_levels


class TestClimaxSectionIndexIsRoleAware:
    """t403 — 텍스트 검색이 이름에 박힌 역할 어휘("Chorus 1")를 절정으로
    오독하지 않는다."""

    def test_red_before_fix_would_pick_the_first_chorus_by_name_text(self):
        """재현: 이름이 전부 "Chorus N" 이면 텍스트 검색은 항상 **첫** 코러스를
        고른다 — 회차·D 레벨과 무관하게. 이 테스트는 고친 함수가 그 함정을
        피해간다는 것을 검증한다(회귀 방지 겸 명세)."""
        sections = _confirmed_sections(_club_diver_shape())
        chorus_indexes = [i + 1 for i, s in enumerate(sections) if s.role == "chorus"]
        first_chorus_index = chorus_indexes[0]
        last_chorus_index = chorus_indexes[-1]
        climax_index = _climax_section_index(sections)
        assert climax_index != first_chorus_index, (
            "절정이 여전히 첫 코러스(3초 지점)에 꽂혀 있다 — t403 결함 재현"
        )
        assert climax_index == last_chorus_index

    def test_ties_break_to_the_later_occurrence(self):
        d_levels = [2, 5, 3, 5, 1]  # chorus at 2 and 4, tied D level
        sections = _confirmed_sections(d_levels)
        assert sections[1].role == "chorus"
        assert sections[3].role == "chorus"
        assert _climax_section_index(sections) == 4

    def test_no_chorus_falls_back_to_finale(self):
        d_levels = [2, 3, 3, 5]
        sections = _confirmed_sections(d_levels)
        assert sections[-1].role == "finale"
        assert _climax_section_index(sections) == len(sections)

    def test_text_search_path_is_unchanged_when_no_role_is_set(self):
        """role 이 전혀 없는(지시문 직접 입력) 경로는 기존 텍스트 검색을
        그대로 쓴다 — 회귀 없음."""
        sections = [
            PositionSheetSection(name="인트로", start_ms=0, mood=""),
            PositionSheetSection(name="후렴", start_ms=1000, mood="드롭"),
            PositionSheetSection(name="아웃트로", start_ms=2000, mood=""),
        ]
        assert _climax_section_index(sections) == 2


class TestAccentLadderFiresMoreThanOnce:
    """t403 통합 — 141초 곡에 액센트가 39구간 중 1개(3초 지점)뿐이던 것을
    고쳐, 짧고 드물게(전부는 아니게) 여러 자리에서 찍히게 한다."""

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

    def test_before_fix_only_one_section_carries_an_accent(self):
        plan = self._plan(_club_diver_shape())
        accented = [d for d in plan.sections if d.accent.accents]
        assert len(accented) > 1, f"액센트가 여전히 {len(accented)}자리뿐이다 — t403 결함 재현"

    def test_accents_stay_rare_not_on_every_chorus(self):
        """정본 §6.1 — 액센트는 짧고 드물어야 한다. 25회 코러스 전부를
        찍으면 그 규범을 어긴다."""
        plan = self._plan(_club_diver_shape())
        accented = [d for d in plan.sections if d.accent.accents]
        assert len(accented) < 25

    def test_the_first_accent_is_no_longer_three_seconds_in(self):
        plan = self._plan(_club_diver_shape())
        accented_indexes = [index for index, d in enumerate(plan.sections) if d.accent.accents]
        assert accented_indexes, "액센트가 하나도 없다"
        assert accented_indexes[0] != 1, "여전히 두 번째 구간(3초 지점)이 첫 액센트다"

    def test_finale_carries_a_white_flash(self):
        plan = self._plan(_club_diver_shape())
        finale_decision = plan.sections[-1]
        assert any("flash" in a for a in finale_decision.accent.accents)

    def test_climax_index_still_wins_when_it_coincides_with_the_ladder(self):
        """장부 규율 — climax_index 와 사다리의 마지막 코러스가 같은 자리를
        가리키면 하나의 액센트만 남는다(§6.1 "한 큐에 하나")."""
        plan = self._plan(_club_diver_shape())
        for decision in plan.sections:
            assert len(decision.accent.accents) <= 1
