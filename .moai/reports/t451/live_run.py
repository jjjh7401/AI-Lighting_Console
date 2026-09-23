"""t451 실기 1회 — ``diagnose_fixture_light`` 를 콘솔에 읽기 전용으로 돌린다.

보내는 요청은 ``state``·``prop`` 뿐이다(exec·deploy 경로 없음). 운영 게이트 포트와
같은 규약으로 감싼다: 응답기가 ``ok:false`` 를 주면 그 ``error`` 문구로 예외를 던진다.

실행 (프로젝트 루트에서):
    .venv/bin/python .moai/reports/t451/live_run.py <fid> [compare_fid]
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
    build_prop_query,
    build_state_query,
    decode_payload,
)
from server.preshow.fixture_light import diagnose_fixture_light  # noqa: E402


class LivePort:
    def __init__(self, bridge, consumer, wait=6.0):
        self._bridge, self._consumer, self._wait = bridge, consumer, wait
        self.calls = []

    def _round_trip(self, line, kind, rid):
        self._bridge.send_command(line)
        end = time.monotonic() + self._wait
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no {kind} reply within {self._wait}s")
            try:
                message = self._consumer.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"no {kind} reply within {self._wait}s") from None
            if not message.args:
                continue
            try:
                payload = decode_payload(message.args[0])
            except ProtocolError:
                continue
            if payload.get("kind") == kind and payload.get("id") == rid:
                return payload

    def query_state(self, path, *, offset=0):
        rid = uuid.uuid4().hex[:8]
        self.calls.append(("state", path, offset))
        payload = self._round_trip(build_state_query(rid, path, offset or None), "state", rid)
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or f"state query failed: {path}"))
        return payload

    def query_property(self, path, property_name):
        rid = uuid.uuid4().hex[:8]
        self.calls.append(("prop", path, property_name))
        return self._round_trip(build_prop_query(rid, path, property_name), "prop", rid)


def main(argv):
    fid = int(argv[0])
    compare = int(argv[1]) if len(argv) > 1 else None
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        port = LivePort(bridge, consumer)
        started = time.monotonic()
        result = diagnose_fixture_light(
            fid, state_port=port, property_port=port, compare_fid=compare
        )
        elapsed = time.monotonic() - started
    verbs = sorted({c[0] for c in port.calls})
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print(f"\n=== requests={len(port.calls)} verbs={verbs} elapsed={elapsed:.1f}s")
    print("\n=== summary\n" + result.summary)


if __name__ == "__main__":
    main(sys.argv[1:])
