"""Deploy pipeline tests (M7 — REQ-MVP-019/027, AC-MVP-010 ①②③ + AC-MVP-018 ①).

The pipeline is the deny-by-default policy sequence for ``deploy_plugin``:

    compile check → destructive scan → human review → gate-owned console
    deploy → plugin-flag registration

Safety asymmetry (Section D): NO deploy without BOTH a compile pass AND an
explicit review approval, via ANY code path — the default review port denies
everything, mirroring the M4 approval model.
"""

from __future__ import annotations

import pytest

from server.deploy.compile import CompileResult, LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.deploy.review import PREVIEW_MAX_CHARS, DenyAllReviewPort, ReviewRequest
from server.orchestrator.ports import ExecutionResult
from server.safety.audit import AuditLog
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset

DESTRUCTIVE_SOURCE = 'local function main()\n    Cmd("Delete Sequence 5")\nend\nreturn main\n'
SAFE_SOURCE = 'local function main()\n    Cmd("Store Group 3")\nend\nreturn main\n'
BROKEN_SOURCE = "function broken( end"


class ScriptedReview:
    """Deterministic ReviewPort — records every request it is shown."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests: list[ReviewRequest] = []

    def request_review(self, request: ReviewRequest) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


class FakeDeployPort:
    """Records gate-bound deploy sends; scriptable outcome."""

    def __init__(self, result: ExecutionResult | None = None):
        self.result = result or ExecutionResult(ok=True, detail="deployed")
        self.deployed: list[tuple[str, str]] = []

    def deploy_plugin_source(self, name: str, lua_source: str) -> ExecutionResult:
        self.deployed.append((name, lua_source))
        return self.result


def _pipeline(tmp_path, **kwargs):
    port = kwargs.pop("deploy_port", None) or FakeDeployPort()
    registry = kwargs.pop("registry", None) or PluginFlagRegistry()
    audit = kwargs.pop("audit", None) or AuditLog(tmp_path / "audit")
    pipeline = DeployPipeline(
        compile_checker=kwargs.pop("compile_checker", None) or LuaCompileChecker(),
        ruleset=kwargs.pop("ruleset", None) or load_ruleset(),
        deploy_port=port,
        registry=registry,
        audit=audit,
        **kwargs,
    )
    return pipeline, port, registry, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestCompileGate:
    def test_compile_failure_blocks_the_deploy(self, tmp_path):
        # AC-MVP-010 ①: compile-failing Lua → deploy blocked, NO deploy
        # attempt, NO review shown (nothing to review yet).
        review = ScriptedReview([True])
        pipeline, port, registry, audit = _pipeline(tmp_path, review_port=review)
        outcome = pipeline.deploy("Cleaner", BROKEN_SOURCE)
        assert outcome.status == "blocked_compile"
        assert outcome.compile_error != ""
        assert port.deployed == []
        assert review.requests == []
        assert registry.lookup("Plugin Cleaner") is None
        assert _events(audit, "deploy_requested") != []
        assert _events(audit, "deploy_blocked") != []

    def test_compile_error_detail_feeds_self_correction(self, tmp_path):
        pipeline, _, _, _ = _pipeline(tmp_path, review_port=ScriptedReview([True]))
        outcome = pipeline.deploy("Cleaner", BROKEN_SOURCE)
        # The structured error text is what the model sees to self-correct.
        assert outcome.compile_error in outcome.detail or outcome.compile_error


class TestReviewGate:
    def test_default_review_port_denies_everything(self, tmp_path):
        # Safety asymmetry: an unwired review channel means NO deploy — the
        # exact fail-safe shape of the M4 DenyAllApprovalPort.
        pipeline, port, registry, _ = _pipeline(tmp_path)
        assert isinstance(DenyAllReviewPort().request_review(None), bool)
        outcome = pipeline.deploy("Cleaner", SAFE_SOURCE)
        assert outcome.status == "review_rejected"
        assert port.deployed == []
        assert registry.lookup("Plugin Cleaner") is None

    def test_review_rejection_voids_the_deploy(self, tmp_path):
        # AC-MVP-010 ②: review not approved → deploy held/voided + audited.
        review = ScriptedReview([False])
        pipeline, port, registry, audit = _pipeline(tmp_path, review_port=review)
        outcome = pipeline.deploy("Cleaner", SAFE_SOURCE)
        assert outcome.status == "review_rejected"
        assert port.deployed == []
        assert registry.lookup("Plugin Cleaner") is None
        assert _events(audit, "deploy_review_rejected") != []
        assert _events(audit, "deployed") == []

    def test_reviewer_sees_scan_result_and_source(self, tmp_path):
        # AC-MVP-010 ③ + REQ-MVP-027: the scan report is explicitly part of
        # what the reviewer is shown, with the compile verdict and source.
        review = ScriptedReview([True])
        pipeline, _, _, _ = _pipeline(tmp_path, review_port=review)
        pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        (request,) = review.requests
        assert request.plugin_name == "Cleaner"
        assert request.compile_ok is True
        assert request.scan.destructive is True
        assert request.scan.findings[0].matched_entry == "Delete"
        assert "Delete Sequence 5" in request.source_preview
        assert request.source_length == len(DESTRUCTIVE_SOURCE)

    def test_source_preview_is_bounded(self, tmp_path):
        review = ScriptedReview([True])
        pipeline, _, _, _ = _pipeline(tmp_path, review_port=review)
        # Above PREVIEW_MAX_CHARS but below the deployment size cap.
        long_source = "-- filler\n" * 500 + SAFE_SOURCE
        pipeline.deploy("Cleaner", long_source)
        (request,) = review.requests
        assert len(request.source_preview) <= PREVIEW_MAX_CHARS
        assert request.source_truncated is True
        assert request.source_length == len(long_source)


class TestApprovedDeploy:
    def test_destructive_plugin_registers_with_the_flag(self, tmp_path):
        # AC-MVP-018 ①: scan shown + "destructive" flag registered on approval.
        review = ScriptedReview([True])
        pipeline, port, registry, audit = _pipeline(tmp_path, review_port=review)
        outcome = pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        assert outcome.status == "deployed"
        assert outcome.destructive is True
        flag = registry.lookup("Plugin Cleaner")
        assert flag is not None and flag.destructive is True
        assert port.deployed == [("Cleaner", DESTRUCTIVE_SOURCE)]
        assert _events(audit, "deploy_review_approved") != []
        assert _events(audit, "deployed") != []

    def test_non_destructive_plugin_registers_unflagged(self, tmp_path):
        review = ScriptedReview([True])
        pipeline, _, registry, _ = _pipeline(tmp_path, review_port=review)
        outcome = pipeline.deploy("Helper", SAFE_SOURCE)
        assert outcome.status == "deployed"
        assert outcome.destructive is False
        flag = registry.lookup("Plugin Helper")
        assert flag is not None and flag.destructive is False

    def test_send_failure_after_approval_keeps_the_flag(self, tmp_path):
        # Safety direction: once approved, the destructive flag is NEVER lost
        # even when the console send fails or is unconfirmed — the plugin MAY
        # exist on the console.
        review = ScriptedReview([True])
        port = FakeDeployPort(ExecutionResult(ok=False, detail="execution unconfirmed — maybe"))
        pipeline, _, registry, audit = _pipeline(tmp_path, review_port=review, deploy_port=port)
        outcome = pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        assert outcome.status == "deploy_failed"
        flag = registry.lookup("Plugin Cleaner")
        assert flag is not None and flag.destructive is True
        assert _events(audit, "deployed") == []  # never claim an unconfirmed deploy

    def test_gate_refusal_is_reported_as_blocked(self, tmp_path):
        # A lock/health refusal from the gate surfaces as "blocked" (Korean
        # rendering happens at the chat surface).
        review = ScriptedReview([True])
        port = FakeDeployPort(ExecutionResult(ok=False, detail="blocked: live lock active"))
        pipeline, _, _, _ = _pipeline(tmp_path, review_port=review, deploy_port=port)
        outcome = pipeline.deploy("Cleaner", SAFE_SOURCE)
        assert outcome.status == "blocked"
        assert "live lock" in outcome.detail


class TestInputValidation:
    @pytest.mark.parametrize("name", ["", "   ", "a" * 65, 'bad"name', "line\nbreak"])
    def test_invalid_plugin_name_is_rejected(self, tmp_path, name):
        pipeline, port, _, _ = _pipeline(tmp_path, review_port=ScriptedReview([True]))
        outcome = pipeline.deploy(name, SAFE_SOURCE)
        assert outcome.status == "blocked_input"
        assert port.deployed == []

    def test_oversized_source_is_rejected_before_compile(self, tmp_path):
        pipeline, port, _, audit = _pipeline(
            tmp_path, review_port=ScriptedReview([True]), max_source_bytes=64
        )
        outcome = pipeline.deploy("Cleaner", SAFE_SOURCE + "-- pad\n" * 20)
        assert outcome.status == "blocked_input"
        assert port.deployed == []
        assert _events(audit, "deploy_blocked") != []


class TestAuditTrail:
    def test_full_approved_flow_audit_sequence(self, tmp_path):
        review = ScriptedReview([True])
        pipeline, _, _, audit = _pipeline(tmp_path, review_port=review)
        pipeline.deploy("Cleaner", DESTRUCTIVE_SOURCE)
        names = [e["event"] for e in audit.iter_events()]
        assert names == ["deploy_requested", "deploy_review_approved", "deployed"]
        deployed = _events(audit, "deployed")[0]
        assert deployed["plugin"] == "Cleaner"
        assert deployed["destructive"] is True

    def test_compile_result_is_rechecked_before_send(self, tmp_path):
        # Defense in depth: a compile checker claiming failure can never be
        # overridden downstream — the pipeline refuses to review or send.
        class BrokenChecker:
            def check(self, lua_source, *, chunk_name="deploy"):
                return CompileResult(ok=False, error="always broken")

        review = ScriptedReview([True])
        pipeline, port, _, _ = _pipeline(
            tmp_path, review_port=review, compile_checker=BrokenChecker()
        )
        outcome = pipeline.deploy("Cleaner", SAFE_SOURCE)
        assert outcome.status == "blocked_compile"
        assert review.requests == []
        assert port.deployed == []
