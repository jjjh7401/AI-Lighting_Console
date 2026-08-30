"""t188 1단계 — patchplan 의 나머지 포트 호출 둘이 **도달하는가**.

카드가 지정한 자극: 루트는 살리고 프로퍼티만 죽인다.

계기부터 검증한다(규약 §3 「재현 안 됨도 대조군 없이는 증거가 아니다」).
A0 이 양성 대조군이다 — 프로퍼티 호출이 실제로 일어나는 것을 스파이로 센다.
A0 이 0을 내면 그 뒤의 「안 죽는다」는 전부 무의미하다.

줄번호는 base 11f9d13 기준으로 다시 쟀다(카드는 0fc0439 기준이라 +22 밀려 있다):
  :1483 query_state(FID_FIXTURE_ROOT)   — 루트
  :1515 query_property 슬롯별 판독      — 카드의 :1493
  :1551 query_property 절단 복구 스윕   — 카드의 :1529
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.safety.console import StateQueryError  # noqa: E402
from server.vwx.patchplan import (  # noqa: E402
    FID_FIXTURE_ROOT,
    FID_PROPERTY_NAME,
    read_existing_fids,
)

WINDOW = 3  # 열거 창. childCount 보다 작게 두면 절단이 되어 스윕이 발화한다.


class Port:
    """루트는 답하고, 지정한 슬롯의 프로퍼티만 죽인다.

    raise_on 에 든 슬롯은 **예외를 던진다** — 프로덕션 포트의 실패 형태다
    (server/safety/console.py:713-721 — query_property 는 타임아웃도 ok=false 도
    전부 StateQueryError 로 올린다. ok=False 를 **반환하지 않는다**).
    """

    def __init__(self, child_count: int, window: int, raise_on: frozenset) -> None:
        self.child_count = child_count
        self.window = window
        self.raise_on = raise_on
        self.state_calls: list = []
        self.prop_calls: list = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path != FID_FIXTURE_ROOT:
            raise AssertionError("이 프로브는 루트만 요청받아야 한다: " + path)
        children = [dict(i=s, name="Spot " + str(s)) for s in range(1, self.window + 1)]
        return dict(ok=True, node=dict(childCount=self.child_count), children=children)

    def query_property(self, path: str, property_name: str) -> dict:
        self.prop_calls.append(path)
        assert property_name == FID_PROPERTY_NAME
        slot = int(path.rsplit("/", 1)[1])
        if slot in self.raise_on:
            raise StateQueryError("no prop reply for slot " + str(slot))
        return dict(ok=True, value=str(100 + slot))


def run(label: str, port: Port) -> None:
    print("--- " + label)
    try:
        read = read_existing_fids(port)
        print("    reason: " + read.reason())
        outcome = (
            "반환됨: complete="
            + str(read.complete)
            + " root_unreadable="
            + str(read.root_unreadable)
            + " fids="
            + str(read.fids)
            + " enumerated="
            + str(read.enumerated_count)
            + " recovered="
            + str(read.recovered_count)
            + " probe_failures="
            + str(read.probe_failures)
            + " unseen="
            + str(read.unseen)
        )
    except BaseException as exc:  # noqa: BLE001 — 무엇이 나오는지가 측정 대상이다
        outcome = "예외 탈출: " + type(exc).__name__ + ": " + str(exc)
        tb = sys.exc_info()[2]
        while tb.tb_next is not None:
            tb = tb.tb_next
        outcome += "  @ " + tb.tb_frame.f_code.co_filename.rsplit("/", 1)[1]
        outcome += ":" + str(tb.tb_lineno)
    print("    " + outcome)
    print(
        "    state 호출 "
        + str(len(port.state_calls))
        + "회 · prop 호출 "
        + str(len(port.prop_calls))
        + "회 "
        + str(port.prop_calls)
    )
    print()


run(
    "A0 대조군: 절단 없음, 아무 슬롯도 안 죽음",
    Port(child_count=WINDOW, window=WINDOW, raise_on=frozenset()),
)

run(
    "A1 :1515 — 열거 슬롯 2의 프로퍼티가 예외",
    Port(child_count=WINDOW, window=WINDOW, raise_on=frozenset([2])),
)

run(
    "A2 대조군: 절단(childCount 6 > 창 3), 안 죽음",
    Port(child_count=6, window=WINDOW, raise_on=frozenset()),
)

run(
    "A3 :1551 — 스윕 대상 슬롯 5의 프로퍼티가 예외",
    Port(child_count=6, window=WINDOW, raise_on=frozenset([5])),
)
