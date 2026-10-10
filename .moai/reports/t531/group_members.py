"""그룹 1~18 의 실제 소속(SELECTIONDATA)을 1.6.6 props 페이징으로 되읽는다.

PROTOCOL.md §4.8(1.6.6): 테이블 값(``SELECTIONDATA`` 등)이 responder 의
``CONFIG.max_prop_value`` 바이트 한도를 넘으면, 그 read 항목 자체에
``offset``·``total``·``truncated`` 가 붙는다 — 요청 쪽은 기존 state/introspect
와 같은 자리(맨 끝)에 ``offset=<n>`` 토큰 하나를 붙인다. ``truncated`` 가
false 가 될 때까지 offset 을 "실제로 받은 개수"만큼 늘려 다시 요청한다
(offset=0 이 매번 전체를 다시 보내는 게 아니라 "받은 만큼 전진"이 계약이다).

``build_props_query``(server/bridge/protocol.py)는 아직 offset 파라미터를
받지 않는다(1.6.6 보다 앞서 쓰여짐) — 이 스크립트는 probe_readonly.py 가
state/introspect 에 쓰는 것과 같은 방식으로, ``m1_common.props_offset_wire``
를 통해 ``build_plugin_call`` 로 직접 조립한다.

이 스크립트는 ping 이 1.6.6 을 답하지 않으면 **거부하고 종료한다**(exit 1,
읽기 메시지). 이 세션의 실기 응답기는 1.6.5 라 — 거부 1회만 확인하고
실제 수집은 돌리지 않는다(지시사항).

실행: uv run python .moai/reports/t531/group_members.py <그룹 번호...>
"""

from __future__ import annotations

import json
import queue
import sys
import time
import uuid

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import GROUPS, props_offset_wire  # noqa: E402

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer  # noqa: E402
from server.bridge.protocol import ProtocolError, build_ping, decode_payload  # noqa: E402

REQUIRED_VERSION = "1.6.6"
POOL = "ShowData/DataPools/Default"


def _await(consumer: QueueFeedbackConsumer, kind: str, rid: str, wait: float) -> dict:
    end = time.monotonic() + wait
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout {wait}s kind={kind} id={rid}")
        try:
            message = consumer.get(timeout=remaining)
        except queue.Empty as error:
            raise TimeoutError(f"timeout {wait}s kind={kind} id={rid}") from error
        if not message.args:
            continue
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            continue
        if payload.get("kind") == kind and payload.get("id") == rid:
            return payload


def _ping(bridge: OscBridge, consumer: QueueFeedbackConsumer) -> str | None:
    rid = uuid.uuid4().hex[:8]
    bridge.send_command(build_ping(rid))
    try:
        reply = _await(consumer, "pong", rid, 6.0)
    except TimeoutError:
        return None
    return reply.get("version")


def read_group_selection(bridge: OscBridge, consumer: QueueFeedbackConsumer, group_no: int) -> dict:
    """offset 을 "받은 개수"만큼 전진하며 SELECTIONDATA 를 전부 모은다.

    진행이 멈추면(개수가 늘지 않으면) ``no_progress`` 를 True 로 남기고
    멈춘다 — truncated 가 영원히 true 로 남는 응답기 결함을 무한 루프로
    받지 않기 위해서다.
    """
    path = f"{POOL}/Groups/{group_no}"
    members: list[str] = []
    offset = 0
    total: int | None = None
    pages = 0
    no_progress = False
    while True:
        rid = uuid.uuid4().hex[:8]
        line = props_offset_wire(rid, path, ["SELECTIONDATA"], offset)
        bridge.send_command(line)
        try:
            reply = _await(consumer, "props", rid, 6.0)
        except TimeoutError:
            return dict(group=group_no, ok=False, error="timeout", members=members, pages=pages)
        pages += 1
        reads = reply.get("reads") or []
        read = next((r for r in reads if r.get("n") == "SELECTIONDATA"), None)
        if read is None or not read.get("ok"):
            return dict(
                group=group_no,
                ok=False,
                error=(read or {}).get("e", "no SELECTIONDATA read"),
                members=members,
                pages=pages,
            )
        total = read.get("total", total)
        try:
            chunk = json.loads(read.get("v", "[]"))
        except (TypeError, ValueError):
            chunk = []
        before = len(members)
        members.extend(chunk)
        truncated = bool(read.get("truncated"))
        if not truncated:
            break
        if len(members) == before:  # 진행 없음 — 멈춘다
            no_progress = True
            break
        offset = len(members)
    return dict(
        group=group_no,
        ok=True,
        total=total,
        received=len(members),
        truncated_no_progress=no_progress,
        members=members,
        pages=pages,
    )


def main(argv: list[str]) -> int:
    group_numbers = [int(a) for a in argv] or list(GROUPS.values())
    consumer = QueueFeedbackConsumer()
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=consumer) as bridge:
        version = _ping(bridge, consumer)
        if version != REQUIRED_VERSION:
            print(
                f"REFUSED — ping 응답이 {REQUIRED_VERSION} 이 아니라 {version!r} 이다. "
                "1.6.6 props offset 페이징은 이 버전에서 보장되지 않으므로 실행을 거부한다."
            )
            return 1
        for group_no in group_numbers:
            result = read_group_selection(bridge, consumer, group_no)
            print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
