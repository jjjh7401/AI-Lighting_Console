"""카드 t394 — 정본 §6 표(docs/proposals/song-structure-lighting-standard.md
~181-202행) "breakdown · bridge → 밝기 20~35% · 무빙·이펙트 정지".

측정(2026-09-20, /private/tmp/claude-501/t394_probe/probe.py, main 트리):
`_section_cue` 는 fx/움직임을 `axis_budget(decision.d.level, ...)` 로만
정하고, role 이 "bridge" 인 구간(session.py `_infer_confirmed_role` 이
breakdown 을 접어 넣는 그 role)은 D2 에서 `fx.permitted == ('slow tilt',)`
`density=1` `speed_beats=0.25` 로 나왔다 — 정지가 아니다. D1 은 그 D 레벨의
예산이 우연히 0 이라 정지처럼 보였을 뿐이다.

고침: `decision.role == "bridge"` 이면 D 레벨과 무관하게 fx 를 전부 비우고
포지션 폭 타이어를 최저(POSITION_WIDTH_TIERS[0], "narrow")로 고정한다.
밝기(디머)·페이드는 §6 이 건드리지 않으므로 그대로 둔다.
"""

from __future__ import annotations

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.lint import POSITION_WIDTH_TIERS
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
        texture=TextureDecision(label="sparse", source="genre"),
        fx=FxDecision(allowed=("slow tilt",), disabled=(), density=1),
        accent=AccentDecision(),
        cue_number=index,
        role=role,
    )


