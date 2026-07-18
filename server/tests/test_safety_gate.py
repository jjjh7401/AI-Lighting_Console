"""Safety gate pipeline tests (M4 — REQ-MVP-011~017, 026~036).

The gate is the SINGLE chokepoint: screening (grammar → risk classification →
human approval) issues clearances, and the gate-owned execution port refuses
any command without one. Safety asymmetry: over-holding is acceptable and
resolved by approval; a blacklisted command reaching the console without
approval must be impossible.
"""

from __future__ import annotations

import json
import threading

from server.llm.types import ModelTurn, ToolCall, ToolResultsMessage, Usage
from server.orchestrator.runner import Orchestrator
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.backup import BackupError, BackupManager
from server.safety.console import ExecOutcome
from server.safety.gate import _MAX_UNCONFIRMED, BACKUP_COMMAND, SafetyGate
from server.safety.lock import LiveLock
from server.safety.monitor import HealthMonitor
from server.safety.registry import PluginFlagRegistry
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key


class FakeConsole:
    """In-memory console port: every execute() call is one console send."""

    def __init__(self, state_tree: dict | None = None):
        self.executed: list[str] = []
        self.fail_on: dict[str, str] = {}
        self.unconfirmed_on: set[str] = set()
        self.ping_ok = True
        self.ping_error: Exception | None = None
        self.state_tree = state_tree or {}

    def execute(self, command: str) -> ExecOutcome:
        self.executed.append(command)
        if command in self.unconfirmed_on:
            return ExecOutcome(status="unconfirmed", detail="no confirmation")
        if command in self.fail_on:
            return ExecOutcome(status="failed", detail=self.fail_on[command])
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return self.ping_ok

    def query_state(self, path: str) -> dict:
        if path not in self.state_tree:
            raise RuntimeError(f"no such path: {path}")
        return self.state_tree[path]


class ScriptedApproval:
    """Deterministic approval port; optionally acts during the request."""

    def __init__(self, decisions=(True,), on_request=None):
        self.decisions = list(decisions)
        self.on_request = on_request
        self.requests = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if self.on_request is not None:
            self.on_request(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


def make_gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or FakeConsole()
    audit = kwargs.pop("audit", None) or AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, **kwargs)
    return gate, console, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestSafePath:
    def test_safe_bundle_clears_and_executes(self, tmp_path):
        gate, console, audit = make_gate(tmp_path)
        decision = gate.screen(["Store Cue 5", "List"])
        assert decision.cleared is True
        assert decision.status == "cleared"
        port = gate.execution_port
        assert port.execute("Store Cue 5").ok is True
        assert port.execute("List").ok is True
        assert console.executed == ["Store Cue 5", "List"]
        executed = _events(audit, "executed")
        assert [e["command"] for e in executed] == ["Store Cue 5", "List"]

    def test_safe_bundle_needs_no_approval_and_no_backup(self, tmp_path):
        # AC-MVP-008 rule 4: the non-risky path never touches the backup.
        approval = ScriptedApproval()
        backup_calls: list[str] = []
        backup = BackupManager(backup_action=lambda: backup_calls.append("b"))
        gate, console, _ = make_gate(tmp_path, approval_port=approval, backup=backup)
        decision = gate.screen(["Store Cue 5"])
        gate.execution_port.execute("Store Cue 5")
        assert decision.cleared
        assert approval.requests == []
        assert backup_calls == []

    def test_status_is_ui_visible(self, tmp_path):
        gate, _, _ = make_gate(tmp_path)
        assert gate.status == {"health": "online", "live_lock": False}


class TestPipelineOrder:
    def test_stages_run_grammar_then_classify_then_approval(self, tmp_path):
        # AC-MVP-015 part 1: the pipeline order is asserted, not assumed.
        stages: list[str] = []
        gate, _, _ = make_gate(
            tmp_path,
            approval_port=ScriptedApproval([True]),
            stage_observer=stages.append,
        )
        gate.screen(["Delete Sequence 5"])
        assert stages == ["grammar", "classify", "approval"]

    def test_safe_bundle_stops_after_classification(self, tmp_path):
        stages: list[str] = []
        gate, _, _ = make_gate(tmp_path, stage_observer=stages.append)
        gate.screen(["Store Cue 5"])
        assert stages == ["grammar", "classify"]


