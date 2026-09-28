"""t480 D3 — 파일째 은퇴한 시험 파일의 시험 수를 D3 직전 커밋에서 센다(읽기 전용).

실행(저장소 루트): `uv run python .moai/reports/t480/d3_count_deleted.py`
"""

import re
import subprocess

BEFORE = "b6eae127^"
FILES = (
    "test_songcue_accent_fixture",
    "test_songcue_chorus_rescue",
    "test_songcue_cross_song",
    "test_songcue_front_fill",
    "test_songcue_report",
    "test_songcue_t429_repeat_chorus_collision",
)

total = 0
for name in FILES:
    src = subprocess.run(
        ["git", "show", f"{BEFORE}:server/tests/{name}.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    count = len(re.findall(r"^\s*def test_", src, flags=re.MULTILINE))
    total += count
    print(f"{name}: {count}")
print(f"total: {total}")
