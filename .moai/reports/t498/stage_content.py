"""t498 — 무대에 실제로 나간 것: 승인·송신된 119줄을 큐 단위로 나눠 색·포지션·디머·그룹을 센다.

실행: uv run python .moai/reports/t498/stage_content.py <approval_request_1.txt>
"""

import re
import sys
from collections import Counter
from pathlib import Path

lines = Path(sys.argv[1]).read_text("utf-8").splitlines()
FIX = re.compile(r"^Fixture ((?:\d+)(?: \+ \d+)*) ;(.*)$")

cues: list[tuple[str, list[str]]] = []
pending: list[str] = []
for x in lines:
    m = re.match(r"^Store Sequence 211 Cue ([\d.]+) '([^']*)'", x)
    if m:
        cues.append((f"{m.group(1)} {m.group(2)}", pending))
        pending = []
    elif x != "ClearAll":
        pending.append(x)

colors, positions, all_fixtures = Counter(), Counter(), set()
print("cue | 기구수 | 포지션 | 디머(기구) | 색(RGB) | 그룹 줄")
for name, body in cues:
    fids, pos, dim, rgb, grp = set(), [], [], set(), []
    for x in body:
        m = FIX.match(x)
        if m:
            ids = m.group(1).split(" + ")
            fids |= set(ids)
            rest = m.group(2)
            if p := re.search(r"At Preset (\S+)", rest):
                pos.append(f"{p.group(1)}x{len(ids)}")
                positions[p.group(1)] += 1
            if d := re.search(r"'Dimmer' At (\d+)", rest):
                dim.append(f"{d.group(1)}x{len(ids)}")
            if "ColorRGB_R" in rest:
                c = tuple(re.findall(r"ColorRGB_[RGB]' At (\d+)", rest))
                rgb.add(c)
                colors[c] += 1
        elif x.startswith("Group"):
            grp.append(x)
    all_fixtures |= fids
    print(f"{name} | {len(fids)} | {pos} | {dim} | {sorted(rgb)} | {grp}")
print("cues:", len(cues), "· distinct fixtures:", len(all_fixtures))
print("distinct RGB values across all cues:", dict(colors))
print("position presets used:", dict(positions))
