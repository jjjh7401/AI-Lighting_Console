"""t601 뮤테이션 — 각 변형을 적용해 시험을 돌리고 원본으로 되돌린다."""

import subprocess
from pathlib import Path

PATH = Path("server/orchestrator/tools.py")
TESTS = [
    "server/tests/test_dedupe_legit_repeat_t601.py",
    "server/tests/test_tools.py",
    "server/tests/test_dedupe_value_lines_t476.py",
]
_OK = "                if result.ok:\n"
MUTATIONS = [
    (
        "R 수정 되돌리기(묶음 안 성공을 다시 기억)",
        _OK,
        _OK + "                    already_executed = already_executed | {command}  # MUTATION\n",
    ),
    (
        "P 앞선 호출 건너뛰기 끄기",
        "        already_executed = context.executed_ok\n",
        "        already_executed = frozenset()  # MUTATION\n",
    ),
]
for name, old, new in MUTATIONS:
    src = PATH.read_text()
    assert src.count(old) == 1, name
    PATH.write_text(src.replace(old, new))
    try:
        r = subprocess.run(
            ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", *TESTS],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        PATH.write_text(src)
    print(name, "→", r.stdout.strip().splitlines()[-1])
