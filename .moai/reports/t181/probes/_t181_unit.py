"""단위 측정 - read_inventory 가 포트 예외를 그대로 흘리는가.

tools.py 의 `except InventoryReadError` 여덟 자리 중 일곱이 read_inventory 를
감싼다(나머지 하나 6505 는 build_patch_sheet_query). 그래서 read_inventory 를
한 번 재면 그 일곱 자리의 성질이 한꺼번에 정해진다 - 도구 일곱을 각각 태울
필요가 없다.

⚠️ 이 측정이 정하는 것은 「그 except 가 이 예외를 안 잡는다」까지다.
   「죽은 경로가 그 자리에 도달한다」는 도구마다 따로 재야 한다 - 여기서는 안 쟀다.

팔 셋:
  A) 포트가 StateQueryError 를 던진다  -> 프로덕션 실패 형태 (측정값)
  B) 포트가 ok=False 를 돌려준다        -> 비공허성. InventoryReadError 가 실제로
                                          나와야 그 except 가 쓸모없지 않음이 증명된다
  C) 살아있는 포트                      -> 계기가 늘 터지는 게 아님을 보인다
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.prechk.inventory import InventoryReadError, read_inventory
from server.safety.console import StateQueryError

FIXTURE_ROOT = "Patch/Stages/1/Fixtures"


class RaisingPort:
    """프로덕션 ConsoleLink 의 실패 형태 - console.py:689/693 이 이것을 던진다."""

    def query_state(self, path, offset=0):
        raise StateQueryError(f"no state reply for {path!r} within 5.0s")

    def query_property(self, path, property_name):
        raise StateQueryError(f"no prop reply for {path!r} {property_name!r} within 5.0s")


class NotOkPort:
    """ok=False 를 돌려주는 포트 - inventory.py:407 이 InventoryReadError 를 던지는 갈래."""

    def query_state(self, path, offset=0):
        return dict(ok=False, error="enumeration refused")

    def query_property(self, path, property_name):
        return dict(ok=False, error="not readable")


class LivePort:
    def query_state(self, path, offset=0):
        return dict(ok=True, truncated=False, node=dict(childCount=0), children=[])

    def query_property(self, path, property_name):
        return dict(ok=False, error="not readable")


for label, port in (
    ("A  StateQueryError (프로덕션 형태, 측정값)", RaisingPort()),
    ("B  ok=False        (비공허성)", NotOkPort()),
    ("C  live            (대조군)", LivePort()),
):
    try:
        result = read_inventory(port)
    except InventoryReadError as error:
        print(f"{label}\n    -> InventoryReadError  (그 except 가 잡는다)  {str(error)[:80]!r}\n")
    except BaseException as error:
        print(
            f"{label}\n    -> {type(error).__name__}  "
            f"**그 except 가 못 잡는다**  {str(error)[:80]!r}\n"
        )
    else:
        print(f"{label}\n    -> 정상 반환  fixtures={len(result.fixtures)}\n")
