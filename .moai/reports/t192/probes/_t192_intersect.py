#!/usr/bin/env python3
# t192 M6 -- 처방의 표적을 좁힌다: 포화 AND 전량 질문.
#
# 포화만으로는 785건이라 경보가 시끄럽다(알려진 사고 3건 대비 260:1).
# 사고가 난 형태는 포화된 출력이 "전량을 묻는 질문" 위에 얹힌 것이다:
#   --help (동사 목록)  ·  grep -c (개수)  ·  grep -n (자리 전수)  ·  목록 나열
# 그 교집합만 세서 경보율을 잰다.
import json
import os
import re

ROOT = "/Users/studiox/.claude/projects"
HEAD_N = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)\b")

TOTALITY = [
    ("help", re.compile(r"--help")),
    ("grep_count", re.compile(r"\bgrep\b[^|]*-[a-zA-Z]*c[a-zA-Z]*\b")),
    ("grep_lineno", re.compile(r"\bgrep\b[^|]*-[a-zA-Z]*n[a-zA-Z]*\b")),
    ("listing", re.compile(r"\b(git\s+branch|git\s+worktree\s+list|git\s+tag|git\s+remote)\b")),
]

sat_total = 0
hit_any = 0
per_kind = dict()
examples = []


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
                continue
            body = out.rstrip("\n")
            lines = 0 if body == "" else body.count("\n") + 1
            if lines != n:
                continue
            sat_total += 1
            kinds = []
            for name, rx in TOTALITY:
                if rx.search(cmd):
                    kinds.append(name)
                    bump(per_kind, name)
            if kinds:
                hit_any += 1
                if len(examples) < 20:
                    examples.append((n, "+".join(kinds), cmd.replace("\n", " ")[:115]))

print("saturated_total=%d" % sat_total)
print("saturated_AND_totality_question=%d" % hit_any)
if sat_total:
    print("share=%.1f%%" % (100.0 * hit_any / sat_total))
print("")
print("=== by totality kind (overlapping) ===")
for k in sorted(per_kind, key=lambda x: -per_kind[x]):
    print("  %-12s %5d" % (k, per_kind[k]))
print("")
print("=== samples (saturated AND totality) ===")
for n, k, c in examples:
    print("  [N=%d %s] %s" % (n, k, c))
