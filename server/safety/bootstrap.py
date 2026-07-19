"""Gate-owned console-stack composition (M5 — REQ-MVP-029 preserved).

Production needs exactly ONE place that constructs the OSC bridge, the console
link, and the safety gate. That place lives HERE, inside ``server/safety`` —
the only production package the AC-MVP-019 import-boundary architecture test
allows to reach the OSC send surface. The web layer (``server/web``) receives
the finished :class:`ConsoleStack` and never imports the bridge.

Composition choices:

- The expand-or-hold body fetcher rides the GATE's state port (audited —
  every body-fetch state query lands in the 1:1 send↔audit reconciliation).
- The session-start backup (REQ-MVP-017 rule ①) is ATTEMPTED at boot; a
  failure is reported on the stack, never raised — REQ-MVP-034 blocks
  executions, not the server process.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from server.bridge.osc import BridgeConfig, OscBridge
from server.safety.audit import DEFAULT_AUDIT_DIR, AuditLog
from server.safety.backup import DEFAULT_INTERVAL_SECONDS, BackupError, BackupManager
from server.safety.console import ConsoleLink, LinkTimeouts, StateBodyFetcher
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import SafetyRuleset, load_ruleset


@dataclass
class ConsoleStack:
    """The composed production console stack (gate + audited transport)."""

    gate: SafetyGate
    audit: AuditLog
    monitor: HealthMonitor
    link: ConsoleLink
    backup: BackupManager
    receive_port: int
    # M7 deploy seam: the pipeline registers plugin flags into the SAME
    # registry the gate's invocation path consults, against the SAME ruleset.
    registry: PluginFlagRegistry
    ruleset: SafetyRuleset
    _stop: Callable[[], None]
    session_backup_ok: bool = False
    session_backup_detail: str = "session-start backup not attempted"

    def attempt_session_backup(self) -> bool:
        """Attempt the REQ-MVP-017 rule-① session-start backup (never raises).

        A failure is recorded on the stack — REQ-MVP-034 blocks EXECUTIONS,
        not the server process.
        """
        try:
            self.gate.start_session()
        except BackupError as error:
            self.session_backup_ok = False
            self.session_backup_detail = str(error)
        else:
            self.session_backup_ok = True
            self.session_backup_detail = "session-start backup confirmed"
        return self.session_backup_ok

    def stop(self) -> None:
        """Shut the bridge down (idempotent)."""
        self._stop()


def build_console_stack(
    *,
    send_host: str = "127.0.0.1",
    send_port: int = 8000,
    receive_host: str = "127.0.0.1",
    receive_port: int = 9000,
    approval_port=None,
    audit_dir: Path | str = DEFAULT_AUDIT_DIR,
    timeouts: LinkTimeouts | None = None,
    backup_interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    attempt_session_backup: bool = True,
    plugin_import_dir: Path | str | None = None,
) -> ConsoleStack:
    """Compose bridge + link + gate; the caller owns ``stop()``.

    ``plugin_import_dir``: when set (co-located server + console), plugin
    deployments use the working file+Import path via that onPC plugins-library
    folder; when None, the OSC ``deploy`` verb is used (remote fallback).
    """
    monitor = HealthMonitor()
    link = ConsoleLink(timeouts=timeouts, monitor=monitor, import_dir=plugin_import_dir)
    bridge = OscBridge(
        BridgeConfig(
            send_host=send_host,
            send_port=send_port,
            receive_host=receive_host,
            receive_port=receive_port,
        ),
        consumer=link,
    )
    bridge.start()
    link.bind_send(bridge.send_command)
    audit = AuditLog(audit_dir)
    registry = PluginFlagRegistry()
    ruleset = load_ruleset()
    gate = SafetyGate(
        console=link,
        audit=audit,
        ruleset=ruleset,
        approval_port=approval_port,
        monitor=monitor,
        plugin_registry=registry,
        # Late-bound closure: body fetches ride the gate's AUDITED state port
        # (AC-MVP-019 ② — the fetch query lands in the send↔audit reconciliation).
        body_fetcher=StateBodyFetcher(query=lambda path: gate.state_port.query_state(path)),
    )
    backup = gate.use_showfile_backup(interval_seconds=backup_interval_seconds)

    stopped = False

    def stop() -> None:
        nonlocal stopped
        if not stopped:
            stopped = True
            bridge.stop()

    stack = ConsoleStack(
        gate=gate,
        audit=audit,
        monitor=monitor,
        link=link,
        backup=backup,
        receive_port=bridge.receive_port,
        registry=registry,
        ruleset=ruleset,
        _stop=stop,
    )
    if attempt_session_backup:
        # Production: the console's reply port is fixed configuration, so the
        # boot-time attempt is meaningful. Tests with an ephemeral reply port
        # wire it first, then call stack.attempt_session_backup().
        stack.attempt_session_backup()
    return stack
