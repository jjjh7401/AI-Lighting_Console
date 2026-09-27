"""카드 t472 — 런북 MIB 칸에 live_move 경고가 보이도록 구간 payload 에 두 값을 싣는다.

**고치기 전에 실측한 것** (트리 ``WT-mib-warning-ui`` @ ea91c389): 조립기는 사전이동
큐마다 ``CueMibData.dark_window_seconds``·``live_move`` 를 계산한다(카드 t471). 그런데
타임라인 구간 사전은 ``mib``(사전이동이 있는가, 참/거짓) 하나만 실어, 어둠이 모자라
「켜진 채 이동」하는 큐도 화면에는 「사전이동 있음」으로만 보였다.

**추가만 한다** — 사전이동이 있는 구간에만 두 키가 붙고, 없는 구간의 사전은 한 글자도
바뀌지 않는다(lane-3 t460·t470 이 같은 payload 를 읽는다).
"""

from __future__ import annotations

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
from server.web.session import _song_timeline_payload


def _section(index: int, label: str, start_ms: int, *, position: str, accents=(), d_level=3):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=("blue",), source="director"),
        position=PositionDecision(preset=position, source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(),
        accent=AccentDecision(accents=tuple(accents)),
        cue_number=index,
    )


def _payload(reveal_start_ms: int) -> dict:
    plan = UnifiedSongLightingPlan(
        song_title="MIB Test",
        sequence_name="MIB Seq",
        sections=(
            _section(1, "Blackout", 0, position="Center", accents=("blackout",), d_level=1),
            _section(2, "Reveal", reveal_start_ms, position="Cross"),
            _section(3, "Verse", reveal_start_ms + 16_000, position="Cross"),
        ),
        timing=TimingPlan.trig_time(),
        music_profile=MusicProfile(bpm=120.0),
        rig_profile=build_rig_profile(patch=[], groups={}, coords=[]),
        approval=ApprovalState.approved(reviewer="LD"),
    )
    return _song_timeline_payload(
        plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
    )


def test_a_short_dark_window_reaches_the_timeline_as_live_move():
    reveal = _payload(2_000)["sections"][1]
    assert reveal["mib"] is True
    assert reveal["dark_window_seconds"] == 2.0
    assert reveal["live_move"] is True


def test_a_long_dark_window_is_carried_without_a_warning():
    reveal = _payload(10_000)["sections"][1]
    assert reveal["mib"] is True
    assert reveal["dark_window_seconds"] == 10.0
    assert reveal["live_move"] is False


def test_sections_without_a_premove_carry_no_new_keys():
    sections = _payload(2_000)["sections"]
    for section in (sections[0], sections[2]):
        assert section["mib"] is False
        assert "dark_window_seconds" not in section
        assert "live_move" not in section
