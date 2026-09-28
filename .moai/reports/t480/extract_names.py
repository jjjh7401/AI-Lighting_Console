"""t480 — session.py 의 모듈 수준 이름들을 새 모듈로 기계적으로 옮긴다(범용판).

`m1_extract.py` 와 같은 규칙: 정의 바로 위에 붙은 주석 블록을 함께 옮기고, 원래
순서를 지키며, session.py 에는 남은 코드가 아직 쓰는 이름만 새 모듈에서 되가져온다.

실행(저장소 루트):
  uv run python .moai/reports/t480/extract_names.py <대상 .py> <모듈 경로> <머리글 파일> <이름...>
"""

import ast
import re
import sys
from pathlib import Path

SESSION = Path("server/web/session.py")
target = Path(sys.argv[1])
module = sys.argv[2]
header = Path(sys.argv[3]).read_text()
names = sys.argv[4:]

src = SESSION.read_text()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)

ranges: dict[str, tuple[int, int]] = {}
for node in tree.body:
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
    if name in names:
        while start > 1 and lines[start - 2].lstrip().startswith("#"):
            start -= 1
        ranges[name] = (start, node.end_lineno)

missing = sorted(set(names) - set(ranges))
assert not missing, f"정의를 못 찾음: {missing}"

ordered = sorted(ranges.items(), key=lambda item: item[1][0])
blocks = ["".join(lines[s - 1 : e]).rstrip("\n") + "\n" for _, (s, e) in ordered]
removed = {n for _, (s, e) in ordered for n in range(s, e + 1)}
remaining = "".join(line for number, line in enumerate(lines, start=1) if number not in removed)
remaining = re.sub(r"\n{4,}", "\n\n\n", remaining)

target.write_text(header + "\n\n".join(blocks))

rest_tree = ast.parse(remaining)
used = {n.id for n in ast.walk(rest_tree) if isinstance(n, ast.Name)}
still_used = [name for name, _ in ordered if name in used]
if still_used:
    block = (
        f"from {module} import (  # 카드 t480 — 자리만 옮김\n"
        + "".join(f"    {name},\n" for name in still_used)
        + ")\n"
    )
    anchor = "from server.design.song_cue_render import ("
    assert anchor in remaining
    remaining = remaining.replace(anchor, block + anchor, 1)
SESSION.write_text(remaining)
print(f"moved={len(ordered)} lines_removed={len(removed)} reimported={len(still_used)}")
