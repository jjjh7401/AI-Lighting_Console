"""t486 ③ — CUE SHEET 밝기와 큐 설명 밝기가 어디서 갈리는지 잰다(콘솔 접촉 0).

t482 의 실경로 페이로드(`make_payload.py`)와 같은 곡을 두 번 만든다.
두 번째는 Chorus 1 의 D 레벨만 5 → 2 로 바꾼다(재려는 축 하나만 건드린다).
시트(`sections[].intensity` KEY)와 설명(구간 행 `description` 의 「최대 N%」)이
그 변경을 따라 움직이는지 본다.
실행: `uv run python .moai/reports/t486/brightness_probe.py`
"""

import dataclasses
import re
import sys

sys.path.insert(0, ".")
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import DLevelDecision, PaletteDecision
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _infer_confirmed_role, _song_timeline_payload

SONG = [
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
MAX = re.compile(r"최대 (\d+)%")


def payload_for(song):
    d_levels = [d for _, d, _ in song]
    sections = []
    for i, (label, d, color) in enumerate(song):
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
    bundle = compose_song_cue_bundle(plan)
    return _song_timeline_payload(plan, bundle, lifecycle="pending_approval", sequence_no=1)


def table(payload):
    """구간별 (라벨, D, 시트 KEY, 컨셉 구간 이름, 설명 최대 %)."""
    rows = [
        r
        for r in payload["concept_report"]["rows"]
        if r["kind"] == "section" and r["screen_position"] is not None
    ]
    by_pos = {r["screen_position"]: r for r in rows}
    out = []
    for i, sec in enumerate(payload["sections"]):
        key = next(x["level"] for x in sec["intensity"] if x["group"] == "KEY")
        row = by_pos.get(i)
        found = MAX.search(row["description"]) if row else None
        out.append(
            (
                sec["label"],
                sec["d_level"],
                key,
                row["section"] if row else None,
                int(found.group(1)) if found else None,
            )
        )
    return out


base = table(payload_for(SONG))
changed = list(SONG)
changed[3] = ("Chorus 1", 2, "red")
probe = table(payload_for(changed))

print("label | D | sheet KEY | concept section | description max %")
same = 0
for row in base:
    same += row[2] == row[4]
    print(" | ".join(str(x) for x in row))
print(f"sheet == description: {same}/{len(base)}")
print()
print("control: Chorus 1 D 5 -> 2")
print("  before:", base[3])
print("  after: ", probe[3])
print("  sheet moved:", base[3][2] != probe[3][2])
print("  description moved:", base[3][4] != probe[3][4])
