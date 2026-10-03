"""카드 t462 — 업로드 길(B, ``server/looks/songcue.py``)의 드롭 전 어둠·절정 길이
상한을 대화 길 조립기(A, ``server/design/song_cue_composer.py``)로 옮긴다.

**고치기 전에 실측한 것** (트리 ``WT-composer-port`` @ fa237e32,
``.moai/reports/t462/probe_a.before.txt``): 실제 대화 길 빌더
(``_build_unified_song_plan``)로 11구간 곡을 만들면 후렴 바로 앞 절(Verse 2·4·5)이
밝기 90 그대로 나가고(드롭 전 어둠 0건), 대화 길이 스스로 붙인 ``climax accent`` /
``white flash`` 는 이름표로만 남아 콘솔 명령이 한 줄도 없었다(블라인더 0건, 복귀
큐 0건).

리드 결정(2026-09-27)으로 범위를 좁혔다 — 밝기 사다리와 B 의 줌·블라인더·아이리스
회전은 옮기지 않는다(A 후렴은 이미 밝기 100 천장이고, A 에 자기 회차 사다리가
있다). 기준값은 **B 에서 불러다 쓴다** — 이 파일의 단언도 기대값을 B 함수로 계산해,
값이 두 곳에 생기면 깨지게 한다.
"""

from __future__ import annotations

import pytest

from server.design.energy import EFFECT_AXIS_CAPABILITY, beats_to_seconds
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import (
    ARC_BLINDER_GROUP_ABSENT,
    ARC_BLINDER_ROW_ABSENT,
    compose_song_cue_bundle,
)
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
from server.looks.section_intent import intent_for_label
from server.looks.songcue import LADDER_BLINDER_OR_FLASH, climax_cap_beats, darkness_target
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.web.session import ChatSession, _blinder_group_no

_FIDS = (1, 2, 3, 4)
_BLIND_GROUP = 14


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    return build_rig_profile(patch=patch, groups={}, coords=[])


def _section(index: int, label: str, start_ms: int, d_level: int, accents=()):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=("blue",), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=tuple(accents)),
        cue_number=index,
    )


#: 대화 길이 실제로 내는 이름 모양(「Verse 2」·「Chorus 1」) — probe_a 와 같다.
_SONG = (
    ("Intro", 2, ()),
    ("Verse 1", 3, ()),
    ("Chorus 1", 5, ()),
    ("Verse 2", 4, ()),
    ("Chorus 2", 5, ("climax accent",)),
    ("Finale", 5, ("white flash",)),
)


def _plan(*, bpm=120.0, timing=None, blinder_group_no=_BLIND_GROUP, song=_SONG, gap_ms=16_000):
    sections = tuple(
        _section(i, label, (i - 1) * gap_ms, d, accents)
        for i, (label, d, accents) in enumerate(song, start=1)
    )
    return UnifiedSongLightingPlan(
        song_title="Arc Test",
        sequence_name="Arc Seq",
        sections=sections,
        timing=timing or TimingPlan.trig_time(),
        music_profile=MusicProfile(bpm=bpm),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
        blinder_group_no=blinder_group_no,
    )


def _cue(bundle, name):
    return next(cue for cue in bundle.cues if cue.cue_name == name)


