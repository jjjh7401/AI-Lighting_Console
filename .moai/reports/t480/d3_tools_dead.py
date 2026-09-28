"""t480 D3 — tools.py 에서 옛 업로드 길(룩 번들에 감독 색을 덮던 일) 전용 도우미를 지운다.

지우는 이름(모두 `prepare_songcue` 가 조립기로 전환된 뒤 호출처 0 — `grep` 으로 잼):
`_songcue_role_occurrences` · `_override_songcue_main_color`(t441) ·
`_songcue_director_primaries` · `_songcue_concept_palettes`(t444).
정의 바로 위에 붙은 주석 블록도 함께 지운다.

실행(저장소 루트): `uv run python .moai/reports/t480/d3_tools_dead.py`
"""

import ast
import re
from pathlib import Path

TOOLS = Path("server/orchestrator/tools.py")
NAMES = {
    "_songcue_role_occurrences",
    "_override_songcue_main_color",
    "_songcue_director_primaries",
    "_songcue_concept_palettes",
}

src = TOOLS.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)
tree = ast.parse(src)
removed: set[int] = set()
found: set[str] = set()
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in NAMES:
        start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
        while start > 1 and lines[start - 2].lstrip().startswith("#"):
            start -= 1
        removed.update(range(start, node.end_lineno + 1))
        found.add(node.name)
assert found == NAMES, NAMES - found
kept = "".join(line for number, line in enumerate(lines, start=1) if number not in removed)
kept = re.sub(r"\n{4,}", "\n\n\n", kept)
TOOLS.write_text(kept, encoding="utf-8")
print(f"removed {len(found)} helpers, {len(removed)} lines")
