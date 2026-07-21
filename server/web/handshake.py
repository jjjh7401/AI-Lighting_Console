"""`/ws` transport handshake — Origin allowlist + per-launch token (M7.1).

REQ-DEPLOY-002a / AC-DEPLOY-025. Before M7.1 the ``/ws`` endpoint called
``accept()`` with zero origin/token/CORS checking, so any local process or any
browser tab could drive the live console — cross-site WebSocket hijacking
(FEAS-9). This module is the pure decision half of the gate; ``server.web.app``
applies it BEFORE ``websocket.accept()``.

Two origin CLASSES, per plan.md §M7.1 — the asymmetry is the design, not a gap:

* **Stage-2 (Tauri) origins** — the token is deliverable over Tauri IPC, an
  in-process channel no other local process can read, so the token is
  **REQUIRED**: missing or wrong is rejected.
* **Stage-1 (localhost browser) origins** — a browser has no Tauri IPC, and
  every alternative delivery (a disk file, an unauthenticated loopback
  endpoint) is readable by the very local process the token is meant to stop.
  So Stage-1's real CSWSH closer is the **Origin allowlist**, and the token is
  **defense-in-depth only**: absent is allowed, WRONG is still rejected.

Transport: the token rides ``Sec-WebSocket-Protocol`` as
``copilot-token.<token>`` — the only channel a browser/webview ``WebSocket``
can set (the API exposes no custom headers), and unlike a query string it does
not land in access logs or a Referer. Disk plaintext: 0 (AC-DEPLOY-029).

This module never imports the OSC send surface — the handshake adds no send
path (AC-DEPLOY-014 / REQ-MVP-029 chokepoint discipline).
"""

from __future__ import annotations

import hmac
from collections.abc import Sequence
from dataclasses import dataclass

# The subprotocol the client also offers so the server has a non-secret token to
# echo in the handshake response: RFC 6455 lets the server select only a
# subprotocol the client offered, and echoing the secret one back is needless.
BASE_SUBPROTOCOL = "copilot.v1"
TOKEN_SUBPROTOCOL_PREFIX = "copilot-token."

# Stage-2 webview origin (Tauri v2) on macOS/Linux — the platforms the Stage-2
# shell is built on first (DECIDE-M2 targets macOS universal2 + Windows x86_64).
#
# DEFERRED TO M7.4 — the Windows Tauri webview serves the app from the origin
# spelled "http://" + "tauri.localhost" (a reserved-TLD loopback name, RFC 6761).
# It is NOT added here yet because the AC-DEPLOY-002 "no remote backend endpoint"
# guard (server/tests/test_deploy_local_only.py) allowlists only the bare
# loopback hosts, so the literal trips it. M7.4 — which is where the Windows
# Tauri shell first exists and can be verified — MUST either extend that guard's
# _LOOPBACK_HOSTS with the reserved-TLD name or scope the origin per-platform.
# Without that, a Windows Tauri window's upgrade is rejected as origin_not_allowed.
TAURI_ORIGINS: tuple[str, ...] = ("tauri://localhost",)

# Reject codes (close reasons) — 1008 "policy violation" in every case; the
# reason string is internal (never sent to the peer: a rejected client learns
# only that it was rejected, not which check failed).
REASON_ORIGIN_MISSING = "origin_missing"
REASON_ORIGIN_NOT_ALLOWED = "origin_not_allowed"
REASON_TOKEN_MISSING = "token_missing"
REASON_TOKEN_MISMATCH = "token_mismatch"

CLOSE_POLICY_VIOLATION = 1008


@dataclass(frozen=True)
class HandshakePolicy:
    """The per-launch handshake secret + the two origin classes it guards."""

    token: str
    trusted_origins: tuple[str, ...] = ()
    """Stage-2 origins (Tauri webview) — token REQUIRED."""
    browser_origins: tuple[str, ...] = ()
    """Stage-1 loopback browser origins — token optional (defense-in-depth)."""


@dataclass(frozen=True)
class HandshakeDecision:
    accepted: bool
    reason: str = ""
    subprotocol: str | None = None


def browser_origins_for(host: str, port: int) -> tuple[str, ...]:
    """Stage-1 browser origins for the served loopback URL.

    Both loopback spellings are included because the operator may reach the app
    at either — the launcher opens ``127.0.0.1`` but ``localhost`` is what many
    people type, and a browser sends whichever one is in the address bar. A
    bind-all host still yields loopback-only origins (REQ: LOCAL-ONLY app).
    """
    return (f"http://127.0.0.1:{port}", f"http://localhost:{port}")


def token_from_subprotocols(subprotocols: Sequence[str] | None) -> str | None:
    """Extract the offered per-launch token from the subprotocol list."""
    for offered in subprotocols or ():
        if offered.startswith(TOKEN_SUBPROTOCOL_PREFIX):
            return offered[len(TOKEN_SUBPROTOCOL_PREFIX) :]
    return None


def _selected_subprotocol(subprotocols: Sequence[str] | None) -> str | None:
    # RFC 6455: the server may select only a subprotocol the client offered.
    return BASE_SUBPROTOCOL if BASE_SUBPROTOCOL in (subprotocols or ()) else None


def _token_matches(policy: HandshakePolicy, offered: str) -> bool:
    # Constant time — a byte-by-byte `==` leaks the shared prefix length and
    # turns an unguessable secret into a per-character search.
    return hmac.compare_digest(offered, policy.token)


# @MX:ANCHOR: [AUTO] `/ws` handshake authorization boundary — the ONLY check
#   standing between an arbitrary local/browser client and the live-console
#   control channel. Every /ws connection is admitted or refused here.
# @MX:REASON: FEAS-9 — the pre-M7.1 endpoint accepted every upgrade with zero
#   origin/token checking (cross-site WebSocket hijacking of a live lighting
#   console). Weakening a branch here (accepting a missing/unknown Origin,
#   swapping compare_digest for ==, or making the Stage-2 token optional)
#   silently reopens that attack surface; the Stage-1 token-optional branch is
#   deliberate and load-bearing (plan §M7.1) — removing it breaks browser mode.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001 (REQ-DEPLOY-002a / AC-DEPLOY-025)
def evaluate_handshake(
    policy: HandshakePolicy,
    *,
    origin: str | None,
    subprotocols: Sequence[str] | None,
) -> HandshakeDecision:
    """Decide whether a ``/ws`` upgrade may be accepted. Pure — no I/O."""
    if origin is None:
        # Fail-closed: an upgrade with no Origin is not attributable to an
        # allowlisted surface. Browsers always send one for a WebSocket.
        return HandshakeDecision(accepted=False, reason=REASON_ORIGIN_MISSING)

    offered = token_from_subprotocols(subprotocols)

    if origin in policy.trusted_origins:  # Stage-2: token required
        if offered is None:
            return HandshakeDecision(accepted=False, reason=REASON_TOKEN_MISSING)
        if not _token_matches(policy, offered):
            return HandshakeDecision(accepted=False, reason=REASON_TOKEN_MISMATCH)
        return HandshakeDecision(accepted=True, subprotocol=_selected_subprotocol(subprotocols))

    if origin in policy.browser_origins:  # Stage-1: token = defense-in-depth
        if offered is not None and not _token_matches(policy, offered):
            return HandshakeDecision(accepted=False, reason=REASON_TOKEN_MISMATCH)
        return HandshakeDecision(accepted=True, subprotocol=_selected_subprotocol(subprotocols))

    return HandshakeDecision(accepted=False, reason=REASON_ORIGIN_NOT_ALLOWED)
