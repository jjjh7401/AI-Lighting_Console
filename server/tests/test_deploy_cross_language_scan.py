"""SAFETY-2 cross-language dual scan (M7.3 — AC-DEPLOY-027, REQ-DEPLOY-023~024).

The Stage-1 guards (``test_architecture.py`` import boundary +
``test_deploy_safety_invariants.py`` AST allowlist) see **Python only**. The
Stage-2 shell adds a Rust/Tauri surface that can reach ``127.0.0.1:<console
port>`` with a raw UDP socket without importing any Python module — invisible to
both. AC-DEPLOY-027 closes that blind spot with two layers, each of which must
be **non-vacuous** (a scan that examined nothing is a FAIL, never a PASS):

Layer ① — Rust deny-all static scan (``packaging/rust_scan.py``)
    ``src-tauri/**/*.rs`` + ``Cargo.toml`` + ``Cargo.lock`` (+ ``capabilities/
    *.json``) scanned with an EMPTY allowlist. An absent or zero-file tree is
    ``blocked`` (FAIL), never a pass, and every result carries ``files_scanned``
    so a 0-file scan can never masquerade as 0 violations.

    ``src-tauri/`` does not exist until M7.4, so the MECHANISM is proven **now**
    against committed positive-control (rogue) and negative-control (clean)
    fixture trees under ``server/tests/fixtures/rust_scan/``. The REAL-tree gate
    is wired here too and flips from skipped to REQUIRED the moment M7.4 creates
    ``src-tauri/`` — grep ``PENDING-M7.4`` for the pending state.

Layer ② — wire-level packet sink (``packaging/wire_sink.py``)
    A UDP sink bound to the **actual configured send_port resolved from
    effective settings** (NOT the hardcoded 8000 default — binding the default
    while the app sends elsewhere yields a vacuous empty capture) records every
    datagram and reconciles it 1:1 against the gate's audit ``executed`` log.
    Fail-closed on any observed-but-unaudited sender, and a **positive
    observation** (>= 1 datagram captured AND reconciled) is REQUIRED so an
    empty capture cannot satisfy "no unenumerated sends".

Layer ③ — Tauri v2 capabilities: ``src-tauri/capabilities/*.json`` does not
    exist yet either. The scanner already reads capability files (network-plugin
    permissions are violations), so the check activates with the scaffold; the
    concrete authoring obligation is recorded in progress.md §E.2 (M7.4).
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "rust_scan"

# The Layer ①/② implementations live in packaging/ (NOT under server/): they
# create raw sockets and are deployment tooling, not server production code —
# putting them under server/ would collide with the AST send-surface allowlist
# in test_deploy_safety_invariants.py. Same sys.path idiom the packaged-E2E
# host script uses.
sys.path.insert(0, str(PROJECT_ROOT / "packaging"))

from rust_scan import (  # noqa: E402
    SRC_TAURI_DIR,
    scan_rust_tree,
)
from wire_sink import (  # noqa: E402
    WirePacketSink,
    parse_datagram,
    reconcile,
)

# @MX:ANCHOR: [AUTO] PENDING-M7.4 — the real-tree Layer ① gate is dormant only
#   while src-tauri/ is absent; it becomes REQUIRED the moment M7.4 scaffolds it.
# @MX:REASON: a silently-skipped security gate is the exact failure mode
#   AC-DEPLOY-027 exists to prevent — the auto-flipping state test below runs
#   ALWAYS and asserts whichever half applies, so the flip cannot be forgotten.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
M74_PENDING_REASON = (
    "PENDING-M7.4: src-tauri/ does not exist yet (M7.3 must not scaffold it). "
    "This deny-all gate flips from skipped to REQUIRED the moment M7.4 creates "
    "src-tauri/ — AC-DEPLOY-027 Layer ①. Greppable marker: PENDING-M7.4."
)


# ----------------------------------------------------------------- Layer ① fixtures


class TestLayer1RogueFixtureIsFlagged:
    """Positive control (MANDATORY CI fixture, not prose) — the scanner FAILS
    on a committed rogue tree. If this stops flagging, Layer ① is defeated."""

    def test_rogue_rust_source_raw_udp_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue")
        assert result.blocked is False, "the rogue fixture tree exists — not a blocked scan"
        assert result.files_scanned > 0
        assert result.ok is False, "the rogue tree passed a DENY-ALL scan"
        markers = {v.marker for v in result.violations}
        assert {"udp_socket", "std_net", "socket_send_to", "loopback_literal"} <= markers
        assert any(v.path.endswith("src/main.rs") for v in result.violations)

    def test_rogue_console_port_literal_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue")
        assert "console_port_literal" in {v.marker for v in result.violations}

    def test_rogue_direct_osc_crate_dependency_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue")
        offenders = {v.detail for v in result.violations if v.marker == "denied_crate_direct"}
        assert any("rosc" in d for d in offenders), offenders

    def test_rogue_direct_raw_socket_crate_dependency_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue")
        offenders = {v.detail for v in result.violations if v.marker == "denied_crate_direct"}
        assert any("socket2" in d for d in offenders), offenders


class TestLayer1TransitiveLockfileScan:
    """The manifest scan must reject OSC/raw-socket crates that arrive only as
    TRANSITIVE Cargo.lock entries — a rogue crate need never be a direct dep."""

    def test_transitive_osc_crate_in_cargo_lock_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue_lock")
        assert result.blocked is False
        assert result.ok is False, "a transitive OSC crate passed the lockfile scan"
        lock_hits = [v for v in result.violations if v.marker == "denied_crate_transitive"]
        assert lock_hits, result.violations
        assert any("nannou_osc" in v.detail for v in lock_hits)
        assert all(v.path.endswith("Cargo.lock") for v in lock_hits)

    def test_benign_transitive_crates_are_not_flagged(self):
        # Tauri legitimately pulls socket2/mio/tokio TRANSITIVELY (via tokio and
        # hyper). Denying those in Cargo.lock would make the gate unpassable at
        # M7.4; they are denied only as DIRECT dependencies (the shell's own
        # choice). The clean fixture's lock carries them and must still pass.
        result = scan_rust_tree(FIXTURES / "clean")
        transitive = [v for v in result.violations if v.marker == "denied_crate_transitive"]
        assert transitive == [], transitive


class TestLayer1CleanFixturePasses:
    """Negative control — a legitimate Tauri shell (sidecar spawn, window,
    tray) needs ZERO raw UDP to the console and must pass the deny-all scan."""

    def test_clean_tree_passes_and_is_not_vacuous(self):
        result = scan_rust_tree(FIXTURES / "clean")
        assert result.blocked is False, result.blocked_reason
        assert result.violations == (), result.violations
        assert result.ok is True
        assert result.files_scanned > 0, "clean PASS on a 0-file scan is vacuous"
        assert result.rust_files_scanned > 0
        assert result.manifest_files_scanned > 0

    def test_comment_mentioning_a_marker_does_not_false_positive(self):
        # The clean fixture's main.rs DISCLAIMS raw sockets in a comment ("no
        # UdpSocket ... anywhere"). Comments are stripped before marker matching
        # (string literals are NOT), mirroring the Python AST scan's prose
        # tolerance in test_deploy_safety_invariants.py.
        source = (FIXTURES / "clean" / "src" / "main.rs").read_text(encoding="utf-8")
        assert "UdpSocket" in source, "fixture lost its prose disclaimer"
        assert scan_rust_tree(FIXTURES / "clean").ok is True

    def test_marker_inside_a_string_literal_is_still_flagged(self):
        # Comment stripping must be string-aware: a loopback literal hidden in a
        # URL string ("http://127.0.0.1:8000") must NOT be swallowed by the
        # "//" line-comment rule — that would be a fail-OPEN stripper.
        from rust_scan import scan_rust_source

        hits = scan_rust_source('let url = "http://127.0.0.1:8000/x";\n', "src/hidden.rs")
        assert {"loopback_literal", "console_port_literal"} <= {h.marker for h in hits}


class TestLayer1CapabilityScan:
    """Layer ③ hook — capability JSON is scanned as soon as it exists; a
    network-plugin permission is a violation, sidecar shell scope is not."""

    def test_network_plugin_permission_is_flagged(self):
        result = scan_rust_tree(FIXTURES / "rogue_capability")
        hits = [v for v in result.violations if v.marker == "denied_capability"]
        assert hits, result.violations
        assert any("http:" in v.detail for v in hits)

    def test_clean_sidecar_only_capability_passes(self):
        result = scan_rust_tree(FIXTURES / "clean")
        assert result.capability_files_scanned > 0, "clean fixture lost its capability file"
        assert [v for v in result.violations if v.marker == "denied_capability"] == []


class TestLayer1FailsClosedOnAnEmptyOrAbsentTree:
    """0 files scanned is FAIL(blocked), never 'PASS, 0 violations found'."""

    def test_absent_tree_is_blocked_not_passed(self, tmp_path):
        result = scan_rust_tree(tmp_path / "does-not-exist")
        assert result.blocked is True
        assert result.ok is False, "an absent tree must not report a pass"
        assert result.files_scanned == 0
        assert "does not exist" in result.blocked_reason

    def test_empty_tree_is_blocked_not_passed(self, tmp_path):
        empty = tmp_path / "src-tauri"
        empty.mkdir()
        result = scan_rust_tree(empty)
        assert result.blocked is True
        assert result.ok is False
        assert result.files_scanned == 0
        assert "no scannable files" in result.blocked_reason

    def test_tree_with_only_ignored_build_output_is_blocked(self, tmp_path):
        # target/ is build output — scanning it would inflate files_scanned and
        # let a genuinely empty source tree fake a non-vacuous scan.
        root = tmp_path / "src-tauri"
        (root / "target" / "debug").mkdir(parents=True)
        (root / "target" / "debug" / "build.rs").write_text("use std::net::UdpSocket;\n")
        result = scan_rust_tree(root)
        assert result.blocked is True
        assert result.files_scanned == 0


class TestLayer1RealSrcTauriGate:
    """The REAL-tree gate. Exactly one of the two branches applies, ALWAYS."""

    def test_real_tree_gate_state_is_accurate(self):
        # Auto-flipping: while src-tauri/ is absent this asserts fail-closed
        # blocking (PENDING-M7.4); once M7.4 scaffolds it, the same test starts
        # asserting the deny-all gate. It can never silently pass unexamined.
        result = scan_rust_tree(SRC_TAURI_DIR)
        if not SRC_TAURI_DIR.exists():
            assert result.blocked is True, "absent src-tauri/ must block, not pass"
            assert result.files_scanned == 0
            assert result.ok is False
        else:
            assert result.blocked is False, f"PENDING-M7.4 flip: {result.blocked_reason}"
            assert result.files_scanned > 0
            assert result.violations == (), result.violations

    @pytest.mark.skipif(not SRC_TAURI_DIR.exists(), reason=M74_PENDING_REASON)
    def test_real_src_tauri_tree_passes_the_deny_all_scan(self):
        result = scan_rust_tree(SRC_TAURI_DIR)
        assert result.ok is True, result.violations
        assert result.rust_files_scanned > 0
        assert result.capability_files_scanned > 0, (
            "M7.4 obligation: src-tauri/capabilities/*.json must deny all network "
            "plugins and scope tauri-plugin-shell to sidecar spawn only"
        )


# ----------------------------------------------------------------- Layer ② wire sink


@pytest.fixture()
def sink():
    """A UDP sink on an OS-assigned loopback port (the stand-in console input)."""
    with WirePacketSink(port=0) as s:
        yield s


@pytest.fixture()
def configured_send_port(tmp_path, sink):
    """The send port as the app resolves it: through effective settings.

    Deliberately NOT the hardcoded 8000 default — audit defect D3 was binding
    the default while the app sends elsewhere, which yields an empty capture
    that vacuously "proves" no unenumerated sends.
    """
    from server.deploy.settings import DEFAULT_CONSOLE_PORT, resolve_effective_settings

    user_file = tmp_path / "settings.toml"
    user_file.write_text(
        "[settings]\n"
        f"console_port = {sink.port}\n"
        f"receive_port = {sink.port + 1}\n",
        encoding="utf-8",
    )
    settings = resolve_effective_settings(user_path=user_file, seed_path=tmp_path / "absent.toml")
    assert settings.console_port == sink.port
    assert settings.console_port != DEFAULT_CONSOLE_PORT, (
        "the fixture must exercise a NON-default port or the D3 defect is untested"
    )
    return settings.console_port


@pytest.fixture()
def gated_stack(tmp_path, configured_send_port):
    """The real packaged-shell console stack aimed at the sink's port."""
    from server.safety.bootstrap import build_console_stack
    from server.safety.console import LinkTimeouts

    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=configured_send_port,
        receive_port=0,  # ephemeral — no console, no port conflict
        audit_dir=tmp_path / "audit",
        attempt_session_backup=False,
        timeouts=LinkTimeouts(
            exec_confirm_seconds=0.05,
            ping_seconds=0.05,
            state_query_seconds=0.05,
            deploy_confirm_seconds=0.05,
        ),
    )
    try:
        yield stack
    finally:
        stack.stop()


