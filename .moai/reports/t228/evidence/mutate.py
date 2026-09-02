"""t228 뮤테이션 배치 — 큐 단위 입도를 지키는 검사가 실제로 지키는지 잰다.

각 회차마다 치환이 **적용됐는지**를 눈이 아니라 단언으로 확인한다(규약 §3.3).
문자열 상수는 줄 길이 규격(100)에 맞추려고 이어붙였다 — 앵커 자체는 소스와
바이트 동일해야 하므로 줄바꿈을 넣지 않고 인접 리터럴로만 나눴다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAP = Path("server/lxseq/cue_mapper.py")
TOOLS = Path("server/orchestrator/tools.py")

M1_OLD = (
    "    if held and not any(cue in rows_by_cue and cue not in held_cue_names for cue in declared):"
)
M2_OLD = (
    "        if rows_by_cue.get(cue) and cue not in cues_already_present "
    "and cue not in held_cue_names"
)
M3_OLD = (
    "        and cue not in held_cue_names\n"
    "        and any(call.cue_no == cue for call in video_calls)"
)

MUTANTS = [
    ("M1 배치 거절로 되돌린다", MAP, M1_OLD, "    if held:"),
    (
        "M2 보류된 큐를 부분 출하시킨다",
        MAP,
        M2_OLD,
        "        if rows_by_cue.get(cue) and cue not in cues_already_present",
    ),
    (
        "M3 보류로 빈 큐를 video_only 로 오분류한다",
        MAP,
        M3_OLD,
        "        and any(call.cue_no == cue for call in video_calls)",
    ),
    (
        "M4 함께 빠진 성한 행 수를 안 센다",
        MAP,
        "            withheld_rows=len(rows_by_cue.get(cue, ())),",
        "            withheld_rows=0,",
    ),
    (
        "M5 부분 출하 표식을 끈다",
        TOOLS,
        '            "partial_ship": bool(result.cues_held) and bool(result.planned),',
        '            "partial_ship": False,',
    ),
    (
        "M6 보류 큐의 참조 목록을 비운다",
        TOOLS,
        "                    preset_refs=sorted(unresolved_by_cue.get(entry.cue_no, ())),",
        "                    preset_refs=[],",
    ),
]

TARGET = [
    "server/tests/test_lxseq_cue_mapper.py",
    "server/tests/test_lxseq_cue_partial_ship.py",
]


def main() -> int:
    for label, path, old, new in MUTANTS:
        original = path.read_text(encoding="utf-8")
        assert original.count(old) == 1, (label, "anchor", original.count(old))
        path.write_text(original.replace(old, new), encoding="utf-8")
        assert path.read_text(encoding="utf-8") != original, (label, "not applied")
        run = subprocess.run(
            [sys.executable, "-m", "pytest", *TARGET, "-q", "--no-header"],
            capture_output=True,
            text=True,
        )
        path.write_text(original, encoding="utf-8")
        tail = [line for line in run.stdout.splitlines() if line.strip()][-1]
        print(label, "->", "DEAD" if run.returncode != 0 else "SURVIVED", "|", tail)
        for line in run.stdout.splitlines():
            if line.startswith("FAILED"):
                print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
