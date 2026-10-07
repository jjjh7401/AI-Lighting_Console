# ruff: noqa: E501 — 근거(경로·판독값)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t519 — 읽기 전용(ping/state/introspect/props 만): BACK 201 과 켜지는 SIDE-L 301 의 패치 속성을 전부 읽어 차이를 낸다.

1) introspect 를 페이징해 Fixture·SubFixture·Stage 의 속성 이름 전체를 얻는다
2) Handle/Custom 을 뺀 스칼라 속성을 16개씩 props 로 읽는다(43=201, 55=301, 각 서브픽스처, Stage 1)
3) 201 과 301 값이 다른 속성만 따로 찍는다

실행: uv run python .moai/reports/t519/diff_reads.py > .moai/reports/t519/r2_diff.txt
콘솔 송신은 읽기 질의뿐이다(build_*_query 만 쓴다). 쓰기 경로 import 0.
"""

import json
import sys
import uuid

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
from probe_readonly import await_  # noqa: E402

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer  # noqa: E402
from server.bridge.protocol import (  # noqa: E402
    build_introspect_query,
    build_props_query,
    build_state_query,
)

SKIP_TYPES = {"Handle", "Custom"}
BACK, SIDE = "Patch/Stages/1/Fixtures/43", "Patch/Stages/1/Fixtures/55"


def ask(bridge, consumer, line_fn, kind):
    rid = uuid.uuid4().hex[:8]
    line = line_fn(rid)
    bridge.send_command(line)
    reply = await_(consumer, kind, rid, 8.0)
    print(f">>> {kind} {line}\n<<< {json.dumps(reply, ensure_ascii=False)}", flush=True)
    return reply


def fields(bridge, consumer, path):
    out, off = [], 0
    while True:
        r = ask(
            bridge,
            consumer,
            lambda rid, off=off: build_introspect_query(rid, path, off or None),
            "introspect",
        )
        got = r.get("fields") or []
        out += got
        off += len(got)
        if not r.get("truncated") or not got:
            return [f["n"] for f in out if f.get("t") not in SKIP_TYPES]


def read_all(bridge, consumer, path, names):
    vals = {}
    for i in range(0, len(names), 16):
        chunk = names[i : i + 16]
        r = ask(
            bridge, consumer, lambda rid, chunk=chunk: build_props_query(rid, path, chunk), "props"
        )
        for x in r.get("reads") or []:
            vals[x["n"]] = x.get("v") if x.get("ok") else f"!err {x.get('err')}"
    return vals


def main():
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        fx_names = fields(bridge, consumer, BACK)
        sub_names = fields(bridge, consumer, BACK + "/1")
        stage_names = fields(bridge, consumer, "Patch/Stages/1")
        ask(
            bridge,
            consumer,
            lambda rid: build_state_query(rid, "Patch/Stages/1/Spaces", None),
            "state",
        )
        result = {
            "201": read_all(bridge, consumer, BACK, fx_names),
            "301": read_all(bridge, consumer, SIDE, fx_names),
            "201.sub": read_all(bridge, consumer, BACK + "/1", sub_names),
            "301.sub": read_all(bridge, consumer, SIDE + "/1", sub_names),
            "stage1": read_all(bridge, consumer, "Patch/Stages/1", stage_names),
        }
    print("\n=== RESULT")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("\n=== DIFF 201 vs 301 (fixture)")
    for k in fx_names:
        if result["201"].get(k) != result["301"].get(k):
            print(f"{k}: 201={result['201'].get(k)!r} 301={result['301'].get(k)!r}")
    print("=== DIFF 201.1 vs 301.1 (subfixture)")
    for k in sub_names:
        if result["201.sub"].get(k) != result["301.sub"].get(k):
            print(f"{k}: 201={result['201.sub'].get(k)!r} 301={result['301.sub'].get(k)!r}")


if __name__ == "__main__":
    main()
