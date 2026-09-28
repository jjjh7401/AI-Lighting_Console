"""t480 D3 — 섞인 시험 파일에서 은퇴한 이름에 닿는 시험만 뺀다(기계적으로).

오염 판정: 은퇴한 이름(``d3_reach.txt``)을 import 한 것 → 그 이름을 쓰는 모듈 수준 정의
(도우미·상수·픽스처)로 전이 → 시험 함수·메서드가 그중 하나를 이름·속성·매개변수로 쓰면
오염. 클래스 안에서는 ``self.<메서드>`` 로 부르는 오염 메서드도 전이한다. 오염된 시험과
도우미를 지우고, 시험이 하나도 안 남은 클래스는 통째로 지운다. 정의 바로 위 주석도
함께 지운다. import 정리는 뒤이어 ruff F401 이 한다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_prune_tests.py <시험 파일>...`
"""

import ast
import re
import sys
from pathlib import Path

REMOVED = {
    line.split()[-1]
    for line in Path(".moai/reports/t480/d3_reach.txt").read_text().splitlines()
    if line.startswith(("  songcue:", "  songcue_report:"))
}
MODS = {"server.looks.songcue", "server.looks.songcue_report"}


def names_in(node: ast.AST) -> set[str]:
    used = {s.id for s in ast.walk(node) if isinstance(s, ast.Name)}
    used |= {s.attr for s in ast.walk(node) if isinstance(s, ast.Attribute)}
    if isinstance(node, ast.FunctionDef):
        used |= {a.arg for a in node.args.args + node.args.kwonlyargs}
    return used


def span(node: ast.AST, lines: list[str]) -> range:
    start = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
    while start > 1 and lines[start - 2].lstrip().startswith("#"):
        start -= 1
    return range(start, node.end_lineno + 1)


def defined_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.FunctionDef | ast.ClassDef):
        return node.name
    if isinstance(node, ast.Assign | ast.AnnAssign):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            return targets[0].id
    return None


for arg in sys.argv[1:]:
    path = Path(arg)
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    # ``songcue_module._apply_climax_duration_cap(...)`` 처럼 모듈 속성으로 부르는 자리도
    # 잡는다 — 은퇴한 이름과 같은 속성 이름은 곧 그 이름이다(첫 판에서 놓쳤다).
    tainted: set[str] = {name for name in REMOVED if name.startswith("_")}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in MODS:
            tainted |= {a.asname or a.name for a in node.names if a.name in REMOVED}
        # 다른 시험 모듈에서 가져오던 이름이 그 모듈의 가지치기로 사라졌으면 그것도 오염이다.
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("server.tests."):
            other = Path(*node.module.split(".")).with_suffix(".py")
            if other.exists():
                other_tree = ast.parse(other.read_text(encoding="utf-8"))
                other_defs = {defined_name(n) for n in other_tree.body} | {
                    a.asname or a.name
                    for n in ast.walk(other_tree)
                    if isinstance(n, ast.ImportFrom | ast.Import)
                    for a in n.names
                }
                tainted |= {a.asname or a.name for a in node.names if a.name not in other_defs}
    module_defs = {defined_name(n): n for n in tree.body if defined_name(n)}
    changed = True
    while changed:
        changed = False
        for name, node in module_defs.items():
            if name in tainted or name.startswith("test") or isinstance(node, ast.ClassDef):
                continue
            if names_in(node) & tainted:
                tainted.add(name)
                changed = True
    remove: set[int] = set()
    removed_tests: list[str] = []
    for node in tree.body:
        name = defined_name(node)
        if name is None:
            continue
        if isinstance(node, ast.ClassDef):
            methods = {m.name: m for m in node.body if isinstance(m, ast.FunctionDef)}
            local = set(tainted)
            grow = True
            while grow:
                grow = False
                for mname, m in methods.items():
                    if mname not in local and names_in(m) & local:
                        local.add(mname)
                        grow = True
            tests = [m for m in methods.values() if m.name.startswith("test")]
            dirty = [m for m in tests if m.name in local]
            if tests and len(dirty) == len(tests):
                remove.update(span(node, lines))
                removed_tests.extend(f"{name}.{m.name}" for m in dirty)
                continue
            for mname, m in methods.items():
                if mname in local:
                    remove.update(span(m, lines))
                    if mname.startswith("test"):
                        removed_tests.append(f"{name}.{mname}")
            continue
        if name in tainted and not name.startswith("test"):
            remove.update(span(node, lines))
        elif name.startswith("test") and names_in(node) & tainted:
            remove.update(span(node, lines))
            removed_tests.append(name)
    kept = "".join(line for n, line in enumerate(lines, start=1) if n not in remove)
    kept = re.sub(r"\n{4,}", "\n\n\n", kept)
    path.write_text(kept, encoding="utf-8")
    print(f"## {path.name}: removed {len(removed_tests)} tests")
    for name in removed_tests:
        print(f"   - {name}")
