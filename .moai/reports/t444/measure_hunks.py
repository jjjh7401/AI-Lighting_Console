"""카드 t444 — tools.py 헝크 재고 측정(커밋 **뒤에** 돌린다, t350 함정).

실행: uv run python .moai/reports/t444/measure_hunks.py > .moai/reports/t444/measure_hunks.out.txt
"""

from __future__ import annotations

from server.tests.test_songcue_bundle import (
    _TOOLS_EXPECTED_HUNK_OLD_STARTS,
    _TOOLS_PROTECTED_OLD_RANGES,
    _overlaps,
    _tools_hunks_from_run_phase_base,
)

# 형제 게이트(test_overlap_preserve.py)의 보호 구간 — t350·t441 항목과 같은 값.
SIBLING_PROTECTED = ((247, 251), (537, 582))

hunks = _tools_hunks_from_run_phase_base()
starts = tuple(start for start, _count in hunks)
expected = set(_TOOLS_EXPECTED_HUNK_OLD_STARTS)
print(f"hunks: {len(_TOOLS_EXPECTED_HUNK_OLD_STARTS)} -> {len(hunks)}")
print("new starts:", sorted(set(starts) - expected))
print("gone starts:", sorted(expected - set(starts)))
for label, ranges in (("protected", _TOOLS_PROTECTED_OLD_RANGES), ("sibling", SIBLING_PROTECTED)):
    overlaps = [
        (start, count)
        for start, count in hunks
        for lo, hi in ranges
        if _overlaps(start, count, lo, hi)
    ]
    print(f"{label} overlaps: {len(overlaps)} {overlaps}")