def _plan(sections):
    return UnifiedSongLightingPlan(
        song_title="t394 Test",
        sequence_name="t394 Test Seq",
        sections=sections,
        timing=TimingPlan.timecode(77),
        music_profile=MusicProfile(bpm=126.048, palette=("blue", "white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


class TestBridgeStopsMovementAndEffectRegardlessOfDLevel:
    def test_bridge_at_d2_has_no_permitted_fx(self) -> None:
        """재현 대상: 고침 전에는 D2 bridge 가 ('slow tilt',) 를 permit 했다."""
        bridge = _section(1, "Bridge", 0, d_level=2, role="bridge")
        result = compose_song_cue_bundle(_plan((bridge,)))
        cue = result.bundle.cues[0]
        assert cue.fx.permitted == (), f"still permits fx: {cue.fx.permitted!r}"
        assert cue.fx.density == 0
        assert cue.fx.speed_beats is None

    def test_bridge_at_d3_has_no_permitted_fx(self) -> None:
        """§6 은 D 레벨을 조건으로 걸지 않는다 — role 이 bridge 면 D3 도 정지."""
        bridge = _section(1, "Bridge", 0, d_level=3, role="bridge")
        result = compose_song_cue_bundle(_plan((bridge,)))
        cue = result.bundle.cues[0]
        assert cue.fx.permitted == ()
        assert cue.fx.density == 0
        assert cue.fx.speed_beats is None

    def test_bridge_position_width_tier_is_forced_to_the_lowest(self) -> None:
        bridge = _section(1, "Bridge", 0, d_level=3, role="bridge")
        result = compose_song_cue_bundle(_plan((bridge,)))
        cue = result.bundle.cues[0]
        assert cue.position.width_tier == POSITION_WIDTH_TIERS[0]

    def test_bridge_at_d1_gets_the_same_stop_role_aware_fix_applies_uniformly(self) -> None:
        """D1 은 고침 전에도 예산이 0 이라 `permitted`(눈에 보이는 축)는 이미
        비어 있었다 — 그러나 `density` 는 여전히 요청값(1)을 들고 있었다
        (`_fx_data`: density=decision.fx.density, 예산과 무관). 고침은 role
        조건 하나로 걸리므로 D1 도 D2 와 똑같이 density 까지 0 이 된다 — §6
        의도(무빙·이펙트 "정지")에 D1 이 더 가까워지는 강화이지 회귀가 아니다.
        """
        bridge = _section(1, "Bridge", 0, d_level=1, role="bridge")
        result = compose_song_cue_bundle(_plan((bridge,)))
        cue = result.bundle.cues[0]
        assert cue.fx.permitted == ()
        assert cue.fx.density == 0
        assert cue.fx.speed_beats is None
        assert cue.position.width_tier == POSITION_WIDTH_TIERS[0]

    def test_bridge_dimmer_and_fade_are_unaffected(self) -> None:
        """§6 은 밝기·페이드를 건드리지 않는다 — 두 축은 분리."""
        bridge = _section(1, "Bridge", 0, d_level=2, role="bridge")
        plain_d2 = _section(2, "D2 reference", 5_000, d_level=2, role=None)
        result = compose_song_cue_bundle(_plan((bridge, plain_d2)))
        cues = {cue.section_index: cue for cue in result.bundle.cues}
        assert cues[1].dimmer.key_pct == cues[2].dimmer.key_pct
        assert cues[1].fade_seconds == cues[2].fade_seconds

    def test_non_bridge_roles_are_unaffected_byte_identical(self) -> None:
        """회귀 없음 — chorus/verse 는 fx 예산 그대로 permit 되어야 한다."""
        chorus = _section(1, "Chorus 1", 0, d_level=5, role="chorus")
        verse = _section(2, "Verse 1", 5_000, d_level=3, role="verse")
        result = compose_song_cue_bundle(_plan((chorus, verse)))
        cues = {cue.section_index: cue for cue in result.bundle.cues}
        assert cues[1].fx.permitted == ("slow tilt",)
        assert cues[2].fx.permitted == ()
        assert cues[2].fx.density == 1, "density(=예산과 무관한 요청값) 는 그대로 유지돼야 한다"


def _characterization_rig(effect_count: int = 40):
    """probe.py 와 바이트 동일한 40-fixture 리그 — AC-2 는 그 스크립트가
    낸 표를 재현해야 하므로 4-fixture 리그(위 `_rig`)를 쓰지 않는다."""
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, effect_count + 1)
    ]
    declared_layers = {"key": [1, 2], "back": [3, 4]}
    return build_rig_profile(patch=patch, groups={}, coords=[], declared_layers=declared_layers)


def _characterization_section(
    index, label, start_ms, d_level, role, *, fx_allowed=(), fx_density=0, accents=()
):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=("blue", "white"), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="mid", source="genre"),
        fx=FxDecision(allowed=fx_allowed, density=fx_density),
        accent=AccentDecision(accents=accents),
        cue_number=index,
        role=role,
    )


