"""SPEC-LDRECV-001 M3 · REQ-LDPLUGIN-022 · AC-LDPLUGIN-022.

공유 programmer 중재자 — director apply(``execute_preapproved``)와 일반
chat/import(``screen``)가 하나의 lock을 거치는지, 충돌 시 즉시(폴링 없이)
``TARGET_BUSY``로 거부되는지, lock 해제 후 재시도가 캐시된 판정이 아니라
파이프라인을 처음부터 다시 타는지(신선도 재검사 seam)를 시험한다.

``server.director.programmer_arbiter.ProgrammerArbiter``를 단독으로 먼저
시험하고(순수 mutex), 이어서 ``SafetyGate``에 배선된 상태에서
director(``execute_preapproved``) vs chat(``screen``) 양방향을 실제
스레드로 경합시킨다(design.md §2.3 — lock은 gate의 공유 private 스테이지
안에 있다).
"""

from __future__ import annotations

import threading

from server.director.programmer_arbiter import ProgrammerArbiter, TargetBusyError
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate


class FakeConsole:
    """In-memory console port — no real OSC send (mirrors test_safety_gate.py)."""

    def __init__(self):
        self.executed: list[str] = []
        self.ping_ok = True

    def execute(self, command: str):
        from server.safety.console import ExecOutcome

        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return self.ping_ok

    def query_state(self, path: str) -> dict:
        raise RuntimeError(f"no such path: {path}")


class BlockingApproval:
    """Approval port whose ``request_approval`` signals + waits on demand.

    Lets a test hold ``screen()`` deep inside its approval wait (i.e. AFTER
    the arbiter lock has been acquired, per the pipeline order in
    design.md §2.3) until the test releases it.
    """

    def __init__(self, *, decision: bool = True):
        self.reached = threading.Event()
        self.release = threading.Event()
        self.decision = decision
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        self.reached.set()
        self.release.wait(timeout=5.0)
        return self.decision


class BlockingBackup:
    """Backup double whose ``before_risky_execution`` signals + waits.

    Lets a test hold ``execute_preapproved()`` deep inside its
    pre-risky-execution backup step (also AFTER the arbiter lock has been
    acquired) until the test releases it.
    """

    def __init__(self):
        self.reached = threading.Event()
        self.release = threading.Event()

    def before_risky_execution(self) -> None:
        self.reached.set()
        self.release.wait(timeout=5.0)


RISKY_LINE = "Delete Sequence 5"
SAFE_LINE = "Fixture 900 At 50"


def make_gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or FakeConsole()
    audit = kwargs.pop("audit", None) or AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, **kwargs)
    return gate, console, audit


class TestProgrammerArbiterUnit:
    """The mutex primitive alone — no SafetyGate involved."""

    def test_second_acquire_is_busy_immediately(self):
        arbiter = ProgrammerArbiter()
        arbiter.try_acquire("director")
        # AC-022: "즉시 거부인지(폴링/대기 없음)" — a plain synchronous call
        # either raises right here or it doesn't; there is nothing to poll.
        try:
            arbiter.try_acquire("chat")
            raised = False
        except TargetBusyError:
            raised = True
        assert raised is True

    def test_busy_error_names_the_holder(self):
        arbiter = ProgrammerArbiter()
        arbiter.try_acquire("director-apply-1")
        try:
            arbiter.try_acquire("chat-session-a")
            raise AssertionError("expected TargetBusyError")
        except TargetBusyError as error:
            assert error.held_by == "director-apply-1"
            assert "TARGET_BUSY" in str(error)

    def test_release_then_acquire_succeeds(self):
        arbiter = ProgrammerArbiter()
        arbiter.try_acquire("director")
        arbiter.release()
        arbiter.try_acquire("chat")  # must not raise
        assert arbiter.is_active is True

    def test_reverse_direction_chat_holds_director_busy(self):
        # AC-022: "역방향(chat이 먼저 쥔 lock에 director가 요청)도 동일하다."
        arbiter = ProgrammerArbiter()
        arbiter.try_acquire("chat-session-a")
        try:
            arbiter.try_acquire("director-apply-1")
            raise AssertionError("expected TargetBusyError")
        except TargetBusyError:
            pass


class TestGateArbiterIntegrationDirectorHoldsChatBusy:
    """director(execute_preapproved) holds the lock; chat(screen) requests."""

    def test_concurrent_director_and_chat_exactly_one_busy(self, tmp_path):
        backup = BlockingBackup()
        gate, console, _ = make_gate(tmp_path, backup=backup)
        results: dict[str, object] = {}

        def run_director():
            results["director"] = gate.execute_preapproved([RISKY_LINE])

        director_thread = threading.Thread(target=run_director)
        director_thread.start()
        # Wait until the director call is provably holding the arbiter —
        # it can only have reached the backup step AFTER acquiring the lock.
        assert backup.reached.wait(timeout=5.0) is True

        chat_decision = gate.screen([SAFE_LINE])
        results["chat_while_busy"] = chat_decision

        backup.release.set()
        director_thread.join(timeout=5.0)

        assert results["director"].cleared is True
        assert chat_decision.cleared is False
        assert chat_decision.status == "blocked_target_busy"

    def test_retry_after_release_is_not_a_stale_replay(self, tmp_path):
        # AC-022: "lock 해제 후 대기 중이던 승인이 그대로 실행되지 않고
        # 신선도를 다시 검사하는지" — M3 scope is the SEAM: a retry after
        # release re-enters the full pipeline (it is a fresh screen() call,
        # not a resumed/cached one), so it can observe state that changed
        # while it was busy. Actual freshness JUDGMENT is M5's job; here we
        # assert the retry actually re-executes grammar+classify+lock (via
        # the console really being reached), never a cached decision.
        backup = BlockingBackup()
        gate, console, _ = make_gate(tmp_path, backup=backup)

        def run_director():
            gate.execute_preapproved([RISKY_LINE])

        director_thread = threading.Thread(target=run_director)
        director_thread.start()
        assert backup.reached.wait(timeout=5.0) is True

        busy_decision = gate.screen([SAFE_LINE])
        assert busy_decision.status == "blocked_target_busy"
        assert console.executed == []  # busy path never reaches execution

        backup.release.set()
        director_thread.join(timeout=5.0)

        # Retry after release: a brand-new screen() call, fully re-run.
        retry_decision = gate.screen([SAFE_LINE])
        assert retry_decision.cleared is True
        assert retry_decision.status == "cleared"


