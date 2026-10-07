"""t519 — 읽기 전용: 기구 유형의 Geometries 트리를 끝까지 걸으며 Beam 노드의 빛 속성을 읽는다.

유형 8(Mac Aura XB, BACK·SIDE) 과 유형 11(MegaPointe, 6.8 m 에서 보이는 무빙) 을 비교한다.
실행: uv run python .moai/reports/t519/geom_walk.py 8 11 > .moai/reports/t519/r9_geom_walk.txt
"""

import json
import sys
import uuid

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
from probe_readonly import await_  # noqa: E402

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer  # noqa: E402
from server.bridge.protocol import build_props_query, build_state_query  # noqa: E402

BEAM = [
    "LUMINOUSINTENSITY",
    "BEAMANGLE",
    "FIELDANGLE",
    "BEAMRADIUS",
    "BEAMTYPE",
    "LAMPTYPE",
    "ISMAINBEAM",
]
GEO = ["NAME", "MODEL"]


def ask(bridge, consumer, build, kind):
    rid = uuid.uuid4().hex[:8]
    bridge.send_command(build(rid))
    return await_(consumer, kind, rid, 8.0)


def walk(bridge, consumer, path, depth):
    r = ask(bridge, consumer, lambda rid: build_state_query(rid, path, None), "state")
    for c in r.get("children") or []:
        child = f"{path}/{c['i']}"
        names = BEAM if c["class"] == "Beam" else GEO
        p = ask(
            bridge,
            consumer,
            lambda rid, child=child, names=names: build_props_query(rid, child, names),
            "props",
        )
        vals = {x["n"]: x.get("v") for x in p.get("reads") or []}
        print(
            "  " * depth
            + json.dumps(
                {"path": child, "class": c["class"], "name": c["name"], **vals}, ensure_ascii=False
            )
        )
        if depth < 8:
            walk(bridge, consumer, child, depth + 1)


def main(types):
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        for t in types:
            print(f"== FixtureType {t}")
            walk(bridge, consumer, f"Patch/FixtureTypes/{t}/Geometries", 0)


if __name__ == "__main__":
    main(sys.argv[1:])
