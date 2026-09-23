"""t445 probe — 기본(modulate) 모드에서 분할 큐 주색이 후렴 안에서 바뀌는가, G7 판정은?

실행: uv run python .moai/reports/t445/probe.py
"""

from server.concept.session_bridge import build_concept_report
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import _build_unified_song_plan, _split_sections_for_density

secs = [PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro")]
t = 8000
for _ in range(3):
    secs.append(PositionSheetSection(name="Verse", start_ms=t, mood="", d_level=3, role="verse"))
    t += 16000
    secs.append(PositionSheetSection(name="Chorus", start_ms=t, mood="", d_level=5, role="chorus"))
    t += 32000
secs.append(PositionSheetSection(name="Outro", start_ms=t, mood="", d_level=2, role="outro"))
profile = MusicProfile(bpm=120.0, palette=("blue", "white"))
expanded, origin, notes = _split_sections_for_density(secs, profile=profile)
plan = _build_unified_song_plan(
    sections=expanded,
    profile=profile,
    rig=build_rig_profile(patch=[], groups={}, coords=[]),
    records=(),
    timing=TimingPlan.manual_go(),
    sequence_no=121,
    section_origin=origin,
)
print("cues", len(plan.sections), "from", len(secs))
for d in plan.sections:
    if "Chorus" in d.section.label:
        print(repr(d.section.label), d.palette.colors, d.palette.source)
rep = build_concept_report(plan)
print("keys", sorted(rep.keys()))
for k, v in rep.items():
    if k != "table":
        print(k, str(v)[:1500])