@pytest.fixture()
def deploying_stack(tmp_path, configured_send_port):
    """The gated stack with the file+Import deploy path armed (M7.5)."""
    from server.safety.bootstrap import build_console_stack
    from server.safety.console import LinkTimeouts

    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=configured_send_port,
        receive_port=0,  # ephemeral — no console, no port conflict
        audit_dir=tmp_path / "audit",
        attempt_session_backup=False,
        plugin_import_dir=tmp_path / "plugins",
        timeouts=LinkTimeouts(
            exec_confirm_seconds=0.05,
            ping_seconds=0.05,
            state_query_seconds=0.05,
            deploy_confirm_seconds=0.05,
        ),
    )
    try:
        yield stack
    finally:
        stack.stop()


class TestLayer2SinkBindsTheConfiguredPort:
    def test_sink_port_comes_from_effective_settings_not_the_default(
        self, sink, configured_send_port
    ):
        from server.deploy.settings import DEFAULT_CONSOLE_PORT

        assert sink.port == configured_send_port
        assert configured_send_port != DEFAULT_CONSOLE_PORT

    def test_sink_observes_a_datagram_sent_to_that_port(self, sink):
        raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            raw.sendto(b"probe", ("127.0.0.1", sink.port))
        finally:
            raw.close()
        observed = sink.drain()
        assert len(observed) == 1
        assert observed[0].raw == b"probe"


