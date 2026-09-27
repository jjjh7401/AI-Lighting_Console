"""t455 — t454 와 같은 8구간 곡에서 컨셉 행(build.rows/table/mib/one_shots)을
재서, 화면 구간 행과의 짝짓기 재료를 확인한다(콘솔 접촉 0)."""

import sys

sys.path.insert(0, ".")

from server.concept.gates import build_song, remap_baseline_sections  # noqa: E402
from server.concept.session_bridge import _raw_sections  # noqa: E402
from server.design.song_cue_composer import compose_song_cue_bundle  # noqa: E402
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section  # noqa: E402
from server.web.session import _song_timeline_payload  # noqa: E402

labels = [
    ("Intro", 0),
    ("Verse 1", 15000),
    ("Chorus 1", 40000),
    ("Verse 2", 60000),
    ("Chorus 2", 85000),
    ("Bridge", 105000),
    ("Chorus 3", 125000),
    ("Outro", 150000),
]
secs = tuple(_section(i + 1, label, s) for i, (label, s) in enumerate(labels))
plan = _plan(bpm=120.0, sections=secs)
payload = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
screen = [(s["index"], s["cue_number"], s["label"], s["start_ms"]) for s in payload["sections"]]
print("screen sections:", len(screen))
for row in screen:
    print("  ", row)

raw = _raw_sections(plan)
remapped = remap_baseline_sections(raw)
print("remapped (screen i -> section, occurrence):")
for i, occ in enumerate(remapped):
    print(f"   {i}: {raw[i]['baseline_name']!r} -> ({occ.section!r}, {occ.occurrence})")

build = build_song({"song": "t455", "bpm": 120.0, "sections": raw})
print("rows", len(build.rows), "table", len(build.table), "mib", len(build.mib))
print("concept_report mib len:", len(payload["concept_report"]["mib"]))
for t, m in zip(build.table, build.mib, strict=True):
    print(
        f"  q={t.q:>2} ts={t.ts:>6} kind={t.kind:<7} {t.section!r:<16} occ={t.occurrence}"
        f" trig={t.trigger!r} track={t.tracking} mib={m.status if m else None}"
    )
print("one_shots:", list(build.one_shots))