class TestGrammarStage:
    def test_unparseable_command_blocks_the_bundle_with_a_reason(self, tmp_path):
        # REQ-MVP-012 / AC-MVP-015 part 2: block + reason for self-correction.
        gate, console, audit = make_gate(tmp_path)
        decision = gate.screen(["Store Cue 5", "'broken"])
        assert decision.cleared is False
        assert decision.status == "blocked_grammar"
        failing = [d for d in decision.commands if d.command == "'broken"]
        assert any("quote" in r for r in failing[0].reasons)
        assert console.executed == []
        assert len(_events(audit, "blocked")) >= 1

    def test_grammar_blocked_commands_never_get_clearance(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        gate.screen(["'broken"])
        result = gate.execution_port.execute("'broken")
        assert result.ok is False
        assert console.executed == []


class TestApprovalStage:
    def test_risky_command_is_held_until_approval(self, tmp_path):
        approval = ScriptedApproval([True])
        gate, console, audit = make_gate(tmp_path, approval_port=approval)
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared is True
        (request,) = approval.requests
        item = request.items[0]
        assert item.command == "Delete Sequence 5"  # command text shown
        assert any("blacklist" in r for r in item.risk_reasons)  # risk reason shown
        assert len(_events(audit, "approved")) == 1

    def test_default_approval_port_denies_everything(self, tmp_path):
        # Fail-safe: without an approval channel nothing risky can run.
        gate, console, _ = make_gate(tmp_path)
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared is False
        assert decision.status == "rejected"
        assert console.executed == []

    def test_rejection_is_all_or_nothing(self, tmp_path):
        # AC-MVP-009: one rejection -> the WHOLE bundle is unexecuted.
        approval = ScriptedApproval([False])
        gate, console, audit = make_gate(tmp_path, approval_port=approval)
        decision = gate.screen(["Store Cue 1", "Delete Sequence 5", "Store Cue 2"])
        assert decision.cleared is False
        assert decision.status == "rejected"
        assert all(d.status == "rejected" for d in decision.commands)
        assert console.executed == []
        assert len(_events(audit, "rejected")) == 1
        for command in ("Store Cue 1", "Store Cue 2"):
            assert gate.execution_port.execute(command).ok is False
        assert console.executed == []

    def test_unspecified_target_warning_reaches_the_approval_request(self, tmp_path):
        # AC-MVP-024: the warning is surfaced with the held command.
        approval = ScriptedApproval([False])
        gate, _, _ = make_gate(tmp_path, approval_port=approval)
        gate.screen(["Delete"])
        (request,) = approval.requests
        assert any("target" in w for w in request.items[0].warnings)


class TestBackupRules:
    def test_pre_risky_backup_runs_before_execution(self, tmp_path):
        # AC-MVP-008 rule 3: backup strictly precedes the risky send.
        order: list[str] = []

        class OrderedConsole(FakeConsole):
            def execute(self, command):
                order.append(f"execute:{command}")
                return super().execute(command)

        console = OrderedConsole()
        backup = BackupManager(backup_action=lambda: order.append("backup"))
        gate, _, _ = make_gate(
            tmp_path, console=console, approval_port=ScriptedApproval([True]), backup=backup
        )
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared
        gate.execution_port.execute("Delete Sequence 5")
        assert order == ["backup", "execute:Delete Sequence 5"]

    def test_backup_failure_blocks_execution_and_notifies(self, tmp_path):
        # AC-MVP-022 fail-safe: backup failure -> block + notify.
        def failing_backup():
            raise RuntimeError("disk full")

        gate, console, audit = make_gate(
            tmp_path,
            approval_port=ScriptedApproval([True]),
            backup=BackupManager(backup_action=failing_backup),
        )
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared is False
        assert decision.status == "blocked_backup_failed"
        assert "backup" in decision.notice
        assert console.executed == []
        assert len(_events(audit, "blocked")) == 1

    def test_start_session_backs_up_once(self, tmp_path):
        calls: list[str] = []
        backup = BackupManager(backup_action=lambda: calls.append("b"))
        gate, _, _ = make_gate(tmp_path, backup=backup)
        gate.start_session()
        assert calls == ["b"]
        assert backup.history[0][0] == "session_start"

    def test_showfile_backup_action_sends_saveshow_via_the_gate(self, tmp_path):
        gate, console, audit = make_gate(tmp_path)
        action = gate.make_showfile_backup_action()
        action()
        assert console.executed == [BACKUP_COMMAND]
        (event,) = _events(audit, "executed")
        assert event["kind"] == "backup"

    def test_showfile_backup_action_raises_on_console_failure(self, tmp_path):
        console = FakeConsole()
        console.fail_on[BACKUP_COMMAND] = "cannot save"
        gate, _, _ = make_gate(tmp_path, console=console)
        backup = BackupManager(backup_action=gate.make_showfile_backup_action())
        try:
            backup.session_start()
            raise AssertionError("expected BackupError")
        except BackupError:
            pass

    def test_showfile_backup_action_blocked_by_live_lock_sends_zero_osc(self, tmp_path):
        # M6c-2 Finding 3 / AC-MVP-007a: the backup path must honor the SAME
        # zero-console-sends-while-locked guarantee every other send path
        # enforces (previously it called the console directly, bypassing it).
        lock = LiveLock()
        lock.activate()
        gate, console, audit = make_gate(tmp_path, lock=lock)
        action = gate.make_showfile_backup_action()
        try:
            action()
            raise AssertionError("expected the backup action to raise while locked")
        except RuntimeError as error:
            assert "lock" in str(error)
        assert console.executed == []
        assert len(_events(audit, "blocked")) == 1

    def test_showfile_backup_action_blocked_by_console_offline_sends_zero_osc(self, tmp_path):
        # M6c-2 Finding 3 / REQ-MVP-030: same guarantee while the console is
        # offline/degraded.
        monitor = HealthMonitor()
        monitor.note_ping_timeout()
        gate, console, audit = make_gate(tmp_path, monitor=monitor)
        action = gate.make_showfile_backup_action()
        try:
            action()
            raise AssertionError("expected the backup action to raise while offline")
        except RuntimeError as error:
            assert "health" in str(error)
        assert console.executed == []
        assert len(_events(audit, "blocked")) == 1

    def test_lock_skipped_backup_is_a_backup_error_not_a_silent_success(self, tmp_path):
        # REQ-MVP-034: a lock/health-skipped backup attempt must be treated
        # the same as a genuine backup failure by any downstream logic that
        # depends on "was a recent backup successful" (here: the periodic
        # timer only advances on a call that completes without raising).
        lock = LiveLock()
        lock.activate()
        gate, console, _ = make_gate(tmp_path, lock=lock)
        backup = BackupManager(backup_action=gate.make_showfile_backup_action())
        try:
            backup.session_start()
            raise AssertionError("expected BackupError")
        except BackupError:
            pass
        assert console.executed == []
        assert backup.history == []


class TestLiveLock:
    def test_lock_active_produces_proposal_only(self, tmp_path):
        # AC-MVP-007a: zero console sends, proposal card only.
        lock = LiveLock()
        lock.activate()
        approval = ScriptedApproval([True])
        gate, console, audit = make_gate(tmp_path, lock=lock, approval_port=approval)
        decision = gate.screen(["Store Cue 5"])
        assert decision.cleared is False
        assert decision.status == "locked"
        assert decision.proposal is not None
        assert decision.proposal.commands == ("Store Cue 5",)
        assert approval.requests == []  # lock outranks the approval stage
        assert console.executed == []
        assert len(_events(audit, "blocked")) == 1

    def test_unlock_restores_the_normal_path(self, tmp_path):
        # AC-MVP-007b.
        lock = LiveLock()
        lock.activate()
        gate, console, _ = make_gate(tmp_path, lock=lock)
        assert gate.screen(["Store Cue 5"]).cleared is False
        lock.deactivate()
        decision = gate.screen(["Store Cue 5"])
        assert decision.cleared is True
        gate.execution_port.execute("Store Cue 5")
        assert console.executed == ["Store Cue 5"]

    def test_lock_first_wins_over_a_pending_approval(self, tmp_path):
        # AC-MVP-023 / REQ-MVP-035: lock arriving DURING the approval wait
        # converts held commands to non-executable even if approved after.
        lock = LiveLock()
        approval = ScriptedApproval([True], on_request=lambda _request: lock.activate())
        gate, console, _ = make_gate(tmp_path, lock=lock, approval_port=approval)
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared is False
        assert decision.status == "locked"
        assert console.executed == []
        # a later approval click cannot execute either — no clearance exists
        assert gate.execution_port.execute("Delete Sequence 5").ok is False
        assert console.executed == []

    def test_executor_rechecks_the_lock_before_every_send(self, tmp_path):
        lock = LiveLock()
        gate, console, _ = make_gate(tmp_path, lock=lock)
        assert gate.screen(["Store Cue 5"]).cleared
        lock.activate()  # lock lands between clearance and execution
        result = gate.execution_port.execute("Store Cue 5")
        assert result.ok is False
        assert console.executed == []


class TestHealthBlocking:
    def test_console_offline_blocks_new_executions(self, tmp_path):
        # AC-MVP-020 part 1.
        monitor = HealthMonitor()
        monitor.note_ping_timeout()
        gate, console, _ = make_gate(tmp_path, monitor=monitor)
        decision = gate.screen(["Store Cue 5"])
        assert decision.cleared is False
        assert decision.status == "blocked_console_offline"
        assert gate.status["health"] == "console_offline"
        assert console.executed == []

    def test_responder_degraded_blocks_side_effectful_commands(self, tmp_path):
        # AC-MVP-020 part 2.
        monitor = HealthMonitor()
        monitor.note_activity()
        monitor.note_ping_timeout()
        gate, console, _ = make_gate(tmp_path, monitor=monitor)
        decision = gate.screen(["Store Cue 5"])
        assert decision.cleared is False
        assert decision.status == "blocked_responder_degraded"
        assert console.executed == []

    def test_executor_rechecks_health_before_every_send(self, tmp_path):
        monitor = HealthMonitor()
        gate, console, _ = make_gate(tmp_path, monitor=monitor)
        assert gate.screen(["Store Cue 5"]).cleared
        monitor.note_ping_timeout()
        assert gate.execution_port.execute("Store Cue 5").ok is False
        assert console.executed == []

    def test_heartbeat_probes_and_audits(self, tmp_path):
        gate, console, audit = make_gate(tmp_path)
        console.ping_ok = True
        assert gate.heartbeat() == "online"
        console.ping_ok = False
        # A failure right after a success means the console was seen alive
        # moments ago -> responder_degraded, not console_offline.
        assert gate.heartbeat() == "responder_degraded"
        heartbeats = [e for e in audit.iter_events() if e.get("kind") == "heartbeat"]
        assert len(heartbeats) == 2

    def test_heartbeat_with_no_prior_traffic_reports_console_offline(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        console.ping_ok = False
        assert gate.heartbeat() == "console_offline"


class TestUnconfirmedExecution:
    def test_unconfirmed_result_is_reported_and_never_auto_resent(self, tmp_path):
        # AC-MVP-020 part 3 / REQ-MVP-032.
        approval = ScriptedApproval([False])
        gate, console, _ = make_gate(tmp_path, approval_port=approval)
        console.unconfirmed_on.add("Store Cue 9")
        assert gate.screen(["Store Cue 9"]).cleared
        result = gate.execution_port.execute("Store Cue 9")
        assert result.ok is False
        assert "unconfirmed" in result.detail
        assert console.executed == ["Store Cue 9"]
        # the SAME command screened again is held for approval, not resent
        decision = gate.screen(["Store Cue 9"])
        assert decision.cleared is False
        (request,) = approval.requests
        assert any("unconfirmed" in r for r in request.items[0].risk_reasons)
        assert console.executed == ["Store Cue 9"]  # still exactly one send


class TestUnconfirmedBoundedGrowth:
    """M6c backlog: ``self._unconfirmed`` had no eviction path — unbounded
    growth over a long-running session, distinct from the REQ-MVP-032 safety
    property itself (which must hold for everything INSIDE the window).
    """

    def test_unconfirmed_set_never_exceeds_the_cap(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        commands = [f"Store Cue {i}" for i in range(_MAX_UNCONFIRMED + 1)]
        for command in commands:
            console.unconfirmed_on.add(command)
            assert gate.screen([command]).cleared
            result = gate.execution_port.execute(command)
            assert result.ok is False
        assert len(gate._unconfirmed) == _MAX_UNCONFIRMED

    def test_oldest_entry_is_evicted_newest_still_forces_a_hold(self, tmp_path):
        # REQ-MVP-032 regression guard: nothing INSIDE the window loses
        # protection; only the entry pushed out by the cap regains
        # auto-resend eligibility — a documented, deliberate trade-off.
        gate, console, _ = make_gate(tmp_path)
        commands = [f"Store Cue {i}" for i in range(_MAX_UNCONFIRMED + 1)]
        for command in commands:
            console.unconfirmed_on.add(command)
            gate.screen([command])
            gate.execution_port.execute(command)

        oldest, newest = commands[0], commands[-1]

        # oldest was evicted by the cap -> re-screening clears with no hold
        assert gate.screen([oldest]).cleared is True

        # newest is still inside the window -> still forces a hold + denial
        newest_decision = gate.screen([newest])
        assert newest_decision.cleared is False
        assert any("unconfirmed" in r for r in newest_decision.commands[0].reasons)


class TestClearanceEnforcement:
    def test_unscreened_command_is_refused(self, tmp_path):
        gate, console, audit = make_gate(tmp_path)
        result = gate.execution_port.execute("Store Cue 5")
        assert result.ok is False
        assert "not cleared" in result.detail
        assert console.executed == []
        assert len(_events(audit, "blocked")) == 1

    def test_a_clearance_is_consumed_by_execution(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        gate.screen(["Store Cue 5"])
        assert gate.execution_port.execute("Store Cue 5").ok is True
        assert gate.execution_port.execute("Store Cue 5").ok is False
        assert console.executed == ["Store Cue 5"]

    def test_a_new_screen_invalidates_outstanding_clearances(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        gate.screen(["Store Cue 5"])
        gate.screen(["List"])  # new bundle replaces the old clearances
        assert gate.execution_port.execute("Store Cue 5").ok is False
        assert console.executed == []


class TestConcurrentSessionClearanceIsolation:
    """M6c-1 Finding 2 — one SafetyGate instance is shared by every concurrent
    ChatSession (``deps.gate`` in server/web/app.py), but ``_clearances`` was
    a single instance-level Counter: session B's ``screen()`` call silently
    invalidated session A's already-cleared, not-yet-executed bundle.
    """

    def test_a_sessions_screen_does_not_invalidate_anothers_clearance(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        key_a = new_session_key()
        key_b = new_session_key()

        token = bind_session_key(key_a)
        try:
            gate.screen(["Store Cue 5"])  # session A clears its own bundle
        finally:
            reset_session_key(token)

        token = bind_session_key(key_b)
        try:
            gate.screen(["List"])  # session B's OWN bundle — must not touch A's
        finally:
            reset_session_key(token)

        token = bind_session_key(key_a)
        try:
            # A's clearance must survive B's unrelated screen() call.
            assert gate.execution_port.execute("Store Cue 5").ok is True
        finally:
            reset_session_key(token)
        assert console.executed == ["Store Cue 5"]

    def test_concurrent_sessions_both_execute_their_own_cleared_bundle(self, tmp_path):
        gate, console, _ = make_gate(tmp_path)
        key_a = new_session_key()
        key_b = new_session_key()
        start = threading.Barrier(2)
        screened = threading.Barrier(2)
        results: dict[str, bool] = {}

        def run_session(key, command, result_key):
            token = bind_session_key(key)
            try:
                start.wait(timeout=5.0)  # both sessions screen at ~the same time
                gate.screen([command])
                screened.wait(timeout=5.0)  # both screened before either executes
                results[result_key] = gate.execution_port.execute(command).ok
            finally:
                reset_session_key(token)

        thread_a = threading.Thread(target=run_session, args=(key_a, "Store Cue 5", "a"))
        thread_b = threading.Thread(target=run_session, args=(key_b, "List", "b"))
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=5.0)
        thread_b.join(timeout=5.0)

        assert results.get("a") is True
        assert results.get("b") is True
        assert set(console.executed) == {"Store Cue 5", "List"}


class TestPluginInvocationGate:
    def test_destructive_flagged_plugin_requires_approval_every_time(self, tmp_path):
        # AC-MVP-018 part 2 (invocation half).
        registry = PluginFlagRegistry()
        registry.register("Plugin 7", destructive=True)
        approval = ScriptedApproval([True, True])
        gate, console, _ = make_gate(tmp_path, plugin_registry=registry, approval_port=approval)
        assert gate.screen(["Plugin 7"]).cleared
        gate.execution_port.execute("Plugin 7")
        assert gate.screen(["Plugin 7"]).cleared
        gate.execution_port.execute("Plugin 7")
        assert len(approval.requests) == 2  # EVERY invocation asks again
        assert console.executed == ["Plugin 7", "Plugin 7"]

    def test_non_destructive_registered_plugin_passes_through_the_gate_audited(self, tmp_path):
        # AC-MVP-018 part 3: no approval, but the gate passage is audited.
        registry = PluginFlagRegistry()
        registry.register("Plugin 8", destructive=False)
        approval = ScriptedApproval()
        gate, console, audit = make_gate(tmp_path, plugin_registry=registry, approval_port=approval)
        decision = gate.screen(["Plugin 8"])
        assert decision.cleared is True
        assert approval.requests == []
        gate.execution_port.execute("Plugin 8")
        (event,) = _events(audit, "executed")
        assert event["command"] == "Plugin 8"


class TestStateQueryPort:
    def test_state_queries_ride_the_gate_owned_port_and_are_audited(self, tmp_path):
        console = FakeConsole(state_tree={"DataPool/Groups": {"ok": True, "children": []}})
        gate, _, audit = make_gate(tmp_path, console=console)
        payload = gate.state_port.query_state("DataPool/Groups")
        assert payload["ok"] is True
        (event,) = _events(audit, "executed")
        assert event["kind"] == "state_query"


# -- orchestrator wiring (REQ-MVP-012 feed + AC-MVP-021 partial atomicity) ----


def _run_turn(commands, call_id):
    return ModelTurn(
        text="",
        tool_calls=(ToolCall(id=call_id, name="run_commands", arguments={"commands": commands}),),
        stop_reason="tool_use",
        usage=Usage(),
        provider="scripted",
    )


def _final(text="완료"):
    return ModelTurn(
        text=text, tool_calls=(), stop_reason="end", usage=Usage(), provider="scripted"
    )


class ScriptedProvider:
    name = "scripted"
    model_id = "scripted-model"
    supports_prompt_caching = False

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls.append(list(conversation))
        return self.turns.pop(0)


class FakeStatePort:
    def query_state(self, path):
        return {"ok": True, "children": []}


def _gated_orchestrator(tmp_path, provider, *, gate=None, console=None, **gate_kwargs):
    if gate is None:
        console = console or FakeConsole()
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(console=console, audit=audit, **gate_kwargs)
    registry = build_toolset(
        execution_port=gate.execution_port,
        state_port=FakeStatePort(),
        bundle_gate=gate,
    )
    return Orchestrator(provider=provider, registry=registry, system_prefix="P"), gate, console


class TestOrchestratorWiring:
    def test_grammar_block_reason_feeds_the_self_correction_loop(self, tmp_path):
        # REQ-MVP-012 / AC-MVP-015 part 2, end to end through the runner.
        provider = ScriptedProvider(
            [_run_turn(["'broken"], "c1"), _run_turn(["Store Cue 5"], "c2"), _final()]
        )
        orchestrator, gate, console = _gated_orchestrator(tmp_path, provider)
        result = orchestrator.handle_instruction("큐 저장해줘")
        assert result.status == "ok"
        assert result.retries_used == 1  # the blocked round counted as a correction
        assert console.executed == ["Store Cue 5"]
        feedback = provider.calls[1][-1]
        assert isinstance(feedback, ToolResultsMessage)
        content = json.loads(feedback.results[0].content)
        assert content["gate_status"] == "blocked_grammar"
        assert any("quote" in r for r in content["commands"][0]["reasons"])

    def test_bundle_partial_failure_atomicity(self, tmp_path):
        # AC-MVP-021: k-th failure stops the bundle; 1..k-1 are never resent.
        provider = ScriptedProvider(
            [
                _run_turn(["Store Cue 1", "Bad Command", "Store Cue 3"], "c1"),
                _run_turn(["Store Cue 1", "Store Cue 2b", "Store Cue 3"], "c2"),
                _final(),
            ]
        )
        console = FakeConsole()
        console.fail_on["Bad Command"] = "Illegal command"
        orchestrator, gate, console = _gated_orchestrator(tmp_path, provider, console=console)
        result = orchestrator.handle_instruction("세 개 실행해줘")
        assert result.status == "ok"
        # Store Cue 1 executed exactly once — the correction round skipped it.
        assert console.executed == [
            "Store Cue 1",
            "Bad Command",
            "Store Cue 2b",
            "Store Cue 3",
        ]
        first_round = [o for o in result.command_outcomes[:3]]
        assert [o.status for o in first_round] == ["executed_ok", "failed", "not_executed"]

    def test_rejected_bundle_reports_and_does_not_execute(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Delete Sequence 5"], "c1"), _final()])
        orchestrator, gate, console = _gated_orchestrator(tmp_path, provider)
        result = orchestrator.handle_instruction("시퀀스 지워줘")
        assert console.executed == []
        assert any(o.status == "rejected" for o in result.command_outcomes)
