"""Live OSC connectivity + receive-port diagnostics for the pre-show checklist.

NON-PRODUCTION diagnostic surface, reusing the ping/state round-trip pattern
from ``server/tools/responder_roundtrip.py`` — deliberately PING + STATE only,
never the ``exec`` verb, so this module never sends an end-user MA3 command
outside safety-gate screening (REQ-MVP-029). It is exempted from the
single-chokepoint architecture test (``server/tests/test_architecture.py``)
the same way the two existing dev tools are — see that file's
``_NAMED_TOOL_EXEMPTIONS`` for the registration this module still needs
(tools.py registration draft, see the SPEC-COPILOT-PRESHOW-001 handoff notes).
"""

from __future__ import annotations

import queue
import uuid

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer, ReceivePortInUseError
from server.bridge.protocol import ProtocolError, build_ping, build_state_query, decode_payload
from server.preshow.models import CheckResult

DEFAULT_STATE_PATH = "DataPool/Sequences"


def check_osc_roundtrip(
    config: BridgeConfig, *, wait: float = 3.0, path: str = DEFAULT_STATE_PATH
) -> CheckResult:
    """Ping + state round trip against the console.

    An unreachable console degrades to ``skip`` (not ``fail``) — a dev
    workstation with no console attached is an environment fact, not a
    checklist defect. A reply that arrives but fails to decode, or a ping
    that answers while state does not, is a genuine ``fail``.
    """
    run_id = uuid.uuid4().hex[:8]
    consumer = QueueFeedbackConsumer()
    data: dict[str, object] = {}
    try:
        with OscBridge(config, consumer=consumer) as bridge:
            try:
                bridge.send_command(build_ping(f"{run_id}-ping"))
            except ValueError as error:
                return CheckResult(
                    name="osc_roundtrip", status="fail", detail=f"ping 전송 거부: {error}"
                )
            try:
                ping_message = consumer.get(timeout=wait)
            except queue.Empty:
                return CheckResult(
                    name="osc_roundtrip",
                    status="skip",
                    detail=(
                        f"콘솔 응답 없음({wait:.1f}s 대기) — 콘솔 미연결이거나 소켓이 스테일 "
                        "상태일 수 있다."
                    ),
                )
            try:
                pong = decode_payload(ping_message.args[0]) if ping_message.args else {}
            except ProtocolError as error:
                return CheckResult(
                    name="osc_roundtrip", status="fail", detail=f"ping 응답 판독 실패: {error}"
                )
            data["ping"] = pong

            bridge.send_command(build_state_query(f"{run_id}-state", path))
            try:
                state_message = consumer.get(timeout=wait)
            except queue.Empty:
                return CheckResult(
                    name="osc_roundtrip",
                    status="fail",
                    detail="ping은 응답했으나 state 조회가 응답하지 않음 — 부분 장애.",
                    data=data,
                )
            try:
                state_payload = decode_payload(state_message.args[0]) if state_message.args else {}
            except ProtocolError as error:
                return CheckResult(
                    name="osc_roundtrip",
                    status="fail",
                    detail=f"state 응답 판독 실패: {error}",
                    data=data,
                )
            data["state"] = state_payload
    except (OSError, ReceivePortInUseError) as error:
        return CheckResult(
            name="osc_roundtrip", status="skip", detail=f"수신 소켓 바인드 실패 — {error}"
        )
    return CheckResult(
        name="osc_roundtrip",
        status="pass",
        detail=f"ping ok (v{pong.get('version', '?')}) · state ok (path={path})",
        data=data,
    )


def check_receive_port_binding(config: BridgeConfig) -> CheckResult:
    """The bound receive port must equal the configured port (no silent drift).

    Needs no live console — only a local socket bind — so this always runs.
    A mismatch (only possible when ``config.receive_port`` is a fixed,
    non-ephemeral value) means the OS did not honor the configured port,
    exactly the class of drift the project's field notes call out.
    """
    try:
        with OscBridge(config) as bridge:
            actual = bridge.receive_port
    except (OSError, ReceivePortInUseError) as error:
        return CheckResult(
            name="receive_port_binding",
            status="fail",
            detail=f"수신 포트 {config.receive_port} 바인드 실패 — {error}",
        )
    if config.receive_port != 0 and actual != config.receive_port:
        return CheckResult(
            name="receive_port_binding",
            status="fail",
            detail=(
                f"수신 포트 드리프트 — 설정값 {config.receive_port} != 실제 바인드 {actual} "
                "(다른 프로세스가 포트를 점유 중일 수 있다)."
            ),
            data={"configured": config.receive_port, "actual": actual},
        )
    return CheckResult(
        name="receive_port_binding",
        status="pass",
        detail=f"수신 포트 {actual} 정상 바인드.",
        data={"configured": config.receive_port, "actual": actual},
    )
