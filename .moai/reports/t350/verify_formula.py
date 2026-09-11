"""t350 계기 6 — 닫힌 식을 세 축 전수 스윕으로 검산한다.

계기 3(`measure_types.py`)이 낸 「기종 1종당 10 왕복」은 **틀린 항이었다**: 채널 2개짜리
템플릿을 복제했으므로 기종 항과 채널 항이 섞였다. 계기 5(`measure_channels.py`)가 채널만
갈라 3 왕복/채널을 냈고, 이 계기가 세 축(장비 · 기종 · 채널)을 함께 스윕해 닫힌 식을
검산한다.

    왕복 = 2*장비 + 4*(기종,모드) + 3*(모든 (기종,모드)의 채널 합) + 3

한 점이라도 안 맞으면 그 자리를 출력한다 — 「대체로 맞는다」를 식이라고 부르지 않는다.
구성된 대조군이고 실기 콘솔 실측이 아니다.
"""

from __future__ import annotations

import itertools
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


def predicted(fixtures: int, channels_per_type: list[int]) -> int:
    return 2 * fixtures + 4 * len(channels_per_type) + 3 * sum(channels_per_type) + 3


def measure(fixtures: int, channels_per_type: list[int]) -> tuple[int, int]:
    slots = list(range(11, 11 + len(channels_per_type)))
    mod._TYPES.clear()
    mod._TYPES.update(
        {
            slot: (
                f"Type {slot}",
                {c: (f"Attr{slot}_{c}", 0.0, 100.0) for c in range(1, channels + 1)},
            )
            for slot, channels in zip(slots, channels_per_type, strict=True)
        }
    )
    mod._FIXTURES.clear()
    mod._FIXTURES.update(
        {slot: (slots[(slot - 1) % len(slots)], 500 + slot) for slot in range(1, fixtures + 1)}
    )
    port = _Counting()
    read = read_design_rig(port, fixture_types_root=mod._TYPES_ROOT)
    read_count = len(read.capabilities.fixtures) if read.capabilities else 0
    return port.n, read_count


original_types = dict(mod._TYPES)
original_fixtures = dict(mod._FIXTURES)

cases: list[tuple[int, list[int]]] = []
for fixtures, types, channels in itertools.product((2, 4, 16, 64), (1, 2, 4), (1, 2, 8, 39)):
    if fixtures < types:
        continue
    cases.append((fixtures, [channels] * types))
# 채널 수가 기종마다 다른 경우 — 정본 리그가 그 모양이다.
cases.append((8, [39, 49]))
cases.append((86, [25, 9, 12, 49, 39, 4, 14, 2]))

mismatches = []
for fixtures, channels_per_type in cases:
    observed, read_count = measure(fixtures, channels_per_type)
    expect = predicted(fixtures, channels_per_type)
    ok = observed == expect and read_count == fixtures
    if not ok:
        mismatches.append((fixtures, channels_per_type, observed, expect, read_count))

mod._TYPES.clear()
mod._TYPES.update(original_types)
mod._FIXTURES.clear()
mod._FIXTURES.update(original_fixtures)

print(f"검산한 점 {len(cases)}개 · 안 맞는 점 {len(mismatches)}개")
for fixtures, channels_per_type, observed, expect, read_count in mismatches:
    print(f"  장비 {fixtures} 채널 {channels_per_type}")
    print(f"    관측 {observed} · 예측 {expect} · 판독된 장비 {read_count}")

canonical = [25, 9, 12, 49, 39, 4, 14, 2]
print("\n정본 리그 (LXSEQ_RIG_01_ShowBase_r3.patch.csv 실측: 장비 86 · (기종,모드) 8쌍 ·")
print(f"채널 합 {sum(canonical)}) -> {predicted(86, canonical)} 왕복 / 저장 1회")
print(f"  같은 리그 실제 측정: {measure(86, canonical)[0]} 왕복")
print(f"  가장 비싼 한 쌍(49ch): {3 * 49} 왕복 — 쌍당 budget 기본값 256 아래")
