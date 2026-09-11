"""t350 계기 3 — 고정비가 기종 수에 따라 어떻게 자라는가.

🔴 **이 계기의 결론(「기종 1종당 10 왕복」)은 항이 섞인 값이라 폐기됐다.** 파일은
지운 게 아니라 남겨 둔다 — 다음 카드가 같은 설계로 다시 재지 않게 하려는 것이다.

무엇이 틀렸는가: 아래 스윕은 채널 2개짜리 템플릿(`template`)을 **복제**해 기종 수만
늘린다. 그래서 기종을 하나 더할 때마다 채널도 둘 늘고, 나온 10 은 기종 항 4 와
채널 항 3x2 의 합이다. 정본 리그의 Spiider Mode 1 은 49ch 이므로 이 혼합식을 그대로
정본 리그에 쓰면 255 왕복이 나오고 실제는 **669** 다(2.6배 과소).

갈라 잰 것은 계기 5(`measure_channels.py`)이고, 닫힌 식은 계기 6
(`verify_formula.py`)이 46개 점에서 검산했다:

    왕복 = 2*장비 + 4*(기종,모드) + 3*(채널 합) + 3

장비 수를 16 로 고정하고 기종 수만 바꾼다. 정본 실측 리그는 기종 15종이었다(t344).
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
template = original_types[11]
FIXTURES = 16
rows = []
for type_count in (1, 2, 4, 8, 15):
    slots = list(range(11, 11 + type_count))
    mod._TYPES.clear()
    mod._TYPES.update({slot: (f"Type {slot}", dict(template[1])) for slot in slots})
    mod._FIXTURES.clear()
    mod._FIXTURES.update(
        {slot: (slots[(slot - 1) % type_count], 500 + slot) for slot in range(1, FIXTURES + 1)}
    )
    port = _Counting()
    read = read_design_rig(port, fixture_types_root=mod._TYPES_ROOT)
    rows.append((type_count, len(read.capabilities.fixtures) if read.capabilities else 0, port.n))

mod._TYPES.clear()
mod._TYPES.update(original_types)
mod._FIXTURES.clear()
mod._FIXTURES.update(original_fixtures)

print(f"장비 {FIXTURES} 고정")
print(f"{'기종':>6} {'판독됨':>6} {'왕복':>6}")
for type_count, fixtures, total in rows:
    print(f"{type_count:>6} {fixtures:>6} {total:>6}")
slope = (rows[-1][2] - rows[0][2]) / (rows[-1][0] - rows[0][0])
print(f"\n기종 1종당 = {slope:.2f} 왕복")
