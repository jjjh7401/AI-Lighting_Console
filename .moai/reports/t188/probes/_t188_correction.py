"""t188 6단계 — 리드의 정정 1을 내가 다시 잰다.

내가 verdict §1-6 에 "unreadable_fids 갈래는 실기에서 죽은 코드다"라고 적었다.
리드가 반증했다: _fid_int 는 ok=True 라도 값이 int 도 decimal str 도 아니면
None 을 돌려주므로 :1524 의 `fid is None` 에 걸린다는 것.

동료 말은 주장이지 관측이 아니다. 실행으로 확인한다.

팔 셋:
  D0 정상 값        — unreadable_fids 가 안 오른다 (대조군)
  D1 ok=True + 깨진 값 — 리드의 주장. 오르면 갈래가 살아 있다
  D2 ok=True + 포인터 문자열 — 원전 독스트링 3번이 말한 실제 형태
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.vwx.patchplan import (  # noqa: E402
    FID_FIXTURE_ROOT,
    FID_PROPERTY_NAME,
    read_existing_fids,
)


class Port:
    def __init__(self, value_for_slot2) -> None:
        self.value_for_slot2 = value_for_slot2

    def query_state(self, path: str) -> dict:
        assert path == FID_FIXTURE_ROOT
        children = [dict(i=s, name="Spot " + str(s)) for s in range(1, 4)]
        return dict(ok=True, node=dict(childCount=3), children=children)

    def query_property(self, path: str, property_name: str) -> dict:
        assert property_name == FID_PROPERTY_NAME
        slot = int(path.rsplit("/", 1)[1])
        if slot == 2:
            return dict(ok=True, value=self.value_for_slot2)
        return dict(ok=True, value=str(100 + slot))


def run(label: str, value) -> None:
    read = read_existing_fids(Port(value))
    print("--- " + label)
    print(
        "    unreadable_fids="
        + str(read.unreadable_fids)
        + " complete="
        + str(read.complete)
        + " fids="
        + str(read.fids)
    )
    print("    reason: " + read.reason())
    print()


run("D0 대조군: 정상 값 '102'", "102")
run("D1 ok=True + 깨진 값 None", None)
run("D2 ok=True + 포인터 문자열", "Ptr:0x7f")