class TestLayer2PositiveObservationAndReconciliation:
    """The gate's legitimate sends must ACTUALLY be seen on the wire and
    reconcile 1:1 with the audit ``executed`` log."""

    def test_gate_heartbeat_is_observed_and_reconciled(self, sink, gated_stack):
        gated_stack.gate.heartbeat()
        observed = sink.drain()
        audited = [e for e in gated_stack.audit.iter_events() if e["event"] == "executed"]

        result = reconcile(observed, audited)
        assert result.observed_count >= 1, "empty capture cannot satisfy the AC (vacuous pass)"
        assert result.positive_observation is True
        assert result.unaudited == (), result.unaudited
        assert result.ok is True, result.detail
        assert observed[0].address == "/copilot/cmd"
        assert observed[0].verb == "ping"

    def test_gate_cleared_command_send_is_observed_and_reconciled(self, sink, gated_stack):
        decision = gated_stack.gate.screen(["Fixture 1 At 100"])
        assert decision.cleared is True, decision
        gated_stack.gate.execution_port.execute("Fixture 1 At 100")

        observed = sink.drain()
        audited = [e for e in gated_stack.audit.iter_events() if e["event"] == "executed"]
        result = reconcile(observed, audited)
        assert result.positive_observation is True
        assert result.unaudited == (), result.unaudited
        assert result.ok is True, result.detail
        assert any(d.verb == "exec" and d.subject == "Fixture 1 At 100" for d in observed)

    def test_empty_capture_does_not_satisfy_the_ac(self, gated_stack):
        # The whole point of AC-DEPLOY-027 Layer ② ③: "no unenumerated sends"
        # must NOT be satisfiable by observing nothing at all.
        result = reconcile((), [])
        assert result.unaudited == ()
        assert result.positive_observation is False
        assert result.ok is False, "an empty capture reported a pass"


