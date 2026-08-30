"""t134 3단계 선행 — 0-255 왕복 전수 검산 (콘솔 접촉 0).

실측 근거: 콘솔은 퍼센트를 16비트로 받는다 (13절, At 70.6 -> 46268 = round(70.6/100*65535)).
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-col.csv"


def coarse_for(pct: float) -> int:
    return round(pct / 100 * 65535) // 256


def roundtrip(v: int, digits: int) -> int:
    return coarse_for(round(v / 255 * 100, digits))


print("정밀도별 왕복 불일치 (0-255 전수 256개)")
for digits in (1, 2, 3, 4):
    bad = [v for v in range(256) if roundtrip(v, digits) != v]
    shown = bad if len(bad) <= 20 else bad[:20]
    print("  소수", digits, "자리 | 불일치", len(bad), "/256 |", shown)

print("")
print("불일치 사례 (소수 1자리)")
for v in (7, 234):
    pct = round(v / 255 * 100, 1)
    wide = round(pct / 100 * 65535)
    print("  v =", v, "-> pct", pct, "-> 16bit", wide, "-> coarse", coarse_for(pct))

print("")
print("이 시트의 실제 값 전수 (RGB 3축 x RGB 있는 행)")
bad_sheet = []
total = 0
for row in csv.DictReader(CSV.open(encoding="utf-8-sig")):
    m = re.search(r"R(\d+)\s+G(\d+)\s+B(\d+)", row["Value"])
    if not m:
        continue
    for axis, raw in zip(("R", "G", "B"), m.groups(), strict=True):
        v = int(raw)
        total += 1
        got = roundtrip(v, 1)
        if got != v:
            bad_sheet.append((row["ID"], axis, v, got))
    print(" ", row["ID"], m.group(0), "->", [round(int(x) / 255 * 100, 1) for x in m.groups()])
print("")
print("시트 값 불일치:", len(bad_sheet), "/", total, bad_sheet if bad_sheet else "(없음)")
