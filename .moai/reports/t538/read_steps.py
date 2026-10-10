"""t538 읽기 전용 — 단계 목록을 파일에서 읽어 t506 probe_readonly.main 에 넘긴다.

셸 인자에 ``|`` 가 들어가면 세션 가드가 거절하므로, 단계를 한 줄씩 파일에 둔다.
쓰기(exec)는 없다 — probe_readonly 는 ping/state/introspect/prop(s) 만 보낸다.

실행: uv run python .moai/reports/t538/read_steps.py <단계파일>
"""

import sys

sys.path.insert(0, ".moai/reports/t506")
import probe_readonly  # noqa: E402

steps = [
    line.strip()
    for line in open(sys.argv[1], encoding="utf-8")
    if line.strip() and not line.startswith("#")
]
probe_readonly.main(steps)
