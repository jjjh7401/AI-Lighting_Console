"""카드 t569 — 칩 서랍 세 풀(Dimmer·Position·Color)의 프리셋 NOTE 전수 판독.

읽기만 한다: ``query_state``(풀·슬롯 목록, 기존 ``paged_pool_children`` 그대로)와
``query_properties``(NAME,NOTE) 두 가지. 쓰기 경로는 import 하지 않는다.

실행: uv run python .moai/reports/t569/note_survey.py
"""

from __future__ import annotations

import json
import sys

from server.design.console_slots import paged_pool_children, resolve_named_pool_no
from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts

POOL_ROOT = "ShowData/DataPools/Default/PresetPools"
POOL_NAMES = ("Dimmer", "Position", "Color")


def main() -> int:
    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=8000,
        receive_host="127.0.0.1",
        receive_port=9005,
        audit_dir=".moai/reports/t569/audit",
        timeouts=LinkTimeouts(state_query_seconds=5),
        attempt_session_backup=False,
    )
    port = stack.gate.state_port

    def query(_probe_id, arguments):
        try:
            return port.query_state(arguments["path"], offset=int(arguments.get("offset") or 0))
        except Exception:
            return None

    out: dict[str, object] = {"pools": []}
    try:
        for pool_name in POOL_NAMES:
            pool_no = resolve_named_pool_no(
                query, POOL_ROOT, pool_name, probe_id=f"t569-{pool_name}-pool"
            )
            entry: dict[str, object] = {"name": pool_name, "no": pool_no, "presets": []}
            if pool_no is not None:
                slots = paged_pool_children(
                    query, f"{POOL_ROOT}/{pool_no}", probe_id=f"t569-{pool_name}-slots"
                )
                entry["slots_read"] = None if slots is None else len(slots)
                for slot in sorted(slots or {}):
                    path = f"{POOL_ROOT}/{pool_no}/{slot}"
                    try:
                        reply = port.query_properties(path, ["NAME", "NOTE"])
                        reads = {r.get("n"): r for r in reply.get("reads") or []}
                        note = reads.get("NOTE", {})
                        entry["presets"].append(
                            {
                                "slot": f"{pool_no}.{slot}",
                                "name": reads.get("NAME", {}).get("v"),
                                "note_ok": note.get("ok"),
                                "note": note.get("v"),
                            }
                        )
                    except Exception as error:  # 읽기 실패는 실패로 적는다
                        entry["presets"].append({"slot": f"{pool_no}.{slot}", "error": str(error)})
            out["pools"].append(entry)
    finally:
        stack.stop()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
