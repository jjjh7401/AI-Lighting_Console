"""t485 재측정 — t482 스크립트 사본(곡·판정기 동일), t486 병합 뒤 트리에서 큐 설명을 다시 낸다.
출력만 ``payload_roles_after_t486.json`` 으로 바꿨다. 실행:
`uv run python .moai/reports/t485/remeasure_desc.py`

원본 독스트링: t482 — 런북 브라우저 확인용 페이로드(콘솔 접촉 0).

`_song_timeline_payload`(서버 실경로)로 만든다. 구간 역할은 손으로 붙이지 않고
실제 앱의 대체 판정기 `_infer_confirmed_role`(D 레벨 순위)로 정한다 — 이
페이로드가 보여 주는 단계 배정은 서버 규칙이 실제로 내는 값이다.
실행: `uv run python .moai/reports/t482/make_payload.py`
"""

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import DLevelDecision, PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _infer_confirmed_role, _song_timeline_payload

OUT = Path(__file__).with_name("payload_roles_after_t486.json")

SONG = [
    # (라벨, D 레벨, 색)
    ("Intro", 2, "blue"),
    ("Verse 1", 3, "blue"),
    ("Pre-Chorus 1", 4, "amber"),
    ("Chorus 1", 5, "red"),
    ("Verse 2", 3, "blue"),
    ("Pre-Chorus 2", 4, "amber"),
    ("Chorus 2", 5, "red"),
    ("Bridge", 2, "cyan"),
    ("Chorus 3", 5, "red"),
    ("Outro", 3, "blue"),
]
d_levels = [d for _, d, _ in SONG]
sections = []
for i, (label, d, color) in enumerate(SONG):
    sec = _section(i + 1, label, i * 12_000)
    sections.append(
        dataclasses.replace(
            sec,
            d=DLevelDecision(level=d, source="section_mood"),
            palette=PaletteDecision(colors=(color,), source="director"),
            role=_infer_confirmed_role(i, d_levels),
        )
    )

plan = _plan(bpm=120.0, sections=tuple(sections))
payload = _song_timeline_payload(
    plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

cr = payload["concept_report"]
print("roles:", [s.get("role") for s in payload["sections"]])
print("available:", cr.get("available"), "row_pairing:", cr.get("row_pairing"))
print("glance:", json.dumps(cr.get("glance"), ensure_ascii=False))
print("descriptions:", [r["description"] for r in cr["rows"][:4]])
