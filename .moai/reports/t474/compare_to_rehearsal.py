"""t474 — 실기 승인 명령과 t475 리허설 승인 명령(107줄)의 구조 비교.

두 목록은 기구 번호(리허설 2대 대역 · 실기 86대)와 그룹 번호(리허설 지어낸 번호 · 실기 번호)가
다르다. 이름으로 맞춘 뒤 줄을 비교한다:
  - `Fixture <목록>` → `Fixture <SEL>` (실기의 RGB 기구·W 기구 두 목록은 각각 <SEL>·<SEL-W>)
  - 그룹 번호 → 그룹 이름 (리허설: t379 이름 순서 1..18, 실기: 콘솔 그룹 풀 읽기)

실행: uv run python .moai/reports/t474/compare_to_rehearsal.py <실기 승인 파일> <리허설 승인 파일>
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

REAL = Path(sys.argv[1]).read_text("utf-8").splitlines()
REHEARSAL = Path(sys.argv[2]).read_text("utf-8").splitlines()

_REHEARSAL_GROUPS = [
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ALL",
    "ODD",
    "EVEN",
]
_REAL_GROUPS = [
    "ALL",
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ODD",
    "EVEN",
]  # run1_readonly_state.txt 의 그룹 풀 i=1..18


def normalize(lines: list[str], groups: list[str]) -> list[str]:
    out = []
    for line in lines:
        line = re.sub(r"Group (\d+)", lambda m: f"Group <{groups[int(m.group(1)) - 1]}>", line)
        if line.startswith("Fixture ") and "ColorRGB_W" in line:
            line = re.sub(r"^Fixture [\d +]+ ;", "Fixture <SEL-W> ;", line)
        else:
            line = re.sub(r"^Fixture [\d +]+ ;", "Fixture <SEL> ;", line)
        out.append(line)
    return out


real = normalize(REAL, _REAL_GROUPS)
rehearsal = normalize(REHEARSAL, _REHEARSAL_GROUPS)
print(f"실기 {len(real)}줄 · 리허설 {len(rehearsal)}줄")
w_lines = [line for line in real if line.startswith("Fixture <SEL-W>")]
print(f"실기에만 있는 W 기구 색 줄: {len(w_lines)}")
real_without_w = [line for line in real if not line.startswith("Fixture <SEL-W>")]
same = real_without_w == rehearsal
print(f"W 줄을 뺀 실기 == 리허설: {same}")
if not same:
    for line in difflib.unified_diff(rehearsal, real_without_w, "rehearsal", "real", lineterm=""):
        print(line)
