"""The safety gate — single chokepoint pipeline (M4, REQ-MVP-011~018, 026~036).

Pipeline per bundle (design.md §C, order asserted by AC-MVP-015):

    health check → ① grammar validator → ② risk classification
    (closed blacklist + expand-or-hold + plugin flags + unspecified-target
    + unconfirmed-history) → live-lock check → ③ human approval (risky only)
    → lock re-check (lock-FIRST, REQ-MVP-035) → pre-risky backup
    → clearance issue

Execution model (clearance tokens): :meth:`screen` ISSUES clearances for a
cleared bundle; the gate-owned execution port CONSUMES exactly one clearance
per send and refuses everything else. Bypass is therefore impossible even for
a caller holding the port directly — no clearance, no send. Every console
send is audited 1:1 (AC-MVP-019 ②).

Safety asymmetry: when in doubt, HOLD. Approval defaults to deny-all.

M6c-1 (cross-session isolation, Finding 2): ONE ``SafetyGate`` instance is
shared by every concurrent ``ChatSession`` (``deps.gate`` in
``server/web/app.py``). ``_clearances`` is therefore keyed per session (via
the ambient session key ``ChatSession.run_instruction`` binds around each
turn — see :mod:`server.safety.session_context`), so session B's
``screen()`` call can never invalidate session A's already-cleared,
not-yet-executed bundle. A lock guards the per-session Counter dict against
concurrent mutation from different sessions' worker threads.
"""

from __future__ import annotations

import threading
import time
from collections import Counter, OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from server.orchestrator.ports import ExecutionResult
from server.safety.approval import (
    ApprovalItem,
    ApprovalPort,
    ApprovalRequest,
    DenyAllApprovalPort,
)
from server.safety.audit import AuditLog
from server.safety.backup import BackupError, BackupManager
from server.safety.classify import RECOGNIZED_REFERENCE_TYPES, classify_command
from server.safety.console import ConsolePort
from server.safety.expand import BodyFetcher, BodyUnavailable, evaluate_reference
from server.safety.grammar import validate
from server.safety.lock import LiveLock, ProposalCard
from server.safety.monitor import HealthMonitor
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import SafetyRuleset, load_ruleset
from server.safety.session_context import SessionKey, current_session_key

# Showfile backup command (REQ-MVP-017). ASSUMPTION (onPC-unverified, M6 live
# calibration): the MA3 ``SaveShow`` keyword saves the current showfile when
# sent through the exec path. Recorded as a check-in ratification item.
BACKUP_COMMAND = "SaveShow"

# Bounded-LRU cap for self._unconfirmed (M6c backlog). Order-of-magnitude
# default for a long-running operating session; no existing constant to
# match since this is the first bound placed on that set.
_MAX_UNCONFIRMED = 500


@dataclass(frozen=True)
class CommandDecision:
    """Per-command screening verdict inside one bundle decision."""

    command: str
    status: str  # "cleared" | "blocked" | "held" | "rejected" | "proposal"
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreenDecision:
    """One bundle's screening outcome (the BundleGate return shape)."""

    cleared: bool
    status: str
    commands: tuple[CommandDecision, ...]
    proposal: ProposalCard | None = None
    approval_request: ApprovalRequest | None = None
    notice: str = ""


@dataclass
class _Finding:
    command: str
    hold: bool
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class _UnavailableBodyFetcher:
    """Safe default fetcher: every reference body is unverifiable -> held."""

    def fetch_body(self, reference: str) -> Sequence[str]:
        raise BodyUnavailable("no body fetcher configured — reference bodies unverifiable")


class _GateExecutor:
    """The sole production CommandExecutionPort implementation (REQ-MVP-029)."""

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate

    def execute(self, command: str) -> ExecutionResult:
        return self._gate._execute_cleared(command)


class _GateStatePort:
    """StateQueryPort implementation riding the gate-audited console link."""

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate

    def query_state(self, path: str) -> dict:
        return self._gate._query_state(path)


