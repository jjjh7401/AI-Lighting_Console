"""t475 — 승인 카드의 명령(의도)과 콘솔이 받은 명령(실제)을 트래킹으로 풀어 큐별 무대 값을 비교한다.

콘솔은 큐에 저장되지 않은 값을 앞 큐에서 이어 받는다(트래킹). 그래서 빠진 줄이 모두
무대 차이를 만드는 것은 아니다 — 앞 큐와 같은 값이 빠진 것은 무해하고, 중간 큐가 값을
바꿔 놓은 뒤 빠진 것만 무대가 달라진다. 이 스크립트는 그 둘을 가른다.

단순화(명시): 한 큐 안의 값 줄은 저장 대상 속성을 그대로 덮는다고 본다(나중 줄이 이긴다).
선택 범위가 다른 줄(Fixture 20+26 대 Group 3)은 서로 다른 대상으로 따로 센다 —
그룹 멤버십은 콘솔에서 못 읽으므로(RG5) 겹침은 계산하지 않는다.

실행: uv run python .moai/reports/t475/tracking_diff.py <run 디렉터리>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
intended = (RUN / "console_commands_approved.txt").read_text("utf-8").splitlines()
actual = (RUN / "console_commands_sent.txt").read_text("utf-8").splitlines()

_STORE = re.compile(r"^Store Sequence \d+ Cue ([\d.]+) '([^']*)'")
_VALUE = re.compile(r"^((?:Fixture|Group) [\d +]+) ; (.*)$")


def per_cue(lines: list[str]) -> list[tuple[str, str, dict[tuple[str, str], str]]]:
    cues, pending = [], {}
    for line in lines:
        if m := _VALUE.match(line):
            target, rest = m.groups()
            if rest.startswith("At Preset"):
                pending[(target, "Position")] = rest.split()[-1]
            else:
                for part in rest.split(" ; "):
                    pm = re.match(r"Attribute '(\w+)' At (\S+)", part)
                    if pm:
                        pending[(target, pm.group(1))] = pm.group(2)
        elif m := _STORE.match(line):
            cues.append((m.group(1), m.group(2), pending))
            pending = {}
    return cues


def tracked(cues):
    state, out = {}, []
    for number, name, values in cues:
        state = {**state, **values}
        out.append((number, name, dict(state)))
    return out


want = tracked(per_cue(intended))
got = tracked(per_cue(actual))
assert [c[0] for c in want] == [c[0] for c in got], "큐 목록이 다르다"

missing = len(intended) - len(actual)
print(f"승인 카드 명령 {len(intended)}줄 · 콘솔이 받은 명령 {len(actual)}줄 · 빠진 줄 {missing}")
dropped = list(intended)
for line in actual:
    dropped.remove(line)
print("\n== 빠진 줄(중복 제거로 건너뜀)")
for line in dropped:
    print("  " + line)

print("\n== 트래킹 후 무대 값이 달라지는 큐")
diffs = 0
for (number, name, w), (_n, _nm, g) in zip(want, got, strict=True):
    for key in sorted(set(w) | set(g)):
        if w.get(key) != g.get(key):
            diffs += 1
            where = f"큐 {number} {name}: {key[0]} {key[1]}"
            print(f"  {where} — 의도 {w.get(key)} · 실제 {g.get(key)}")
print(f"\n무대 차이 {diffs}건")
