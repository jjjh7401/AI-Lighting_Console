"""t350 계기 4 — 기종당 10 왕복이 **라이브러리 전체**인가 **참조된 기종**인가.

라이브러리에 15종을 두고 장비가 2종만 참조하게 한다. 왕복이 15종분이면 라이브러리
전체이고, 2종분이면 참조된 것만이다. 이 갈림이 정본 리그의 예상치를 두 배 이상 가른다.
구성된 대조군이다.
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
template = original_types[11]

for library_size, referenced in ((2, 2), (15, 2), (15, 15)):
    slots = list(range(11, 11 + library_size))
    mod._TYPES.clear()
    mod._TYPES.update({slot: (f"Type {slot}", dict(template[1])) for slot in slots})
    used = slots[:referenced]
    mod._FIXTURES.clear()
    mod._FIXTURES.update(
        {slot: (used[(slot - 1) % referenced], 500 + slot) for slot in range(1, 17)}
    )
    port = _Counting()
    read_design_rig(port, fixture_types_root=mod._TYPES_ROOT)
    print(f"라이브러리 {library_size:>2}종 · 참조 {referenced:>2}종 · 장비 16 -> 왕복 {port.n}")

mod._TYPES.clear()
mod._TYPES.update(original_types)
mod._FIXTURES.clear()
mod._FIXTURES.update(original_fixtures)