class SafetyGate:
    """3-stage safety gate + live lock + backup + health + audit (M4)."""

    def __init__(
        self,
        *,
        console: ConsolePort,
        audit: AuditLog,
        ruleset: SafetyRuleset | None = None,
        approval_port: ApprovalPort | None = None,
        lock: LiveLock | None = None,
        monitor: HealthMonitor | None = None,
        backup: BackupManager | None = None,
        body_fetcher: BodyFetcher | None = None,
        plugin_registry: PluginFlagRegistry | None = None,
        reference_types: tuple[str, ...] = RECOGNIZED_REFERENCE_TYPES,
        stage_observer: Callable[[str], None] | None = None,
    ) -> None:
        self._console = console
        self._audit = audit
        self._ruleset = ruleset or load_ruleset()
        self._approval_port = approval_port or DenyAllApprovalPort()
        self.lock = lock or LiveLock()
        self.monitor = monitor or HealthMonitor()
        self._backup = backup
        self._body_fetcher = body_fetcher or _UnavailableBodyFetcher()
        self._plugin_registry = plugin_registry
        self._reference_types = reference_types
        self._stage_observer = stage_observer
        # Session-keyed (M6c-1 Finding 2) — one Counter per calling session,
        # so concurrent ChatSessions never invalidate each other's clearances.
        self._clearances: dict[SessionKey, Counter[str]] = {}
        self._clearances_lock = threading.Lock()
        # @MX:DEBT: [AUTO] bounded-LRU ordered set (OrderedDict[str, None]),
        #   NOT an unbounded set — a command once unconfirmed always
        #   re-requires human approval (REQ-MVP-032), but only within the
        #   cap; entries evicted beyond it silently regain auto-resend
        #   eligibility.
        # @MX:CEILING: at most _MAX_UNCONFIRMED (500) distinct commands
        #   retained; oldest is evicted first (insertion/re-add order).
        # @MX:UPGRADE: if a real operational session is observed to exceed
        #   _MAX_UNCONFIRMED distinct unconfirmed commands, revisit with
        #   persistent/audited storage instead of an in-memory bounded set.
        self._unconfirmed: OrderedDict[str, None] = OrderedDict()
        self._executor = _GateExecutor(self)
        self._state_port = _GateStatePort(self)

    # -- public surface ---------------------------------------------------------

    @property
    def execution_port(self) -> _GateExecutor:
        """The ONLY production CommandExecutionPort (REQ-MVP-029)."""
        return self._executor

    @property
    def state_port(self) -> _GateStatePort:
        """The gate-owned StateQueryPort (state queries are audited too)."""
        return self._state_port

    @property
    def status(self) -> dict:
        """UI-visible gate state (REQ-MVP-030: health shown to the user)."""
        return {"health": self.monitor.state, "live_lock": self.lock.is_active}

    def start_session(self) -> None:
        """Session start: backup rule ① (REQ-MVP-017); BackupError propagates."""
        if self._backup is not None:
            self._backup.session_start()

    def heartbeat(self) -> str:
        """Probe the responder once; audited; returns the resulting health state."""
        ok = self._console.ping()
        if ok:
            self.monitor.note_ping_success()
        else:
            self.monitor.note_ping_timeout()
        self._audit.log_executed("ping", kind="heartbeat", ok=ok)
        return self.monitor.state

    def use_showfile_backup(
        self,
        *,
        interval_seconds: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> BackupManager:
        """Attach a BackupManager whose action saves the showfile via this gate."""
        manager = BackupManager(
            backup_action=self.make_showfile_backup_action(),
            interval_seconds=interval_seconds,
            clock=clock,
        )
        self._backup = manager
        return manager

    def make_showfile_backup_action(self) -> Callable[[], None]:
        """A backup action sending ``SaveShow`` through the audited gate path.

        M6c-2 Finding 3 (AC-MVP-007a / REQ-MVP-030~031): every OTHER
        console-send path re-checks the live-lock and health-monitor state
        immediately before sending (see :meth:`_execute_cleared` and
        :meth:`deploy_plugin_source`). This backup path previously called
        the console directly, so a periodic/session-start/pre-risky backup
        could send ``SaveShow`` while the live lock was active — directly
        violating AC-MVP-007a's "zero console sends during an active live
        lock" guarantee — or while the console was offline/degraded.

        A lock/health-blocked attempt now raises instead of sending, so
        :class:`~server.safety.backup.BackupManager` converts it into a
        :class:`~server.safety.backup.BackupError` — the SAME fail-safe
        REQ-MVP-034 treats a genuine backup-action failure with. This is
        intentional: a skipped backup must never be silently indistinguishable
        from a successful one to anything downstream that depends on backup
        state (e.g. the periodic timer, which only advances on a call that
        completes without raising).
        """

        def action() -> None:
            if self.lock.is_active:
                reason = "live lock active (read-only) — showfile backup skipped"
                self._audit.log_blocked(BACKUP_COMMAND, reason=reason)
                raise RuntimeError(f"showfile backup skipped: {reason}")
            if self.monitor.executions_blocked:
                reason = f"health: {self.monitor.state} — showfile backup skipped"
                self._audit.log_blocked(BACKUP_COMMAND, reason=reason)
                raise RuntimeError(f"showfile backup skipped: {reason}")
            outcome = self._console.execute(BACKUP_COMMAND)
            self._audit.log_executed(
                BACKUP_COMMAND, kind="backup", ok=outcome.status == "ok", detail=outcome.detail
            )
            if outcome.status != "ok":
                raise RuntimeError(f"showfile backup not confirmed: {outcome.detail}")

        return action

    # -- screening pipeline (BundleGate) ---------------------------------------

    # @MX:ANCHOR: [AUTO] the 3-stage gate pipeline entry — run_commands (via the
    #   BundleGate wiring), the M5 approval UI flow, and every FN-corpus/E2E test
    #   pass bundles through this single method
    # @MX:REASON: REQ-MVP-011/029 — exactly ONE screening path may exist; a second
    #   entry would be a gate bypass by construction (fan_in >= 3)
    def screen(self, commands: Sequence[str]) -> ScreenDecision:
        """Screen one command bundle; issues clearances only on full clearance."""
        commands = list(commands)
        session_key = current_session_key()
        with self._clearances_lock:
            # A new bundle invalidates THIS session's old clearances only —
            # never another concurrently-screening session's (M6c-1 Finding 2).
            self._clearances[session_key] = Counter()

        health = self._check_health(commands)
        if health is not None:
            return health

        grammar = self._stage_grammar(commands)
        if isinstance(grammar, ScreenDecision):
            return grammar

        findings = self._stage_classify(grammar)

        locked = self._check_lock(commands, findings, phase="live lock active")
        if locked is not None:
            return locked

        approval_request: ApprovalRequest | None = None
        held = [f for f in findings if f.hold]
        if held:
            self._observe("approval")
            approval_request = ApprovalRequest(
                items=tuple(
                    ApprovalItem(command=f.command, risk_reasons=f.reasons, warnings=f.warnings)
                    for f in held
                )
            )
            approved = self._approval_port.request_approval(approval_request)
            if not approved:
                self._audit.log_rejected(commands, held=[f.command for f in held])
                return ScreenDecision(
                    cleared=False,
                    status="rejected",
                    commands=tuple(
                        CommandDecision(
                            command=f.command,
                            status="rejected",
                            reasons=f.reasons or ("bundle rejected (all-or-nothing, REQ-MVP-015)",),
                            warnings=f.warnings,
                        )
                        for f in findings
                    ),
                    approval_request=approval_request,
                    notice="bundle rejected by the approver — nothing was executed",
                )
            self._audit.log_approved(commands, held=[f.command for f in held])

            # Lock-FIRST (REQ-MVP-035): a lock activated while the approval was
            # pending converts the held commands to non-executable.
            locked = self._check_lock(
                commands, findings, phase="live lock activated during approval (lock-first)"
            )
            if locked is not None:
                return locked

            # Backup rule ③ (REQ-MVP-017): only the RISKY path backs up.
            if self._backup is not None:
                try:
                    self._backup.before_risky_execution()
                except BackupError as error:
                    for command in commands:
                        self._audit.log_blocked(command, reason=f"backup failed: {error}")
                    return ScreenDecision(
                        cleared=False,
                        status="blocked_backup_failed",
                        commands=tuple(
                            CommandDecision(
                                command=f.command, status="blocked", reasons=(str(error),)
                            )
                            for f in findings
                        ),
                        approval_request=approval_request,
                        notice=f"showfile backup failed — execution blocked (fail-safe): {error}",
                    )

        with self._clearances_lock:
            self._clearances[session_key] = Counter(commands)
        return ScreenDecision(
            cleared=True,
            status="cleared",
            commands=tuple(
                CommandDecision(
                    command=f.command, status="cleared", reasons=f.reasons, warnings=f.warnings
                )
                for f in findings
            ),
            approval_request=approval_request,
        )

    # -- pipeline stages ---------------------------------------------------------

    def _observe(self, stage: str) -> None:
        if self._stage_observer is not None:
            self._stage_observer(stage)

    def _check_health(self, commands: list[str]) -> ScreenDecision | None:
        state = self.monitor.state
        if state == HealthMonitor.ONLINE:
            return None
        if state == HealthMonitor.CONSOLE_OFFLINE:
            status = "blocked_console_offline"
            reason = "console offline — new executions are blocked (REQ-MVP-030)"
        else:
            status = "blocked_responder_degraded"
            reason = (
                "responder degraded — result confirmation unavailable; "
                "side-effectful commands are not started (REQ-MVP-031)"
            )
        for command in commands:
            self._audit.log_blocked(command, reason=reason)
        return ScreenDecision(
            cleared=False,
            status=status,
            commands=tuple(
                CommandDecision(command=c, status="blocked", reasons=(reason,)) for c in commands
            ),
            notice=reason,
        )

    def _stage_grammar(self, commands: list[str]) -> list | ScreenDecision:
        self._observe("grammar")
        parsed = []
        failures: dict[str, str] = {}
        for command in commands:
            result = validate(command)
            if result.ok:
                parsed.append(result.parsed)
            else:
                failures[command] = result.reason
        if not failures:
            return parsed
        decisions = []
        for command in commands:
            if command in failures:
                reason = f"grammar: {failures[command]}"
                self._audit.log_blocked(command, reason=reason)
                decisions.append(
                    CommandDecision(command=command, status="blocked", reasons=(reason,))
                )
            else:
                decisions.append(
                    CommandDecision(
                        command=command,
                        status="blocked",
                        reasons=("bundle blocked: another command failed grammar validation",),
                    )
                )
        return ScreenDecision(
            cleared=False,
            status="blocked_grammar",
            commands=tuple(decisions),
            notice="grammar validation failed — block reasons feed the self-correction loop",
        )

    def _stage_classify(self, parsed_commands: list) -> list[_Finding]:
        self._observe("classify")
        findings: list[_Finding] = []
        for parsed in parsed_commands:
            verdict = classify_command(parsed, self._ruleset, reference_types=self._reference_types)
            reasons = list(verdict.reasons)
            warnings: list[str] = []
            hold = verdict.risky
            if verdict.unspecified_target:
                warnings.append(
                    "unspecified-target warning: destructive command without an "
                    "explicit target (REQ-MVP-036b)"
                )
            if verdict.category == "invoking":
                expansion = evaluate_reference(
                    verdict.reference,
                    ruleset=self._ruleset,
                    fetcher=self._body_fetcher,
                    plugin_registry=self._plugin_registry,
                )
                reasons.extend(expansion.reasons)
                if expansion.hold:
                    hold = True
            if parsed.raw in self._unconfirmed:
                hold = True
                reasons.append(
                    "previously unconfirmed execution — automatic resend is "
                    "prohibited (REQ-MVP-032); human approval required to re-attempt"
                )
            findings.append(
                _Finding(
                    command=parsed.raw,
                    hold=hold,
                    reasons=tuple(reasons),
                    warnings=tuple(warnings),
                )
            )
        return findings

    def _check_lock(
        self, commands: list[str], findings: list[_Finding], *, phase: str
    ) -> ScreenDecision | None:
        if not self.lock.is_active:
            return None
        for command in commands:
            self._audit.log_blocked(command, reason=phase)
        proposal = ProposalCard(
            commands=tuple(commands),
            reasons=(f"{phase} — read-only proposal (REQ-MVP-016)",),
        )
        return ScreenDecision(
            cleared=False,
            status="locked",
            commands=tuple(
                CommandDecision(
                    command=f.command, status="proposal", reasons=(phase,), warnings=f.warnings
                )
                for f in findings
            ),
            proposal=proposal,
            notice=f"{phase} — no console sends; proposal card only",
        )

    # -- plugin deployment (M7 — REQ-MVP-019/029) ---------------------------------

    def deploy_plugin_source(self, name: str, lua_source: str) -> ExecutionResult:
        """Send one REVIEWED plugin deployment to the console (M7).

        This is the gate-owned deploy surface — the only production route for
        deployment sends (REQ-MVP-029). Policy (compile + scan + human review)
        lives in :class:`server.deploy.pipeline.DeployPipeline`, which calls
        this ONLY after review approval; this method re-checks the runtime
        safety state at send time (lock/health — same discipline as
        :meth:`_execute_cleared`) and audits the send 1:1 (kind="deploy").
        """
        if self.lock.is_active:
            self._audit.log_blocked(f"deploy:{name}", reason="live lock active (read-only)")
            return ExecutionResult(ok=False, detail="blocked: live lock active (read-only)")
        if self.monitor.executions_blocked:
            reason = f"health: {self.monitor.state}"
            self._audit.log_blocked(f"deploy:{name}", reason=reason)
            return ExecutionResult(ok=False, detail=f"blocked: {reason}")
        outcome = self._console.deploy_plugin(name, lua_source)
        self._audit.log_executed(
            name,
            kind="deploy",
            ok=outcome.status == "ok",
            detail=outcome.detail,
            outcome=outcome.status,
            source_bytes=len(lua_source.encode("utf-8")),
        )
        if outcome.status == "ok":
            return ExecutionResult(ok=True, detail=outcome.detail)
        if outcome.status == "unconfirmed":
            return ExecutionResult(
                ok=False,
                detail=(
                    "execution unconfirmed — the deployment may or may not have "
                    f"reached the console; it will NOT be auto-resent (REQ-MVP-032): "
                    f"{outcome.detail}"
                ),
            )
        return ExecutionResult(ok=False, detail=outcome.detail)

    # -- execution (clearance consumption) ----------------------------------------

    def _execute_cleared(self, command: str) -> ExecutionResult:
        if self.lock.is_active:
            self._audit.log_blocked(command, reason="live lock active (read-only)")
            return ExecutionResult(ok=False, detail="blocked: live lock active (read-only)")
        if self.monitor.executions_blocked:
            reason = f"health: {self.monitor.state}"
            self._audit.log_blocked(command, reason=reason)
            return ExecutionResult(ok=False, detail=f"blocked: {reason}")
        session_key = current_session_key()
        with self._clearances_lock:
            clearances = self._clearances.setdefault(session_key, Counter())
            if clearances[command] <= 0:
                self._audit.log_blocked(command, reason="not cleared by the safety gate")
                return ExecutionResult(
                    ok=False, detail="blocked: command was not cleared by the safety gate"
                )
            clearances[command] -= 1
        outcome = self._console.execute(command)
        self._audit.log_executed(
            command,
            kind="command",
            ok=outcome.status == "ok",
            detail=outcome.detail,
            outcome=outcome.status,
        )
        if outcome.status == "ok":
            return ExecutionResult(ok=True, detail=outcome.detail)
        if outcome.status == "unconfirmed":
            self._remember_unconfirmed(command)
            return ExecutionResult(
                ok=False,
                detail=(
                    "execution unconfirmed — the command may or may not have run on "
                    f"the console; it will NOT be auto-resent (REQ-MVP-032): {outcome.detail}"
                ),
            )
        return ExecutionResult(ok=False, detail=outcome.detail)

    def _remember_unconfirmed(self, command: str) -> None:
        """Record ``command`` as unconfirmed, evicting the oldest entry
        beyond the bounded-LRU cap (see ``@MX:DEBT`` on ``self._unconfirmed``).
        """
        if command in self._unconfirmed:
            self._unconfirmed.move_to_end(command)
        else:
            self._unconfirmed[command] = None
        if len(self._unconfirmed) > _MAX_UNCONFIRMED:
            self._unconfirmed.popitem(last=False)

    def _query_state(self, path: str) -> dict:
        # Audited even on failure: a timed-out query still SENT one OSC
        # request, and the 1:1 send↔audit reconciliation must not lose it.
        try:
            payload = self._console.query_state(path)
        except Exception:
            self._audit.log_executed(path, kind="state_query", ok=False)
            raise
        self._audit.log_executed(path, kind="state_query", ok=True)
        return payload
