#!/usr/bin/env python3
# t192 M5 -- 포화를 센다: `head -N` 을 씌운 출력이 정확히 N 행으로 돌아온 횟수.
#
# §4.0: "출력이 정확히 N행이라 「개수 N」과 「상한 N」이 바이트 동일" -- 이 순간이
# 사고가 가능해지는 유일한 순간이다. N 미만이면 상한에 안 닿았으므로 개수로 읽어도
# 참이다. 그래서 처방의 표적은 7,479건 전부가 아니라 포화된 부분집합이다.
#
# 계기 한계: tool_result 를 못 찾은 호출은 unpaired 로 따로 세고 분모에서 뺀다.
import json
import os
import re

ROOT = "/Users/studiox/.claude/projects"
HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")

saturated = 0
under = 0
unpaired = 0
sat_by_n = dict()
sat_examples = []


def bump(d, k):
    d[k] = d.get(k, 0) + 1


def walk_uses(obj, out):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use" and obj.get("name") == "Bash":
            inp = obj.get("input")
            tid = obj.get("id")
            if isinstance(inp, dict) and isinstance(tid, str):
                cmd = inp.get("command")
                if isinstance(cmd, str):
                    out.append((tid, cmd))
        for v in obj.values():
            walk_uses(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_uses(v, out)


def walk_results(obj, out):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_result":
            tid = obj.get("tool_use_id")
            c = obj.get("content")
            text = None
            if isinstance(c, str):
                text = c
            elif isinstance(c, list):
                parts = []
                for p in c:
                    if isinstance(p, dict) and isinstance(p.get("text"), str):
                        parts.append(p["text"])
                if parts:
                    text = "\n".join(parts)
            if isinstance(tid, str) and text is not None:
                out[tid] = text
        for v in obj.values():
            walk_results(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_results(v, out)


for entry in sorted(os.listdir(ROOT)):
    pdir = os.path.join(ROOT, entry)
    if not os.path.isdir(pdir):
        continue
    for fn in os.listdir(pdir):
        if not fn.endswith(".jsonl"):
            continue
        uses = []
        results = dict()
        try:
            fh = open(os.path.join(pdir, fn), "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                walk_uses(rec, uses)
                walk_results(rec, results)
        for tid, cmd in uses:
            m = HEAD_N.search(cmd)
            if not m:
                continue
            n = int(m.group(1))
            if n <= 0:
                continue
            out = results.get(tid)
            if out is None:
                unpaired += 1
                continue
            body = out.rstrip("\n")
            lines = 0 if body == "" else body.count("\n") + 1
            if lines == n:
                saturated += 1
                bump(sat_by_n, n)
                if len(sat_examples) < 15:
                    sat_examples.append((n, cmd.replace("\n", " ")[:120]))
            elif lines < n:
                under += 1
            else:
                # 출력이 N 보다 길다 -- head 가 마지막 파이프가 아니었거나 배너가 붙었다
                bump(sat_by_n, -1)

paired = saturated + under
print("head_minus_N_invocations_paired=%d  unpaired=%d" % (paired, unpaired))
if paired:
    print("saturated(lines==N)=%d (%.1f%% of paired)" % (saturated, 100.0 * saturated / paired))
    print("under(lines<N, count is trustworthy)=%d (%.1f%%)" % (under, 100.0 * under / paired))
print("")
print("=== saturated count by N (ALL rows) ===")
for n in sorted(sat_by_n, key=lambda x: -sat_by_n[x]):
    label = "over/banner" if n == -1 else ("N=%d" % n)
    print("  %-12s %6d" % (label, sat_by_n[n]))
print("")
print("=== saturated samples ===")
for n, c in sat_examples:
    print("  [N=%d] %s" % (n, c))
