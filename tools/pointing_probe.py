"""One-off live probe for SPATIAL pointing analysis (bridge-direct, like console_probe).

Enumerates Patch/Stages/1/Fixtures slots: FID, Name, Pos*, Rot*.
Run: .venv/bin/python tools/pointing_probe.py
"""

from __future__ import annotations

import json
import queue
import sys
import time
import uuid

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer
from server.bridge.protocol import (
    ProtocolError,
    build_prop_query,
    build_state_query,
    decode_payload,
)


def _await(consumer, *, kind: str, request_id: str, wait: float = 6.0) -> dict:
    deadline = time.monotonic() + wait
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout kind={kind} id={request_id}")
        try:
            message = consumer.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError(f"timeout kind={kind} id={request_id}") from None
        if not message.args:
            continue
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            continue
        if payload.get("kind") == kind and payload.get("id") == request_id:
            return payload


def main() -> int:
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    consumer = QueueFeedbackConsumer()
    rows = []
    with OscBridge(config, consumer=consumer) as bridge:
        rid = uuid.uuid4().hex[:8]
        bridge.send_command(build_state_query(rid, "Patch/Stages/1/Fixtures"))
        listing = _await(consumer, kind="state", request_id=rid)
        slots = [child["i"] for child in listing.get("children", [])]
        # truncated listings: scan a wider slot range anyway
        scan = sorted(set(slots) | set(range(1, 61)))
        for slot in scan:
            path = f"Patch/Stages/1/Fixtures/{slot}"
            record: dict[str, object] = {"slot": slot}
            ok = True
            for prop in ("FID", "Name", "Posx", "Posy", "Posz", "Rotx", "Roty", "Rotz"):
                rid = uuid.uuid4().hex[:8]
                bridge.send_command(build_prop_query(rid, path, prop))
                try:
                    reply = _await(consumer, kind="prop", request_id=rid, wait=3.0)
                except TimeoutError:
                    ok = False
                    break
                if reply.get("ok") is not True:
                    ok = False
                    break
                record[prop] = reply.get("value")
                time.sleep(0.03)
            if ok:
                rows.append(record)
    print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
