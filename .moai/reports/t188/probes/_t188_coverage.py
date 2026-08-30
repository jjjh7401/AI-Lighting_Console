"""t188 3단계 — read_existing_fids 세 소비 지점의 **예외 방어 여부**를 기계로 잰다.

들여쓰기를 눈으로 읽지 않는다. tools.py 를 파싱해 각 호출이 어떤 try 블록의
**본문 안**에 있는지, 그 try 가 어떤 예외를 잡는지 답하게 한다.

양성 대조군: 4750(import_lxseq_groups)은 t182 가 except StateQueryError 로
감쌌다. 계기가 그 자리를 「안 덮임」으로 답하면 계기가 고장난 것이다.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = "server/orchestrator/tools.py"
TEXT = Path(SRC).read_text(encoding="utf-8")
TREE = ast.parse(TEXT)

targets = []
for node in ast.walk(TREE):
    if not isinstance(node, ast.Call):
        continue
    fn = node.func
    if isinstance(fn, ast.Name) and fn.id == "read_existing_fids":
        targets.append(node.lineno)
targets.sort()
print("read_existing_fids 호출 자리: " + str(targets))
print()


def handlers_covering(line: int) -> list:
    """line 을 try 의 **본문**(handler 절이 아니라)에 품은 try 들의 잡는 종류."""
    out = []
    for node in ast.walk(TREE):
        if not isinstance(node, ast.Try):
            continue
        body_lines = []
        for stmt in node.body:
            body_lines.append((stmt.lineno, getattr(stmt, "end_lineno", stmt.lineno)))
        if not body_lines:
            continue
        lo = min(a for a, _ in body_lines)
        hi = max(b for _, b in body_lines)
        if not (lo <= line <= hi):
            continue
        kinds = []
        for h in node.handlers:
            if h.type is None:
                kinds.append("BARE")
            else:
                kinds.append(ast.unparse(h.type))
        out.append((node.lineno, kinds))
    return out


for line in targets:
    cover = handlers_covering(line)
    print("tools.py:" + str(line))
    if not cover:
        print("    덮는 try 없음 — 예외가 이 도구를 그대로 탈출한다")
    else:
        for try_line, kinds in cover:
            print("    try@" + str(try_line) + " 가 잡는 것: " + str(kinds))
    print()
