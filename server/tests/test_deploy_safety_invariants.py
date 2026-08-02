"""Safety-invariant regression under the packaged deploy shell (M10 Part B).

AC-DEPLOY-014 — the TOP security invariant (acceptance.md §D.9 / §품질게이트
"배포 셸이 안전 게이트를 우회하지 않음이 최상위 보안 불변식"). REQ-DEPLOY-023~024.
CI-상시 자동 (수동 검증 불인정). Three sub-invariants, verified with the packaged
shell's REAL composition (server.safety.bootstrap / server.web.serve):

  ① 단일 관문 아키텍처 (AC-MVP-019) 유지 green + deploy-shell 포함 — every
     deploy-shell module reaches the console ONLY through the single SafetyGate;
     no deploy-shell module opens a bypass OSC send surface.
  ② 블랙리스트 승인 회귀 (AC-MVP-004) — a Delete-family blacklist command is NOT
     executed without human approval in the packaged-shell gate composition.
  ③ 결정적 OSC 송신 표면 스캔 (SAFETY-1 / SAFETY-2) — a single NAMED allowlist
     enumerates the legitimate OSC send surface (only the gate reaches it); a
     source scan across ALL ``server/`` Python modules FAILS-CLOSED if any
     un-allowlisted module enters the send surface. This consolidates the three
     interim M3/M4 per-module guards (test_web_settings_api /
     test_web_provision_api / test_deploy_provisioning ``TestNoOscSendSurface``)
     into one authoritative allowlist test.

Stage boundary (SAFETY-2, AC-DEPLOY-014 ③b/③c):
    This is the **Stage-1 Python-source** scan (structural AST markers: raw
    ``socket.socket`` creation, ``python-osc`` import, UDP-client instantiation).
    The **Rust/Tauri source scan** and the **wire-level "all OSC sends observed
    at the console receive port" enumeration** are **Stage-2 (M7~M9) N/A** — the
    Tauri shell + sidecar + updater do not exist yet, so there is no Rust source
    to scan and no packaged E2E to observe. Those are a SEPARATE later delegation
    (M10 Part D, packaged E2E). This file locks the Stage-1 Python surface.

The AST-based marker scan deliberately ignores docstrings/comments — ``server/web/app.py``
and ``server/web/__init__.py`` MENTION ``pythonosc`` / ``server.bridge`` in prose to
document that they never touch it; a naive substring scan would false-positive on
those, so the scan keys on real import/call nodes only.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent


# ---------------------------------------------------------------- send-surface scanner

# The OSC library import roots that mark a module as touching the OSC send surface.
_OSC_IMPORT_ROOTS = ("pythonosc", "server.bridge")
# python-osc client constructors (the concrete "I will send UDP to a console" call).
_UDP_CLIENT_NAMES = frozenset({"SimpleUDPClient", "udp_client"})
# Socket methods that put BYTES ON THE WIRE. A raw socket that only binds is a
# probe; a raw socket that transmits is a send surface, whatever it is called.
# ``connect`` is included because it selects a peer for a later bare ``send``.
_TRANSMIT_ATTRS = frozenset({"sendto", "sendall", "sendmsg", "send", "connect"})


def _scan_send_surface_markers(source: str, filename: str) -> set[str]:
    """Return the set of send-surface markers an AST scan finds in ``source``.

    Markers:
      * ``osc_import``  — imports ``pythonosc`` or ``server.bridge`` (the OSC surface).
      * ``udp_client``  — instantiates a python-osc UDP client (SimpleUDPClient / udp_client).
      * ``raw_socket``  — creates a raw ``socket.socket(...)`` (any family — could be
                          a UDP OSC send OR a TCP port probe; the allowlist distinguishes).
      * ``socket_transmit`` — calls a socket method that puts bytes on the wire
                          (``sendto``/``sendall``/``sendmsg``/``send``/``connect``).
                          This is what separates a bind-only probe from a send
                          surface, and it is what the raw-socket exemption is
                          conditioned on.

    AST-based: docstrings and comments that merely NAME these symbols do not match
    (they are not Import/Call nodes), so prose disclaimers never false-positive.
    """
    markers: set[str] = set()
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(
                    alias.name == r or alias.name.startswith(r + ".") for r in _OSC_IMPORT_ROOTS
                ):
                    markers.add("osc_import")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if any(mod == r or mod.startswith(r + ".") for r in _OSC_IMPORT_ROOTS):
                markers.add("osc_import")
            if mod.startswith("pythonosc"):
                for alias in node.names:
                    if alias.name in _UDP_CLIENT_NAMES:
                        markers.add("udp_client")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if (
                    func.attr == "socket"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "socket"
                ):
                    markers.add("raw_socket")
                if func.attr in _UDP_CLIENT_NAMES:
                    markers.add("udp_client")
                if func.attr in _TRANSMIT_ATTRS:
                    markers.add("socket_transmit")
            elif isinstance(func, ast.Name) and func.id in _UDP_CLIENT_NAMES:
                markers.add("udp_client")
    return markers


def _iter_production_modules():
    """Yield (rel_posix_path, source) for every non-test server Python module."""
    for path in sorted(SERVER_DIR.rglob("*.py")):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if "/tests/" in f"/{rel}" or "/__pycache__/" in f"/{rel}":
            continue
        yield rel, path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- the NAMED allowlist

# ③(a) — the LEGITIMATE OSC send surface, fixed in this fixture. ONLY the gate
# (server/safety) and the surface it wraps (server/bridge) may import the OSC
# library or instantiate a UDP client. This mirrors the AC-MVP-019 allowed
# prefixes verbatim — the single chokepoint.
_OSC_SEND_SURFACE_PREFIXES = (
    "server/bridge/",  # the OSC send/recv surface itself (python-osc)
    "server/safety/",  # the gate — the sole PRODUCTION caller (REQ-MVP-029)
)

# File-exact NON-PRODUCTION operator diagnostics that exercise the transport
# BENEATH the gate (same exemption AC-MVP-019 grants). A NEW tool touching the
# surface is NOT here and therefore fails closed.
_NAMED_TOOL_EXEMPTIONS = frozenset(
    {
        "server/tools/osc_smoke.py",
        "server/tools/responder_roundtrip.py",
        "server/preshow/osc_check.py",
    }
)

# ③ raw-socket carve-out: modules permitted to create a raw socket for a
# NON-OSC-send purpose — they BIND, they never transmit.
#
#   * launcher.py — the port-in-use preflight (REQ-DEPLOY-026 fail-loud) and
#     listener teardown.
#   * reply_discovery.py — listens on a bounded candidate set to find where the
#     console is actually replying (REQ-DEPLOY-018/026 follow-up). Its one ping
#     is the GATE's own heartbeat, injected: this module opens no transmitting
#     socket of its own.
#
# The exemption is file-exact AND conditioned on the absence of a
# ``socket_transmit`` marker, so it cannot be used to smuggle a raw send — which
# a bare file list could. Adding a path here does not buy the right to transmit.
_RAW_SOCKET_EXEMPTIONS = frozenset(
    {
        "server/web/launcher.py",  # port-in-use probe + teardown (bind only)
        "server/web/reply_discovery.py",  # reply-port listeners (bind only)
    }
)

# Deploy-shell modules whose safety AC-DEPLOY-014 ① must confirm (Section A list).
_DEPLOY_SHELL_MODULES = (
    "server/deploy/settings.py",
    "server/deploy/keystore.py",
    "server/deploy/provisioning.py",
    "server/web/settings_api.py",
    "server/web/provision_api.py",
    "server/web/launcher.py",
    "server/web/serve.py",
    "server/resources.py",
)


def _on_osc_surface_allowlist(rel: str) -> bool:
    return rel.startswith(_OSC_SEND_SURFACE_PREFIXES) or rel in _NAMED_TOOL_EXEMPTIONS


def _classify_offense(rel: str, markers: set[str]) -> str | None:
    """Fail-closed classifier: return an offense string if ``rel`` illegitimately
    touches the OSC send surface, else ``None``.

    * osc_import / udp_client → allowed ONLY on the OSC-send-surface allowlist.
    * raw_socket → allowed on the OSC-send-surface allowlist OR the raw-socket
      (bind-only) exemption; anything else creating a raw socket is suspect.
    * raw_socket + socket_transmit → an exempted module that TRANSMITS is a new
      send surface regardless of its path, and fails closed. The exemption buys
      the right to bind, never the right to send.
    """
    if ("osc_import" in markers or "udp_client" in markers) and not _on_osc_surface_allowlist(rel):
        return f"{rel} enters the OSC send surface {sorted(markers)} but is not on the allowlist"
    if "raw_socket" in markers and not _on_osc_surface_allowlist(rel):
        if rel not in _RAW_SOCKET_EXEMPTIONS:
            return (
                f"{rel} creates a raw socket but is on neither the OSC nor the bind-only allowlist"
            )
        if "socket_transmit" in markers:
            return (
                f"{rel} is exempted to BIND a raw socket but transmits on one "
                f"{sorted(markers)} — that is a new OSC send surface"
            )
    return None


# ------------------------------------------------------------ ① single-gate architecture


class TestAcDeploy014SingleGateArchitecture:
    """① AC-MVP-019 유지 green + deploy-shell 포함 (REQ-DEPLOY-023)."""

    def test_ac_mvp_019_import_boundary_still_clean_across_whole_tree(self):
        # Re-run the SPEC-COPILOT-MVP-001 single-chokepoint import-boundary scan
        # (AC-MVP-019) and assert it remains green WITH the deploy shell present —
        # only server/bridge + server/safety (+ named tools) reach the surface.
        from .test_architecture import (
            _ALLOWED_PREFIXES,
            _FORBIDDEN_MODULE_PREFIXES,
            _imports,
        )
        from .test_architecture import (
            _NAMED_TOOL_EXEMPTIONS as _MVP_TOOL_EXEMPTIONS,
        )

        violations: list[str] = []
        for source in sorted(SERVER_DIR.rglob("*.py")):
            rel = source.relative_to(PROJECT_ROOT).as_posix()
            if rel.startswith(_ALLOWED_PREFIXES) or rel in _MVP_TOOL_EXEMPTIONS:
                continue
            for module in _imports(source):
                if module.startswith(_FORBIDDEN_MODULE_PREFIXES):
                    violations.append(f"{rel} imports {module}")
        assert violations == [], f"AC-MVP-019 regressed under the deploy shell: {violations}"

    def test_deploy_shell_modules_open_no_osc_send_path(self):
        # Every deploy-shell module (settings/keystore/provisioning + settings_api/
        # provision_api/launcher/serve + resources) reaches the console ONLY through
        # the gate — none imports the OSC library or instantiates a UDP client. The
        # ONE console command any deploy path issues (Import Plugin) transits
        # server.safety (REQ-DEPLOY-011a), NOT these modules.
        offenders: dict[str, list[str]] = {}
        for rel in _DEPLOY_SHELL_MODULES:
            source = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            markers = _scan_send_surface_markers(source, rel)
            if "osc_import" in markers or "udp_client" in markers:
                offenders[rel] = sorted(markers)
        assert offenders == {}, f"deploy-shell modules opened an OSC send path: {offenders}"

    def test_every_deploy_shell_module_exists(self):
        # Guard against a silently-vacuous ① scan: the listed modules must exist.
        missing = [rel for rel in _DEPLOY_SHELL_MODULES if not (PROJECT_ROOT / rel).is_file()]
        assert missing == [], f"deploy-shell module list is stale: {missing}"


# ------------------------------------------------------------ ② blacklist approval regression


@pytest.fixture()
def packaged_gate(tmp_path):
    """The REAL packaged-shell console stack (server.safety.bootstrap.build_console_stack —
    the SAME composition server.web.serve.build_runtime uses), on an ephemeral
    loopback reply port so no real console is required."""
    from server.safety.bootstrap import build_console_stack

    def _build(approval_port=None):
        stack = build_console_stack(
            receive_port=0,  # ephemeral loopback — no port conflict, no onPC needed
            approval_port=approval_port,
            audit_dir=tmp_path / "audit",
            attempt_session_backup=False,
        )
        return stack

    built = []

    def factory(approval_port=None):
        stack = _build(approval_port)
        built.append(stack)
        return stack

    yield factory
    for stack in built:
        stack.stop()


class TestAcDeploy014BlacklistApprovalRegression:
    """② AC-MVP-004 회귀 — a blacklist command needs human approval, in the
    packaged deploy-shell gate composition (REQ-DEPLOY-024)."""

    def test_blacklist_delete_not_executed_without_approval(self, packaged_gate):
        # Fail-safe default: with NO approval channel, a Delete-family blacklist
        # command is rejected — never reaches the console.
        stack = packaged_gate(approval_port=None)
        decision = stack.gate.screen(["Delete Sequence 5"])
        assert decision.cleared is False
        assert decision.status == "rejected"
        executed = [e for e in stack.audit.iter_events() if e["event"] == "executed"]
        assert executed == [], f"a blacklist command was executed without approval: {executed}"
        # The execution port also refuses to send it (no clearance was issued).
        assert stack.gate.execution_port.execute("Delete Sequence 5").ok is False

    def test_blacklist_delete_is_held_for_human_approval(self, packaged_gate):
        # With an approval channel present, the Delete command is HELD — surfaced to
        # the human-approval path with its blacklist risk reason, never sent directly.
        # In the packaged stack (no live console) the pre-risky backup (AC-MVP-008
        # rule 3) additionally cannot confirm, so the command is fail-safe blocked —
        # a STRONGER guarantee. Either way the blacklist command reaches the human
        # review surface and is NOT executed.
        from .test_safety_gate import ScriptedApproval

        approval = ScriptedApproval([True])
        stack = packaged_gate(approval_port=approval)
        decision = stack.gate.screen(["Delete Sequence 5"])

        # Held for human review: an approval request carries the command + its
        # blacklist risk reason (never silently dropped, never silently sent).
        assert decision.approval_request is not None
        item = decision.approval_request.items[0]
        assert item.command == "Delete Sequence 5"
        assert any("blacklist" in reason for reason in item.risk_reasons)

        # And it is NOT executed on the console. The only "executed" audit entry is
        # the pre-risky safety BACKUP (kind='backup', AC-MVP-008 rule 3) — a safety
        # mechanism, not a command send. No non-backup command reaches the console,
        # and the Delete command itself is never sent.
        executed = [e for e in stack.audit.iter_events() if e["event"] == "executed"]
        non_backup = [e for e in executed if e.get("kind") != "backup"]
        assert non_backup == [], f"a non-backup command reached the console: {non_backup}"
        assert not any(e.get("command") == "Delete Sequence 5" for e in executed), (
            "the blacklist Delete command was executed on the console"
        )


# ------------------------------------------------------------ ③ OSC send-surface allowlist scan


class TestAcDeploy014OscSendSurfaceAllowlist:
    """③ SAFETY-1/2 결정적 송신 표면 스캔 — fail-closed named allowlist
    (REQ-DEPLOY-023~024). Consolidates the three interim per-module guards."""

    def test_only_allowlisted_modules_reach_the_osc_send_surface(self):
        # (d) fail-closed: scan ALL server Python modules; any module NOT on the
        # named allowlist that imports the OSC library, instantiates a UDP client,
        # or creates a non-probe raw socket is a violation.
        offenses: list[str] = []
        for rel, source in _iter_production_modules():
            markers = _scan_send_surface_markers(source, rel)
            offense = _classify_offense(rel, markers)
            if offense is not None:
                offenses.append(offense)
        assert offenses == [], (
            "AC-DEPLOY-014 ③ fail-closed: an un-allowlisted module entered the "
            f"OSC send surface: {offenses}"
        )

    def test_the_allowlist_is_not_vacuous(self):
        # Positive control: the real OSC send surface (server/bridge/osc.py) IS
        # detected by the scanner — the allowlist protects a real, non-empty set.
        surface = (PROJECT_ROOT / "server/bridge/osc.py").read_text(encoding="utf-8")
        markers = _scan_send_surface_markers(surface, "server/bridge/osc.py")
        assert "osc_import" in markers and "udp_client" in markers
        assert _on_osc_surface_allowlist("server/bridge/osc.py")

    def test_named_tool_exemptions_still_exist(self):
        # A stale exemption is a dormant bypass hole — every named tool must exist.
        for rel in _NAMED_TOOL_EXEMPTIONS | _RAW_SOCKET_EXEMPTIONS:
            assert (PROJECT_ROOT / rel).is_file(), f"stale exemption: {rel}"

    def test_launcher_raw_socket_is_a_tcp_probe_not_a_udp_send(self):
        # The launcher's raw-socket exemption is justified ONLY because it is a TCP
        # bind probe. Assert it opens NO OSC send path (no osc_import / udp_client).
        source = (PROJECT_ROOT / "server/web/launcher.py").read_text(encoding="utf-8")
        markers = _scan_send_surface_markers(source, "server/web/launcher.py")
        assert "raw_socket" in markers
        assert "osc_import" not in markers and "udp_client" not in markers

    def test_every_bind_only_exemption_really_only_binds(self):
        # The exemption's whole justification. reply_discovery.py binds UDP (not
        # TCP like the launcher), so "it is a TCP probe" no longer carries the
        # argument for the list as a whole — "it never transmits" does, and it is
        # asserted here rather than asserted in prose.
        for rel in sorted(_RAW_SOCKET_EXEMPTIONS):
            markers = _scan_send_surface_markers(
                (PROJECT_ROOT / rel).read_text(encoding="utf-8"), rel
            )
            assert "socket_transmit" not in markers, (
                f"{rel} is exempted to BIND a raw socket but transmits on one"
            )
            assert "osc_import" not in markers and "udp_client" not in markers, rel

    def test_the_bind_only_exemption_cannot_be_used_to_smuggle_a_send(self):
        # Positive control for the strengthened rule: the SAME exempted path is
        # rejected the moment it transmits. Without this, adding a file to
        # _RAW_SOCKET_EXEMPTIONS would silently grant it a send surface.
        exempted = sorted(_RAW_SOCKET_EXEMPTIONS)[0]
        binding_only = "import socket\ndef probe():\n    socket.socket().bind(('h', 1))\n"
        transmitting = (
            "import socket\n"
            "def leak():\n"
            "    s = socket.socket()\n"
            "    s.sendto(b'/copilot/cmd', ('127.0.0.1', 8000))\n"
        )
        assert (
            _classify_offense(exempted, _scan_send_surface_markers(binding_only, exempted)) is None
        )
        offense = _classify_offense(exempted, _scan_send_surface_markers(transmitting, exempted))
        assert offense is not None and "send surface" in offense

    def test_scan_fails_closed_on_a_synthetic_bypass_module(self):
        # Demonstrate fail-closed WITHOUT touching the real tree: a fabricated
        # "updater" module that opens a raw UDP OSC send is flagged by the scanner
        # AND rejected by the allowlist classifier. If this ever stopped flagging,
        # the whole ③ guard would be silently defeated.
        rogue_rel = "server/web/rogue_updater.py"
        rogue_source = (
            "import socket\n"
            "from pythonosc.udp_client import SimpleUDPClient\n"
            "\n"
            "def push_update():\n"
            "    client = SimpleUDPClient('127.0.0.1', 8000)\n"
            "    client.send_message('/copilot/cmd', 'Delete Sequence 5')\n"
            "    raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
            "    raw.sendto(b'x', ('127.0.0.1', 8000))\n"
        )
        markers = _scan_send_surface_markers(rogue_source, rogue_rel)
        assert {"osc_import", "udp_client", "raw_socket"} <= markers
        assert _classify_offense(rogue_rel, markers) is not None

    def test_prose_mentions_do_not_false_positive(self):
        # server/web/app.py and __init__.py NAME pythonosc/server.bridge in their
        # docstrings to disclaim any send path. The AST scanner must NOT flag them.
        for rel in ("server/web/app.py", "server/web/__init__.py"):
            source = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            markers = _scan_send_surface_markers(source, rel)
            assert _classify_offense(rel, markers) is None, (
                f"{rel} was false-flagged despite only mentioning the surface in prose"
            )
