"""t432 2단계 — 패치 8종의 PhysicalDescriptions 를 읽기만 한다(state·props, exec 0).

    uv run python .moai/reports/t432/c6_all_types.py > .moai/reports/t432/c6_all_types.txt

1단계(state)로 각 컨테이너의 자식 수를 세고, 이미터는 자식마다 읽을 수 있는 필드
(introspect 로 확인한 19개 중 값 필드)를 읽는다. COLOR 는 Custom 형이라 응답기
1.6.5 가 읽지 못한다(c4·c5) — 그래도 요청에 넣어 거부 문면을 기종마다 남긴다.
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("probe", ROOT / ".moai/reports/t431/probe_t431.py")
probe = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT))
spec.loader.exec_module(probe)

TYPES = (8, 9, 10, 4, 11, 13, 14, 15)  # 패치에 쓰는 타입(t442 run4 재집계)
CONTAINERS = ("Emitters", "CRIs", "FTFilters", "ColorSpaceCollect", "GamutCollect")
EMITTER_FIELDS = "NAME,COLOR,INTENSITY,DOMINANTWAVELENGTH,DIODEPART"
# 이미터 수 상한(Lustr X8 이 7) — 없는 번호는 not found 로 돌아온다(읽기만).
MAX_EMITTERS = 8

steps = []
for no in TYPES:
    base = f"Patch/FixtureTypes/{no}/PhysicalDescriptions"
    steps.append(f"state:Patch/FixtureTypes/{no}")
    steps.extend(f"state:{base}/{name}" for name in CONTAINERS)
    steps.extend(f"props:{base}/Emitters/{i}|{EMITTER_FIELDS}" for i in range(1, MAX_EMITTERS + 1))
    steps.append(f"state:Patch/FixtureTypes/{no}/Wheels")
print(json.dumps({"steps": len(steps)}), flush=True)
probe.main(steps)
