"""t511 대본(stdin)의 표 행을 종류별로 센다. 전체와 0~25마디(시작 시각 0:55.1 이하) 두 범위.

사용(측정 대상 5e064752 = t514 수정본): git show origin/WT-loveattack-m1:.moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md \
        | python3 .moai/reports/t515/count_kinds.py
"""

import collections
import re
import sys

KINDS = ("킥/스네어 펄스", "체이스 한 칸", "색/위치 한 단계", "움직임 효과")
BAR25_END = 55.1  # 26마디 1박 = 0:55.1 (대본 표기). 그 미만에서 시작한 행이 0~25마디


def main() -> None:
    total: collections.Counter[str] = collections.Counter()
    early: collections.Counter[str] = collections.Counter()
    for line in sys.stdin:
        m = re.match(r"\| (\d):(\d\d)\.(\d)", line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        layer, action = cells[1], cells[3]
        kind = "강조" if layer == "강조" else next((k for k in KINDS if action.startswith(k)), "?")
        if kind == "?":
            print("unclassified:", cells[0], "|", layer, "|", action[:60])
        total[kind] += 1
        start = int(m[1]) * 60 + int(m[2]) + int(m[3]) / 10
        if start < BAR25_END:
            early[kind] += 1
    print("rows", sum(total.values()), dict(total))
    print("rows starting before 0:55.1 (bars 0-25)", sum(early.values()), dict(early))


if __name__ == "__main__":
    main()
