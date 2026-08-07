"""Paperwork REST API (W3 — P0 UI exposure, docs/reports/2026-08-06-workflow-
coverage-review.html §5).

Two endpoints surface the three read-only printable documents
(``build_patch_sheet`` / ``build_cue_sheet`` / ``build_preset_list``) that were
previously reachable ONLY through an LLM tool call — see
``server/orchestrator/tools.py``'s own ``build_patch_sheet`` /
``build_cue_sheet`` / ``build_preset_list`` handlers, whose wording and
failure-cause split this module deliberately mirrors:

    GET  /api/paperwork            generatable kinds + the last generation
                                    result for each kind (``None`` before the
                                    first successful generation this run)
    POST /api/paperwork/{kind}     generate one document; ``kind`` is one of
                                    the closed table below. An unrecognised
                                    kind is a 400 and never reaches the
                                    filesystem.

Safety boundary (this module is deliberately narrow):

* **No OSC-send surface.** This module imports ONLY the read-only
  ``server.paperwork`` builders/renderers (which themselves never import the
  OSC send surface — ``server/tests/test_paperwork_boundary.py`` enforces
  that) plus the gate-owned query ports composed by the caller. It never
  imports ``server.bridge`` or an execution-capable port — a source scan in
  ``test_web_paperwork_api.py`` enforces this for THIS module too.
* **Read-only.** Every handler here writes only the deterministic paperwork
  HTML file (``server.paperwork.output.write_paperwork_html`` — a fixed
  basename per kind, overwritten on every run); it never sends a console
  command.
* **``kind`` is a closed table (``_KIND_TABLE``).** The client-supplied path
  segment is looked up, never interpolated into a filename — an unknown
  ``kind`` can never reach the filesystem.
* **No HTML body in the response.** The rendered document is written to
  disk and only its path + a small numeric summary ride the JSON response —
  the same reasoning ``build_patch_sheet``/``build_cue_sheet``/
  ``build_preset_list`` in ``server/orchestrator/tools.py`` already applied:
  a human opens the file in a browser, and 3-6KB of markup has no use on the
  wire.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
from server.paperwork.data import (
    build_cue_sheet as _build_cue_sheet_query,
)
from server.paperwork.data import (
    build_patch_sheet as _build_patch_sheet_query,
)
from server.paperwork.data import (
    build_preset_list as _build_preset_list_query,
)
from server.paperwork.output import write_paperwork_html
from server.paperwork.render import render_cue_sheet, render_patch_sheet, render_preset_list
from server.prechk.inventory import InventoryReadError


class _InventoryPort:
    """Joins the state + property reads the patch-sheet builder needs.

    Mirrors ``server.orchestrator.tools._InventoryPort`` line for line — that
    class is local to a function in a module this router must not edit
    (W1/W2 own ``server/paperwork/**`` and ``server/orchestrator/tools.py``),
    so the two lines are repeated here rather than imported.
    """

    def __init__(self, state: StateQueryPort, prop: PropertyQueryPort) -> None:
        self._state = state
        self._prop = prop

    def query_state(self, path: str) -> dict:
        return self._state.query_state(path)

    def query_property(self, path: str, property_name: str) -> dict:
        return self._prop.query_property(path, property_name)


@dataclass
class PaperworkDeps:
    """Everything the paperwork API consumes — composed by serve.py / tests.

    ``state_port`` is the gate-owned query port (``SafetyGate.state_port`` in
    production — it implements both ``query_state`` and ``query_property``).
    ``property_port`` mirrors ``build_toolset``'s own fallback
    (``server/orchestrator/tools.py``): when omitted it is adopted from
    ``state_port`` if that object also implements ``query_property``, so
    production wiring needs no extra plumbing while a narrow test double
    stays narrow and ``POST /api/paperwork/patch_sheet`` reports the missing
    capability instead of a false-empty sheet.
    """

    state_port: StateQueryPort
    property_port: PropertyQueryPort | None = None
    rig_paths: dict[str, str] | None = None


def _resolve_property_port(deps: PaperworkDeps) -> PropertyQueryPort | None:
    if deps.property_port is not None:
        return deps.property_port
    if hasattr(deps.state_port, "query_property"):
        return deps.state_port  # narrow duck-type: the gate's port has both
    return None


# -- kind builders (closed table below) --------------------------------------
#
# Each returns (filename, rendered_html, summary) or raises HTTPException.
# ``filename`` is a fixed constant per kind — never derived from the client's
# ``kind`` path segment — so an unrecognised kind can never reach disk.


def _patch_sheet(deps: PaperworkDeps) -> tuple[str, str, dict]:
    property_port = _resolve_property_port(deps)
    if property_port is None:
        # Same missing-capability wording tools.py's build_patch_sheet uses —
        # never answer "zero fixtures" when the capability is simply unwired.
        raise HTTPException(
            status_code=503,
            detail={
                "error": "capability_unavailable",
                "message": (
                    "property reads are not wired — the paperwork API needs a "
                    "property_port (or a state_port that also implements "
                    "query_property)"
                ),
            },
        )
    try:
        sheet = _build_patch_sheet_query(_InventoryPort(deps.state_port, property_port))
    except InventoryReadError as error:
        # Distinct error code from capability_unavailable above (③ vs ④ in
        # the brief): the capability IS wired, but the query itself failed
        # (root unreadable — includes an unreachable console).
        raise HTTPException(
            status_code=502,
            detail={
                "error": "query_failed",
                "message": f"fixture inventory unreadable: {error}",
            },
        ) from error
    summary = {
        "fixture_count": sheet.observed_count,
        "child_count": sheet.child_count,
        "completeness": sheet.completeness,
    }
    return "patch_sheet.html", render_patch_sheet(sheet), summary


def _cue_sheet(deps: PaperworkDeps) -> tuple[str, str, dict]:
    rig_paths = deps.rig_paths or DEFAULT_RIG_CONTEXT_PATHS
    listing = _build_cue_sheet_query(
        deps.state_port,
        sequences_path=rig_paths.get("sequences", DEFAULT_RIG_CONTEXT_PATHS["sequences"]),
    )
    if listing.unavailable_reason is not None:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "query_failed",
                "message": f"the sequences pool did not arrive: {listing.unavailable_reason}",
                "reason": listing.unavailable_reason,
                "detail": listing.unavailable_detail,
            },
        )
    summary = {
        "sequence_count": len(listing.pools),
        "cue_count": sum(len(pool.items) for pool in listing.pools),
        "truncated": listing.truncated,
        "drilldown_capped": listing.drilldown_capped,
    }
    return "cue_sheet.html", render_cue_sheet(listing), summary


def _preset_list(deps: PaperworkDeps) -> tuple[str, str, dict]:
    rig_paths = deps.rig_paths or DEFAULT_RIG_CONTEXT_PATHS
    listing = _build_preset_list_query(
        deps.state_port,
        preset_pools_path=rig_paths.get("preset_pools", DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]),
    )
    if listing.unavailable_reason is not None:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "query_failed",
                "message": f"the preset pools did not arrive: {listing.unavailable_reason}",
                "reason": listing.unavailable_reason,
                "detail": listing.unavailable_detail,
            },
        )
    summary = {
        "pool_count": len(listing.pools),
        "preset_count": sum(len(pool.items) for pool in listing.pools),
        "truncated": listing.truncated,
        "drilldown_capped": listing.drilldown_capped,
    }
    return "preset_list.html", render_preset_list(listing), summary


# The closed routing table (REQ per the brief §① "kind는 닫힌 테이블로 라우팅
# 한다"). Deliberately does NOT carry a "handover" entry — the handover
# package button is W2's scope, out of this SPEC slice; a new kind is added
# here later by adding one entry, never by widening the client contract.
_KIND_TABLE: dict[str, Callable[[PaperworkDeps], tuple[str, str, dict]]] = {
    "patch_sheet": _patch_sheet,
    "cue_sheet": _cue_sheet,
    "preset_list": _preset_list,
}


# @MX:ANCHOR: [AUTO] the paperwork-generation REST surface — the ONLY web
#   entry point that turns the three read-only paperwork builders into a
#   file the operator can open. High fan_in (create_app wiring, tests).
# @MX:REASON: mirrors the OSC-send-surface invariant every sibling web router
#   in this package pins for itself (settings_api.py / provision_api.py) — a
#   new endpoint here that imports a raw socket / OSC module / an
#   execution-capable port would open an ungated console-command path (a
#   safety regression); test_web_paperwork_api.py's source scan enforces it.
def build_paperwork_router(deps: PaperworkDeps) -> APIRouter:
    """Build the paperwork REST router around one composed dependency set."""
    router = APIRouter()

    # Process-lifetime only (no persistence) — mirrors WebDeps.panel's
    # in-memory PanelStore for "last known result" state; a restart forgets
    # it, and GET /api/paperwork reports None until the next successful POST.
    last_results: dict[str, dict] = {}

    @router.get("/api/paperwork")
    def list_kinds() -> dict:
        return {
            "kinds": list(_KIND_TABLE),
            "last_results": {kind: last_results.get(kind) for kind in _KIND_TABLE},
        }

    @router.post("/api/paperwork/{kind}")
    def generate(kind: str) -> dict:
        builder = _KIND_TABLE.get(kind)
        if builder is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unknown_kind",
                    "message": f"unknown paperwork kind: {kind!r}",
                },
            )
        filename, html, summary = builder(deps)
        try:
            path = write_paperwork_html(filename, html)
        except OSError as error:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "write_failed",
                    "message": f"{kind} could not be written to disk: {error}",
                },
            ) from error
        result = {"path": str(path), **summary}
        last_results[kind] = result
        return {"ok": True, "kind": kind, **result}

    return router
