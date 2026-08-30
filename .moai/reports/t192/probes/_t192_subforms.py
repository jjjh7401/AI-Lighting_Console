#!/usr/bin/env python3
"""t192 M4b — `| head` 안에서 위험한 하위 형태를 갈라낸다.

전체 `| head` 는 Bash 명령의 27% 라 처방 대상이 못 된다. 사고가 실제로 난 형태는
"전량이 필요한 질문에 상한을 씌운 것"이다. 그 하위 형태만 센다.
"""

import re

from _t192_common import bump, iter_transcripts

PIPE_HEAD = re.compile(r"\|\s*head\b")
F_HELP = re.compile(r"--help[^|]*\|\s*head\b")
F_GREP = re.compile(r"\bgrep\b[^|]*\|\s*head\b")
F_LIST = re.compile(r"\b(ls|find|git\s+branch|git\s+worktree\s+list|git\s+tag)\b[^|]*\|\s*head\b")
F_COUNTN = re.compile(r"\|\s*head\s+-n?\s*([0-9]+)")
F_GREP_COUNT = re.compile(r"grep\s+[^|]*-[a-zA-Z]*c[a-zA-Z]*\b[^|]*\|\s*head")

per_form: dict = {}
per_form_projects: dict = {}
n_dist: dict = {}
grep_c_head = 0
examples_help: list = []
examples_grep: list = []


def add_project(store: dict, key: str, project: str) -> None:
    store.setdefault(key, set()).add(project)


for project, uses, _results, _bad in iter_transcripts():
    for _tid, cmd in uses:
        if not PIPE_HEAD.search(cmd):
            continue
        flat = cmd.replace("\n", " ")
        if F_HELP.search(cmd):
            bump(per_form, "help_then_head")
            add_project(per_form_projects, "help_then_head", project)
            if len(examples_help) < 12:
                examples_help.append(flat[:130])
        if F_GREP.search(cmd):
            bump(per_form, "grep_then_head")
            add_project(per_form_projects, "grep_then_head", project)
            if len(examples_grep) < 12:
                examples_grep.append(flat[:130])
        if F_GREP_COUNT.search(cmd):
            grep_c_head += 1
        if F_LIST.search(cmd):
            bump(per_form, "list_then_head")
            add_project(per_form_projects, "list_then_head", project)
        found = F_COUNTN.search(cmd)
        if found:
            bump(n_dist, int(found.group(1)))

print("=== risky sub-forms of pipe-to-head (count / distinct projects) ===")
for form in sorted(per_form, key=lambda name: -per_form[name]):
    print(f"{per_form[form]:6d}  in {len(per_form_projects[form]):3d} projects   {form}")
print("")
print(f"grep_with_count_flag_then_head={grep_c_head}")
print("")
print("=== head -N value distribution (ALL values, no cap) ===")
print(f"total_with_explicit_N={sum(n_dist.values())}")
for value in sorted(n_dist, key=lambda key: -n_dist[key]):
    print(f"  N={value:<6d} {n_dist[value]:6d}")
print("")
print("=== samples: --help then head ===")
for sample in examples_help:
    print(f"  {sample}")
print("")
print("=== samples: grep then head ===")
for sample in examples_grep:
    print(f"  {sample}")
