"""t188 5단계 — patch_fixtures(tools.py:4369)를 **실제로 태워** 사용자 문면을 본다.

4단계에서 read_inventory 가 FID 프로퍼티를 0회 읽는 것을 쟀다. 그러므로 FID
프로퍼티만 죽는 자극에서는 t181 의 거절이 먼저 걸리지 않는다 — 그 추론을 여기서
도구 dispatch 로 확인한다. ast 의 '덮는 try 없음'은 도달의 증거가 아니다.

대조군 두 팔(규약 §3):
  C0 아무것도 안 죽음      — 이 하네스가 원래 통과하는 것을 보인다
  C1 FID 프로퍼티만 죽음   — 측정 대상
  C2 Patch 프로퍼티가 죽음 — t181 이 먼저 거절하는 것을 보인다(자극 대비군)
"""

from __future__ import annotations

import importlib.util
import sys

sys.path.insert(0, ".")

_spec = importlib.util.spec_from_file_location(
    "_stagedpatch", "server/tests/test_vwx_stagedpatch.py"
)
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

from server.safety.console import StateQueryError  # noqa: E402
from server.vwx.patchplan import FID_PROPERTY_NAME  # noqa: E402


class KillProperty:
    """지정한 **프로퍼티 이름**의 판독만 예외로 만든다. 경로는 안 가린다."""

    def __init__(self, base, prop_name: str) -> None:
        self._base = base
        self._prop = prop_name
        self.hits = 0

    def query_state(self, path: str, *args, **kwargs):
        return self._base.query_state(path, *args, **kwargs)

    def query_property(self, path: str, property_name: str):
        if property_name == self._prop:
            self.hits += 1
            raise StateQueryError("no prop reply for " + path + " " + property_name)
        return self._base.query_property(path, property_name)

    def __getattr__(self, name):
        return getattr(self._base, name)


def run(label: str, ports) -> None:
    print("--- " + label)
    try:
        payload, _deploy, _runner = T._patch(T._EMPTY, T._TWO_NEW, ports=ports)
    except BaseException as exc:  # noqa: BLE001 — 무엇이 나오는지가 측정 대상이다
        tb = sys.exc_info()[2]
        while tb.tb_next is not None:
            tb = tb.tb_next
        print("    🔴 예외가 도구를 탈출: " + type(exc).__name__ + ": " + str(exc))
        print(
            "       @ " + tb.tb_frame.f_code.co_filename.rsplit("/", 1)[1] + ":" + str(tb.tb_lineno)
        )
        print()
        return
    keys = ["ok", "status", "refusal", "error", "existing_fid_read"]
    for k in keys:
        if k in payload:
            print("    " + k + " = " + str(payload[k])[:160])
    print()


run("C0 대조군: 아무것도 안 죽음", T.ConsolePorts(T._EMPTY, T._TWO_NEW))
run(
    "C1 측정: FID 프로퍼티만 죽음",
    KillProperty(T.ConsolePorts(T._EMPTY, T._TWO_NEW), FID_PROPERTY_NAME),
)
run(
    "C2 자극 대비군: Patch 프로퍼티가 죽음 (t181 자리)",
    KillProperty(T.ConsolePorts(T._EMPTY, T._TWO_NEW), "Patch"),
)
