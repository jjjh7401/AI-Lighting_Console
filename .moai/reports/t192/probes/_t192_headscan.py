#!/usr/bin/env python3
# t192 M4 -- 위험 표면을 잰다, 사고를 재는 것이 아니다.
#
# 이 기계의 모든 Claude Code transcript 에서 `| head` 로 흘려보낸 Bash 호출을
# 프로젝트 디렉터리별로 센다.
#
# `| head` 자체는 사고가 아니다. 사고는 head 로 잘린 출력을 개수나 부재의
# 근거로 인용하는 것이고, 그 추론 단계는 어떤 스캔도 볼 수 없다. 그래서 이
# 스캔은 사고가 필요로 하는 표면만 재고, 보고서는 그 구별을 반드시 적는다.
import json
import os
import re

ROOT = "/Users/studiox/.claude/projects"

PIPE_HEAD = re.compile(r"\|\s*head\b")
HELP_HEAD = re.compile(r"--help[^|]*\|\s*head\b")

per_project_cmds = dict()
per_project_head = dict()
per_project_helphead = dict()
examples = []
bad_lines = 0
files_read = 0


def bump(d, k):
    d[k] = d.get(k, 0) + 1


def walk(obj, out):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use" and obj.get("name") == "Bash":
            inp = obj.get("input")
            if isinstance(inp, dict):
                cmd = inp.get("command")
                if isinstance(cmd, str):
                    out.append(cmd)
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out)


for entry in sorted(os.listdir(ROOT)):
    pdir = os.path.join(ROOT, entry)
    if not os.path.isdir(pdir):
        continue
    for fn in os.listdir(pdir):
        if not fn.endswith(".jsonl"):
            continue
        files_read += 1
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
                    bad_lines += 1
                    continue
                cmds = []
                walk(rec, cmds)
                for cmd in cmds:
                    bump(per_project_cmds, entry)
                    if PIPE_HEAD.search(cmd):
                        bump(per_project_head, entry)
                        if len(examples) < 30:
                            examples.append((entry, cmd.replace("\n", " ")[:140]))
                    if HELP_HEAD.search(cmd):
                        bump(per_project_helphead, entry)

total_cmds = sum(per_project_cmds.values())
total_head = sum(per_project_head.values())
total_helphead = sum(per_project_helphead.values())
pct = (100.0 * total_head / total_cmds) if total_cmds else 0.0

print("files_read=%d unparseable_lines=%d" % (files_read, bad_lines))
print("projects_with_bash=%d" % len(per_project_cmds))
print("bash_commands_total=%d" % total_cmds)
print("piped_into_head_total=%d (%.2f%% of bash commands)" % (total_head, pct))
print("help_piped_into_head_total=%d" % total_helphead)
print("projects_with_at_least_one_pipe_head=%d" % len(per_project_head))
print("")
print("=== per-project, pipe-head count / bash count (ALL rows, no cap) ===")
rows = sorted(per_project_head.items(), key=lambda kv: -kv[1])
for proj, n in rows:
    print("%6d / %-7d  %s" % (n, per_project_cmds[proj], proj))
print("")
zero = [p for p in per_project_cmds if p not in per_project_head]
print("projects_with_bash_but_zero_pipe_head=%d" % len(zero))
print("")
print("=== sample commands (first %d encountered) ===" % len(examples))
for proj, cmd in examples:
    print("  [%s] %s" % (proj[:46], cmd))
