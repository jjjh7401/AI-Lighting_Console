"""t431 읽기 전용 프로브 — ping / state / prop 만 보낸다. exec·deploy 는 없다.

실행 (프로젝트 루트에서, grandMA3 onPC 가 응답기를 띄운 상태):
    .venv/bin/python .moai/reports/t431/probe_t431.py ping state:ShowData/GelPools ...

단계 형식:
    ping                         응답기 이름·버전 (pong)
    state:<경로>[@<offset>]      객체 자식 목록 (offset 은 1.6.0+ 페이징)
    introspect:<경로>[@<offset>] 객체가 가진 속성 이름 목록 (1.6.1+, 1.6.2+ 페이징)
    prop:<경로>|<속성이름>       속성 하나
    props:<경로>|<이름,이름,...> 속성 여러 개를 한 번에 (1.6.1+, 최대 16개)
"""
import json
import queue
import sys
import time
import uuid

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer  # noqa: E402
from server.bridge.protocol import (  # noqa: E402
    ProtocolError,
    build_introspect_query,
    build_ping,
    build_prop_query,
    build_props_query,
    build_state_query,
    decode_payload,
)


def await_(consumer, kind, rid, wait):
    end = time.monotonic() + wait
    while True:
        rem = end - time.monotonic()
        if rem <= 0:
            raise TimeoutError(f"timeout {wait}s kind={kind} id={rid}")
        try:
            message = consumer.get(timeout=rem)
        except queue.Empty:
            raise TimeoutError(f"timeout {wait}s kind={kind} id={rid}") from None
        if not message.args:
            continue
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            continue
        if payload.get("kind") == kind and payload.get("id") == rid:
            return payload


def main(steps):
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        for raw in steps:
            rid = uuid.uuid4().hex[:8]
            if raw == "ping":
                line, kind = build_ping(rid), "pong"
            elif raw.startswith("state:"):
                body, _, off = raw[6:].partition("@")
                line, kind = build_state_query(rid, body, int(off) if off else None), "state"
            elif raw.startswith("introspect:"):
                body, _, off = raw[11:].partition("@")
                line, kind = build_introspect_query(rid, body, int(off) if off else None), "introspect"
            elif raw.startswith("props:"):
                path, _, names = raw[6:].partition("|")
                line, kind = build_props_query(rid, path, names.split(",")), "props"
            elif raw.startswith("prop:"):
                path, _, prop = raw[5:].partition("|")
                line, kind = build_prop_query(rid, path, prop), "prop"
            else:
                print("!! unknown step", raw)
                continue
            print(f"\n>>> {raw}\n    wire: {line}")
            bridge.send_command(line)
            try:
                reply = await_(consumer, kind, rid, 6.0)
                print("<<< " + json.dumps(reply, ensure_ascii=False, sort_keys=True))
            except TimeoutError as error:
                print("<<< TIMEOUT", error)
            time.sleep(0.3)


if __name__ == "__main__":
    main(sys.argv[1:])
