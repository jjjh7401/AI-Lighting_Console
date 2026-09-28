"""t480 D3 — 룩 라이브러리 조립기 은퇴 범위를 잰다(읽기 전용).

운영 코드(server/ 아래, tests 제외)가 ``server.looks.songcue`` · ``songcue_report`` 에서
import 하는 이름을 뿌리로 삼아, 두 모듈 안에서 **닿는** 모듈 수준 이름을 계산한다.
닿지 않는 이름이 은퇴 후보다. 시험이 무엇을 부르는지도 함께 센다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_reach.py`
"""

import ast
from pathlib import Path

MODULES = {
    "server.looks.songcue": Path("server/looks/songcue.py"),
    "server.looks.songcue_report": Path("server/looks/songcue_report.py"),
}


def imported_names(path: Path, module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.name for alias in node.names)
    return names


def defs_of(path: Path) -> dict[str, ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defs: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            defs[node.name] = node
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    defs[target.id] = node
    return defs


production = [
    p
    for p in Path("server").rglob("*.py")
    if "tests" not in p.parts and p not in MODULES.values()
]
tests = list(Path("server/tests").glob("*.py"))

all_defs: dict[str, tuple[str, ast.AST]] = {}
for module, path in MODULES.items():
    for name, node in defs_of(path).items():
        all_defs[name] = (module, node)
# songcue_report 가 songcue 에서 가져오는 이름도 모듈 사이 간선이다.
cross = imported_names(MODULES["server.looks.songcue_report"], "server.looks.songcue")

roots: set[str] = set()
for path in production:
    for module in MODULES:
        roots |= imported_names(path, module)

seen: set[str] = set()
stack = list(roots)
while stack:
    name = stack.pop()
    if name in seen or name not in all_defs:
        continue
    seen.add(name)
    module, node = all_defs[name]
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in all_defs:
            stack.append(sub.id)
        if isinstance(sub, ast.Attribute) and sub.attr in all_defs:
            stack.append(sub.attr)
    if module == "server.looks.songcue_report":
        stack.extend(cross)

unreached = sorted(set(all_defs) - seen, key=lambda n: (all_defs[n][0], all_defs[n][1].lineno))
lines = {
    module: sum(
        all_defs[n][1].end_lineno - all_defs[n][1].lineno + 1
        for n in unreached
        if all_defs[n][0] == module
    )
    for module in MODULES
}
print("roots (production imports):", sorted(roots))
print(f"reached: {len(seen)}  unreached: {len(unreached)}  lines: {lines}")
for name in unreached:
    module, node = all_defs[name]
    print(f"  {module.rsplit('.', 1)[-1]}:{node.lineno} {name}")

print("\ntests importing an unreached name:")
for path in sorted(tests):
    used: set[str] = set()
    for module in MODULES:
        used |= imported_names(path, module)
    hit = sorted(used & set(unreached))
    if hit:
        print(f"  {path.name}: {hit}")
