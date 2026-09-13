"""카드 t386 — 페이드가 D 레벨만 보고 정해져, 절정(chorus)과 종결(finale)이
같은 D5 를 받으면 같은 하프비트 페이드를 받았다.

측정: 126.048 BPM · 1마디 1.904s 기준 D 레벨별 페이드(§3 표, `energy.py`)는
D1→3.808s(2마디) · D2→1.904s(1마디) · D4→0.714s(1.5박) · D5→0.238s(반박) —
16배 스프레드로 이미 다양하다. 그런데 `_ARC_D_LEVEL`(session.py)은
chorus 와 finale 이 똑같이 D5 를 받으므로, 곡을 닫는 finale 큐가
chorus 히트용 반박 페이드를 그대로 물려받았다. 연출 기준 §6은
"outro → 느린 페이드 1회"를 요구한다.

고침: `SectionDecision.role` 이 "finale" 이면 D 레벨(밝기)은 그대로 두고
페이드만 D1 행(§3 표에서 가장 느린 페이드)으로 바꾼다.
"""

from __future__ import annotations

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
)


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 5)
    ]
    return build_rig_profile(patch=patch, groups={}, coords=[])


def _section(
    index: int, label: str, start_ms: int, *, d_level: int, role: str | None
) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_arc"),
        palette=PaletteDecision(colors=("blue", "white"), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(),
        cue_number=index,
        role=role,
    )


def _plan(sections):
    return UnifiedSongLightingPlan(
        song_title="t386 Test",
        sequence_name="t386 Test Seq",
        sections=sections,
        timing=TimingPlan.timecode(77),
        music_profile=MusicProfile(bpm=126.048, palette=("blue", "white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


class TestFinaleGetsASlowFadeInsteadOfChorusHalfBeat:
    def test_chorus_and_finale_share_d5_but_not_the_same_fade(self) -> None:
        """재현 대상: 고침 전에는 이 둘의 fade_seconds 가 바이트 동일했다."""
        chorus = _section(1, "Chorus 1", 0, d_level=5, role="chorus")
        finale = _section(2, "Finale", 10_000, d_level=5, role="finale")
        result = compose_song_cue_bundle(_plan((chorus, finale)))
        cues = {cue.section_index: cue for cue in result.bundle.cues}
        assert cues[1].d_level == cues[2].d_level == 5, "전제가 깨졌다 — 둘 다 D5 여야 한다"
        assert cues[1].fade_seconds != cues[2].fade_seconds, (
            f"chorus={cues[1].fade_seconds} finale={cues[2].fade_seconds} — 여전히 같다"
        )

    def test_finale_fade_matches_the_d1_slow_fade_row(self) -> None:
        finale = _section(1, "Finale", 0, d_level=5, role="finale")
        plain_d1 = _section(2, "D1 reference", 5_000, d_level=1, role=None)
        result = compose_song_cue_bundle(_plan((finale, plain_d1)))
        cues = {cue.section_index: cue for cue in result.bundle.cues}
        # D1 이 그 자체로 이미 가장 느린 페이드 행이므로, finale 은 그 값과
        # 같아야 한다(§3 의 D1 행을 새 숫자 없이 그대로 재사용).
        assert cues[1].fade_seconds == cues[2].fade_seconds

    def test_finale_brightness_axis_is_unaffected_by_the_slow_fade(self) -> None:
        """페이드만 바뀌고 디머(밝기)는 D5 그대로여야 한다 — 두 축은 분리."""
        finale = _section(1, "Finale", 0, d_level=5, role="finale")
        result = compose_song_cue_bundle(_plan((finale,)))
        cue = result.bundle.cues[0]
        assert cue.d_level == 5
        assert cue.dimmer.key_pct > 50.0, "D5 디머 범위를 벗어났다"

    def test_a_fade_override_still_wins_over_the_role_based_slow_fade(self) -> None:
        finale = SectionDecision(
            section=TimestampedSection(index=1, label="Finale", start_ms=0),
            d=DLevelDecision(level=5, source="section_arc"),
            palette=PaletteDecision(colors=("blue",), source="director"),
            position=PositionDecision(preset="Center", source="director"),
            texture=TextureDecision(label="long fade", source="genre"),
            fx=FxDecision(allowed=(), disabled=(), density=0),
            accent=AccentDecision(),
            cue_number=1,
            fade_override=2.5,
            role="finale",
        )
        result = compose_song_cue_bundle(_plan((finale,)))
        assert result.bundle.cues[0].fade_seconds == 2.5

    def test_non_finale_roles_are_unaffected_byte_identical(self) -> None:
        chorus = _section(1, "Chorus 1", 0, d_level=5, role="chorus")
        verse = _section(2, "Verse 1", 5_000, d_level=3, role="verse")
        result = compose_song_cue_bundle(_plan((chorus, verse)))
        bundle = result.bundle
        # 회귀 없음 — 기존 D 레벨 기반 값과 같아야 한다(카드 t386 이전 동작).
        assert bundle.cues[0].fade_seconds == pytest_approx_half_beat(126.048)
        assert bundle.cues[1].fade_seconds > 0


def pytest_approx_half_beat(bpm: float) -> float:
    """D5 행의 페이드(0~1박 평균 0.5박)를 그대로 계산 — 새 숫자를 지어내지
    않고 §3 표와 같은 산식을 쓴다."""
    return 0.5 * (60.0 / bpm)