class TestLayer2DeploySpanningCapture:
    """M7.5 — a capture that SPANS a file+Import deploy reconciles 1:1: every
    deploy-internal round-trip (pool read, Import Plugin exec) has its own
    audit entry, so legitimate deploy traffic is never flagged as an
    unenumerated sender. Closes the M7.3 accounting caveat."""

    def test_deploy_spanning_capture_reconciles_one_to_one(self, sink, deploying_stack):
        result_exec = deploying_stack.gate.deploy_plugin_source("CopilotResponder", "return 1")
        # The sink never replies, so the deploy ends unconfirmed — but its
        # datagrams DID reach the wire and every one must be audited.
        assert result_exec.ok is False

        observed = sink.drain()
        audited = [e for e in deploying_stack.audit.iter_events() if e["event"] == "executed"]
        result = reconcile(observed, audited)

        assert result.observed_count >= 2, "a file+Import deploy must span multiple datagrams"
        assert {d.verb for d in observed} == {"state", "exec"}
        assert result.unaudited == (), (
            f"deploy-internal round-trips were flagged as unenumerated: {result.detail}"
        )
        assert result.positive_observation is True
        assert result.ok is True, result.detail

    def test_deploy_plus_rogue_datagram_still_fails_closed(self, sink, deploying_stack):
        # Per-send granularity must not blunt the guard: an off-gate datagram
        # arriving DURING a deploy-spanning capture is still flagged.
        deploying_stack.gate.deploy_plugin_source("CopilotResponder", "return 1")
        rogue = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            rogue.sendto(
                _osc_message("/copilot/cmd", "Delete Sequence 5"), ("127.0.0.1", sink.port)
            )
        finally:
            rogue.close()

        observed = sink.drain()
        audited = [e for e in deploying_stack.audit.iter_events() if e["event"] == "executed"]
        result = reconcile(observed, audited)
        assert len(result.unaudited) == 1, result
        assert result.ok is False, "an off-gate sender must still fail closed across a deploy"


