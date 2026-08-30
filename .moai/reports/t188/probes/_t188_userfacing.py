"""t188 2단계 — :1515 가 죽을 때 **사용자가 무엇을 보는가**.

1단계에서 :1515 의 예외가 read_existing_fids 를 그대로 탈출하는 것을 쟀다.
소비 지점은 셋인데 방어가 갈린다(base 11f9d13):
  tools.py:4369 patch_fixtures        — read_existing_fids 를 안 감쌌다
  tools.py:4750 import_lxseq_groups   — t182 가 except StateQueryError 로 감쌌다
  tools.py:5457 import_lxseq_patch    — 안 감쌌다

여기서 재는 것은 4750 하나다. 나머지 둘은 인자 조립이 무거워 따로 잰다.
물음: t182 의 catch 가 살려는 주지만 **무엇이라고 말하는가**.
루트는 읽혔고 슬롯 하나가 죽은 상황인데 unreadable_root() 를 돌려주면
「콘솔의 픽스처 루트 상태를 읽지 못했다」가 나간다 — 그것은 거짓이다.

대조군을 둘 둔다(규약 §3 「대조군은 두 팔」):
  B0 아무것도 안 죽음        — 이 사유가 늘 붙는 게 아님을 보인다
  B1 루트가 죽음(t182 자리)  — 그 사유가 **참인** 경우를 보인다
  B2 슬롯 프로퍼티가 죽음    — 측정 대상. 같은 사유가 나오면 둘이 안 갈린다
"""

from __future__ import annotations

import importlib.util
import json
import sys

sys.path.insert(0, ".")

_spec = importlib.util.spec_from_file_location(
    "_t152mod", "server/tests/test_lxseq_group_section_request.py"
)
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

from server.safety.console import StateQueryError  # noqa: E402
from server.vwx.patchplan import FID_FIXTURE_ROOT  # noqa: E402


class RaisingSlotProperty:
    """루트 state 는 통과시키고, 지정 슬롯의 query_property 만 예외로 만든다."""

    def __init__(self, base, slot: int) -> None:
        self._base = base
        self._slot = slot
        self.prop_calls: list = []

    def query_state(self, path: str, *args, **kwargs) -> dict:
        return self._base.query_state(path, *args, **kwargs)

    def query_property(self, path: str, property_name: str) -> dict:
        self.prop_calls.append(path)
        if path.rsplit("/", 1)[1] == str(self._slot):
            raise StateQueryError("no prop reply for " + path)
        return self._base.query_property(path, property_name)

    def __getattr__(self, name):
        return getattr(self._base, name)


class RaisingRoot:
    """t182 가 고친 자리 — 루트 state 자체가 죽는다."""

    def __init__(self, base) -> None:
        self._base = base

    def query_state(self, path: str, *args, **kwargs) -> dict:
        if path == FID_FIXTURE_ROOT:
            raise StateQueryError("no state reply for " + path)
        return self._base.query_state(path, *args, **kwargs)

    def query_property(self, path: str, property_name: str) -> dict:
        return self._base.query_property(path, property_name)

    def __getattr__(self, name):
        return getattr(self._base, name)


def run(label: str, port) -> None:
    print("--- " + label)
    try:
        execution = T._dispatch(port)
    except BaseException as exc:  # noqa: BLE001 — 무엇이 나오는지가 측정 대상이다
        tb = sys.exc_info()[2]
        while tb.tb_next is not None:
            tb = tb.tb_next
        print("    예외 탈출: " + type(exc).__name__ + ": " + str(exc))
        print("    @ " + tb.tb_frame.f_code.co_filename.rsplit("/", 1)[1] + ":" + str(tb.tb_lineno))
        print()
        return
    if execution.result.is_error:
        print("    거절: " + str(execution.result.content)[:200])
        print()
        return
    payload = json.loads(execution.result.content)
    print("    console_read_incomplete = " + str(payload.get("console_read_incomplete")))
    print("    console_read_reason     = " + str(payload.get("console_read_reason")))
    print()


fids = T._patch_fids()

run("B0 대조군: 아무것도 안 죽음", T._Console(fids))
run("B1 대조군: 루트 state 가 죽음 (t182 가 고친 자리)", RaisingRoot(T._Console(fids)))
run("B2 측정: 슬롯 2의 프로퍼티만 죽음 (:1515)", RaisingSlotProperty(T._Console(fids), 2))
