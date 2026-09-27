"""t462 재현 — 실제 대화 길 빌더(_build_unified_song_plan) + 조립기로 한 곡을 만들고
세 기능(후렴 밝기 사다리 · 드롭 전 어둠 · 절정 복귀 큐)이 있는지 본다.

실행: uv run python .moai/reports/t462/probe_a.py
"""

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _build_unified_song_plan,
    _confirmed_section_names,
    _infer_confirmed_role,
)

d_levels = [2, 3, 4, 5, 3, 4, 5, 2, 4, 5, 5]
roles = [_infer_confirmed_role(i, d_levels) for i in range(len(d_levels))]
names = _confirmed_section_names(roles)
sections, t = [], 0
for n, r, d in zip(names, roles, d_levels, strict=True):
    sections.append(PositionSheetSection(name=n, start_ms=t, mood="", d_level=d, role=r))
    t += 16000
plan = _build_unified_song_plan(
    sections=sections,
    profile=MusicProfile(bpm=120.0),
    rig=build_rig_profile(patch=[], groups={}, coords=[]),
    records=(),
    timing=TimingPlan.trig_time(),
    sequence_no=120,
)
res = compose_song_cue_bundle(plan)
print("requery:", len(res.requery_requirements))
for c in res.bundle.cues:
    print(
        f"{c.cue_number:>5g} {c.kind:12} {c.cue_name:14} D{c.d_level} "
        f"key={c.dimmer.key_pct} fade={c.fade_seconds} accents={c.accents} "
        f"start={c.timing.start_ms}"
    )
