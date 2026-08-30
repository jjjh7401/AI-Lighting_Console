#!/usr/bin/env python3
# t192 M7 -- 권고할 기계가 내 사고 자리에 닿는가.
#
# 내 사고(#3)의 출력은 "Output too large" 로 파일에 밀려났다. 라벨을 붙이는
# 처방이 그 경우에도 닿는지 보려면, head -N 호출 중 저장본으로 밀려난 것이
# 몇 건인지, 그리고 그때 tool_result 본문에 무엇이 남는지를 봐야 한다.
import json
import os
import re

ROOT = "/Users/studiox/.claude/projects"
HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")
PERSIST = re.compile(r"Output too large|persisted-output")

n_head = 0
n_head_persisted = 0
n_persist_all = 0
samples = []


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
        for tid, body in results.items():
            if PERSIST.search(body):
                n_persist_all += 1
        for tid, cmd in uses:
            if not HEAD_N.search(cmd):
                continue
            n_head += 1
            out = results.get(tid)
            if out is None:
                continue
            if PERSIST.search(out):
                n_head_persisted += 1
                if len(samples) < 8:
                    samples.append(cmd.replace("\n", " ")[:110])

print("head_minus_N_invocations=%d" % n_head)
print("of_those_persisted_to_file=%d" % n_head_persisted)
print("persisted_results_overall=%d" % n_persist_all)
print("")
print("=== samples: head -N whose output was persisted ===")
for s in samples:
    print("  " + s)
