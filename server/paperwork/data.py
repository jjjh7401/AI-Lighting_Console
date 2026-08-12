"""Read-only paperwork data builders (SPEC-COPILOT-PAPERWORK-001).

Four printable documents — patch sheet, cue sheet, preset list, magic sheet —
built entirely from the SAME gate-audited query ports every other rig-context
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
    SPATIAL_PROPERTY_QUERY_CAP,
    collect_rig_sections,
    read_spatial_fixtures,
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


# -- magic sheet (REDUCED form) --------------------------------------------------
#
# The FULL magic sheet — a group tile showing which fixtures it holds — is not
# buildable and will not become buildable by fixing this module. Group
# membership is not readable on grandMA3: the `prop` ladder was walked in full
# (nine variants plus the `COUNT` accessors) and every one closed, and the four
# real groups all read `0` while a FABRICATED control group answered
# `ok:false` — which is what proves the `0` is a real read rather than a miss
# (SPEC-COPILOT-GROUPGEN-001/spec.md:361-364, progress.md:387-389).
#
# So this builder makes the REDUCED sheet: the three things that ARE readable.
#
#   1. group and preset NAMES — an operator recognises a rig by its own
#      vocabulary, and the names arrive with the pool enumeration.
#   2. a patch SUMMARY — counts and completeness, not the full row table; the
#      patch sheet already prints that and duplicating it here would give a
#      reader two places to check for one fact.
#   3. placement COORDINATES — `(fid, name, x, y, z)` per fixture. This axis
#      did NOT exist when the reduced sheet was first proposed as a
#      consolation prize; SPEC-COPILOT-SPATIAL-001 opened it afterwards, so a
#      plan-view seating chart is now MORE possible than the proposal assumed.
#
# What this sheet must never do is let a reader infer membership from
# adjacency. Group names and fixture coordinates on one page invite exactly
# that inference, so `GROUP_MEMBERSHIP_UNAVAILABLE` is not optional metadata:
# it is a required field of the dataclass, it always carries a value, and the
# renderer prints it beside the group tiles rather than in a footnote.

#: Why the group tiles carry no members. A CONSTANT, not a computed string: it
#: is a platform fact, so a build that "found nothing" and a build that never
#: could look must not be distinguishable by their wording.
GROUP_MEMBERSHIP_UNAVAILABLE = (
    "그룹 멤버십은 grandMA3에서 판독되지 않는다 — `prop` 사다리 9종과 `COUNT` 접근자가"
    " 전량 닫혔고, 실사용 그룹 4개가 모두 0을 반환하는 동안 날조 대조군은 ok:false를"
    " 반환했다(SPEC-COPILOT-GROUPGEN-001). 아래 그룹은 이름만이며, 좌표표의 픽스처가"
    " 어느 그룹에 속하는지는 이 문서로 알 수 없다."
)


@dataclass(frozen=True)
class Placement:
    """One fixture's stage position, as read off ``Patch/Stages/.../Fixtures``."""

    fid: int | None
    name: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class MagicSheet:
    """The reduced magic sheet (names + patch summary + placement).

    ``placements_complete`` is the SPATIAL/TRUNCATE coverage verdict carried
    through unchanged, and ``placements_missing`` is its arithmetic
    (``expected``/``received``/``unseen_count``) — never an adjective. A reader
    of a plan view has no way to notice an absent fixture, which is precisely
    why the shortfall has to be stated as a number on the page.
    """

    group_names: tuple[str, ...]
    group_membership_unavailable: str
    groups_unavailable_reason: str | None
    preset_names: tuple[str, ...]
    presets_unavailable_reason: str | None
    patch: PatchSheet | None
    patch_unavailable: str | None
    placements: tuple[Placement, ...]
    placements_complete: bool
    placements_missing: tuple[int | None, int, int | None]
    placements_unreadable: tuple[str, ...]


