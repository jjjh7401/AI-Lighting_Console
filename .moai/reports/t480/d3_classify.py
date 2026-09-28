"""t480 D3 — 지워진 이름을 import 하는 시험 파일을 분류할 재료를 뽑는다(읽기 전용).

파일마다: 지워진 이름 · 남은 songcue 이름 · 시험 함수 수 · 지워진 이름을 **쓰는** 시험 수.
「지워진 이름을 쓰지 않는 시험」이 있으면 그 파일은 통째로 지우면 안 된다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_classify.py`
"""

import ast
from pathlib import Path

REMOVED_LIST = Path(".moai/reports/t480/d3_reach.txt").read_text().splitlines()
removed = {
    line.split()[-1]
    for line in REMOVED_LIST
    if line.startswith("  songcue:") or line.startswith("  songcue_report:")
}
MODS = {"server.looks.songcue", "server.looks.songcue_report"}

for path in sorted(Path("server/tests").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_removed: set[str] = set()
    imported_kept: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in MODS:
            for alias in node.names:
                (imported_removed if alias.name in removed else imported_kept).add(alias.name)
    if not imported_removed:
        continue
    # 모듈 수준 도우미가 지워진 이름을 쓰면, 그 도우미를 부르는 시험도 오염된다.
    helpers: dict[str, ast.AST] = {
        n.name: n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("test")
    }
    tainted = set(imported_removed)
    changed = True
    while changed:
        changed = False
        for name, node in helpers.items():
            if name in tainted:
                continue
            used = {s.id for s in ast.walk(node) if isinstance(s, ast.Name)}
            if used & tainted:
                tainted.add(name)
                changed = True
    tests: list[tuple[str, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
            used = {s.id for s in ast.walk(node) if isinstance(s, ast.Name)}
            used |= {s.attr for s in ast.walk(node) if isinstance(s, ast.Attribute)}
            tests.append((node.name, bool(used & tainted)))
    clean = [name for name, dirty in tests if not dirty]
    dirty = len(tests) - len(clean)
    print(f"## {path.name}: tests={len(tests)} use_removed={dirty} clean={len(clean)}")
    print(f"   removed imports: {sorted(imported_removed)}")
    print(f"   kept imports:    {sorted(imported_kept)}")
    for name in clean[:12]:
        print(f"   clean: {name}")
