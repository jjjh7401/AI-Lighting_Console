"""t493 — t458 스크립트 재실행(출력 경로만 교체).
원문: t458 — 런북 미리보기용 서버 실출력(#503 뒤). t454 와 같은 8구간·120 BPM 곡에
구간마다 다른 색을 줘서 HEX 해석(t456)·미해석(흰색·gold·핑크)이 함께 보이게 한다.
콘솔 접촉 0.

실행: .venv/bin/python .moai/reports/t493/measure_payload.py
출력: .moai/reports/t493/payload.json (ui/src/components/runbookServerPayload.json 에 복사)
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
payload = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
report = payload["concept_report"]
print("row_pairing:", report.get("row_pairing"), "rows:", len(report.get("rows", [])))
print("hex:", [s.get("palette_primary_hex") for s in payload["sections"]])
with open(".moai/reports/t493/payload.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=1)
