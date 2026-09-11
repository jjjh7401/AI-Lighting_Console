"""t350 계기 2 — 왕복 수가 장비 수에 따라 어떻게 자라는가.

t351 시험 모듈의 `_FIXTURES` 를 갈아끼우며 같은 계기를 반복한다. 기종은 2종 고정이고
장비 수만 바꾼다 — 기울기(장비 1대당 왕복)와 절편(기종·루트 판독 고정비)을 가른다.
구성된 대조군이고 실기 콘솔 실측이 아니다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.design.rig_capability_read import read_design_rig
from server.tests import test_lxseq_preset_group_range as mod


class _Counting(mod._FakeConsole):
    def __init__(self) -> None:
        super().__init__()
        self.n = 0

    def query_state(self, path, *, offset=0):
        self.n += 1
        return super().query_state(path, offset=offset)

    def query_property(self, path, name):
        self.n += 1
        return super().query_property(path, name)

    def query_properties(self, path, property_names):
        self.n += 1
        return super().query_properties(path, property_names)


original = dict(mod._FIXTURES)
rows = []
for count in (2, 4, 8, 16, 32, 64):
    half = count // 2
    mod._FIXTURES.clear()
    mod._FIXTURES.update({slot: (11, 500 + slot) for slot in range(1, half + 1)})
    mod._FIXTURES.update({slot: (12, 500 + slot) for slot in range(half + 1, count + 1)})
    port = _Counting()
    read = read_design_rig(port, fixture_types_root=mod._TYPES_ROOT)
    fixtures = len(read.capabilities.fixtures) if read.capabilities else 0
    rows.append((count, fixtures, port.n))

mod._FIXTURES.clear()
mod._FIXTURES.update(original)

print(f"{'장비':>6} {'판독됨':>6} {'왕복':>6} {'대당':>7}")
for count, fixtures, total in rows:
    print(f"{count:>6} {fixtures:>6} {total:>6} {total / count:>7.2f}")
slope = (rows[-1][2] - rows[0][2]) / (rows[-1][0] - rows[0][0])
intercept = rows[0][2] - slope * rows[0][0]
print(f"\n기울기 = {slope:.2f} 왕복/장비 · 절편 = {intercept:.2f} 왕복(고정비)")
