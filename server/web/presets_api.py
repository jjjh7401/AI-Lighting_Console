"""Preset-pool browsing REST API (dashboard popup, on-demand).

The dashboard's ``dash_catalog`` snapshot deliberately shows preset POOLS as
read-only category tiles and never lists the presets inside every pool: pool
contents ride a bounded per-call drilldown budget, and a showfile with many
pools exhausts it (the panel then shows the honest ``드릴다운 예산 소진``
badge with nothing inside). This module is the other half of that design: when
the operator OPENS one pool, its contents are fetched fresh from the console —
exactly one ``query_state`` for the pool listing plus one for the pool itself,
independent of the dash budget, and always current (a preset stored seconds ago
is visible on the next open).

    GET /api/presets              the pool listing (no/name per pool)
    GET /api/presets/{pool_no}    one pool's presets (no/name per slot)

Safety boundary (deliberately narrow, the ``paperwork_api`` precedent):

* **No OSC-send surface.** Imports ONLY the gate-owned ``StateQueryPort`` and
  the shared rig-shape helpers (``rig_object``/``rig_section``) so the real-
  ``no`` rule and the truncation signal keep one implementation. It never
  imports ``server.bridge`` or an execution-capable port.
* **Read-only.** No handler sends a console command or writes a file.
* **``pool_no`` is validated against the pool LISTING** the console just
  returned — an unlisted number is a 404, never an interpolated guess (the
  same never-guess rule ``select_preset_number`` applies on the write side).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from server.orchestrator.ports import StateQueryPort
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    rig_object,
    rig_section,
)


@dataclass
class PresetsDeps:
    """Everything the presets API consumes — composed by serve.py / tests.

    ``state_port`` is the gate-owned query port, the same seam every other
    read surface (dash, panel, paperwork) rides.
    """

    state_port: StateQueryPort
    preset_pools_path: str = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


def _section_of(payload: dict) -> dict:
    """The shared wire shape: objects (real ``no`` only) + completeness."""
    children = payload.get("children", [])
    objects = [rig_object(child) for child in children if isinstance(child, dict)]
    return rig_section(objects, payload)


def build_presets_router(deps: PresetsDeps) -> APIRouter:
    """Build the preset-browsing REST router around one composed dependency set."""
    router = APIRouter()

    def _pools() -> dict:
        try:
            payload = deps.state_port.query_state(deps.preset_pools_path)
        except Exception as error:
            # One refusal for every port failure: the pool listing did not
            # arrive, and nothing downstream may pretend it did.
            raise HTTPException(
                status_code=502, detail=f"프리셋 풀 목록을 읽지 못했습니다: {error}"
            ) from error
        return _section_of(payload)

    @router.get("/api/presets")
    def list_pools() -> dict:
        section = _pools()
        return {
            "pools": section["objects"],
            "truncated": section["truncated"],
            "total": section["total"],
        }

    @router.get("/api/presets/{pool_no}")
    def read_pool(pool_no: int) -> dict:
        pools = _pools()
        listed = {
            obj["no"]: str(obj.get("name", ""))
            for obj in pools["objects"]
            if isinstance(obj.get("no"), int)
        }
        if pool_no not in listed:
            # Absence from a TRUNCATED listing is not evidence of absence,
            # but it is not evidence of presence either — the honest answer
            # names the condition instead of interpolating the number.
            detail = f"프리셋 풀 {pool_no}은(는) 이 리그의 풀 목록에 없습니다"
            if pools["truncated"]:
                detail += " (풀 목록이 잘려 있어 존재 여부를 판정할 수 없습니다)"
            raise HTTPException(status_code=404, detail=detail)
        try:
            payload = deps.state_port.query_state(f"{deps.preset_pools_path}/{pool_no}")
        except Exception as error:
            raise HTTPException(
                status_code=502, detail=f"프리셋 풀 {pool_no}을(를) 읽지 못했습니다: {error}"
            ) from error
        section = _section_of(payload)
        return {
            "pool": {"no": pool_no, "name": listed[pool_no]},
            "presets": section["objects"],
            "truncated": section["truncated"],
            "total": section["total"],
        }

    return router