class TestLayer2FailsClosedOnAnUnauditedSender:
    def test_synthetic_rogue_datagram_is_flagged(self, sink, gated_stack):
        # The dynamic analogue of the Python synthetic-bypass test: a datagram
        # that did NOT transit the gate (as a Rust sidecar's raw UDP would not)
        # has no audit entry and must be flagged.
        gated_stack.gate.heartbeat()  # one legitimate, audited send
        rogue = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            packet = _osc_message("/copilot/cmd", "Delete Sequence 5")
            rogue.sendto(packet, ("127.0.0.1", sink.port))
        finally:
            rogue.close()

        observed = sink.drain()
        audited = [e for e in gated_stack.audit.iter_events() if e["event"] == "executed"]
        result = reconcile(observed, audited)

        assert result.positive_observation is True, "the legitimate send must still be observed"
        assert len(result.unaudited) == 1, result
        assert "Delete Sequence 5" in result.unaudited[0].payload
        assert result.ok is False, "an observed-but-unaudited sender did not fail closed"

    def test_reconcile_is_fail_closed_on_an_unparseable_datagram(self, sink, gated_stack):
        gated_stack.gate.heartbeat()
        raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            raw.sendto(b"\x00\x01not-an-osc-packet", ("127.0.0.1", sink.port))
        finally:
            raw.close()
        observed = sink.drain()
        audited = [e for e in gated_stack.audit.iter_events() if e["event"] == "executed"]
        result = reconcile(observed, audited)
        assert result.ok is False
        assert any(d.verb == "?" for d in result.unaudited)

    def test_audited_but_unobserved_is_not_a_violation(self):
        # Direction matters: a gate send that never reached the wire (UDP loss,
        # or a pre-send validation failure that still audits) is NOT a bypass.
        # Only observed-but-unaudited is the security hazard.
        request = 'Plugin "CopilotResponder" "exec gate-1 Fixture 1 At 0"'
        wire = _osc_message("/copilot/cmd", request)
        observed = (parse_datagram(wire, ("127.0.0.1", 1)),)
        audited = [
            {"event": "executed", "kind": "command", "command": "Fixture 1 At 0"},
            {"event": "executed", "kind": "command", "command": "never-sent"},
        ]
        result = reconcile(observed, audited)
        assert result.unaudited == ()
        assert result.ok is True


def _osc_message(address: str, arg: str) -> bytes:
    """Minimal OSC 1.0 string-argument message (rogue-injection helper)."""

    def pad(raw: bytes) -> bytes:
        return raw + b"\x00" * (4 - len(raw) % 4)

    return pad(address.encode()) + pad(b",s") + pad(arg.encode())
