"""t516 v2 근거 — 실기에서 켜진 앱 송신 파일과 v1 승인 파일의 줄 모양을 센다.

선택 줄이 혼자 오는지(`Group 4` 한 줄), 값과 한 줄로 묶이는지(`Group 4 ; Attribute …`),
Fixture 번호 목록인지 Group 인지, 페이저(Step)·ClearAll 이 몇 줄인지.

실행: uv run python .moai/reports/t516/line_shapes.py <파일> [<파일> …]
"""

import re
import sys
from pathlib import Path

SHAPES = {
    "lone Group": r"^Group \d+$",
    "lone Fixture list": r"^Fixture [\d +]+$",
    "Group ; Attribute (one line)": r"^Group \d+ ; Attribute",
    "Fixture list ; Attribute (one line)": r"^Fixture [\d +]+ ; Attribute",
    "Fixture list ; At Preset": r"^Fixture [\d +]+ ; At Preset",
    "Attribute-first line": r"^Attribute",
    "Step line": r"^Step ",
    "ClearAll": r"^ClearAll$",
    "Store Sequence": r"^Store Sequence",
}
for name in sys.argv[1:]:
    lines = Path(name).read_text("utf-8").splitlines()
    print(f"== {name} ({len(lines)} lines)")
    for label, pattern in SHAPES.items():
        print(f"  {label:38s} {sum(1 for ln in lines if re.match(pattern, ln))}")
