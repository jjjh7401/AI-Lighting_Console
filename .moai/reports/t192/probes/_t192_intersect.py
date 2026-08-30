#!/usr/bin/env python3
"""t192 M6 — 처방의 표적을 좁힌다: 포화 AND 전량 질문.

포화만으로는 경보가 넓다. 사고가 난 형태는 포화된 출력이 "전량을 묻는 질문" 위에
얹힌 것이다: --help(동사 목록) · grep -c(개수) · grep -n(자리 전수) · 목록 나열.
그 교집합만 세서 경보가 몇 번 울릴지를 잰다.
"""

import re

from _t192_common import bump, iter_transcripts, line_count

HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")

TOTALITY = [
    ("help", re.compile(r"--help")),
    ("grep_count", re.compile(r"\bgrep\b[^|]*-[a-zA-Z]*c[a-zA-Z]*\b")),
    ("grep_lineno", re.compile(r"\bgrep\b[^|]*-[a-zA-Z]*n[a-zA-Z]*\b")),
    ("listing", re.compile(r"\b(git\s+branch|git\s+worktree\s+list|git\s+tag|git\s+remote)\b")),
]

sat_total = 0
hit_any = 0
per_kind: dict = {}
examples: list = []

for _project, uses, results, _bad in iter_transcripts():
    for tid, cmd in uses:
        found = HEAD_N.search(cmd)
        if not found:
            continue
        n = int(found.group(1))
        if n <= 0:
            continue
        output = results.get(tid)
        if output is None or line_count(output) != n:
            continue
        sat_total += 1
        kinds = [name for name, pattern in TOTALITY if pattern.search(cmd)]
        for name in kinds:
            bump(per_kind, name)
        if kinds:
            hit_any += 1
            if len(examples) < 20:
                examples.append((n, "+".join(kinds), cmd.replace("\n", " ")[:115]))

print(f"saturated_total={sat_total}")
print(f"saturated_AND_totality_question={hit_any}")
if sat_total:
    print(f"share={100.0 * hit_any / sat_total:.1f}%")
print("")
print("=== by totality kind (overlapping) ===")
for kind in sorted(per_kind, key=lambda key: -per_kind[key]):
    print(f"  {kind:<12} {per_kind[kind]:5d}")
print("")
print("=== samples (saturated AND totality) ===")
for value, kind, cmd in examples:
    print(f"  [N={value} {kind}] {cmd}")
