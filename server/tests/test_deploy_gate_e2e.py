"""Deploy → invocation E2E (M7 — AC-MVP-018 full loop, REQ-MVP-027/028).

The M7 pipeline POPULATES the M4 plugin-flag registry at deploy time; the
EXISTING M4 invocation gate then enforces per-invocation human approval for
destructive-flagged plugins with no further wiring. This file proves the
handshake end to end on one shared registry + gate:

    deploy (approved, destructive) → invoke → held for approval every time
    deploy (approved, safe)        → invoke → passes, audited
"""

from __future__ import annotations

from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset

from .test_deploy_pipeline import DESTRUCTIVE_SOURCE, SAFE_SOURCE, ScriptedReview
from .test_deploy_transport import DeployableFakeConsole
from .test_safety_gate import ScriptedApproval


def _stack(tmp_path, *, review_decisions=(True,), approval_decisions=()):
    """One shared gate + registry + pipeline over a deployable fake console."""
    console = DeployableFakeConsole()
    audit = AuditLog(tmp_path / "audit")
    registry = PluginFlagRegistry()
    ruleset = load_ruleset()
    approval = ScriptedApproval(decisions=list(approval_decisions))
    gate = SafetyGate(
        console=console,
        audit=audit,
        ruleset=ruleset,
        approval_port=approval,
        plugin_registry=registry,
    )
    review = ScriptedReview(list(review_decisions))
    pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=ruleset,
        deploy_port=gate,
        registry=registry,
        audit=audit,
        review_port=review,
    )
    return pipeline, gate, console, audit, approval, review


class TestDestructiveDeployThenInvoke:
    def test_every_invocation_of_a_deployed_destructive_plugin_needs_approval(self, tmp_path):
        # AC-MVP-018 E2E: deploy destructive (approved) → invocation held.
        pipeline, gate, console, _, approval, _ = _stack(tmp_path, approval_decisions=[False, True])
        outcome = pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        assert outcome.status == "deployed"
        assert console.deployed == [("Cleaner", DESTRUCTIVE_SOURCE)]

        # 1st invocation: approver denies → nothing reaches the wire.
        decision = gate.screen(['Plugin "Cleaner"'])
        assert decision.cleared is False
        assert decision.status == "rejected"
        assert console.executed == []
        assert len(approval.requests) == 1
        reasons = " ".join(decision.commands[0].reasons)
        assert "destructive-flagged plugin" in reasons

        # 2nd invocation: approver approves → executes, approval asked AGAIN
        # (REQ-MVP-028: EVERY invocation needs approval — no caching).
        decision = gate.screen(['Plugin "Cleaner"'])
        assert decision.cleared is True
        gate.execution_port.execute('Plugin "Cleaner"')
        assert console.executed == ['Plugin "Cleaner"']
        assert len(approval.requests) == 2

    def test_rejected_review_leaves_the_invocation_gate_unregistered(self, tmp_path):
        # A review-rejected plugin never registers: its invocation falls into
        # expand-or-hold (unverifiable → held) — the M4 safe default.
        pipeline, gate, console, _, approval, _ = _stack(tmp_path, review_decisions=[False])
        outcome = pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        assert outcome.status == "review_rejected"
        decision = gate.screen(['Plugin "Cleaner"'])
        assert decision.cleared is False  # held (unverifiable) + deny-all default
        assert console.executed == []


class TestSafeDeployThenInvoke:
    def test_registered_non_destructive_plugin_passes_audited(self, tmp_path):
        pipeline, gate, console, audit, approval, _ = _stack(tmp_path)
        outcome = pipeline.deploy("Helper", SAFE_SOURCE)
        assert outcome.status == "deployed"
        assert outcome.destructive is False

        decision = gate.screen(['Plugin "Helper"'])
        assert decision.cleared is True
        assert approval.requests == []  # no approval needed (M4 behavior)
        gate.execution_port.execute('Plugin "Helper"')
        assert console.executed == ['Plugin "Helper"']
        executed = [
            e for e in audit.iter_events() if e["event"] == "executed" and e["kind"] == "command"
        ]
        assert [e["command"] for e in executed] == ['Plugin "Helper"']
