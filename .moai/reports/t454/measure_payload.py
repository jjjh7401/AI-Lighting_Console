"""t454 — _song_timeline_payload 가 실제로 내보내는 필드를 잰다(콘솔 접촉 0)."""

import json
import sys

sys.path.insert(0, ".")
from server.design.song_cue_composer import compose_song_cue_bundle
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _song_timeline_payload

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
p = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
print("TOP KEYS:", sorted(p))
print("SECTION KEYS:", sorted(p["sections"][0]))
print("n sections:", len(p["sections"]))
cr = p["concept_report"]
print("CR KEYS:", sorted(cr))
print(json.dumps({k: v for k, v in cr.items() if k != "mib"}, ensure_ascii=False, indent=1))
print("mib len:", len(cr.get("mib", [])), "values:", [m and m["status"] for m in cr.get("mib", [])])

# 화면 확인용 — 같은 페이로드를 JSON 으로 남긴다(런북 미리보기가 그대로 읽는다).
with open(".moai/reports/t454/payload.json", "w", encoding="utf-8") as fh:
    json.dump(p, fh, ensure_ascii=False, indent=1)
