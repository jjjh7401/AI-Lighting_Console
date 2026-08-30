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
from server.rig.paging import PAGE_CAP, claims_more, paged_children


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


def _phaser_hexes_by_label() -> dict[str, tuple[str, ...]]:
    """페이저 라벨 → 스텝 순서의 ``#rrggbb`` 목록 — 앱이 아는 색만.

    같은 정직성 규율의 확장이다: 콘솔은 프리셋 색을 노출하지 않지만, 멀티컬러
    페이저 10종은 앱 자신이 ``COLOR_PHASER_SEQUENCE``의 팔레트 스텝으로
    저장했다(4.31~4.40, 2026-08-16 실기) — 그 스텝 색이 콘솔이 ⋯ 프리셋에
    그리는 분할 원의 유일하게 정직한 출처다. 수동 페이저는 여기 없으므로
    여전히 색 없이 강등된다.
    """
    from server.web.session import COLOR_PALETTE_SEQUENCE, COLOR_PHASER_SEQUENCE

    def _hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(f"{round(v * 255 / 100):02x}" for v in rgb)

    palette = {label: _hex(rgb) for label, rgb in COLOR_PALETTE_SEQUENCE}
    return {
        label: tuple(palette[step] for step in steps)
        for label, steps, _form, _phase in COLOR_PHASER_SEQUENCE
    }


def _combo_phaser_hexes_by_label() -> dict[str, tuple[str, ...]]:
    """콤보(컬러+디머) 페이저 라벨 → 스텝 순서의 ``#rrggbb`` 목록 —
    ``_phaser_hexes_by_label``의 확장. 콘솔은 프리셋 색을 노출하지 않으므로
    앱이 저장 시점에 실은 값만 정직한 출처다: 각 스텝의 팔레트 RGB를 그
    스텝의 디머%로 스케일(``rgb × dimmer/100``)한 뒤 hex로 바꾼다 — 밝기가
    낮은 스텝은 어둡게, 0%(예: Drop Slam 2스텝)는 검정으로 보인다.
    """
    from server.web.session import COLOR_PALETTE_SEQUENCE, COMBO_PHASER_SEQUENCE

    def _hex(rgb: tuple[float, float, float]) -> str:
        return "#" + "".join(f"{round(v * 255 / 100):02x}" for v in rgb)

    palette = dict(COLOR_PALETTE_SEQUENCE)
    result: dict[str, tuple[str, ...]] = {}
    for label, steps, _form, _phase in COMBO_PHASER_SEQUENCE:
        hexes = []
        for palette_label, dimmer in steps:
            r, g, b = palette[palette_label]
            hexes.append(_hex((r * dimmer / 100, g * dimmer / 100, b * dimmer / 100)))
        result[label] = tuple(hexes)
    return result


def _gray_hex(value: int) -> str:
    """레벨 v(0~100) → 회색 ``#rrggbb``(R=G=B=round(255*v/100)) — 디머 프리셋
    전용 색 소스(T5 지시). 컬러와 같은 정직성 규율: 콘솔은 프리셋 색을
    노출하지 않으므로, 앱이 저장 시점에 실은 값(디머는 팔레트가 아니라
    레벨 그 자체)만이 유일하게 정직한 출처다.
    """
    channel = round(value * 255 / 100)
    return f"#{channel:02x}{channel:02x}{channel:02x}"


def _dimmer_hex_by_label() -> dict[str, str]:
    """디머 레벨 라벨 → 회색 ``#rrggbb`` — ``_palette_hex_by_label``의 미러,
    소스만 ``DIMMER_LEVEL_SEQUENCE``. 컬러 팔레트와 라벨이 서로소다(Dim 10..
    Full vs Warm White..Lavender) — 병합에 충돌이 없다.
    """
    from server.web.session import DIMMER_LEVEL_SEQUENCE

    return {label: _gray_hex(value) for label, value in DIMMER_LEVEL_SEQUENCE}


def _dimmer_phaser_hexes_by_label() -> dict[str, tuple[str, ...]]:
    """디머 페이저 라벨 → 스텝 순서의 회색 ``#rrggbb`` 목록 —
    ``_phaser_hexes_by_label``의 미러, 소스만 ``DIMMER_PHASER_SEQUENCE``.
    컬러 페이저와 라벨이 서로소다(Breathe Soft.. vs Breathe Warm..) — 병합에
    충돌이 없다.
    """
    from server.web.session import DIMMER_PHASER_SEQUENCE

    return {
        label: tuple(_gray_hex(value) for value in values)
        for label, values, _form, _phase in DIMMER_PHASER_SEQUENCE
    }


def _base_name(name: object) -> str | None:
    """콘솔 중복명 접미 제거 — ``Warm White#2``는 여전히 Warm White."""
    if not isinstance(name, str):
        return None
    return name.split("#", 1)[0]


def _with_swatches(objects: list[dict], *, pool_name: str) -> list[dict]:
    """앱 카탈로그 색을 **풀 이름으로 스코핑**해 붙인다.

    라벨-단독 매칭은 다른 풀의 동명 수동 프리셋(예: Color 풀에 운영자가
    저장한 'Full'이나 'Police')에 앱이 저장한 적 없는 색을 붙인다 —
    발명 금지 규율의 실질 위반 경로(2026-08-17 리뷰). 각 카탈로그는 앱이
    저장하는 풀이 정해져 있으므로(팔레트·컬러 페이저=Color, 디머 레벨·
    페이저=Dimmer, 콤보=All N) 그 풀 이름에서만 매칭한다. 풀 이름이 어느
    카탈로그 풀도 아니면(운영자가 풀을 개명했거나 미지의 풀) 스와치 없이
    정직하게 강등된다. 같은 풀 안의 동명 수동 프리셋 오인은 남는다 —
    슬롯 대장이 없는 한 이름 매칭의 불가피한 한계(주석으로 계약 고지).
    """
    palette: dict[str, str] = {}
    phasers: dict[str, tuple[str, ...]] = {}
    if pool_name == "Color":
        palette = _palette_hex_by_label()
        phasers = _phaser_hexes_by_label()
    elif pool_name == "Dimmer":
        palette = _dimmer_hex_by_label()
        phasers = _dimmer_phaser_hexes_by_label()
    elif pool_name.startswith("All"):
        phasers = _combo_phaser_hexes_by_label()
    enriched = []
    for obj in objects:
        base = _base_name(obj.get("name"))
        steps = phasers.get(base) if base else None
        if steps:
            enriched.append({**obj, "colors": list(steps)})
            continue
        swatch = palette.get(base) if base else None
        enriched.append({**obj, "color": swatch} if swatch else obj)
    return enriched


# 페이징 규율은 ``server/rig/paging.py`` 하나가 갖는다 (t131). 여기 사본을 두면
# 무진전 방어가 갈리고, 갈린 날 한쪽만 고쳐진다 — ``rig/section.py``가 술어를 한
# 자리로 모은 것과 같은 이유다. 이름만 이 모듈의 어휘로 남긴다.
_POOL_PAGE_CAP = PAGE_CAP
_claims_more = claims_more
_paged_pool_children = paged_children


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
        if isinstance(child_count, bool):  # bool-as-int 배제 (SEC-TYPE-002)
            child_count = None
        return {
            "pool": {"no": pool_no, "name": name if isinstance(name, str) else ""},
            "presets": _with_swatches(objects, pool_name=name if isinstance(name, str) else ""),
            "truncated": truncated,
            "total": child_count if isinstance(child_count, int) else None,
        }

    return router
