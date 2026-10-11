"""t601 — tools.py 헝크를 두 보호 시험의 기준(base)에서 잰다(커밋 뒤 실행)."""

from server.tests import test_overlap_preserve as op
from server.tests import test_songcue_bundle as sc

print("overlap base:", op._PRECHK_BASE)
hunks = op._hunks(op._PRECHK_BASE, op._TOOLS_PATH)
cross = [
    (s, c, p) for s, c in hunks for p in op._TOOLS_PROTECTED_OLD_RANGES if op._overlaps(s, c, *p)
]
print("overlap crossings:", cross)
for s, _c, _p in cross:
    print(" added@", s, op._added_lines(op._PRECHK_BASE, op._TOOLS_PATH, s))

print("songcue base:", sc._RUN_PHASE_BASE)
sc_hunks = sc._tools_hunks_from_run_phase_base()
starts = tuple(s for s, _c in sc_hunks)
expected = sc._TOOLS_EXPECTED_HUNK_OLD_STARTS
print("songcue hunk count:", len(starts), "expected:", len(expected))
print("new starts:", sorted(set(starts) - set(expected)))
print("gone starts:", sorted(set(expected) - set(starts)))
sc_cross = [
    (s, c)
    for s, c in sc_hunks
    for ps, pe in sc._TOOLS_PROTECTED_OLD_RANGES
    if sc._overlaps(s, c, ps, pe)
]
print("songcue crossings:", sc_cross)
for s, _c in sc_cross:
    print(" added@", s, sc._added_lines_of_hunk(s))
