"""t188 4단계 — 내 자극에서 read_inventory 가 **먼저 거절하는가**.

t182 커밋 본문이 적은 실측: "4368·5447 은 t181 이 고친 read_inventory 에서 먼저
거절된다". 그 자극은 픽스처 **경로 전체**를 죽였다. 내 자극은 **슬롯 프로퍼티
하나만** 죽인다. 두 자극이 다르므로 그 값을 그대로 옮겨 쓸 수 없다.

물음: read_inventory 가 FID 프로퍼티를 읽는가. 안 읽으면 내 자극에서 살아남고,
그러면 제어가 read_existing_fids 까지 내려간다.

patchplan 독스트링은 "prechk.inventory 는 FID를 화이트리스트 밖에 두어 아예 읽지
않는다"고 적었다. 그건 **문면**이고, 여기서는 포트 호출을 세서 재는 것이다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.prechk.inventory import read_inventory  # noqa: E402
from server.vwx.patchplan import FID_FIXTURE_ROOT, FID_PROPERTY_NAME  # noqa: E402


class SpyPort:
    def __init__(self, child_count: int) -> None:
        self.child_count = child_count
        self.state_calls: list = []
        self.prop_calls: list = []

    def query_state(self, path: str, *args, **kwargs) -> dict:
        self.state_calls.append(path)
        children = [
            dict(i=s, name="Spot " + str(s), fid=str(100 + s))
            for s in range(1, self.child_count + 1)
        ]
        return dict(ok=True, node=dict(childCount=self.child_count), children=children)

    def query_property(self, path: str, property_name: str) -> dict:
        self.prop_calls.append((path, property_name))
        return dict(ok=True, value="stub")


port = SpyPort(child_count=3)
try:
    inv = read_inventory(port)
    print("read_inventory 반환됨: " + type(inv).__name__)
except BaseException as exc:  # noqa: BLE001
    print("read_inventory 예외: " + type(exc).__name__ + ": " + str(exc))

print()
print("state 호출 " + str(len(port.state_calls)) + "회")
print("prop  호출 " + str(len(port.prop_calls)) + "회")
for c in port.prop_calls:
    print("    " + str(c))
print()
fid_props = [c for c in port.prop_calls if c[1] == FID_PROPERTY_NAME]
print("그중 FID 프로퍼티(" + FID_PROPERTY_NAME + ") 판독: " + str(len(fid_props)) + "회")
print("FID 루트 경로 상수: " + FID_FIXTURE_ROOT)
