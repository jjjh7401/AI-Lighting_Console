"""Read-only paperwork data builders (SPEC-COPILOT-PAPERWORK-001).

Three printable documents — patch sheet, cue sheet, preset list — built
entirely from the SAME gate-audited query ports every other rig-context
consumer uses (``server/orchestrator/tools.py``'s ``collect_rig_sections``
for the pool/drilldown shape, ``server/prechk/inventory.py``'s
``read_inventory`` for per-fixture addresses). This module never imports the
OSC send surface and never calls a command-execution port — every function
here reads a ``StateQueryPort``/``PropertyQueryPort`` and returns a plain
dataclass; nothing is ever written back to the console.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.orchestrator.ports import StateQueryPort
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    RIG_DRILLDOWN_QUERY_CAP,
    collect_rig_sections,
)
from server.prechk import footprint as _footprint
from server.prechk.footprint import WalkOutcome
from server.prechk.inventory import (
    FIXTURE_ROOT,
    InventoryPolicy,
    InventoryPort,
    InventoryReadError,
    read_inventory,
)
from server.prechk.patch import normalize_address

# -- patch sheet ----------------------------------------------------------------


@dataclass(frozen=True)
class PatchRow:
    """One fixture's printable patch-sheet row.

    ``universe``/``address`` are ``None`` when the console's own ``Patch``
    value did not parse (``normalize_address``) — the row still prints, with
    the raw text carried in ``patch_raw`` rather than a fabricated number.
    """

    slot: int
    name: str | None
    universe: int | None
    address: int | None
    patch_raw: str | None
    fixture_type: str | None
    mode: str | None


@dataclass(frozen=True)
class PatchSheet:
    """The full patch sheet: every observed fixture plus the read's own
    completeness verdict (``server.prechk.inventory.Inventory``), so an
    incomplete enumeration prints as incomplete instead of as a finished rig.

    ``bound``/``bound_source``/``bound_unavailable`` carry the channel-width
    upper bound from ``server.prechk.footprint`` (the weaker proposition that
    survived ``ASSUMPTION-27``'s refutation — see that module's docstring).
    All three default to ``None``: a caller that never passes ``walk`` to
    :func:`build_patch_sheet` gets a sheet that says nothing about a bound,
    never a fabricated "none" verdict.
    """

    root: str
    rows: tuple[PatchRow, ...]
    child_count: int
    observed_count: int
    completeness: str
    bound: int | None = None
    bound_source: str | None = None
    bound_unavailable: str | None = None


def build_patch_sheet(
    port: InventoryPort,
    *,
    policy: InventoryPolicy | None = None,
    walk: WalkOutcome | None = None,
) -> PatchSheet:
    """Build a patch sheet from the fixture inventory reader.

    Raises :class:`server.prechk.inventory.InventoryReadError` when the
    fixture root itself is unreadable — the caller reports a query failure,
    never an empty (and misleading) sheet.

    ``walk`` is the optional ``server.prechk.footprint.WalkOutcome`` from the
    channel-width upper-bound walk. When omitted the sheet's three bound
    fields stay ``None`` and the renderer emits no bound line at all. When
    present, the bound is folded via ``footprint.upper_bound`` (never a raw
    ``max`` here — an incomplete mode set would fold to a bound smaller than
    the true one and clear gaps it must not clear).
    """
    inventory = read_inventory(port, policy)
    rows = tuple(
        PatchRow(
            slot=fixture.slot,
            name=fixture.name,
            universe=normalize_address(fixture.patch_raw).universe,
            address=normalize_address(fixture.patch_raw).address,
            patch_raw=fixture.patch_raw,
            fixture_type=fixture.fixture_type,
            mode=fixture.mode,
        )
        for fixture in inventory.fixtures
    )
    bound: int | None = None
    bound_source_value: str | None = None
    bound_unavailable: str | None = None
    if walk is not None:
        bound = _footprint.upper_bound(walk)
        if bound is not None:
            bound_source_value = _footprint.bound_source(walk) or None
        else:
            bound_unavailable = walk.failure_detail or None
    return PatchSheet(
        root=FIXTURE_ROOT,
        rows=rows,
        child_count=inventory.child_count,
        observed_count=inventory.observed_count,
        completeness=inventory.completeness,
        bound=bound,
        bound_source=bound_source_value,
        bound_unavailable=bound_unavailable,
    )


# -- cue sheet / preset list (shared pool+drilldown shape) -----------------------


@dataclass(frozen=True)
class PoolEntry:
    """One drilled pool item — a sequence's cue, or a preset stored in a
    pool. ``no`` is the REAL console slot (never a list position); it is
    ``None`` for a degraded name-only child the responder could not address
    (see ``server.orchestrator.tools.rig_object``)."""

    no: int | None
    name: str


@dataclass(frozen=True)
class Pool:
    """One top-level pool object (a sequence, or a preset-pool type) plus
    what its drilldown found — a verified-empty pool, an unreachable one, or
    the items it holds."""

    no: int | None
    name: str
    items: tuple[PoolEntry, ...]
    contents_unavailable: bool


@dataclass(frozen=True)
class PoolListing:
    """A drilled section (sequences -> cues, preset pools -> presets),
    carrying the same two-failure-cause classification every rig-context
    consumer surfaces (``path_not_resolved`` vs ``console_unreachable``)."""

    path: str
    pools: tuple[Pool, ...]
    truncated: bool
    drilldown_capped: bool
    unavailable_reason: str | None = None
    unavailable_detail: str | None = None


def _build_pool_listing(
    state_port: StateQueryPort,
    section_name: str,
    path: str,
    query_cap: int,
) -> PoolListing:
    summary, _resolved, _failed = collect_rig_sections(
        state_port, {section_name: path}, frozenset({section_name}), query_cap
    )
    entry = summary[section_name]
    if entry is None or "reason" in entry:
        reason = entry.get("reason") if isinstance(entry, dict) else None
        detail = entry.get("error") if isinstance(entry, dict) else None
        return PoolListing(
            path=path,
            pools=(),
            truncated=False,
            drilldown_capped=False,
            unavailable_reason=reason,
            unavailable_detail=detail,
        )
    pools: list[Pool] = []
    for obj in entry["objects"]:
        contents = obj.get("contents")
        contents_unavailable = bool(obj.get("contents_unavailable"))
        items = (
            tuple(
                PoolEntry(no=child.get("no"), name=str(child.get("name", ""))) for child in contents
            )
            if contents is not None
            else ()
        )
        pools.append(
            Pool(
                no=obj.get("no"),
                name=str(obj.get("name", "")),
                items=items,
                contents_unavailable=contents_unavailable,
            )
        )
    return PoolListing(
        path=path,
        pools=tuple(pools),
        truncated=bool(entry.get("truncated", False)),
        drilldown_capped=bool(entry.get("drilldown_capped", False)),
    )


def build_cue_sheet(
    state_port: StateQueryPort,
    *,
    sequences_path: str = DEFAULT_RIG_CONTEXT_PATHS["sequences"],
    query_cap: int = RIG_DRILLDOWN_QUERY_CAP,
) -> PoolListing:
    """Build a cue sheet: every sequence, drilled one level into its cues."""
    return _build_pool_listing(state_port, "sequences", sequences_path, query_cap)


def build_preset_list(
    state_port: StateQueryPort,
    *,
    preset_pools_path: str = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"],
    query_cap: int = RIG_DRILLDOWN_QUERY_CAP,
) -> PoolListing:
    """Build a preset list: every preset-pool type, drilled into the presets
    actually stored inside it."""
    return _build_pool_listing(state_port, "preset_pools", preset_pools_path, query_cap)


__all__ = [
    "PatchRow",
    "PatchSheet",
    "PoolEntry",
    "Pool",
    "PoolListing",
    "build_patch_sheet",
    "build_cue_sheet",
    "build_preset_list",
    "InventoryReadError",
]
