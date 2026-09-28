"""t480 M1 — session.py 에서 옮길 모듈 수준 이름의 전이 폐포를 잰다(읽기 전용).

실행: 저장소 루트에서 `uv run python .moai/reports/t480/m1_closure.py <root> ...`
"""

import ast
import sys
from pathlib import Path

src = Path("server/web/session.py").read_text()
tree = ast.parse(src)
defs: dict[str, ast.AST] = {}
for node in tree.body:
    if isinstance(node, ast.FunctionDef | ast.ClassDef):
        defs[node.name] = node
    elif isinstance(node, ast.Assign | ast.AnnAssign):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                defs[target.id] = node
imported: set[str] = set()
import_source: dict[str, str] = {}
for node in tree.body:
    if isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            imported.add(local)
            module = node.module if isinstance(node, ast.ImportFrom) else alias.name
            import_source[local] = f"{module}.{alias.name}"

roots = sys.argv[1:]
seen: set[str] = set()
stack = list(roots)
while stack:
    name = stack.pop()
    if name in seen or name not in defs:
        continue
    seen.add(name)
    for sub in ast.walk(defs[name]):
        if isinstance(sub, ast.Name) and sub.id in defs and sub.id not in seen:
            stack.append(sub.id)
lines = sum(defs[n].end_lineno - defs[n].lineno + 1 for n in seen)  # type: ignore[attr-defined]
used_imports = {
    sub.id
    for n in seen
    for sub in ast.walk(defs[n])
    if isinstance(sub, ast.Name) and sub.id in imported
}
print("roots:", roots)
print("closure names:", len(seen), "lines:", lines)
print("imported names used:", len(used_imports))
for name in sorted(used_imports, key=lambda k: import_source[k]):
    print(f"  import {import_source[name]} as {name}")
for n in sorted(seen, key=lambda k: defs[k].lineno):  # type: ignore[attr-defined]
    print(f"  {defs[n].lineno:6d} {n}")  # type: ignore[attr-defined]
