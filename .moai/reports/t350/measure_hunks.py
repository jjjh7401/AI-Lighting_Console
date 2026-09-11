"""t350 계기 7 — `tools.py` hunk 재고와 보호 구간 겹침을 **커밋된 HEAD** 에 대고 잰다.

🔴 이 계기가 있는 이유: 1차 측정이 **작업 트리를 못 보는 계기**였다. `git diff A..HEAD`
는 커밋된 HEAD 만 비교하므로, 커밋 전에 그 명령을 돌리면 내 변경이 **한 줄도 안 들어간**
diff 를 잰다. 그때 나온 「84 -> 84, 새 시작점 0」은 「내 변경이 hunk 를 안 옮겼다」가
아니라 「내 변경을 안 봤다」였다. 같은 이유로 `test_songcue_bundle.py` 의 트립와이어
검사도 커밋 전에는 공허하게 통과한다 — 그 검사도 같은 명령을 쓴다.

실제 델타는 커밋 뒤 CI 가 잡았다: **84 -> 93 hunks**.

두 base 를 함께 잰다. 겹침 판정은 `test_songcue_bundle.py` · `test_overlap_preserve.py`
의 `_overlaps` 와 같은 식이다.
"""

from __future__ import annotations

import re
import subprocess
import sys

sys.path.insert(0, ".")

HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")
TOOLS = "server/orchestrator/tools.py"

#: (이름, base 커밋, 보호 구간). 값은 각 검사 파일이 고정한 것을 그대로 옮긴 것이다.
BASES = (
    ("SONGCUE", "38a6e7e2157a4862721fcd868056e0dbbb09c4c0", ((234, 238), (524, 569))),
    ("PRECHK", "95687a0e0eba90b325daf76efbd0ac197e69e2fc", ((247, 251), (537, 582))),
)


def hunks(base: str) -> list[tuple[int, int]]:
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--unified=0", f"{base}..HEAD", "--", TOOLS],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    out: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        match = HUNK_RE.match(line)
        if match is not None:
            out.append((int(match.group("old_start")), int(match.group("old_count") or "1")))
    return out


def overlaps(old_start: int, old_count: int, protected_start: int, protected_end: int) -> bool:
    old_end = old_start + max(old_count, 1) - 1
    return old_start <= protected_end and protected_start <= old_end


for name, base, protected_ranges in BASES:
    rows = hunks(base)
    starts = [start for start, _count in rows]
    crossings = [
        (start, count, protected)
        for start, count in rows
        for protected in protected_ranges
        if overlaps(start, count, *protected)
    ]
    print(f"=== {name} base {base[:7]} ===")
    print(f"hunk 수: {len(rows)}")
    print("시작점: " + " ".join(str(s) for s in starts))
    print(f"보호 구간 {protected_ranges} 겹침: {len(crossings)}")
    for start, count, protected in crossings:
        print(f"  🔴 hunk {start}(+{count}) 가 {protected} 를 건드린다")
    # 비공허성 — 겹침 술어가 늘 거짓이 아님을 같은 실행에서 보인다.
    probe_start, probe_end = protected_ranges[0]
    assert overlaps(probe_start, 1, probe_start, probe_end)
    assert not overlaps(probe_end + 1, 1, probe_start, probe_end)
    print("겹침 술어 비공허성: 심어둔 hunk 는 잡고, 바로 밖은 안 잡는다")
    print()
