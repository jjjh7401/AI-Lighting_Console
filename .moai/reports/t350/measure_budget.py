"""t350 계기 — `read_design_rig` 한 번이 콘솔 왕복을 몇 번 쓰는가.

t351 시험의 `_FakeConsole` 을 그대로 쓰고 세 읽기를 센다. 구성된 리그(16대·기종 2종)다.
이 숫자는 **구성된 대조군**이고 실기 콘솔 실측이 아니다 — 규모의 자릿수를 재는 계기다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.design.rig_capability_read import read_design_rig
from server.tests.test_lxseq_preset_group_range import _TYPES_ROOT, _FakeConsole


class _Counting(_FakeConsole):
    def __init__(self) -> None:
        super().__init__()
        self.calls: dict[str, int] = {
            "query_state": 0,
            "query_property": 0,
            "query_properties": 0,
        }

    def query_state(self, path, *, offset=0):
        self.calls["query_state"] += 1
        return super().query_state(path, offset=offset)

    def query_property(self, path, name):
        self.calls["query_property"] += 1
        return super().query_property(path, name)

    def query_properties(self, path, property_names):
        self.calls["query_properties"] += 1
        return super().query_properties(path, property_names)


port = _Counting()
read = read_design_rig(port, fixture_types_root=_TYPES_ROOT)
total = sum(port.calls.values())
print("attempted =", read.attempted, "| whole =", read.whole, "| gap =", read.gap or "(none)")
print("fixtures =", len(read.capabilities.fixtures) if read.capabilities else None)
print("calls    =", port.calls)
print("TOTAL round trips =", total)
