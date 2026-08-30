#!/usr/bin/env python3
"""t192 M4 — 위험 표면을 잰다, 사고를 재는 것이 아니다.

이 기계의 모든 Claude Code transcript 에서 `| head` 로 흘려보낸 Bash 호출을
프로젝트 디렉터리별로 센다.

`| head` 자체는 사고가 아니다. 사고는 head 로 잘린 출력을 개수나 부재의 근거로
인용하는 것이고, 그 추론 단계는 어떤 스캔도 볼 수 없다. 그래서 이 스캔은 사고가
필요로 하는 표면만 재고, 보고서는 그 구별을 반드시 적는다.
"""

import re

from _t192_common import bump, iter_transcripts

PIPE_HEAD = re.compile(r"\|\s*head\b")
HELP_HEAD = re.compile(r"--help[^|]*\|\s*head\b")

per_project_cmds: dict = {}
per_project_head: dict = {}
per_project_helphead: dict = {}
examples: list = []
bad_lines = 0
files_read = 0

for project, uses, _results, bad in iter_transcripts():
    files_read += 1
    bad_lines += bad
    for _tid, cmd in uses:
        bump(per_project_cmds, project)
        if PIPE_HEAD.search(cmd):
            bump(per_project_head, project)
            if len(examples) < 30:
                examples.append((project, cmd.replace("\n", " ")[:140]))
        if HELP_HEAD.search(cmd):
            bump(per_project_helphead, project)

total_cmds = sum(per_project_cmds.values())
total_head = sum(per_project_head.values())
total_helphead = sum(per_project_helphead.values())
pct = (100.0 * total_head / total_cmds) if total_cmds else 0.0

print(f"files_read={files_read} unparseable_lines={bad_lines}")
print(f"projects_with_bash={len(per_project_cmds)}")
print(f"bash_commands_total={total_cmds}")
print(f"piped_into_head_total={total_head} ({pct:.2f}% of bash commands)")
print(f"help_piped_into_head_total={total_helphead}")
print(f"projects_with_at_least_one_pipe_head={len(per_project_head)}")
print("")
print("=== per-project, pipe-head count / bash count (ALL rows, no cap) ===")
for project, count in sorted(per_project_head.items(), key=lambda kv: -kv[1]):
    print(f"{count:6d} / {per_project_cmds[project]:<7d}  {project}")
print("")
zero = [p for p in per_project_cmds if p not in per_project_head]
print(f"projects_with_bash_but_zero_pipe_head={len(zero)}")
print("")
print(f"=== sample commands (first {len(examples)} encountered) ===")
for project, cmd in examples:
    print(f"  [{project[:46]}] {cmd}")
