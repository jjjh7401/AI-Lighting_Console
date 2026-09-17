"""SPEC-LDRECV-001 M3 · REQ-LDPLUGIN-021 §2.0-가 · AC-LDPLUGIN-021 항목 3·4.

``SafetyGate.execute_preapproved`` — director의 자체 승인(``ApprovalBinding``,
M2)이 이미 있는 apply 경로가 일반 chat/WS ``ApprovalPort`` 재질문만 건너뛰고,
grammar/classify/backup/health/audit 다섯은 ``screen()``과 동일하게 통과시키는지
대조 시험한다(design.md §1.3의 채택안 C).

항목 3 — ``execute_preapproved``가 위반 명령을 ``screen()``과 동일하게
거부하는지 + ``self._approval_port.request_approval``이 호출되지 않는지.
항목 4 — 새 메서드 추가가 기존 ``screen()`` 자체의 동작을 바꾸지 않는지
(이 파일이 자체로 재확인 — §1.4의 characterization 전수 재확인은 기존
``test_safety_gate.py`` 등 gate 테스트 스위트 전체 실행이 진짜 증거다).
"""

from __future__ import annotations

from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.safety.monitor import HealthMonitor


class FakeConsole:
    def __init__(self):
        self.executed: list[str] = []
        self.ping_ok = True

    def execute(self, command: str) -> ExecOutcome:
        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return self.ping_ok

    def query_state(self, path: str) -> dict:
        raise RuntimeError(f"no such path: {path}")


class ScriptedApproval:
    """Deterministic approval port — records every call it receives."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


RISKY_LINE = "Delete Sequence 5"
SAFE_LINE = "Fixture 901 At 50"
GRAMMAR_BROKEN = "'broken"


def make_gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or FakeConsole()
    audit = kwargs.pop("audit", None) or AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, **kwargs)
    return gate, console, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestExecutePreapprovedSkipsOnlyApproval:
    def test_safe_command_clears_without_approval_call(self, tmp_path):
        approval = ScriptedApproval()
        gate, console, _ = make_gate(tmp_path, approval_port=approval)
        decision = gate.execute_preapproved([SAFE_LINE])
        assert decision.cleared is True
        assert decision.status == "cleared"
        assert approval.requests == []

    def test_risky_command_clears_without_asking_the_general_approval_channel(self, tmp_path):
        # This is the whole point of §2.0-가: a director-preapproved risky
        # command must NOT be re-questioned through the general ApprovalPort
        # (it would fall to DenyAllApprovalPort with no UI session and be
        # rejected — exactly the double-approval bug design.md §1.1 names).
        approval = ScriptedApproval(decisions=[False])  # would reject if ever asked
        gate, console, audit = make_gate(tmp_path, approval_port=approval)
        decision = gate.execute_preapproved([RISKY_LINE])
        assert decision.cleared is True
        assert approval.requests == []  # never consulted
        assert len(_events(audit, "approved")) == 1  # still audited as approved

    def test_backup_rule_still_runs_for_the_risky_path(self, tmp_path):
        # Backup rule (3): only the RISKY path backs up — unchanged by
        # skipping the approval re-ask (design.md §1.3, the pipeline order
        # is preserved end to end).
        backup_calls: list[str] = []

        class Backup:
            def before_risky_execution(self) -> None:
                backup_calls.append("b")

        gate, _, _ = make_gate(tmp_path, backup=Backup())
        gate.execute_preapproved([RISKY_LINE])
        assert backup_calls == ["b"]

    def test_safe_command_never_touches_backup(self, tmp_path):
        backup_calls: list[str] = []

        class Backup:
            def before_risky_execution(self) -> None:
                backup_calls.append("b")

        gate, _, _ = make_gate(tmp_path, backup=Backup())
        gate.execute_preapproved([SAFE_LINE])
        assert backup_calls == []


class TestExecutePreapprovedMirrorsScreenRejections:
    """항목 3 — 위반 명령을 넣었을 때 screen()과 동일하게 거부되는지."""

    def test_grammar_violation_rejected_identically(self, tmp_path):
        gate_a, _, _ = make_gate(tmp_path)
        gate_b, _, _ = make_gate(tmp_path)
        screen_decision = gate_a.screen([GRAMMAR_BROKEN])
        preapproved_decision = gate_b.execute_preapproved([GRAMMAR_BROKEN])
        assert screen_decision.status == preapproved_decision.status == "blocked_grammar"
        assert screen_decision.cleared == preapproved_decision.cleared is False

    def test_console_offline_rejected_identically(self, tmp_path):
        monitor_a = HealthMonitor()
        monitor_a.note_ping_timeout()
        monitor_b = HealthMonitor()
        monitor_b.note_ping_timeout()
        gate_a, _, _ = make_gate(tmp_path, monitor=monitor_a)
        gate_b, _, _ = make_gate(tmp_path, monitor=monitor_b)
        screen_decision = gate_a.screen([SAFE_LINE])
        preapproved_decision = gate_b.execute_preapproved([SAFE_LINE])
        assert screen_decision.status == preapproved_decision.status
        assert screen_decision.status == "blocked_console_offline"

    def test_live_lock_active_rejected_identically(self, tmp_path):
        lock_a = LiveLock()
        lock_a.activate()
        lock_b = LiveLock()
        lock_b.activate()
        gate_a, _, _ = make_gate(tmp_path, lock=lock_a)
        gate_b, _, _ = make_gate(tmp_path, lock=lock_b)
        screen_decision = gate_a.screen([SAFE_LINE])
        preapproved_decision = gate_b.execute_preapproved([SAFE_LINE])
        assert screen_decision.status == preapproved_decision.status == "locked"
        assert screen_decision.proposal is not None
        assert preapproved_decision.proposal is not None


class TestExecutePreapprovedAudited:
    def test_grammar_block_is_audited_same_as_screen(self, tmp_path):
        gate, _, audit = make_gate(tmp_path)
        gate.execute_preapproved([GRAMMAR_BROKEN])
        assert len(_events(audit, "blocked")) >= 1
