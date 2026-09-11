"""t350 계기 5 — 기종 항이 실제로 무엇에 비례하는가 (기종 수인가 **채널 수**인가).

계기 3(`measure_types.py`)은 채널 2개짜리 템플릿을 복제해 기종 수만 늘렸으므로
「기종 1종당 10 왕복」을 냈다. 그 10 은 기종 수 항과 채널 수 항이 **섞인** 값이다.
정본 리그의 MegaPointe Mode 1 은 39ch 이므로 이 갈림이 추정을 몇 배 가른다.

장비 수를 4로, 기종 수를 1로 고정하고 **채널 수만** 바꾼다.
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


original_types = dict(mod._TYPES)
original_fixtures = dict(mod._FIXTURES)
FIXTURES = 4
rows = []
for channels in (1, 2, 4, 8, 39, 49):
    mod._TYPES.clear()
    mod._TYPES.update(
        {11: ("One Type", {slot: (f"Attr{slot}", 0.0, 100.0) for slot in range(1, channels + 1)})}
    )
    mod._FIXTURES.clear()
    mod._FIXTURES.update({slot: (11, 500 + slot) for slot in range(1, FIXTURES + 1)})
    port = _Counting()
    read = read_design_rig(port, fixture_types_root=mod._TYPES_ROOT)
    rows.append((channels, len(read.capabilities.fixtures) if read.capabilities else 0, port.n))

mod._TYPES.clear()
mod._TYPES.update(original_types)
mod._FIXTURES.clear()
mod._FIXTURES.update(original_fixtures)

print(f"장비 {FIXTURES} · 기종 1 고정")
print(f"{'채널':>6} {'판독됨':>6} {'왕복':>6}")
for channels, fixtures, total in rows:
    print(f"{channels:>6} {fixtures:>6} {total:>6}")
slope = (rows[-1][2] - rows[0][2]) / (rows[-1][0] - rows[0][0])
intercept = rows[0][2] - slope * rows[0][0]
print(f"\n채널 1개당 = {slope:.2f} 왕복 · 절편 = {intercept:.2f}")
print("\n정본 리그 추정 (장비 86 · 기종 8 · 기종당 평균 채널 39 가정):")
print(f"  = 2*86 + 8*({slope:.0f}*39 + (기종 고정비)) + (루트 고정비)")
