"""Console-info dashboard catalog builder (SPEC-COPILOT-DASHUI-001 M2).

Builds the read-only ``dash_catalog`` sections the left-hand dashboard
consumes: groups, preset pools (drilled), macros, plugins, a fixture-count
summary, and an executor-resolution report. Every section rides the SAME
gate-audited ``state_port`` seam ``get_rig_context``/``build_catalog`` use, and
reuses ``server/orchestrator/tools.py``'s shared rig-shape helpers so the
real-`no` rule, the truncation signal, and the two-failure-cause distinction
have exactly one implementation (REQ-DASHUI-004).

Chokepoint discipline (REQ-DASHUI-016/019): like ``server/web/panel.py``, this
module holds NO execution surface of its own — it never imports the OSC send
surface and never will.

Scope decision (plan.md §B M2, documented judgment call): ``dash_catalog``
carries the read-only info sections REQ-DASHUI-007 names (groups / presets /
plugins / fixture-summary) plus macros — macros are ALSO fireable via
``panel_catalog``'s additive ``macro`` target_kind (see ``panel.py``
``PANEL_CATALOG_SECTIONS``), but design.md §2 Zone C still wants a read-only
reference row for them. Sequences and Executors are NOT duplicated here as
info rows; ``panel_catalog`` (SHOWUI M2/M3, UNCHANGED by this module) is
already the single source for both — everything a dashboard tile needs
(number, name, appearance) is already on that shape. What THIS module adds
for executors is narrower and REQ-DASHUI-011-specific: a
resolution-transparency report, so the UI can learn which page-drilled
executor candidates the console's own address form actually confirms.
``panel_catalog``'s own (frozen, SHOWUI-owned) executor generation is
intentionally left untouched here; wiring that resolution verdict into what
the dashboard actually renders as a press-able tile is an M3-M5 UI concern.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from server.orchestrator.ports import StateQueryPort
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    drill_into,
    rig_object,
    rig_section,
)
from server.web.messages import dash_catalog_event, dash_item, dash_section

# Per-section drilldown budgets (plan.md §B M2 item 2 / design.md §5 "섹션별
# 유계 예산으로 분리(M2 수치 확정)"). Sharing panel.py's single
# PANEL_DRILLDOWN_QUERY_CAP (16) across preset pools (~8-10 TYPES per
# tools.py's header) AND the executor page-walk AND the executor
# resolution-verify step would always cap one at the others' expense, so each
# concern below gets its OWN bounded budget instead. The exact figures are a
# documented M2 choice — REQ-DASHUI-008 requires BOUNDEDNESS, not a specific
# number.

# Preset pools drilldown: tools.py names ~8-10 preset TYPES; 12 gives a
# typical showfile headroom while staying bounded.
DASH_PRESET_POOL_QUERY_CAP = 12

# Executor page walk: one query per page opened (usually few pages).
DASH_EXECUTOR_PAGE_QUERY_CAP = 8

# Executor resolution: one "Executor <n>" verification query per candidate,
# bounded separately from the page walk since it is a distinct query class.
DASH_EXECUTOR_VERIFY_QUERY_CAP = 16


@dataclass(frozen=True)
class _DashSectionSpec:
    """One flat / drilldown / count-only dash source."""

    name: str
    path: str
    drilldown: bool = False
    count_only: bool = False


# design.md §2 Zone B/C priority order, minus Sequences/Executors' FIREABLE
# half (panel_catalog owns that — see module docstring).
_DASH_SECTIONS = (
    _DashSectionSpec(name="groups", path=DEFAULT_RIG_CONTEXT_PATHS["groups"]),
    _DashSectionSpec(
        name="preset_pools", path=DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], drilldown=True
    ),
    _DashSectionSpec(name="macros", path=DEFAULT_RIG_CONTEXT_PATHS["macros"]),
    _DashSectionSpec(name="plugins", path=DEFAULT_RIG_CONTEXT_PATHS["plugins"]),
    _DashSectionSpec(name="fixtures", path=DEFAULT_RIG_CONTEXT_PATHS["fixtures"], count_only=True),
)


def _flat_items(objects: list[dict]) -> list[dict]:
    return [
        dash_item(no=obj["no"], name=str(obj.get("name", "")))
        for obj in objects
        if obj.get("no") is not None
    ]


def _drilldown_items(objects: list[dict]) -> list[dict]:
    """One dash_item per opened pool, with a ``meta`` note on what the drill
    found — the "there IS a pool" vs "something IS stored in it" distinction
    (acceptance.md §D edge case 3), never collapsed into a bare pool list.
    """
    items: list[dict] = []
    for obj in objects:
        no = obj.get("no")
        if no is None:
            continue
        if obj.get("contents_unavailable"):
            meta = {"contents_unavailable": True}
        else:
            contents = obj.get("contents")
            meta = {"stored_count": len(contents)} if contents is not None else None
        items.append(dash_item(no=no, name=str(obj.get("name", "")), meta=meta))
    return items


def _count_only_items(entry: dict, objects: list[dict]) -> list[dict]:
    """REQ-DASHUI-009: a count summary, never a per-fixture listing — the
    slot != FID trap is avoided structurally by never presenting a slot
    number at all (design.md §2 point 4, "목록 미제시로 구조적으로 회피").
    """
    total = entry.get("total")
    count = total if isinstance(total, int) else len(objects)
    return [dash_item(no=1, name="", meta={"count": count})]


def _confirm_executor_no(
    state_port: StateQueryPort, candidate_no: int, expected_name: str
) -> bool:
    """One name-verified probe of the console's "Executor <n>" address form —
    the SAME form ``server/safety/console.py::StateBodyFetcher.
    _fetch_executor_body`` and the EXECBODY-001 responder
    ``resolve_path``/``ObjectList`` path use."""
    try:
        identity = state_port.query_state(f"Executor {candidate_no}")
    except Exception:
        return False
    node = identity.get("node") if isinstance(identity, dict) else None
    resolved_name = node.get("name") if isinstance(node, dict) else None
    return resolved_name == expected_name


def _executor_candidates(slot_no: int, page_no: int | None) -> list[int]:
    """Console-number candidates for one page-drilled executor slot.

    The page drilldown's pool-slot number is NOT assumed to be the
    console-displayed executor number (EXECBODY design.md §5.8's
    "reverse-address problem"). Live-measured on onPC 2.4.2 (2026-07-24,
    DASHUI M6 root-cause probe): the console form is ``page_no*100 + slot``
    ("Executor 101" is page 1 slot 1; the raw slot is not addressable). The
    raw slot stays FIRST for backward compatibility with consoles that do
    address it directly; every candidate is name-VERIFIED before being
    believed and an unconfirmed candidate is never emitted (EXECBODY
    AC-016's inherited principle — no child-index or offset guessing).
    """
    candidates = [slot_no]
    if page_no is not None:
        page_form = page_no * 100 + slot_no
        if page_form != slot_no:
            candidates.append(page_form)
    return candidates


def _build_executors_section(
    state_port: StateQueryPort,
    pages_path: str,
    *,
    page_query_cap: int,
    verify_query_cap: int,
) -> tuple[dict | None, bool]:
    """The resolution-transparency report REQ-DASHUI-011 requires: which
    page-drilled executor candidates the console actually confirms.

    ``panel_catalog``'s own executor tiles (server/web/panel.py, SHOWUI
    M2/M3) are UNCHANGED by this function — this is read-only reporting, so
    an unresolved candidate is DOCUMENTED here (``meta.resolved: False``),
    never silently hidden and never used to filter the existing (frozen)
    playback catalog. Wiring that verdict into press-ability is an M3-M5 UI
    concern (progress.md §E.2 M2 evidence names this as a Gap).

    Returns ``(section, resolved)`` — ``resolved`` feeds the SAME
    two-failure-cause classification the other dash sections use, so a
    console that answered only the pages path (and nothing else) still
    reports every OTHER failed section as ``path_not_resolved``, not
    ``console_unreachable``, and vice versa.
    """
    try:
        pages_payload = state_port.query_state(pages_path)
    except Exception:
        return None, False

    page_children = pages_payload.get("children", [])
    pages = [rig_object(child) for child in page_children if isinstance(child, dict)]
    entry = rig_section(pages, pages_payload)
    drill_into(state_port, pages, pages_path, entry, page_query_cap)

    candidates: list[tuple[int, int | None, str]] = []
    for page in pages:
        page_no = page.get("no")
        for child in page.get("contents", []):
            no = child.get("no")
            if no is None:
                continue
            candidates.append((no, page_no, str(child.get("name", ""))))

    verify_budget = verify_query_cap
    capped = bool(entry.get("drilldown_capped"))
    items: list[dict] = []
    for no, page_no, name in candidates:
        if verify_budget <= 0:
            capped = True
            break
        resolved_no: int | None = None
        for candidate_no in _executor_candidates(no, page_no):
            if verify_budget <= 0:
                capped = True
                break
            verify_budget -= 1
            if _confirm_executor_no(state_port, candidate_no, name):
                resolved_no = candidate_no
                break
        # The item's `no` stays the POOL SLOT (onPC pool-window parity); the
        # verified console number rides `meta.console_no` and is the ONLY
        # number a press may target (AC-DASHUI-005 — 해석된 콘솔 번호).
        meta: dict[str, object] = {"resolved": resolved_no is not None}
        if resolved_no is not None:
            meta["console_no"] = resolved_no
        items.append(dash_item(no=no, name=name, meta=meta))

    section = dash_section(
        name="executors",
        status="ok",
        items=items,
        truncated=bool(entry.get("truncated")),
        drilldown_capped=capped,
        contents_unavailable=any(p.get("contents_unavailable") for p in pages),
    )
    return section, True


def build_dash_catalog(
    state_port: StateQueryPort,
    *,
    paths: dict[str, str] | None = None,
    preset_pool_query_cap: int = DASH_PRESET_POOL_QUERY_CAP,
    executor_page_query_cap: int = DASH_EXECUTOR_PAGE_QUERY_CAP,
    executor_verify_query_cap: int = DASH_EXECUTOR_VERIFY_QUERY_CAP,
) -> list[dict]:
    """Build every dash_catalog section (REQ-DASHUI-005/007/008/009/011)."""
    overrides = dict(paths or {})
    sections: list[dict | None] = []
    failed: list[tuple[int, str]] = []
    resolved = 0

    for spec in _DASH_SECTIONS:
        path = overrides.get(spec.name, spec.path)
        try:
            payload = state_port.query_state(path)
        except Exception:
            failed.append((len(sections), spec.name))
            sections.append(None)
            continue
        resolved += 1
        children = payload.get("children", [])
        objects = [rig_object(child) for child in children if isinstance(child, dict)]
        entry = rig_section(objects, payload)
        contents_unavailable = False
        if spec.count_only:
            items = _count_only_items(entry, objects)
        elif spec.drilldown:
            drill_into(state_port, objects, path, entry, preset_pool_query_cap)
            contents_unavailable = any(obj.get("contents_unavailable") for obj in objects)
            items = _drilldown_items(objects)
        else:
            items = _flat_items(objects)
        sections.append(
            dash_section(
                name=spec.name,
                status="ok",
                items=items,
                truncated=bool(entry.get("truncated")),
                drilldown_capped=bool(entry.get("drilldown_capped")),
                contents_unavailable=contents_unavailable,
            )
        )

    executors_section, executors_resolved = _build_executors_section(
        state_port,
        overrides.get("pages", DEFAULT_RIG_CONTEXT_PATHS["pages"]),
        page_query_cap=executor_page_query_cap,
        verify_query_cap=executor_verify_query_cap,
    )
    if executors_resolved:
        resolved += 1
        sections.append(executors_section)
    else:
        failed.append((len(sections), "executors"))
        sections.append(None)

    status = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE
    for index, name in failed:
        sections[index] = dash_section(name=name, status=status, items=[])

    return [s for s in sections if s is not None]


def resolved_executor_nos(sections: list[dict]) -> list[int]:
    """The console-VERIFIED executor numbers of one dash catalog build.

    These are the only numbers a dash executor press may target
    (AC-DASHUI-005), and therefore the numbers the panel membership must
    recognise — the SHOWUI catalog's own executor tiles carry the page
    drill's POOL SLOTS, which the console does not address (live-measured:
    page 1 slot 1 is "Executor 101").
    """
    numbers: list[int] = []
    for section in sections:
        if section.get("name") != "executors":
            continue
        for item in section.get("items", []):
            meta = item.get("meta") or {}
            console_no = meta.get("console_no")
            if meta.get("resolved") is True and isinstance(console_no, int):
                numbers.append(console_no)
    return numbers


def dash_catalog_snapshot(state_port: StateQueryPort, **kwargs: object) -> dict:
    """The full ``dash_catalog`` server event for one refresh (REQ-DASHUI-006).

    A refresh REPLACES the whole section list — no server-side caching, no
    merge with a previous build (REQ-DASHUI-021 refresh-on-demand only).
    """
    return dash_catalog_event(sections=build_dash_catalog(state_port, **kwargs))


def send_dash_catalog(
    state_port: StateQueryPort, send_event: Callable[[dict], None], **kwargs: object
) -> dict:
    """Build + emit one dash_catalog snapshot.

    Synchronous (worker thread) — like ``PanelRuntime.send_catalog``, the
    read is a bounded set of console round trips through the gate-audited
    state port, so callers run it off the event loop.
    """
    event = dash_catalog_snapshot(state_port, **kwargs)
    send_event(event)
    return event
