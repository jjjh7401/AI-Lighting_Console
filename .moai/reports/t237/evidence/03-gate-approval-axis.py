"""t237 — 오프라인 게이트 재현. 콘솔 접촉 0 (가짜 ConsolePort, 소켓 없음)."""

import pathlib
import tempfile

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate


class FakeConsole:
    """어떤 명령도 실제로 안 나간다 — screen() 만 쓰므로 호출되지도 않는다."""

    def send(self, *a, **k):
        raise AssertionError("이 프로브는 콘솔에 안 보낸다")


class Approve:
    def request_approval(self, request):
        return True


CMDS = ["Off Fixture 501", "Clear", "Fixture 501", "Attribute 'Zoom' At 45"]


def run(label, approval_port):
    tmp = pathlib.Path(tempfile.mkdtemp())
    gate = SafetyGate(console=FakeConsole(), audit=AuditLog(tmp), approval_port=approval_port)
    print(f"--- {label} ---")
    for c in CMDS:
        d = gate.screen([c])
        print(
            f"  {c!r:28} cleared={str(d.cleared):5} status={d.status:9} "
            f"reasons={d.commands[0].reasons if d.commands else ()}"
        )


run("approval_port=None  (기본값 = DenyAllApprovalPort — t233 프로브 배선)", None)
run("approval_port=Approve()  (승인 통로 있음 — t135 배선)", Approve())
