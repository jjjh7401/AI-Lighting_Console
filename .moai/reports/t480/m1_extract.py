"""t480 M1 — session.py 의 계획 조립·명령 줄 헬퍼 48개를 새 모듈로 기계적으로 옮긴다.

이름 목록은 `m1_names.txt`(전이 폐포, `m1_closure.py` 산출). 정의 바로 위에
붙은 주석 줄(빈 줄 없이 이어진 `#` 줄)도 함께 옮긴다. 옮긴 뒤 session.py 에는
아직 쓰는 이름만 새 모듈에서 import 한다(ruff F401 회피 — 시험이 session 에서
가져가는 이름은 `m1_test_imports` 로 따로 센다).

실행(저장소 루트): `uv run python .moai/reports/t480/m1_extract.py`
"""

import ast
import re
from pathlib import Path

SESSION = Path("server/web/session.py")
TARGET = Path("server/design/song_cue_render.py")
NAMES = Path(".moai/reports/t480/m1_names.txt").read_text().split()

src = SESSION.read_text()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)

ranges: dict[str, tuple[int, int]] = {}
for node in tree.body:
    name = None
    if isinstance(node, ast.FunctionDef | ast.ClassDef):
        name = node.name
        start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
    elif isinstance(node, ast.Assign | ast.AnnAssign):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            name = targets[0].id
            start = node.lineno
    if name in NAMES:
        # 바로 위에 붙은 주석 블록을 함께 옮긴다.
        while start > 1 and lines[start - 2].lstrip().startswith("#"):
            start -= 1
        ranges[name] = (start, node.end_lineno)

missing = sorted(set(NAMES) - set(ranges))
assert not missing, f"정의를 못 찾음: {missing}"

# 원래 순서 그대로 새 모듈 본문을 만든다.
ordered = sorted(ranges.items(), key=lambda item: item[1][0])
moved_blocks = ["".join(lines[s - 1 : e]) for _, (s, e) in ordered]
removed = set()
for _, (s, e) in ordered:
    removed.update(range(s, e + 1))

remaining = "".join(line for number, line in enumerate(lines, start=1) if number not in removed)
remaining = re.sub(r"\n{4,}", "\n\n\n", remaining)

HEADER = '''"""곡 큐 계획 조립과 콘솔 값 줄 — 대화 길·업로드 길이 함께 쓰는 순수 계산.

카드 t480(SPEC-LDDESIGN-001 REQ-003, AC-017) — 원래 ``server/web/session.py`` 에
있던 계획 조립(``_build_unified_song_plan``)과 명령 값 줄 헬퍼를 이 모듈로 옮겼다.
업로드 길(``server/orchestrator/tools.py``)은 ``server.web`` 을 import 할 수 없어
(층 경계) 세션 안에 있으면 같은 조립기를 쓸 수 없었기 때문이다. 코드는 한 글자도
바꾸지 않고 자리만 옮겼다 — 세션의 콘솔 명령은 바이트 동일
(``.moai/reports/t480/m1_session_dump.*``).

이 모듈은 콘솔을 읽지 않는다. 콘솔에서 찾아야 하는 슬롯(포지션·페이저·흰색 프리셋)은
호출자가 찾아서 넘긴다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design import color_names as _COLOR_NAMES
from server.design.cue_density import rotate_palette
from server.design.interview import (
    Q1_CONCEPT,
    Q2_PALETTE,
    Q2B_COLOR_USAGE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
)
from server.design.profile import (
    SOURCE_GLOBAL_DEFAULT,
    DirectorOverride,
    MusicProfile,
    SectionMoodResolution,
    UnresolvedMood,
    resolve_section,
)
from server.design.section_palette import _section_palette_choice
from server.design.song_plan import (
    COLOR_USAGE_AXIS,
    D_AXIS,
    FX_AXIS,
    PALETTE_AXIS,
    POSITION_AXIS,
    TEXTURE_AXIS,
    AccentDecision,
    ApprovalState,
    DirectorDecision,
    DisabledNote,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
)
from server.spatial.pointing import SpatialPointingError
from server.spatial.position_cuesheet import PositionSheetSection

'''

TARGET.write_text(HEADER + "\n\n".join(block.rstrip("\n") + "\n" for block in moved_blocks))

# session.py 에 남은 코드가 아직 쓰는 이름만 되가져온다.
rest_tree = ast.parse(remaining)
used = {n.id for n in ast.walk(rest_tree) if isinstance(n, ast.Name)} | {
    n.attr for n in ast.walk(rest_tree) if isinstance(n, ast.Attribute)
}
still_used = [name for name, _ in ordered if name in used]
import_block = (
    "from server.design.song_cue_render import (  # 카드 t480 — 자리만 옮김\n"
    + "".join(f"    {name},\n" for name in still_used)
    + ")\n"
)
anchor = "from server.design.song_cue_composer import ("
assert anchor in remaining
remaining = remaining.replace(anchor, import_block + anchor, 1)
SESSION.write_text(remaining)
print(f"moved={len(ordered)} lines_removed={len(removed)} reimported={len(still_used)}")
print("not reimported:", [name for name, _ in ordered if name not in used])
