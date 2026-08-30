#!/usr/bin/env python3
"""t192 M5 — 포화를 센다: `head -N` 을 씌운 출력이 정확히 N 행으로 돌아온 횟수.

§4.0: "출력이 정확히 N행이라 「개수 N」과 「상한 N」이 바이트 동일" — 이 순간이
사고가 가능해지는 유일한 순간이다. N 미만이면 상한에 안 닿았으므로 개수로 읽어도
참이다. 그래서 처방의 표적은 pipe-to-head 전량이 아니라 포화된 부분집합이다.

계기 한계: 출력이 N 보다 길면(head 가 마지막 단이 아니었거나 배너가 앞에 붙은
경우) 행수로 포화를 판정할 수 없다 — over 로 따로 세고 분모에서 뺀다.
"""

import re

from _t192_common import bump, iter_transcripts, line_count

HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")

saturated = 0
under = 0
over = 0
unpaired = 0
sat_by_n: dict = {}
sat_examples: list = []

for _project, uses, results, _bad in iter_transcripts():
    for tid, cmd in uses:
        found = HEAD_N.search(cmd)
        if not found:
            continue
        n = int(found.group(1))
        if n <= 0:
            continue
        output = results.get(tid)
        if output is None:
            unpaired += 1
            continue
        lines = line_count(output)
        if lines == n:
            saturated += 1
            bump(sat_by_n, n)
            if len(sat_examples) < 15:
                sat_examples.append((n, cmd.replace("\n", " ")[:120]))
        elif lines < n:
            under += 1
        else:
            over += 1

paired = saturated + under
print(f"head_minus_N_invocations_judgeable={paired}  unpaired={unpaired}  over={over}")
if paired:
    print(f"saturated(lines==N)={saturated} ({100.0 * saturated / paired:.1f}% of judgeable)")
    print(f"under(lines<N, count is trustworthy)={under} ({100.0 * under / paired:.1f}%)")
print("")
print("=== saturated count by N (ALL rows) ===")
for value in sorted(sat_by_n, key=lambda key: -sat_by_n[key]):
    print(f"  N={value:<6d} {sat_by_n[value]:6d}")
print("")
print("=== saturated samples ===")
for value, cmd in sat_examples:
    print(f"  [N={value}] {cmd}")