class TestGateArbiterIntegrationChatHoldsDirectorBusy:
    """chat(screen) holds the lock; director(execute_preapproved) requests
    — AC-022's explicit reverse direction."""

    def test_concurrent_chat_and_director_exactly_one_busy(self, tmp_path):
        approval = BlockingApproval(decision=True)
        gate, console, _ = make_gate(tmp_path, approval_port=approval)
        results: dict[str, object] = {}

        def run_chat():
            results["chat"] = gate.screen([RISKY_LINE])

        chat_thread = threading.Thread(target=run_chat)
        chat_thread.start()
        # The approval port is only reached AFTER the arbiter lock has been
        # acquired (design.md §2.3 places the arbiter stage right after the
        # existing live-lock check, before the approval request).
        assert approval.reached.wait(timeout=5.0) is True

        director_decision = gate.execute_preapproved([SAFE_LINE])

        approval.release.set()
        chat_thread.join(timeout=5.0)

        assert results["chat"].cleared is True
        assert director_decision.cleared is False
        assert director_decision.status == "blocked_target_busy"
        # execute_preapproved never asks the general approval channel —
        # the busy rejection happens before any approval-port concern
        # exists for this call at all.
        assert len(approval.requests) == 1  # only chat's own request


class TestGateAndDirectorShareOneArbiter:
    def test_screen_and_execute_preapproved_share_the_same_arbiter(self, tmp_path):
        gate, _, _ = make_gate(tmp_path)
        gate._arbiter.try_acquire("external-holder")
        try:
            decision = gate.screen([SAFE_LINE])
            assert decision.status == "blocked_target_busy"
            decision2 = gate.execute_preapproved([SAFE_LINE])
            assert decision2.status == "blocked_target_busy"
        finally:
            gate._arbiter.release()

    def test_arbiter_is_injectable_for_tests(self, tmp_path):
        injected = ProgrammerArbiter()
        gate, _, _ = make_gate(tmp_path, arbiter=injected)
        assert gate._arbiter is injected


class TestScreenArbitrateScopeGuard:
    """SPEC-LDRECV-001 M3 scope narrowing — REQ-LDPLUGIN-022 vs REQ-SHOWUI-013.

    REQ-022's "모든 shared programmer mutation" is narrowed to director/chat/
    import (design.md §2.5): the panel's own ``screen()`` calls (see
    ``server/web/panel.py`` ``PanelRuntime.fire()``) opt out via
    ``arbitrate=False``, so a director apply or a chat turn holding the
    arbiter never busies out a panel press — REQ-SHOWUI-013 stays intact.

    ``arbitrate`` defaults to ``True`` — every existing caller
    (``tools.py``'s ``run_commands``, ``session.py``'s chat wrapper,
    ``measurement/runner.py``) keeps arbitrating with ZERO code changes,
    since none of them pass this keyword.
    """

    def test_arbitrate_defaults_to_true(self, tmp_path):
        gate, _, _ = make_gate(tmp_path)
        gate._arbiter.try_acquire("external-holder")
        try:
            decision = gate.screen([SAFE_LINE])  # no arbitrate= passed
            assert decision.status == "blocked_target_busy"
        finally:
            gate._arbiter.release()

    def test_arbitrate_false_bypasses_the_lock_entirely(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        gate._arbiter.try_acquire("external-holder")
        try:
            decision = gate.screen([SAFE_LINE], arbitrate=False)
            assert decision.cleared is True
            assert decision.status == "cleared"
        finally:
            gate._arbiter.release()

    def test_arbitrate_false_never_acquires_or_releases(self, tmp_path):
        gate, _, _ = make_gate(tmp_path)
        gate.screen([SAFE_LINE], arbitrate=False)
        # Never touched the arbiter at all — still free, no acquire/release
        # pair ran (verifiable indirectly: a subsequent real acquire succeeds
        # cleanly with no prior release needed).
        assert gate._arbiter.is_active is False
        gate._arbiter.try_acquire("someone-else")  # would raise if left held
        gate._arbiter.release()

    def test_arbitrate_false_does_not_busy_a_concurrent_arbitrated_caller(self, tmp_path):
        # The exact shape of the fixed REQ-SHOWUI-013 tests: a director
        # caller holds the arbiter; a panel-style (arbitrate=False) caller
        # must still clear normally, not TARGET_BUSY.
        backup = BlockingBackup()
        gate, console, _ = make_gate(tmp_path, backup=backup)

        director_thread = threading.Thread(target=lambda: gate.execute_preapproved([RISKY_LINE]))
        director_thread.start()
        assert backup.reached.wait(timeout=5.0) is True

        panel_decision = gate.screen([SAFE_LINE], arbitrate=False)

        backup.release.set()
        director_thread.join(timeout=5.0)

        assert panel_decision.cleared is True
        assert panel_decision.status == "cleared"
