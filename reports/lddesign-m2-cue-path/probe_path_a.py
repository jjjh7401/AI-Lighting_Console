"""길 A(감독 확정) 실측 — 컨셉 색이 콘솔 명령까지 가는가. (임시 탐침, 커밋 안 함)"""

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


def rig():
    patch = [
        {"fid": f, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for f in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch, groups={}, coords=[], declared_layers={"key": [1, 2], "back": [3, 4]}
    )


def section(i, label, start_ms, d, colors, cue_no):
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


# 색을 구간마다 **다르게** 준다 — 명령에 색이 실리면 반드시 달라져야 한다.
sections = (
    section(1, "Intro", 0, 3, ("blue", "cyan"), 101),
    section(2, "Verse", 20_000, 4, ("amber", "white"), 102),
    section(3, "Chorus", 40_000, 5, ("magenta", "red"), 103),
)
plan = UnifiedSongLightingPlan(
    song_title="Probe Song",
    sequence_name="Probe Seq",
    sections=sections,
    timing=TimingPlan.timecode(9),
    music_profile=MusicProfile(bpm=120.0, palette=("blue", "white")),
    rig_profile=rig(),
    approval=ApprovalState.approved(reviewer="director"),
)

comp = compose_song_cue_bundle(plan)
print("=== 1) 설계층(컴포저)이 색을 들고 있는가")
for cue in comp.bundle.cues:
    print(f"  Q{cue.cue_number}  color={cue.color}")

print()
print("=== 2) 그 색이 콘솔 명령으로 나가는가")


class Stub:
    _last_phaser_failures: dict = {}

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands


cmds = ChatSession._reviewed_song_commands(
    Stub(),
    comp,
    sequence_no=210,
    preset_start=1,
    fids=[1, 2, 3, 4],
    timing=plan.timing,
    layer_mapping=(),
)
for c in cmds:
    print("   ", c)
print()
print(f"  명령 총 {len(cmds)}줄")
tokens = ("color", "colour", "cyan", "amber", "magenta", "blue", "red", "white")
hits = [c for c in cmds if any(t in c.lower() for t in tokens)]
print(f"  색 관련 줄: {len(hits)}")
for h in hits:
    print("    ->", h)
