"""카드 t439 — REQ-LDDESIGN-004/REQ-LDDESIGN-030/AC-LDDESIGN-016.

`_arc_palette`/`_per_chorus_palette`(둘 다 `server/web/session.py`)는 더 이상
후렴 회차마다 보조색을 회전시키지 않는다 — 후렴(Chorus) 구간 전체는 동일한
주색을 유지한다(Final Chorus의 클라이맥스 색 전환만 예외). 회차 에스컬레이션은
REQ-043의 6개 축(기구군 수·면적·밝기·모션·포지션·큐 밀도)이 표현하고, 색은
그 축에 없다.

RED 재현 — 이 파일의 단정은 고치기 전(`origin/main@903f1b75`) 코드에서
`_arc_palette(("blue","white"), "chorus", k)` 가 k=1..6 에서 (blue,warm
white)/(blue,magenta) 두 상태를 교대로 냈던 것과 같은 결함을 정면으로
재현한다(AC-LDDESIGN-016 Given 문장 그대로).
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _arc_palette,
    _build_unified_song_plan,
    _per_chorus_palette,
    _section_palette_choice,
)


class TestArcPaletteChorusIdentityAcrossOccurrences:
    """REQ-LDDESIGN-004 — `_arc_palette` 는 chorus/finale 역할에서 회차와
    무관하게 항상 occurrence=1 의 팔레트를 낸다."""

    def test_chorus_accent_is_identical_across_six_occurrences(self):
        base = ("blue",)
        palettes = {_arc_palette(base, "chorus", occurrence=k) for k in range(1, 7)}
        assert len(palettes) == 1, (
            f"코러스 6회차가 팔레트 {len(palettes)}종을 냈다 — REQ-004 위반 (t439)"
        )

    def test_chorus_occurrence_n_equals_occurrence_one_byte_for_byte(self):
        base = ("blue", "white")
        first = _arc_palette(base, "chorus", occurrence=1)
        for occurrence in range(2, 9):
            later = _arc_palette(base, "chorus", occurrence=occurrence)
            assert later == first, (
                f"회차 {occurrence}: {later} != 1회차 {first} — REQ-004 위반"
            )

    def test_finale_accent_is_identical_across_occurrences(self):
        """finale 은 보통 회차 1로만 나타나지만, 함수 계약 자체가 회차를
        무시해야 한다(REQ-004 는 chorus 뿐 아니라 finale 도 명시한다)."""
        base = ("blue",)
        palettes = {_arc_palette(base, "finale", occurrence=k) for k in range(1, 5)}
        assert len(palettes) == 1

    def test_verse_intro_bridge_rotation_is_unaffected_regression_guard(self):
        """REQ-004/030 은 후렴(chorus/finale) 한정이다 — verse/intro/bridge
        의 회차별 보조색 회전은 이 카드의 범위 밖이며 바이트 동일해야 한다.

        메인 컬러는 "red" 로 둔다 — "블루" 를 메인으로 두면
        `_distinct_from_primary` 의 언어 중복 회피(카드 t406)가 verse
        아크(("blue","cyan"))의 "blue" 쪽 회전 산출을 매번 "cyan" 으로
        가려서, 회전 자체가 살아 있어도 이 회귀 가드가 우연히 항등을
        관측하게 된다 — 그 충돌을 피하려고 아크 색과 겹치지 않는 메인을
        고른다.
        """
        base = ("red",)
        for role in ("intro", "verse", "bridge"):
            first = _arc_palette(base, role, occurrence=1)
            second = _arc_palette(base, role, occurrence=2)
            if role == "verse":
                # verse 아크(("blue","cyan"))는 회차 2 에서 회전해 2회차가
                # 1회차와 달라야 한다 — 카드 t402 가 이미 실측한 성질.
                assert first != second, f"{role} 회전이 사라졌다 — 회귀"


class TestPerChorusChorusIdentityAcrossOccurrences:
    """REQ-LDDESIGN-004 — `_per_chorus_palette` 도 같은 계약을 진다."""

    def test_per_chorus_ladder_no_longer_varies_by_occurrence(self):
        base = ("blue",)
        palettes = {_per_chorus_palette(base, "chorus", occurrence=k) for k in range(1, 7)}
        assert len(palettes) == 1, (
            f"per_chorus 사다리가 회차마다 여전히 갈린다 — {len(palettes)}종 (REQ-004 위반)"
        )

    def test_per_chorus_matches_arc_palette_for_every_occurrence(self):
        """REQ-004 정정 후: `per_chorus` 는 이제 `modulate` 와 바이트 동일하다
        (둘 다 occurrence=1 의 항등 출력으로 얼어붙는다)."""
        base = ("blue",)
        for occurrence in range(1, 6):
            assert _per_chorus_palette(base, "chorus", occurrence) == _arc_palette(
                base, "chorus", 1
            )

    def test_section_palette_choice_per_chorus_mode_is_frozen(self):
        """`_section_palette_choice` 를 통한 실제 소비 경로에서도 동일해야
        한다(session.py:1884 분기, Q2B_COLOR_USAGE="per_chorus")."""
        profile = MusicProfile(palette=("블루",))
        results = [
            _section_palette_choice(
                PositionSheetSection(name="S", start_ms=0, mood=""),
                role="chorus",
                profile=profile,
                color_tendency="블루",
                palette_mode="palette",
                concept_colors=(),
                occurrence=n,
                color_usage="per_chorus",
            )[0]
            for n in range(1, 6)
        ]
        assert len(set(results)) == 1, f"per_chorus 소비 경로가 회차마다 갈린다 — {results}"


def _confirmed_chorus_plan(chorus_occurrences: int, *, with_finale: bool):
    """확정 구간 합성 — intro 1 + chorus N회 (+ finale 1). role 을 직접 명시해
    회차 계산을 `_build_unified_song_plan` 자신이 하게 만든다(카드 t402 방식)."""
    sections = [
        PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro"),
    ]
    start_ms = 4000
    for _ in range(chorus_occurrences):
        sections.append(
            PositionSheetSection(
                name="Chorus", start_ms=start_ms, mood="", d_level=5, role="chorus"
            )
        )
        start_ms += 4000
    if with_finale:
        sections.append(
            PositionSheetSection(
                name="Final Chorus", start_ms=start_ms, mood="", d_level=5, role="finale"
            )
        )
    profile = MusicProfile()
    return _build_unified_song_plan(
        sections=sections,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=(),
        timing=TimingPlan.manual_go(),
        sequence_no=121,
    )


class TestBuildUnifiedSongPlanChorusColorIdentity:
    """AC-LDDESIGN-016 통합 — 실제 계획 조립 층에서 6회 이상 반복되는 후렴이
    전부 동일한 팔레트를 낸다. Final Chorus 는 별도 역할(finale)이라 클라이맥스
    색 전환 예외를 이 단정과 충돌 없이 함께 검증한다."""

    def test_all_non_final_chorus_occurrences_share_one_palette(self):
        plan = _confirmed_chorus_plan(6, with_finale=True)
        chorus_palettes = {
            tuple(decision.palette.colors)
            for decision in plan.sections
            if decision.role == "chorus"
        }
        assert len(chorus_palettes) == 1, (
            f"REQ-030 위반 — 후렴 구간 전체가 팔레트 {len(chorus_palettes)}종을 냈다: "
            f"{chorus_palettes}"
        )

    def test_final_chorus_may_still_differ_the_climax_exception(self):
        """REQ-030 의 명시된 유일한 예외 — Final Chorus(role=finale)는 이 항등
        단정에서 제외된다. 여기서는 존재만 확인한다(색 전환 메커니즘 자체는
        이 카드의 범위 밖, concept 계층/§3.5).
        """
        plan = _confirmed_chorus_plan(4, with_finale=True)
        roles = [decision.role for decision in plan.sections]
        assert "finale" in roles


class TestFabricatedControlRotationStillBreaksTheGuard:
    """날조 대조군 — REQ-004 를 되돌리면(회차 회전을 되살리면) 위 단정들이
    실제로 빨개진다는 것을 보여, 위 GREEN 이 공허하지 않음을 증명한다."""

    def test_reintroducing_occurrence_rotation_fails_the_identity_assertion(self, monkeypatch):
        import server.web.session as session_module

        original_arc_palette = session_module._arc_palette

        def _rotating_arc_palette(base, role, occurrence=1):
            """고치기 전 동작 재현 — chorus/finale 도 예외 없이 회전한다."""
            from server.design.cue_density import rotate_palette

            arc = session_module._ARC_PALETTE.get(role)
            if arc is None:
                return base or ("white",)
            rotated = arc
            if len(arc) > 1 and occurrence > 1:
                rotated = rotate_palette(arc, occurrence - 1)
            if not base:
                return rotated
            primary = base[0]
            if role == "verse":
                accent = session_module._distinct_from_primary(
                    rotated[-1], primary, fallback=rotated[0]
                )
            else:
                accent = session_module._distinct_from_primary(
                    rotated[0], primary, fallback=rotated[-1]
                )
            return tuple(dict.fromkeys((primary, accent)))

        monkeypatch.setattr(session_module, "_arc_palette", _rotating_arc_palette)
        try:
            base = ("blue",)
            palettes = {
                session_module._arc_palette(base, "chorus", occurrence=k) for k in range(1, 7)
            }
            assert len(palettes) > 1, (
                "날조 대조군이 공허하다 — 회전을 되살렸는데도 상태가 하나뿐이다"
            )
        finally:
            assert session_module._arc_palette is _rotating_arc_palette
            monkeypatch.setattr(session_module, "_arc_palette", original_arc_palette)
