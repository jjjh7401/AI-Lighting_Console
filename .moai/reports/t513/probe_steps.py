"""t513 — t498 probe_readonly.py 를 단계 파일로 돌린다.

읽기 전용: ping/state/introspect/prop/props 만.

실행: uv run python .moai/reports/t513/probe_steps.py <단계 파일>
"""

import runpy
import sys
from pathlib import Path

steps = [s for s in Path(sys.argv[1]).read_text("utf-8").splitlines() if s.strip()]
sys.argv = ["probe_readonly.py", *steps]
runpy.run_path(".moai/reports/t498/probe_readonly.py", run_name="__main__")
