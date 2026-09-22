"""길 A 탐침 공용 부품 — 계획 조립 + 명령 생성(실제 함수 호출)."""

import sys

sys.path.insert(0, ".")

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
from server.web.session import ChatSession

_TOKENS = ("color", "colour", "cyan", "amber", "magenta", "blue", "red", "white")


def _rig():
    patch = [
        {"fid": f, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for f in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch, groups={}, coords=[], declared_layers={"key": [1, 2], "back": [3, 4]}
    )


def _section(i, label, start_ms, d, colors, cue_no):
    return SectionDecision(
        section=TimestampedSection(index=i, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d, source="section_mood"),
        palette=PaletteDecision(colors=colors, source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=()),
        cue_number=cue_no,
    )


def build_composition():
    sections = (
        _section(1, "Intro", 0, 3, ("blue", "cyan"), 101),
        _section(2, "Verse", 20_000, 4, ("amber", "red"), 102),
        _section(3, "Chorus", 40_000, 5, ("magenta", "red"), 103),
    )
    plan = UnifiedSongLightingPlan(
        song_title="Probe Song",
        sequence_name="Probe Seq",
        sections=sections,
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=120.0, palette=("blue", "white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )
    return compose_song_cue_bundle(plan)


def commands(comp, fids, extra):
    """실제 `_reviewed_song_commands` 를 부르되 색 값 라인만 주입한다."""

    class Stub:
        _last_phaser_failures: dict = {}

        def _phaser_slots_for_bundle(self, bundle):
            return {}, {}

        _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands

    import server.web.session as S

    original = S._back_layer_value_lines
    S._back_layer_value_lines = lambda cue, layer_mapping: (
        *original(cue, layer_mapping),
        *extra(cue),
    )
    try:
        return ChatSession._reviewed_song_commands(
            Stub(),
            comp,
            sequence_no=210,
            preset_start=1,
            fids=fids,
            timing=TimingPlan.timecode(9),
            layer_mapping=(),
        )
    finally:
        S._back_layer_value_lines = original


def color_hits(cmds):
    return sum(1 for c in cmds if any(t in c.lower() for t in _TOKENS))
