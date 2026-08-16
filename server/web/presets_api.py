"""Preset-pool browsing REST API (dashboard popup, on-demand).

The dashboard's ``dash_catalog`` snapshot deliberately shows preset POOLS as
read-only category tiles and never lists the presets inside every pool: pool
contents ride a bounded per-call drilldown budget, and a showfile with many
pools exhausts it (the panel then shows the honest ``드릴다운 예산 소진``
badge with nothing inside). This module is the other half of that design: when
the operator OPENS one pool, its contents are fetched fresh from the console —
one ``query_state`` for the pool listing, and a PAGED read for the pool itself
(the responder caps ``children`` at 24 per reply, PROTOCOL §4.2 — a Color pool
past 24 presets needs follow-up ``offset`` windows, the same discipline as the
session's ``_paged_pool_children``), independent of the dash budget, and always
current (a preset stored seconds ago is visible on the next open).

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
from typing import Protocol

from fastapi import APIRouter, HTTPException

from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    rig_object,
    rig_section,
)


class PoolStatePort(Protocol):
    """StateQueryPort + optional §4.2 paging (``offset``).

    The production port (``_GateStatePort``) accepts ``offset``; a legacy
    double without the kwarg still works — the paged reader catches the
    ``TypeError`` and degrades to an honest ``truncated`` flag instead of
    pretending the first window was the whole pool.
    """

    def query_state(self, path: str, *, offset: int = 0) -> dict: ...


@dataclass
class PresetsDeps:
    """Everything the presets API consumes — composed by serve.py / tests.

    ``state_port`` is the gate-owned query port, the same seam every other
    read surface (dash, panel, paperwork) rides.
    """

    state_port: PoolStatePort
    preset_pools_path: str = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


def _section_of(payload: dict) -> dict:
    """The shared wire shape: objects (real ``no`` only) + completeness."""
    children = payload.get("children", [])
    objects = [rig_object(child) for child in children if isinstance(child, dict)]
    return rig_section(objects, payload)


def _palette_hex_by_label() -> dict[str, str]:
    """Palette label → ``#rrggbb`` from the session's own COLOR_PALETTE_SEQUENCE.

    Imported lazily to keep this module's import surface narrow (the router
    is composed by serve.py, which loads the session anyway). The console
    does NOT expose a preset's colour (Appearance/Color props answered
    "not readable", live-probed 2026-08-16), so the ONLY honest colour
    source is the palette the app itself stored — a manual preset's colour
    is unknown and never invented.
    """
    from server.web.session import COLOR_PALETTE_SEQUENCE

    def _hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(f"{round(v * 255 / 100):02x}" for v in rgb)

    return {label: _hex(rgb) for label, rgb in COLOR_PALETTE_SEQUENCE}


def _swatch_of(name: object, palette: dict[str, str]) -> str | None:
    """The known palette colour for a preset NAME, tolerating the console's
    duplicate-name suffix (``Warm White#2`` is still Warm White)."""
    if not isinstance(name, str):
        return None
    base = name.split("#", 1)[0]
    return palette.get(base)


def _with_swatches(objects: list[dict]) -> list[dict]:
    palette = _palette_hex_by_label()
    enriched = []
    for obj in objects:
        swatch = _swatch_of(obj.get("name"), palette)
        enriched.append({**obj, "color": swatch} if swatch else obj)
    return enriched


#: 세션 ``_paged_pool_children``과 같은 상한 — 10창(240슬롯)이면 실제 풀
#: 크기의 여유 상계다. 상한 초과는 완전 판독 주장 없이 ``truncated``로 남는다.
_POOL_PAGE_CAP = 10


def _claims_more(payload: dict, seen: int) -> bool:
    """절단 판정 이중 방어 — 응답기 truncated 플래그 또는 childCount 산술
    (세션 판독기와 동일, TRUNCATE-001)."""
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    return bool(payload.get("truncated")) or (isinstance(child_count, int) and child_count > seen)


def _paged_pool_children(
    state_port: PoolStatePort, path: str, first: dict
) -> tuple[list[dict], bool]:
    """``first`` 창 이후를 offset 페이징으로 이어 읽는다 — ``(children, truncated)``.

    세션 판독기(``session._paged_pool_children``)의 무진전 방어를 그대로
    상속하되, 강등 방향만 다르다: 세션은 부분 판독을 None(판독 불가)으로
    떨어뜨리지만(저장 검증은 완전성이 전제), 읽기 전용 팝업은 이미 받은
    창을 보여주면서 ``truncated=True``로 미완을 고지한다 — 부분을 전체로
    꾸미지 않는 같은 규율의 다른 표현이다. 무진전 갈래: 페이징을 모르는
    포트(TypeError)·후속 창 오류·에코 부재/불일치(구버전 응답기는 offset을
    무시하고 항상 첫 창을 돌려준다)·빈 창·페이지 상한.
    """
    children = [c for c in first.get("children", []) if isinstance(c, dict)]
    payload = first
    seen = len(payload.get("children", [])) if isinstance(payload.get("children"), list) else 0
    for _page in range(_POOL_PAGE_CAP):
        if not _claims_more(payload, seen):
            return children, False
        try:
            payload = state_port.query_state(path, offset=seen)
        except TypeError:
            return children, True  # 포트가 페이징을 모른다 — 첫 창만, 정직 고지
        except Exception:
            return children, True  # 후속 창 실패 — 받은 만큼만, 정직 고지
        echo = payload.get("offset") if isinstance(payload, dict) else None
        window = payload.get("children") if isinstance(payload, dict) else None
        if isinstance(echo, bool) or echo != seen or not isinstance(window, list) or not window:
            return children, True  # 무진전 — 에코 불일치/빈 창은 전진 불가
        children.extend(c for c in window if isinstance(c, dict))
        seen += len(window)
    return children, _claims_more(payload, seen)  # 상한 도달 — 남은 주장만큼 절단


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
        # ONE query on the happy path (popup-open latency is one OSC round
        # trip): the pool is read DIRECTLY, and its own ``node.name`` names it.
        # Only a pool past the responder's 24-child window (PROTOCOL §4.2)
        # spends follow-up offset reads — live 2026-08-16: the ten phaser
        # presets 4.31~4.40 fell outside the first window and the popup showed
        # a pool the console disagreed with. This is still never-guess — the
        # console itself either answers for that exact path or refuses it;
        # only the FAILURE path spends a query on the pool listing, to tell
        # "no such pool" (404, with the truncation caveat when the listing
        # cannot prove absence) apart from "console unreachable" (502).
        path = f"{deps.preset_pools_path}/{pool_no}"
        try:
            payload = deps.state_port.query_state(path)
        except Exception as error:
            pools = _pools()  # raises its own 502 when the console is down
            listed = {obj.get("no") for obj in pools["objects"]}
            if pool_no in listed:
                raise HTTPException(
                    status_code=502,
                    detail=f"프리셋 풀 {pool_no}을(를) 읽지 못했습니다: {error}",
                ) from error
            detail = f"프리셋 풀 {pool_no}은(는) 이 리그의 풀 목록에 없습니다"
            if pools["truncated"]:
                detail += " (풀 목록이 잘려 있어 존재 여부를 판정할 수 없습니다)"
            raise HTTPException(status_code=404, detail=detail) from error
        children, truncated = _paged_pool_children(deps.state_port, path, payload)
        objects = [rig_object(child) for child in children]
        node = payload.get("node")
        name = node.get("name") if isinstance(node, dict) else None
        child_count = node.get("childCount") if isinstance(node, dict) else None
        return {
            "pool": {"no": pool_no, "name": name if isinstance(name, str) else ""},
            "presets": _with_swatches(objects),
            "truncated": truncated,
            "total": child_count if isinstance(child_count, int) else None,
        }

    return router
