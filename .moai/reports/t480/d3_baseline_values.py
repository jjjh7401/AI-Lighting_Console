"""t480 D3 — 조립기에서 부르는 기준값(절정 상한·어둠 바닥·블라인더 칸)이 은퇴 전후로
글자까지 같은지 잰다(읽기 전용). 기준은 `d6ded877`(카드 착수 시점 origin/main).

조립기(`song_cue_composer.py:34`)가 `server.looks.songcue` 에서 가져오는 이름과, 그 이름이
닿는 모듈 수준 정의(전이 폐포)를 두 시점의 소스에서 잘라 바이트 비교한다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_baseline_values.py`
"""

import ast
import subprocess
from pathlib import Path

ROOTS = ("climax_cap_beats", "darkness_target", "LADDER_BLINDER_OR_FLASH")
BASE = "d6ded877"


def closure(src: str) -> dict[str, str]:
    tree = ast.parse(src)
    defs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            defs[node.name] = node
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    defs[target.id] = node
    seen: set[str] = set()
    stack = list(ROOTS)
    while stack:
        name = stack.pop()
        if name in seen or name not in defs:
            continue
        seen.add(name)
        for sub in ast.walk(defs[name]):
            if isinstance(sub, ast.Name) and sub.id in defs:
                stack.append(sub.id)
    return {name: ast.get_source_segment(src, defs[name]) for name in sorted(seen)}


before = closure(
    subprocess.run(
        ["git", "show", f"{BASE}:server/looks/songcue.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
)
after = closure(Path("server/looks/songcue.py").read_text(encoding="utf-8"))
print(f"names: before={len(before)} after={len(after)}")
for name in sorted(set(before) | set(after)):
    same = before.get(name) == after.get(name)
    print(f"  {'same' if same else 'DIFF'} {name}")
print("ALL SAME" if before == after else "DIFFERENT")
