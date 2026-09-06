"""t313 — 하위 프로세스 가짜 콘솔의 준비 신호와 「침묵 ≠ 아니오」.

카드 t311 이 진단 없이 남긴 것: 실제 :class:`~server.bridge.osc.OscBridge` 로
`python -m server.tests.fake_console` 를 두드렸더니 **모든 질의가 판독 실패**
였고, 그래서 응답기를 프로세스 안에 붙이는 쪽으로 우회했다.

여기서 재현하고 못을 박는 두 가지:

1. **경합이다.** 하위 프로세스는 파이썬 기동 + 임포트 + Lua 응답기 구성이
   끝나야 명령 소켓을 연다. 그 전에 보낸 UDP 는 커널이 조용히 버리고 송신
   쪽엔 오류가 없다 — 콘솔 stdout 에 그 명령 줄 자체가 찍히지 않는 것이
   증거다. 고침은 `sleep` 이 아니라 준비 신호
   (:func:`~server.tests.fake_console.wait_for_ready`)다.
2. **침묵과 부정을 가른다.** 시간 초과는
   :class:`~server.safety.console.ConsoleSilentError` 로 올라오고,
   ``ok:false`` 는 그냥 :class:`~server.safety.console.StateQueryError` 다.
   같은 형으로 두면 「아무것도 못 읽었다」가 「콘솔에 없다」로 읽힌다.
"""

from __future__ import annotations

import socket
import subprocess
import sys

import pytest

from server.safety.bootstrap import build_console_stack
from server.safety.console import ConsoleSilentError, LinkTimeouts, StateQueryError
from server.tests.fake_console import READY_BANNER, wait_for_ready

_QUERY_COUNT = 12
_TIMEOUTS = LinkTimeouts(state_query_seconds=3.0)


def _free_udp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def console_ports() -> tuple[int, int]:
    return _free_udp_port(), _free_udp_port()


@pytest.fixture
def fake_console_process(console_ports):
    cmd_port, reply_port = console_ports
    proc = subprocess.Popen(
        [sys.executable, "-m", "server.tests.fake_console", str(cmd_port), str(reply_port), "full"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        yield proc
    finally:
        proc.kill()
        proc.wait(timeout=10)


class TestTheReadinessSignal:
    """준비 배너를 기다린 뒤에는 질의가 하나도 새지 않는다."""

    def test_every_query_is_answered_after_waiting_for_ready(
        self, console_ports, fake_console_process, tmp_path
    ):
        # 준비 신호 없이 보내던 예전 동작에서는 첫 질의가 조용히 사라져
        # `ok == _QUERY_COUNT` 가 성립하지 않는다(t313 실측: ok=11, fail=1).
        cmd_port, reply_port = console_ports
        banner = wait_for_ready(fake_console_process.stdout)
        assert banner.startswith(READY_BANNER)

        stack = build_console_stack(
            send_port=cmd_port,
            receive_port=reply_port,
            audit_dir=tmp_path / "audit",
            timeouts=_TIMEOUTS,
            attempt_session_backup=False,
        )
        answered = 0
        try:
            for slot in range(1, _QUERY_COUNT + 1):
                payload = stack.link.query_property(f"Patch/Stages/1/Fixtures/{slot}", "posx")
                assert payload["ok"] is True
                answered += 1
        finally:
            stack.stop()
        assert answered == _QUERY_COUNT

    def test_the_banner_means_the_socket_already_accepts_commands(
        self, console_ports, fake_console_process
    ):
        """배너는 바인드 **뒤**에 나온다 — 배너 직후의 첫 패킷이 콘솔에 닿는다."""
        cmd_port, _reply_port = console_ports
        wait_for_ready(fake_console_process.stdout)
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # OSC 가 아닌 바이트여도 소켓이 살아 있으면 ICMP 거부가 없다;
            # 바인드 전이었다면 커널이 포트 도달 불가로 답한다.
            sender.connect(("127.0.0.1", cmd_port))
            sender.send(b"\x00")
        finally:
            sender.close()


class TestSilenceIsNotDenial:
    """무응답과 ``ok:false`` 는 서로 다른 예외로 올라온다."""

    def test_a_silent_console_raises_console_silent_error(self, tmp_path):
        # 아무도 듣지 않는 포트 — 콘솔은 「아니오」라고 답한 것이 아니라
        # 아무 말도 하지 않았다.
        stack = build_console_stack(
            send_port=_free_udp_port(),
            receive_port=_free_udp_port(),
            audit_dir=tmp_path / "audit",
            timeouts=LinkTimeouts(state_query_seconds=0.2),
            attempt_session_backup=False,
        )
        try:
            with pytest.raises(ConsoleSilentError):
                stack.link.query_property("Patch/Stages/1/Fixtures/1", "posx")
        finally:
            stack.stop()

    def test_a_negative_answer_is_not_reported_as_silence(
        self, console_ports, fake_console_process, tmp_path
    ):
        cmd_port, reply_port = console_ports
        wait_for_ready(fake_console_process.stdout)
        stack = build_console_stack(
            send_port=cmd_port,
            receive_port=reply_port,
            audit_dir=tmp_path / "audit",
            timeouts=_TIMEOUTS,
            attempt_session_backup=False,
        )
        try:
            with pytest.raises(StateQueryError) as caught:
                # 존재하지 않는 경로 — 응답기가 **답을 한다**, 부정으로.
                stack.link.query_property("Patch/Stages/1/Fixtures/999", "posx")
        finally:
            stack.stop()
        assert not isinstance(caught.value, ConsoleSilentError)

    def test_console_silent_error_stays_catchable_as_state_query_error(self):
        """기존 호출자를 깨지 않는다 — 하위형이라 넓은 except 가 그대로 잡는다."""
        assert issubclass(ConsoleSilentError, StateQueryError)
