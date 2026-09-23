"""카드 t444 — 8곡 fixture 게이트 행렬 재측정(입력에 색 없음).

실행: uv run python .moai/reports/t444/gen_gates_8songs.py > .moai/reports/t444/gates_8songs.txt
"""

from __future__ import annotations

import json
from pathlib import Path

from server.concept.gates import GATE_NAMES, evaluate_song

songs = [
    s
    for s in json.loads(Path("server/tests/fixtures/pilot_baseline.json").read_text("utf-8"))
    if "error" not in s
]
mark = {True: "PASS", None: "n/a", False: "FAIL"}
totals = {"PASS": 0, "n/a": 0, "FAIL": 0}
print("곡 | " + " | ".join(name.split(" ")[0] for name in GATE_NAMES))
for song in songs:
    result = evaluate_song(song)
    cells = [mark[result[name].passed] for name in GATE_NAMES]
    for cell in cells:
        totals[cell] += 1
    print(f"{song['song']} | " + " | ".join(cells))
print()
print(f"집계: PASS {totals['PASS']} · n/a {totals['n/a']} · FAIL {totals['FAIL']}")
print()
print("색 게이트 상세(첫 곡):")
first = evaluate_song(songs[0])
for name in GATE_NAMES:
    if name.startswith(("G2", "G5", "G6", "G7")):
        print(f"  {name}: {mark[first[name].passed]} — {first[name].detail}")
