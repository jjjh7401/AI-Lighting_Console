"""t525 — 읽기 전용: 앱 경로(read_spatial_fixtures)로 지금 쇼의 픽스처 좌표·회전을 읽는다.

보내는 것: ping / state / prop / props 만. exec·deploy 는 없다(execute 를 부르지 않는다).
앱의 get_spatial_context 와 같은 함수·같은 예산 계산(_spatial_read_budget)을 쓴다.

실행 (프로젝트 루트에서, R=.moai/reports/t525):
    .venv/bin/python $R/probe_spatial.py bulk    > $R/r1_spatial_bulk.json
    .venv/bin/python $R/probe_spatial.py pername > $R/r2_spatial_pername.json
"""

import json
import sys
import time

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.orchestrator.tools import (  # noqa: E402
    DEFAULT_RIG_CONTEXT_PATHS,
    SPATIAL_PROPERTY_QUERY_CAP,
    _spatial_read_budget,
    read_spatial_fixtures,
)
from server.prechk.query import bulk_capable  # noqa: E402
from server.safety.console import ConsoleLink  # noqa: E402


class CountingPort:
    """읽기 메서드만 노출하고 왕복 수를 센다. execute 는 일부러 없다."""

    def __init__(self, link, *, bulk):
        self._link = link
        self.calls = {"state": 0, "prop": 0, "props": 0}
        if bulk:
            self.query_properties = self._props

    def query_state(self, path, *, offset=0):
        self.calls["state"] += 1
        return self._link.query_state(path, offset=offset)

    def query_property(self, path, name):
        self.calls["prop"] += 1
        return self._link.query_property(path, name)

    def _props(self, path, names):
        self.calls["props"] += 1
        return self._link.query_properties(path, names)


def main(mode):
    link = ConsoleLink(id_prefix="t525")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        pong = link.ping()
        port = CountingPort(link, bulk=(mode == "bulk"))
        path = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
        budget = _spatial_read_budget(True, bulk=bulk_capable(port))
        t0 = time.monotonic()
        reply = read_spatial_fixtures(port, port, path, budget, include_rotation=True)
        elapsed = time.monotonic() - t0
        records = reply.get("fixtures") or reply.get("partial_fixtures") or []
        rot_full = sum(1 for r in records if all(k in r for k in ("rotx", "roty", "rotz")))
        print(
            json.dumps(
                {
                    "mode": mode,
                    "ping": pong,
                    "responder_version": link.responder_version,
                    "path": path,
                    "cap": SPATIAL_PROPERTY_QUERY_CAP,
                    "budget": budget,
                    "bulk_capable": bulk_capable(port),
                    "elapsed_s": round(elapsed, 2),
                    "calls": port.calls,
                    "shape": "fixtures" if "fixtures" in reply else "partial_fixtures",
                    "coverage": reply.get("coverage"),
                    "truncated": reply.get("truncated"),
                    "roundtrip_capped": reply.get("roundtrip_capped"),
                    "missing": reply.get("missing"),
                    "records": len(records),
                    "unreadable": reply.get("unreadable"),
                    "rotation_full": rot_full,
                    "fixtures": records,
                },
                ensure_ascii=False,
                indent=1,
            )
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bulk")
