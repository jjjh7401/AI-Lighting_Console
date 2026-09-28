"""t480 D3 — 룩 라이브러리 조립기만 닿는 모듈 수준 이름을 지운다(기계적으로).

`d3_reach.py` 와 같은 뿌리(운영 코드가 import 하는 이름)에서 닿지 않는 이름만 지운다.
정의 바로 위에 붙은 주석 블록(빈 줄 없이 이어진 `#` 줄)도 함께 지운다. 지운 뒤
남는 코드가 아무도 안 쓰는 import 는 ruff F401 이 정리한다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_retire.py`
"""

import ast
import re
import runpy

reach = runpy.run_path(".moai/reports/t480/d3_reach.py", run_name="d3_reach_import")
unreached: list[str] = reach["unreached"]
all_defs = reach["all_defs"]
MODULES = reach["MODULES"]

for module, path in MODULES.items():
    names = {name for name in unreached if all_defs[name][0] == module}
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    removed: set[int] = set()
    body = tree.body
    for index, node in enumerate(body):
        name = None
        start = 0
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            name = node.name
            start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                name = targets[0].id
                start = node.lineno
        if name not in names:
            continue
        while start > 1 and lines[start - 2].lstrip().startswith("#"):
            start -= 1
        # 대입문 바로 뒤의 속성 독스트링(`#:` 가 아니라 문자열 식)도 함께 지운다.
        end = node.end_lineno
        following = body[index + 1] if index + 1 < len(body) else None
        if (
            isinstance(node, ast.Assign | ast.AnnAssign)
            and isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        ):
            end = following.end_lineno
        removed.update(range(start, end + 1))
    kept = "".join(line for number, line in enumerate(lines, start=1) if number not in removed)
    kept = re.sub(r"\n{4,}", "\n\n\n", kept)
    path.write_text(kept, encoding="utf-8")
    print(f"{path}: removed {len(names)} names, {len(removed)} lines")
