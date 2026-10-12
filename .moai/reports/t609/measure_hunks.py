"""카드 t609 — tools.py hunk 재고 목록 갱신용 측정(커밋 뒤에 잰다).

``test_songcue_bundle`` 의 도우미를 그대로 불러 기대 목록과 실제 시작점을 비교하고,
보호 구간 겹침을 같은 ``_overlaps`` 로 다시 잰다.
"""

from server.tests import test_overlap_preserve as overlap
from server.tests import test_songcue_bundle as bundle

hunks = bundle._tools_hunks_from_run_phase_base()
actual = tuple(start for start, _count in hunks)
expected = bundle._TOOLS_EXPECTED_HUNK_OLD_STARTS
print("hunks:", len(expected), "->", len(actual))
print("new starts:", sorted(set(actual) - set(expected)))
print("gone starts:", sorted(set(expected) - set(actual)))
print("hunks with count:", [(s, c) for s, c in hunks if s not in expected])
names = [n for n in dir(bundle) if "PROTECT" in n.upper() or "RANGE" in n.upper()]
print("protected-range names in bundle:", names)
names2 = [n for n in dir(overlap) if "PROTECT" in n.upper() or "RANGE" in n.upper()]
print("protected-range names in overlap:", names2)
