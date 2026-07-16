"""Deploy pipeline — the deny-by-default policy sequence (M7, REQ-MVP-019/027).

    deploy_plugin(name, lua_source)
      → input validation (name shape, source size)
      → pcall compile check        fail → structured error (self-correction)
      → destructive Cmd() scan     (always — the reviewer-assist signal)
      → human review gate          reject/deny → deploy voided (audited)
      → plugin-flag registration   (on approval — REQ-MVP-027)
      → gate-owned console deploy  (REQ-MVP-029 — the ONLY console route)

Safety asymmetry (design.md §D): no deploy without BOTH a compile pass AND an
explicit review approval — the default review port denies everything. The
destructive flag is registered ON APPROVAL, before the console send, and is
never rolled back on a failed/unconfirmed send: the plugin MAY exist on the
console, and losing the flag would silently disarm the M4 invocation gate.

Audit events (conservative additive kinds, AC-MVP-006 4-type reconciliation
untouched): deploy_requested / deploy_blocked / deploy_review_approved /
deploy_review_rejected / deployed. The console send itself is audited by the
gate as an ``executed`` event (kind="deploy") for the 1:1 reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.deploy.compile import CompileResult
from server.deploy.review import DenyAllReviewPort, ReviewPort, build_review_request
from server.deploy.scan import ScanReport, scan_lua_source
from server.orchestrator.ports import ExecutionResult
from server.safety.ruleset import SafetyRuleset

# Wire-size guard: the source rides ONE percent-encoded UDP command line
# (encoding inflates it further). ASSUMPTION (onPC-unverified): MA3's OSC
# input accepts command lines of this order; calibrate at M6.
DEFAULT_MAX_SOURCE_BYTES = 16000

MAX_PLUGIN_NAME_CHARS = 64


class CompileChecker(Protocol):
    """The pcall compile harness surface (server.deploy.compile implements)."""

    def check(self, lua_source: str, *, chunk_name: str = "deploy") -> CompileResult: ...


class PluginDeployPort(Protocol):
    """Gate-owned console deployment surface (REQ-MVP-029)."""

    def deploy_plugin_source(self, name: str, lua_source: str) -> ExecutionResult: ...


class FlagRegistry(Protocol):
    """The M4 plugin-flag registry surface consumed at deploy time."""

    def register(self, reference: str, *, destructive: bool) -> None: ...


class AuditSink(Protocol):
    """Any-event audit surface (server.safety.audit.AuditLog implements)."""

    def record(self, event: dict) -> None: ...


@dataclass(frozen=True)
class DeployOutcome:
    """One deploy_plugin request's outcome (chat-surface + model feedback)."""

    status: str  # "deployed" | "blocked_input" | "blocked_compile"
    #             | "review_rejected" | "blocked" | "deploy_failed"
    detail: str = ""
    destructive: bool = False
    compile_error: str = ""
    scan: ScanReport | None = None


def _invalid_name_reason(name: str) -> str | None:
    if not isinstance(name, str) or not name.strip():
        return "plugin name must be a non-empty string"
    if len(name) > MAX_PLUGIN_NAME_CHARS:
        return f"plugin name exceeds {MAX_PLUGIN_NAME_CHARS} characters"
    if any(ord(ch) < 32 for ch in name):
        return "plugin name must not contain control characters"
    if '"' in name:
        return "plugin name must not contain a double quote"
    return None


class DeployPipeline:
    """REQ-MVP-019: deploy ONLY when compile AND human review both pass."""

    def __init__(
        self,
        *,
        compile_checker: CompileChecker,
        ruleset: SafetyRuleset,
        deploy_port: PluginDeployPort,
        registry: FlagRegistry,
        audit: AuditSink,
        review_port: ReviewPort | None = None,
        max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    ) -> None:
        self._compile = compile_checker
        self._ruleset = ruleset
        self._deploy_port = deploy_port
        self._registry = registry
        self._audit = audit
        self._review = review_port or DenyAllReviewPort()
        self._max_source_bytes = max_source_bytes

    # @MX:ANCHOR: [AUTO] the ONE deploy policy path — the deploy_plugin tool,
    #   the web review flow, and every M7 AC test route deployments through here
    # @MX:REASON: REQ-MVP-019 requires compile+review to be unbypassable; a
    #   second deploy sequence would fork the deny-by-default policy (fan_in >= 3)
    def deploy(self, name: str, lua_source: str) -> DeployOutcome:
        """Run one deployment through compile → scan → review → console."""
        source_bytes = len(lua_source.encode("utf-8")) if isinstance(lua_source, str) else 0
        self._audit.record(
            {"event": "deploy_requested", "plugin": str(name), "source_bytes": source_bytes}
        )

        reason = _invalid_name_reason(name)
        if reason is None and not isinstance(lua_source, str):
            reason = "lua_source must be a string"
        if reason is None and source_bytes > self._max_source_bytes:
            reason = (
                f"lua source is {source_bytes} bytes — exceeds the "
                f"{self._max_source_bytes}-byte deployment limit"
            )
        if reason is not None:
            self._audit.record({"event": "deploy_blocked", "plugin": str(name), "reason": reason})
            return DeployOutcome(status="blocked_input", detail=reason)

        compiled = self._compile.check(lua_source, chunk_name=name)
        if not compiled.ok:
            reason = f"lua compile failed: {compiled.error}"
            self._audit.record({"event": "deploy_blocked", "plugin": name, "reason": reason})
            return DeployOutcome(
                status="blocked_compile", detail=reason, compile_error=compiled.error
            )

        scan = scan_lua_source(lua_source, self._ruleset)
        request = build_review_request(name, lua_source, compile_ok=True, scan=scan)
        approved = self._review.request_review(request)
        if not approved:
            self._audit.record(
                {
                    "event": "deploy_review_rejected",
                    "plugin": name,
                    "destructive": scan.destructive,
                }
            )
            return DeployOutcome(
                status="review_rejected",
                detail="deployment was not approved by the reviewer",
                destructive=scan.destructive,
                scan=scan,
            )
        self._audit.record(
            {"event": "deploy_review_approved", "plugin": name, "destructive": scan.destructive}
        )

        # REQ-MVP-027: register the scan verdict ON APPROVAL — before the send,
        # never rolled back (an unconfirmed send may still have deployed).
        self._registry.register(f"Plugin {name}", destructive=scan.destructive)

        result = self._deploy_port.deploy_plugin_source(name, lua_source)
        if not result.ok:
            status = "blocked" if result.detail.startswith("blocked:") else "deploy_failed"
            return DeployOutcome(
                status=status, detail=result.detail, destructive=scan.destructive, scan=scan
            )
        self._audit.record(
            {
                "event": "deployed",
                "plugin": name,
                "destructive": scan.destructive,
                "detail": result.detail,
            }
        )
        return DeployOutcome(
            status="deployed", detail=result.detail, destructive=scan.destructive, scan=scan
        )
