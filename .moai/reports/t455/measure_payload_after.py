"""t455·t456 — 수정 뒤 _song_timeline_payload 가 내보내는 새 필드를 잰다.

t454 와 같은 8구간 곡. 색은 구간마다 달리 줘서 HEX 해석·미해석(흰색·gold)을
함께 보인다. 콘솔 접촉 0.
"""

import json
import sys
from dataclasses import replace

sys.path.insert(0, ".")

from server.design.song_cue_composer import compose_song_cue_bundle  # noqa: E402
from server.design.song_plan import PaletteDecision  # noqa: E402
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section  # noqa: E402
from server.web.session import _song_timeline_payload  # noqa: E402

labels = [
    ("Intro", 0, ("Blue",)),
    ("Verse 1", 15000, ("블루", "Amber")),
    ("Chorus 1", 40000, ("Warm White",)),
    ("Verse 2", 60000, ("흰색",)),
    ("Chorus 2", 85000, ("gold", "Red")),
    ("Bridge", 105000, ("Lavender",)),
    ("Chorus 3", 125000, ("Cyan", "Magenta")),
    ("Outro", 150000, ("핑크",)),
]
secs = tuple(
    replace(_section(i + 1, label, s), palette=PaletteDecision(colors=colors, source="director"))
    for i, (label, s, colors) in enumerate(labels)
)
plan = _plan(bpm=120.0, sections=secs)
p = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
print("section hex:")
for s in p["sections"]:
    print(
        f"  {s['label']:<9} palette={s['palette']!r:<24}"
        f" primary_hex={s['palette_primary_hex']} secondary_hex={s['palette_secondary_hex']}"
    )
cr = p["concept_report"]
print("concept_report keys:", sorted(cr))
print("row_pairing:", cr.get("row_pairing"))
for row in cr.get("rows", []):
    print("  ", json.dumps(row, ensure_ascii=False))
