#!/usr/bin/env python3
"""t192 M7 — 권고할 기계가 이 사고 자리에 닿는가.

사고 #3 의 출력은 "Output too large" 로 파일에 밀려났다. 출력에 라벨을 덧대는
처방이 그 경우에도 닿는지 보려면, head -N 호출 중 저장본으로 밀려난 것이 몇
건인지를 먼저 알아야 한다.
"""

import re

from _t192_common import iter_transcripts

HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")
PERSIST = re.compile(r"Output too large|persisted-output")

n_head = 0
n_head_persisted = 0
n_persist_all = 0
samples: list = []

for _project, uses, results, _bad in iter_transcripts():
    for body in results.values():
        if PERSIST.search(body):
            n_persist_all += 1
    for tid, cmd in uses:
        if not HEAD_N.search(cmd):
            continue
        n_head += 1
        output = results.get(tid)
        if output is None or not PERSIST.search(output):
            continue
        n_head_persisted += 1
        if len(samples) < 8:
            samples.append(cmd.replace("\n", " ")[:110])

print(f"head_minus_N_invocations={n_head}")
print(f"of_those_persisted_to_file={n_head_persisted}")
print(f"persisted_results_overall={n_persist_all}")
print("")
print("=== samples: head -N whose output was persisted ===")
for sample in samples:
    print(f"  {sample}")