def _characterization_plan():
    sections = (
        _characterization_section(1, "Intro", 0, 2, "intro", fx_allowed=(), fx_density=0),
        _characterization_section(
            2, "Verse 1", 16000, 3, "verse", fx_allowed=("slow pan",), fx_density=1
        ),
        _characterization_section(
            3,
            "Chorus 1",
            48000,
            5,
            "chorus",
            fx_allowed=("dimmer chase", "pan sweep"),
            fx_density=2,
        ),
        _characterization_section(
            4, "Verse 2", 80000, 3, "verse", fx_allowed=("slow pan",), fx_density=1
        ),
        _characterization_section(
            5,
            "Chorus 2",
            112000,
            5,
            "chorus",
            fx_allowed=("dimmer chase", "pan sweep"),
            fx_density=2,
        ),
        _characterization_section(
            6, "Bridge", 144000, 2, "bridge", fx_allowed=("slow tilt",), fx_density=1
        ),
        _characterization_section(
            7, "Breakdown", 160000, 1, "bridge", fx_allowed=("slow tilt",), fx_density=1
        ),
        _characterization_section(
            8,
            "Chorus 3",
            176000,
            5,
            "chorus",
            fx_allowed=("dimmer chase", "pan sweep"),
            fx_density=2,
            accents=("white flash",),
        ),
        _characterization_section(
            9,
            "Finale",
            208000,
            5,
            "finale",
            fx_allowed=("dimmer chase", "accent sweep"),
            fx_density=2,
            accents=("white flash",),
        ),
    )
    return UnifiedSongLightingPlan(
        song_title="t394 probe",
        sequence_name="t394 probe seq",
        sections=sections,
        timing=TimingPlan.timecode(77),
        music_profile=MusicProfile(bpm=126.0, palette=("blue", "white")),
        rig_profile=_characterization_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


#: AC-2 — 고치기 전(main, /private/tmp/claude-501/t394_probe/probe.py) 캡처한
#: 9행. (label, role, d_level, fade_seconds, width_tier, fx_permitted,
#: fx_density, speed_beats, accents). 이 튜플은 고침 전 실측값을 그대로
#: 옮긴 것이라 이 테스트 파일 안에서 새로 계산하지 않는다.
_BEFORE_FIX_ROWS = (
    ("Intro", "intro", 2, 1.905, "narrow", (), 0, None, ()),
    ("Verse 1", "verse", 3, 1.429, "medium", ("slow pan",), 1, 1.0, ()),
    ("Chorus 1", "chorus", 5, 0.238, "max", ("dimmer chase", "pan sweep"), 2, 2.0, ()),
    ("Verse 2", "verse", 3, 1.429, "medium", ("slow pan",), 1, 1.0, ()),
    ("Chorus 2", "chorus", 5, 0.238, "max", ("dimmer chase", "pan sweep"), 2, 2.0, ()),
    ("Bridge", "bridge", 2, 1.905, "narrow", ("slow tilt",), 1, 0.25, ()),
    ("Breakdown", "bridge", 1, 3.810, "narrow", (), 1, None, ()),
    (
        "Chorus 3",
        "chorus",
        5,
        0.238,
        "max",
        ("dimmer chase", "pan sweep"),
        2,
        2.0,
        ("white flash",),
    ),
    (
        "Finale",
        "finale",
        5,
        3.810,
        "max",
        ("dimmer chase", "accent sweep"),
        2,
        2.0,
        ("white flash",),
    ),
)

#: 정본 §6 이 실제로 요구하는 두 행(bridge role 의 D2 "Bridge" · D1
#: "Breakdown")만 fx/movement 열이 바뀐다 — 라벨로 인덱싱한다.
_CHANGED_LABELS = frozenset({"Bridge", "Breakdown"})


class TestCharacterizationOnlyBridgeRoleRowsChange:
    """AC-2 — 9행 표는 bridge role 두 행(fx/movement 열)만 바뀌고 나머지는
    고치기 전 값과 바이트 동일해야 한다."""

    def test_nine_row_table_matches_before_except_bridge_role_rows(self) -> None:
        result = compose_song_cue_bundle(_characterization_plan())
        cues = result.bundle.cues
        assert len(cues) == len(_BEFORE_FIX_ROWS)
        for before, cue in zip(_BEFORE_FIX_ROWS, cues, strict=True):
            label, role, d_level, fade_s, tier, fx_permitted, density, speed, accents = before
            after = (
                cue.d_level,
                round(cue.fade_seconds, 3),
                cue.position.width_tier,
                cue.fx.permitted,
                cue.fx.density,
                cue.fx.speed_beats,
                cue.accents,
            )
            if label in _CHANGED_LABELS:
                # role==bridge 행 — fx 관련 열만 정지 값으로 바뀐다. D
                # 레벨·페이드·타이어는 §6 이 건드리지 않으므로 그대로다.
                assert after[0] == d_level, label
                assert after[1] == fade_s, label
                assert after[2] == tier, label
                assert after[3] == (), f"{label}: fx.permitted still {after[3]!r}"
                assert after[4] == 0, f"{label}: fx.density still {after[4]!r}"
                assert after[5] is None, f"{label}: fx.speed_beats still {after[5]!r}"
                assert after[6] == accents, label
            else:
                expected = (d_level, fade_s, tier, fx_permitted, density, speed, accents)
                assert after == expected, f"{label} changed unexpectedly: {after!r} != {expected!r}"