def _names_only(
    state_port: StateQueryPort, section: str, path: str
) -> tuple[tuple[str, ...], str | None]:
    """Enumerate one pool WITHOUT drilling into it.

    Empty ``drilldown`` on purpose. Drilling ``DataPool/Groups`` returns an
    empty child list for every group — that is the unreadable-membership wall,
    not an empty group — and a listing that carried those empties would render
    as "group X holds nothing", which is a claim this project cannot make.
    """
    summary, _resolved, _failed = collect_rig_sections(
        state_port, {section: path}, frozenset(), RIG_DRILLDOWN_QUERY_CAP
    )
    entry = summary[section]
    if entry is None or "reason" in entry:
        reason = entry.get("reason") if isinstance(entry, dict) else None
        return (), reason
    names = tuple(str(obj.get("name", "")) for obj in entry["objects"])
    return names, None


def build_magic_sheet(
    port: InventoryPort,
    *,
    groups_path: str = DEFAULT_RIG_CONTEXT_PATHS["groups"],
    preset_pools_path: str = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"],
    fixtures_path: str = DEFAULT_RIG_CONTEXT_PATHS["fixtures"],
    policy: InventoryPolicy | None = None,
    budget: int = SPATIAL_PROPERTY_QUERY_CAP,
) -> MagicSheet:
    """Build the reduced magic sheet from one inventory-capable port.

    Degrades per SECTION rather than raising: an unreadable patch leaves
    ``patch=None`` with ``patch_unavailable`` saying why while the group names
    and placements still render, mirroring the per-document isolation
    :func:`server.paperwork.bundle.build_handover_pack` applies one level up.
    A page that omits one section silently is the failure this splits to avoid.
    """
    group_names, groups_reason = _names_only(port, "groups", groups_path)
    preset_names, presets_reason = _names_only(port, "preset_pools", preset_pools_path)

    patch: PatchSheet | None = None
    patch_unavailable: str | None = None
    try:
        patch = build_patch_sheet(port, policy=policy)
    except InventoryReadError as error:
        patch_unavailable = str(error)

    reply = read_spatial_fixtures(port, port, fixtures_path, budget)
    # TRUNCATE-001: a partial read arrives under a DIFFERENT key and carries no
    # ``fixtures`` at all, so reading ``reply["fixtures"]`` would raise rather
    # than quietly hand back a short list. Both shapes are handled here, and
    # the branch is the same predicate the reply itself used.
    complete = "fixtures" in reply
    records = reply["fixtures"] if complete else reply["partial_fixtures"]
    placements = tuple(
        Placement(
            fid=record.get("fid") if isinstance(record.get("fid"), int) else None,
            name=str(record.get("name", "")),
            x=float(record["x"]),
            y=float(record["y"]),
            z=float(record["z"]),
        )
        for record in records  # type: ignore[union-attr]
    )
    missing = reply.get("missing") if isinstance(reply.get("missing"), dict) else None
    if missing is None:
        # The complete shape carries no ``missing`` block, and inventing one
        # here would be reporting an unobserved number. Received is the only
        # figure this branch actually knows.
        placements_missing: tuple[int | None, int, int | None] = (
            len(placements),
            len(placements),
            0,
        )
    else:
        placements_missing = (
            missing.get("expected"),
            int(missing.get("received", len(placements))),
            missing.get("unseen_count"),
        )
    unreadable = tuple(
        f"{item.get('name', '')}: {item.get('reason', '')}"
        for item in reply.get("unreadable", [])  # type: ignore[union-attr]
        if isinstance(item, dict)
    )

    return MagicSheet(
        group_names=group_names,
        group_membership_unavailable=GROUP_MEMBERSHIP_UNAVAILABLE,
        groups_unavailable_reason=groups_reason,
        preset_names=preset_names,
        presets_unavailable_reason=presets_reason,
        patch=patch,
        patch_unavailable=patch_unavailable,
        placements=placements,
        placements_complete=complete,
        placements_missing=placements_missing,
        placements_unreadable=unreadable,
    )


__all__ = [
    "PatchRow",
    "PatchSheet",
    "PoolEntry",
    "Pool",
    "PoolListing",
    "Placement",
    "MagicSheet",
    "GROUP_MEMBERSHIP_UNAVAILABLE",
    "build_patch_sheet",
    "build_cue_sheet",
    "build_preset_list",
    "build_magic_sheet",
    "InventoryReadError",
]
