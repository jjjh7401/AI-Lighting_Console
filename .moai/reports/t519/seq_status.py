"""t519 — 읽기 전용: 시퀀스 풀 전체(페이징)를 돌며 NAME·NO·CURRENTCUE·LOADEDCUE·PRIORITY 를 읽는다.

CURRENTCUE 가 비어 있지 않은 시퀀스 = 지금 켜져 있어 BACK 속성을 쥘 수 있는 후보다.
실행: uv run python .moai/reports/t519/seq_status.py > .moai/reports/t519/r7_seq_status.txt
"""

import json
import sys
import uuid

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
from probe_readonly import await_  # noqa: E402

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer  # noqa: E402
from server.bridge.protocol import build_props_query, build_state_query  # noqa: E402

POOL = "ShowData/DataPools/Default/Sequences"
NAMES = ["NAME", "NO", "CURRENTCUE", "LOADEDCUE", "CUENO", "CUENAME", "PRIORITY", "OFFWHENOVERRIDDEN"]


def ask(bridge, consumer, build, kind):
    rid = uuid.uuid4().hex[:8]
    bridge.send_command(build(rid))
    return await_(consumer, kind, rid, 8.0)


def main():
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        children, off = [], 0
        while True:
            r = ask(bridge, consumer, lambda rid: build_state_query(rid, POOL, off or None), "state")
            got = r.get("children") or []
            children += got
            off += len(got)
            if not r.get("truncated") or not got:
                break
        print(f"children={len(children)} node={r.get('node')}")
        for c in children:
            path = f"{POOL}/{c['i']}"
            r = ask(bridge, consumer, lambda rid: build_props_query(rid, path, NAMES), "props")
            vals = {x["n"]: x.get("v") for x in r.get("reads") or []}
            print(json.dumps({"i": c["i"], **vals}, ensure_ascii=False))


if __name__ == "__main__":
    main()
