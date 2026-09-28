"""AC-UI 마무리 — 런북 화면 브라우저 확인용 페이로드를 서버 함수로 만든다(콘솔 접촉 0).

t454 `measure_payload.py` 와 같은 경로(`_song_timeline_payload`)를 쓰되, AC-020 이
요구하는 "큐가 화면 높이를 넘는 곡"을 만들려고 36구간·구간별 다른 색을 넣는다.
실행: `uv run python .moai/specs/SPEC-LDDESIGN-001/sync-evidence/ac_ui/make_payload.py`
"""

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from server.design.song_cue_composer import compose_song_cue_bundle
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _song_timeline_payload

OUT = Path(__file__).with_name("payload_36.json")

BLOCK = [
    "Intro",
    "Verse",
    "Pre-Chorus",
    "Chorus",
    "Verse",
    "Pre-Chorus",
    "Chorus",
    "Bridge",
    "Chorus",
]
COLORS = ["blue", "red", "amber", "green", "magenta", "cyan"]

labels: list[str] = []
counts: dict[str, int] = {}
for repeat in range(4):
    for base in BLOCK:
        if base == "Intro" and repeat:
            base = "Verse"
        counts[base] = counts.get(base, 0) + 1
        labels.append(base if base == "Intro" else f"{base} {counts[base]}")
labels[-1] = "Outro"

secs = []
for i, label in enumerate(labels):
    sec = _section(i + 1, label, i * 5000)
    palette = dataclasses.replace(sec.palette, colors=(COLORS[i % len(COLORS)],))
    secs.append(dataclasses.replace(sec, palette=palette))

plan = _plan(bpm=120.0, sections=tuple(secs))
payload = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

cr = payload["concept_report"]
print("sections:", len(payload["sections"]))
print("concept_report keys:", sorted(cr))
print("available:", cr.get("available"), "reason:", cr.get("reason"))
print("row_pairing:", cr.get("row_pairing"))
print("hex sample:", [(s["label"], s.get("palette_primary_hex")) for s in payload["sections"][:6]])