class TestPreDropDarkness:
    """완료 조건 ③-a — 드롭(§6 chorus · drop 행) 바로 앞 큐가 B 의 목표값으로 내려간다."""

    def test_the_cue_before_each_chorus_is_darkened_to_bs_target(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        for name in ("Verse 1", "Verse 2"):
            cue = _cue(bundle, name)
            expected = darkness_target(intent_for_label(name))
            assert cue.dimmer.key_pct == expected, f"{name} 가 드롭 앞 어둠을 안 받았다"
            assert cue.pre_drop_from is not None and cue.pre_drop_from > expected

    def test_back_layer_follows_the_key_down(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        cue = _cue(bundle, "Verse 1")
        # 조립기의 key→back 비율(0.8)을 어둠 뒤에도 지킨다 — back 이 key 보다 밝으면
        # 어둠이 어둠으로 안 읽힌다. 이 리그는 back 층이 없어 None 이다.
        assert cue.dimmer.back_pct is None

    def test_a_chorus_after_a_chorus_is_not_darkened(self):
        song = (("Chorus 1", 5, ()), ("Chorus 2", 5, ()))
        bundle = compose_song_cue_bundle(_plan(song=song)).bundle
        assert all(cue.pre_drop_from is None for cue in bundle.cues)

    def test_cues_not_before_a_drop_keep_their_value(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        assert _cue(bundle, "Intro").pre_drop_from is None


class TestBlinderAccent:
    """완료 조건 ③-b — A 가 스스로 붙인 절정 액센트가 블라인더 그룹으로 나간다."""

    def test_climax_accent_on_a_chorus_fires_the_blinder_at_bs_row_floor(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        fixture = _cue(bundle, "Chorus 2").accent_fixture
        assert fixture is not None
        assert fixture.rung == LADDER_BLINDER_OR_FLASH
        assert fixture.group_no == _BLIND_GROUP
        assert fixture.dimmer_pct == intent_for_label("Chorus 2").brightness[0]

    def test_no_blinder_group_means_no_fixture_and_a_reason(self):
        result = compose_song_cue_bundle(_plan(blinder_group_no=None))
        assert all(cue.accent_fixture is None for cue in result.bundle.cues)
        assert any(ARC_BLINDER_GROUP_ABSENT in note for note in result.bundle.arc_notes)

    def test_a_label_with_no_six_row_is_withheld_not_invented(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        assert _cue(bundle, "Finale").accent_fixture is None
        assert any(ARC_BLINDER_ROW_ABSENT in note for note in bundle.arc_notes)

    def test_plain_cues_carry_no_fixture(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        assert _cue(bundle, "Chorus 1").accent_fixture is None


class TestClimaxReturn:
    """완료 조건 ③-c — 블라인더 큐 뒤 B 의 상한 박수가 지나면 복귀 큐가 선다."""

    def test_a_return_cue_lands_at_bs_cap(self):
        bundle = compose_song_cue_bundle(_plan()).bundle
        climax = _cue(bundle, "Chorus 2")
        returns = [cue for cue in bundle.cues if cue.kind == "climax_return"]
        assert len(returns) == 1
        ret = returns[0]
        cap_ms = climax.timing.start_ms + round(
            beats_to_seconds(climax_cap_beats(LADDER_BLINDER_OR_FLASH), 120.0) * 1000
        )
        assert ret.timing.start_ms == cap_ms
        assert climax.cue_number < ret.cue_number < _cue(bundle, "Finale").cue_number
        assert ret.accent_fixture is None
        assert ret.dimmer.key_pct == climax.dimmer.key_pct

    def test_no_bpm_means_no_return(self):
        bundle = compose_song_cue_bundle(_plan(bpm=None)).bundle
        assert not [cue for cue in bundle.cues if cue.kind == "climax_return"]

    def test_manual_go_has_no_clock_so_no_return(self):
        bundle = compose_song_cue_bundle(_plan(timing=TimingPlan.manual_go())).bundle
        assert not [cue for cue in bundle.cues if cue.kind == "climax_return"]

    def test_a_next_cue_inside_the_cap_needs_no_return(self):
        # 120 BPM 에서 2박 = 1000ms. 구간 간격 800ms 면 다음 큐가 먼저 온다.
        bundle = compose_song_cue_bundle(_plan(gap_ms=800)).bundle
        assert not [cue for cue in bundle.cues if cue.kind == "climax_return"]


class _Stub:
    def __init__(self) -> None:
        self._last_phaser_failures: dict[str, str] = {}
        self._last_color_failures: dict[str, str] = {}
        self._last_phaser_slots: dict[str, tuple[int, int]] = {}

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    def _pregenerate_missing_phasers(self, bundle, resolved, failed):
        # SPEC-LDRENDER-001 M6(REQ-LDRENDER-011, t501) — this accent-ladder
        # stub never has phasers to resolve; see test_song_cue_color_emission's
        # twin stub for the same rationale.
        return resolved, failed

    def _resolve_position_preset_labels(self, labels, *, start, span, pool_no=None):
        return {label: start + BASIC_POSITION_SEQUENCE.index(label) for label in labels}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands


def _commands(plan):
    return ChatSession._reviewed_song_commands(
        _Stub(),
        compose_song_cue_bundle(plan),
        sequence_no=210,
        preset_start=1,
        fids=list(_FIDS),
        timing=plan.timing,
    )


class TestConsoleLines:
    """완료 조건 ③ — 실행 출력(콘솔 명령)에 세 줄이 실제로 나온다."""

    def test_blinder_turns_on_then_off_on_the_return(self):
        commands = _commands(_plan())
        on = f"Group {_BLIND_GROUP} ; Attribute 'Dimmer' At 80"
        off = f"Group {_BLIND_GROUP} ; Attribute 'Dimmer' At 0"
        assert commands.count(on) == 1
        assert commands.index(on) < commands.index(off)

    def test_the_return_cue_is_stored_and_timed(self):
        commands = _commands(_plan())
        stores = [line for line in commands if line.startswith("Store Sequence 210 Cue 5.5")]
        assert len(stores) == 1
        assert any(
            line.startswith("Set Cue 5.5 Sequence 210 Property 'TrigTime'") for line in commands
        )

    def test_the_darkened_value_reaches_the_console(self):
        commands = _commands(_plan())
        assert "Fixture 1 + 2 + 3 + 4 ; Attribute 'Dimmer' At 25" in commands

    def test_integral_cue_numbers_keep_their_old_timing_text(self):
        commands = _commands(_plan())
        assert any(
            line.startswith("Set Cue 1 Sequence 210 Property 'TrigType'") for line in commands
        )


class TestBlinderGroupLookup:
    @pytest.mark.parametrize("name", ["BLIND", "blinder", " Blind "])
    def test_exact_name_match_only(self, name):
        mapping = [{"role": "effect", "group_no": 14, "group_name": name}]
        assert _blinder_group_no(mapping) == 14

    def test_substring_does_not_match(self):
        mapping = [{"role": "effect", "group_no": 14, "group_name": "BLIND-L"}]
        assert _blinder_group_no(mapping) is None
