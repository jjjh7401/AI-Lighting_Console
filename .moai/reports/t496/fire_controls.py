"""t496 — 대조 시험을 어긋난 사본으로 쏜다(사본 파일은 건드리지 않고 메모리에서 비교).

대조군:
- C0 지금 사본(재생성 뒤) → 차이 0 이어야 한다
- C1 t493 직전 사본(git b9c28959, t458 시점) → t493 이 찾은 어긋남을 잡아야 한다
- C2 t496 착수 시 사본(git 25d912a1, t493 시점) → beat_grid 를 잡아야 한다
- M1 concept_report.rows 한 줄 뺌 · M2 rows[0] 에 키 하나 더함 · M3 sections[0].intensity 한 칸 뺌
- M4 값만 바꿈(구조 같음) → 차이 0 이어야 한다(값은 비교 대상이 아니다)

실행: 워크트리 루트에서 ``uv run python .moai/reports/t496/fire_controls.py``
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys

sys.path.insert(0, ".")
from server.tests.runbook_payload_fixture import FIXTURE_PATH, build_payload  # noqa: E402
from server.tests.test_runbook_payload_fixture_t496 import structure_diff  # noqa: E402

REL = "ui/src/components/runbookServerPayload.json"


def at(rev: str) -> dict:
    text = subprocess.run(
        ["git", "show", f"{rev}:{REL}"], capture_output=True, text=True, check=True
    ).stdout
    return json.loads(text)


server = build_payload()
current = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

m1 = copy.deepcopy(current)
m1["concept_report"]["rows"].pop()
m2 = copy.deepcopy(current)
m2["concept_report"]["rows"][0]["extra"] = 1
m3 = copy.deepcopy(current)
m3["sections"][0]["intensity"].pop()
m4 = copy.deepcopy(current)
m4["sections"][0]["label"] = "바뀐 값"
m4["concept_report"]["rows"][0]["q"] = 999

cases = [
    ("C0 지금 사본", current, "0"),
    ("C1 t458 시점 사본(b9c28959)", at("b9c28959"), ">0"),
    ("C2 착수 시 사본(25d912a1)", at("25d912a1"), ">0"),
    ("M1 rows 한 줄 뺌", m1, ">0"),
    ("M2 rows[0] 키 추가", m2, ">0"),
    ("M3 intensity 한 칸 뺌", m3, ">0"),
    ("M4 값만 바꿈", m4, "0"),
]
ok = 0
for name, payload, want in cases:
    diff = structure_diff(server, payload)
    good = (len(diff) == 0) if want == "0" else (len(diff) > 0)
    ok += good
    print(f"{'OK ' if good else 'BAD'} {name}: 차이 {len(diff)}건 (기대 {want})")
    for line in diff[:4]:
        print(f"      {line}")
print(f"{ok}/{len(cases)} 기대대로")
