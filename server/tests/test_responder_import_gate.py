"""App-issued ``Import Plugin`` transits the single safety gate (AC-DEPLOY-017).

SAFETY-3 regression guard. Provisioning copies plugin files on the filesystem
(off-gate), but the ONE console command it may issue as part of the working
"deploy verb → file+Import" mechanism — ``Import Plugin`` — MUST transit the
SPEC-COPILOT-MVP-001 single safety gate (REQ-MVP-029) and be audit-logged 1:1.

This drives a full DeployPipeline → SafetyGate.deploy_plugin_source → the REAL
``ConsoleLink`` file+Import path over an in-process recording console that
captures the actual ``Import Plugin`` wire command. It proves:

  ① the ``Import Plugin`` OSC send transits the gate (gate-pass audit record);
  ② gate-pass record ↔ audit log correspond 1:1 (one deploy → one ``deploy``
     executed audit event, exactly one ``Import Plugin`` on the wire);
  ③ zero gate-bypassing ``Import Plugin`` sends — a live-locked gate blocks the
     send before it reaches the wire (blocked audit, zero wire sends).

If a future change routed an app-issued ``Import Plugin`` around the gate, ③
(and the import-boundary architecture test, AC-MVP-019) would fail.
"""

from __future__ import annotations

import re

from server.bridge.osc import FEEDBACK_ADDRESS, STATE_ADDRESS, FeedbackMessage
from server.bridge.protocol import encode_payload
from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.safety.audit import AuditLog
from server.safety.console import ConsoleLink, LinkTimeouts
from server.safety.gate import SafetyGate
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset

from .test_deploy_pipeline import SAFE_SOURCE, ScriptedReview
from .test_safety_gate import ScriptedApproval

_RESPONDER = "CopilotResponder"
_REQUEST = re.compile(r'^Plugin "CopilotResponder" "(ping|state|exec) (\S+)(?: (.*))?"$')


class RecordingConsole:
    """In-process ConsoleLink send target.

    Parses each M2-wrapped wire command, records it, and synchronously delivers a
    matching feedback reply so ``ConsoleLink`` round-trips complete without UDP or
    timeouts. Tracks imported plugin names so the file+Import confirm query sees
    the new plugin in the pool.
    """

    def __init__(self, link: ConsoleLink) -> None:
        self._link = link
        self.exec_commands: list[str] = []
        self.raw_unwrapped: list[str] = []
        self._pool: list[str] = []

    @property
    def import_plugin_sends(self) -> list[str]:
        return [c for c in self.exec_commands if c.startswith("Import Plugin")]

    def send(self, wire: str) -> None:
        match = _REQUEST.match(wire)
        if match is None:
            self.raw_unwrapped.append(wire)
            return
        kind, rid, rest = match.groups()
        if kind == "ping":
            self._reply(FEEDBACK_ADDRESS, {"v": 1, "kind": "pong", "id": rid, "ok": True})
        elif kind == "exec":
            self.exec_commands.append(rest)
            if rest and rest.startswith("Import Plugin"):
                self._pool.append(_RESPONDER)  # the import lands the plugin in the pool
            self._reply(
                FEEDBACK_ADDRESS,
                {"v": 1, "kind": "result", "id": rid, "ok": True, "result": "OK"},
            )
        else:  # state
            children = [{"name": name, "i": i} for i, name in enumerate(self._pool, start=1)]
            self._reply(
                STATE_ADDRESS,
                {
                    "v": 1,
                    "kind": "state",
                    "id": rid,
                    "ok": True,
                    "path": rest,
                    "children": children,
                },
            )

    def _reply(self, address: str, payload: dict) -> None:
        self._link.deliver(FeedbackMessage(address=address, args=(encode_payload(payload),)))


def _stack(tmp_path, *, review_decision=True):
    """Full deploy stack over a REAL ConsoleLink (file+Import) + recording console."""
    link = ConsoleLink(
        timeouts=LinkTimeouts(exec_confirm_seconds=2.0, state_query_seconds=2.0),
        import_dir=tmp_path / "plugins",
    )
    console = RecordingConsole(link)
    link.bind_send(console.send)

    audit = AuditLog(tmp_path / "audit")
    registry = PluginFlagRegistry()
    ruleset = load_ruleset()
    gate = SafetyGate(
        console=link,
        audit=audit,
        ruleset=ruleset,
        approval_port=ScriptedApproval(decisions=[]),
        plugin_registry=registry,
    )
    pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=ruleset,
        deploy_port=gate,
        registry=registry,
        audit=audit,
        review_port=ScriptedReview([review_decision]),
    )
    return pipeline, gate, console, audit


def _deploy_events(audit: AuditLog) -> list[dict]:
    return [e for e in audit.iter_events() if e["event"] == "executed" and e["kind"] == "deploy"]


class TestImportPluginTransitsTheGate:
    def test_import_plugin_send_transits_gate_and_is_audited_one_to_one(self, tmp_path):
        # ① + ②: an approved deploy issues exactly one Import Plugin on the wire,
        # and it maps 1:1 to a single gate-pass "deploy" audit record.
        pipeline, _gate, console, audit = _stack(tmp_path)

        outcome = pipeline.deploy(_RESPONDER, SAFE_SOURCE)
        assert outcome.status == "deployed"

        # Exactly one Import Plugin actually reached the wire.
        assert len(console.import_plugin_sends) == 1
        # Nothing bypassed the M2 exec wrap (every wire command was gate-shaped).
        assert console.raw_unwrapped == []

        # 1:1 — one gate-pass "deploy" audit record for the one deploy send.
        deploy_events = _deploy_events(audit)
        assert len(deploy_events) == 1
        assert deploy_events[0]["command"] == _RESPONDER
        assert deploy_events[0]["ok"] is True

        # The Import Plugin count equals the gate-pass audit-record count (1:1).
        assert len(console.import_plugin_sends) == len(deploy_events)

    def test_live_locked_gate_blocks_the_import_plugin_send(self, tmp_path):
        # ③: with the live lock ON, the Import Plugin never reaches the wire —
        # it is blocked at the gate (REQ-MVP-016), proving no ungated send path.
        pipeline, gate, console, audit = _stack(tmp_path)
        gate.lock.activate()

        outcome = pipeline.deploy(_RESPONDER, SAFE_SOURCE)
        assert outcome.status == "blocked"

        # Zero Import Plugin sends on the wire.
        assert console.import_plugin_sends == []
        # No successful deploy audit record; a blocked record names the lock.
        assert _deploy_events(audit) == []
        blocked = [e for e in audit.iter_events() if e["event"] == "blocked"]
        assert any("lock" in e["reason"] for e in blocked)

    def test_no_ungated_import_plugin_send_across_the_deploy(self, tmp_path):
        # The number of Import Plugin wire sends never exceeds the number of
        # gate-pass deploy audit records — no send escapes the 1:1 accounting.
        pipeline, _gate, console, audit = _stack(tmp_path)
        pipeline.deploy(_RESPONDER, SAFE_SOURCE)

        assert len(console.import_plugin_sends) == len(_deploy_events(audit))
