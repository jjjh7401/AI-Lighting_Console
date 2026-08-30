#!/usr/bin/env python3
# t192 M4b -- `| head` 안에서 위험한 하위 형태를 갈라낸다.
#
# 전체 `| head` 는 27% 라 처방 대상이 못 된다. 사고가 실제로 난 형태는
# "전량이 필요한 질문에 상한을 씌운 것"이다. 그 하위 형태만 센다.
import json
import os
import re

ROOT = "/Users/studiox/.claude/projects"

PIPE_HEAD = re.compile(r"\|\s*head\b")
# 하위 형태들 -- 전량이 필요한 질문 위에 상한이 얹힌 모양
F_HELP = re.compile(r"--help[^|]*\|\s*head\b")        # 도움말: 동사 목록 = 전량 질문
F_GREP = re.compile(r"\bgrep\b[^|]*\|\s*head\b")      # 검색 결과에 상한
F_LIST = re.compile(r"\b(ls|find|git\s+branch|git\s+worktree\s+list|git\s+tag)\b[^|]*\|\s*head\b")
F_COUNTN = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)")  # N 값 분포

per_form = dict()
per_form_projects = dict()
n_dist = dict()
grep_c_head = 0   # grep -c 에 head -- 개수 질문에 상한
examples_help = []
examples_grep = []


def bump(d, k):
    d[k] = d.get(k, 0) + 1


def addproj(d, k, p):
    s = d.get(k)
    if s is None:
        s = set()
        d[k] = s
    s.add(p)


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
                cmds = []
                walk(rec, cmds)
                for cmd in cmds:
                    if not PIPE_HEAD.search(cmd):
                        continue
                    flat = cmd.replace("\n", " ")
                    if F_HELP.search(cmd):
                        bump(per_form, "help_then_head")
                        addproj(per_form_projects, "help_then_head", entry)
                        if len(examples_help) < 12:
                            examples_help.append(flat[:130])
                    if F_GREP.search(cmd):
                        bump(per_form, "grep_then_head")
                        addproj(per_form_projects, "grep_then_head", entry)
                        if len(examples_grep) < 12:
                            examples_grep.append(flat[:130])
                    if re.search(r"grep\s+[^|]*-[a-zA-Z]*c[a-zA-Z]*\b[^|]*\|\s*head", cmd):
                        grep_c_head += 1
                    if F_LIST.search(cmd):
                        bump(per_form, "list_then_head")
                        addproj(per_form_projects, "list_then_head", entry)
                    m = F_COUNTN.search(cmd)
                    if m:
                        bump(n_dist, int(m.group(1)))


print("=== risky sub-forms of `| head` (count / distinct projects) ===")
for k in sorted(per_form, key=lambda x: -per_form[x]):
    print("%6d  in %3d projects   %s" % (per_form[k], len(per_form_projects[k]), k))
print("")
print("grep_with_count_flag_then_head=%d" % grep_c_head)
print("")
print("=== `head -N` N distribution (ALL values, no cap) ===")
tot = sum(n_dist.values())
print("total_with_explicit_N=%d" % tot)
for n in sorted(n_dist, key=lambda x: -n_dist[x]):
    print("  N=%-6d %6d" % (n, n_dist[n]))
print("")
print("=== samples: --help then head ===")
for e in examples_help:
    print("  " + e)
print("")
print("=== samples: grep then head ===")
for e in examples_grep:
    print("  " + e)
