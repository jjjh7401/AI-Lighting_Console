"""t194 5절 미측정 항목 측정.

물음: 포트 **단위** 어댑터가 스윕의 `probe_failures` 계수를 조용히 바꾸는가,
그리고 **기존 스위트가 그 변화를 관측하는가**.

이 프로브는 표식(`unreachable`) 없는 번역을 재는 **대조군**이다 — 채택된 D1 은
표식을 달아 스윕이 계속 세게 한다. 여기 나오는 2 -> 0 이 표식이 필요한 이유다.

t194 워크트리 루트에서:  uv run python .moai/reports/t194/probes/_t194_sweep_exc.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from server.safety.console import StateQueryError  # noqa: E402
from server.vwx.patchplan import _existing_fids_from_console  # noqa: E402


class SweepPort:
    """실물 절단 재현 — 열거는 `rows` 만, 나머지 슬롯은 `exc` 를 던진다."""

    def __init__(self, *, total, rows, present, exc):
        self.total = total
        self.rows = rows
        self.present = present
        self.exc = exc

    def query_state(self, path):
        node = {"name": "Fixtures", "class": "Fixtures", "childCount": self.total}
        return {
            "ok": True,
            "path": path,
            "node": node,
            "children": [{"i": s, "name": f"f{s}"} for s in self.rows],
        }

    def query_property(self, path, property_name):
        slot = int(path.rsplit("/", 1)[1])
        if slot in self.present:
            return {
                "ok": True,
                "path": path,
                "property": property_name,
                "value": str(self.present[slot]),
            }
        raise self.exc(f"no answer for {path}")


class TranslatingPort:
    """표식 **없는** 포트 단위 번역 — 리드가 경고한 형태.

    열거 판독과 스윕 프로브가 같은 포트 객체를 쓰므로 여기 씌우면 둘 다 덮인다.
    """

    def __init__(self, inner):
        self._inner = inner

    def query_state(self, path):
        return self._inner.query_state(path)

    def query_property(self, path, property_name):
        try:
            return self._inner.query_property(path, property_name)
        except StateQueryError:
            return {"ok": False, "path": path, "property": property_name}


def measure(label, port):
    r = _existing_fids_from_console(port)
    print(f"{label:38s} probe_failures={r.probe_failures}  unseen={r.unseen}")
    return r


BASE = {"total": 3, "rows": [1], "present": {1: 101}}

print("=== axis 1: 날 포트 (번역 없음) ===")
a = measure("TimeoutError    <- 기존 검사가 쏘는 종류", SweepPort(exc=TimeoutError, **BASE))
b = measure("StateQueryError <- 프로덕션 종류", SweepPort(exc=StateQueryError, **BASE))

print("")
print("=== axis 2: 표식 없는 포트 단위 번역 ===")
c = measure("TimeoutError    + 번역", TranslatingPort(SweepPort(exc=TimeoutError, **BASE)))
d = measure("StateQueryError + 번역", TranslatingPort(SweepPort(exc=StateQueryError, **BASE)))

print("")
print("=== 판정 ===")
print(f"기존 검사 종류(TimeoutError) 가 변하나?  {a.probe_failures != c.probe_failures}")
print(f"  probe_failures {a.probe_failures} -> {c.probe_failures}")
print(f"프로덕션 종류(StateQueryError) 가 변하나? {b.probe_failures != d.probe_failures}")
print(f"  probe_failures {b.probe_failures} -> {d.probe_failures}")
print(f"안전 결과(complete) 가 변하나?           {b.complete != d.complete}")
print(f"unseen 이 변하나?                        {b.unseen != d.unseen}")
