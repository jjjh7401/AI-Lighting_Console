"""Turn one look into a console command bundle + an honest report (REQ-LOOKLIB-010..013).

This module BUILDS text. It never sends any: the returned bundle is handed to
the existing ``run_commands`` tool, which screens it through the one gate path.
There is no execution surface here and no import of one.

# @MX:NOTE: [AUTO] the destination/ClearAll discipline below is mechanised, not
#   conventional. MA3 tracks: values left in the programmer TRACK into the next
#   capture and silently corrupt it (31_choreography_patterns.md:40-41), and a
#   Store from an EMPTY programmer still creates a preset rather than failing
#   (M0 measurement 4's discarded control) — so both mistakes are silent. Every
#   Store therefore lives inside a ClearAll-delimited capture cycle, and the
#   bundle closes with a ClearAll so the next bundle starts clean.

Two capture shapes are generated from the same look data, which is what
REQ-LOOKLIB-001's family-splittability rule exists for:

``CAPTURE_SHARED``
    One capture, then one ``Store`` per pool. This is the M0 ASSUMPTION-14 GO
    shape and the default. It relies on ``Store Preset`` capturing only the
    values belonging to that pool's family.

``CAPTURE_PER_FAMILY``
    One isolated cycle per family. Depends on no capture semantics at all,
    because the programmer holds exactly one family's values at store time.
    This is the M0 FALLBACK branch, which stays live: the GO verdict is
    structurally inferred, not directly observed (progress.md §E.2 measurement
    4 + gap G3).

Selecting between them is a keyword argument, not a rewrite.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.looks.resolver import GroupCandidate, RoleResolution, UnmappedRole, resolve_roles
from server.looks.schema import IN_SCOPE_POOL_FAMILIES, AttributeValue, Look, payload_for_family

__all__ = [
    "CAPTURE_PER_FAMILY",
    "CAPTURE_SHARED",
    "CONFLICT",
    "NO_FREE_SLOT",
    "POOL_UNADDRESSABLE",
    "POOL_UNRESOLVED",
    "CreatedPreset",
    "LookInstantiation",
    "LookInstantiationError",
    "PoolBinding",
    "PoolIndex",
    "SkippedStore",
    "build_instantiation",
    "instantiate_look",
    "resolve_pools",
]

CAPTURE_SHARED = "shared_capture"
CAPTURE_PER_FAMILY = "per_family_capture"
CAPTURE_SHAPES = (CAPTURE_SHARED, CAPTURE_PER_FAMILY)

# Why one intended preset store did not happen. Kept apart rather than summed:
# each names a different rig state and a different repair.
CONFLICT = "conflict"  # this pool already holds a preset with this look's name
NO_FREE_SLOT = "no_free_slot"  # no free slot was OBSERVED (incl. never opened)
POOL_UNRESOLVED = "pool_unresolved"  # no pool name resolves to this family
POOL_UNADDRESSABLE = "pool_unaddressable"  # a pool does, and carries no number

_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"


class LookInstantiationError(ValueError):
    """Raised when a look cannot be turned into a well-formed bundle."""


@dataclass(frozen=True)
class PoolBinding:
    """What the rig said about the pool holding one attribute family.

    ``occupied`` is ``None`` when occupancy was never observed — an unopened
    pool, a failed drill, or a pool holding a preset the responder could not
    number. That is NOT the same as an empty pool (``()``), and treating it as
    one is how a store lands on top of somebody's work.
    """

    family: str
    number: int | None = None
    name: str = ""
    occupied: tuple[int, ...] | None = None
    labels: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class PoolIndex:
    """The in-scope pool families, resolved against one preset_pools section."""

    bindings: Mapping[str, PoolBinding]
    drilldown_capped: bool = False
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class CreatedPreset:
    """One preset the bundle stores (REQ-LOOKLIB-013 (a))."""

    family: str
    pool: int
    slot: int
    label: str


@dataclass(frozen=True)
class SkippedStore:
    """One preset store that did NOT happen, and why (REQ-LOOKLIB-013 (c)).

    The unit is one preset store, never one look: a look whose Color slot is
    free while its Dimmer pool already holds it is ``1 created + 1 skipped``,
    and a look-unit count cannot say that (design.md AP-15).
    """

    family: str
    reason: str
    pool: int | None = None
    slot: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class LookInstantiation:
    """The bundle plus the four-element report of what it does and does not do."""

    look_id: str
    display_name: str
    capture_shape: str
    commands: tuple[str, ...] = ()
    created: tuple[CreatedPreset, ...] = ()
    unmapped: tuple[UnmappedRole, ...] = ()
    skipped: tuple[SkippedStore, ...] = ()
    drilldown_capped: bool = False
    bound: Mapping[str, tuple[GroupCandidate, ...]] = None  # type: ignore[assignment]

    @property
    def skipped_count(self) -> int:
        """N in "N개 건너뜀" — skipped preset STORES, not skipped looks."""
        return len(self.skipped)

    @property
    def complete(self) -> bool:
        """True only when nothing was dropped — partial runs never read as whole."""
        return not self.skipped and not self.unmapped

    def to_dict(self) -> dict:
        """The structured summary (REQ-LOOKLIB-013 (a)-(d))."""
        return {
            "look_id": self.look_id,
            "display_name": self.display_name,
            "capture_shape": self.capture_shape,
            "complete": self.complete,
            "created": [
                {"family": c.family, "pool": c.pool, "slot": c.slot, "label": c.label}
                for c in self.created
            ],
            "unmapped": [
                {"role": u.role, "reason": u.reason, "groups": list(u.groups)}
                for u in self.unmapped
            ],
            "skipped": [
                {
                    "family": s.family,
                    "reason": s.reason,
                    "pool": s.pool,
                    "slot": s.slot,
                    "detail": s.detail,
                }
                for s in self.skipped
            ],
            "skipped_count": self.skipped_count,
            "drilldown_capped": self.drilldown_capped,
            "mapped": [
                {"role": role, "groups": [{"no": g.number, "name": g.name} for g in groups]}
                for role, groups in (self.bound or {}).items()
            ],
            "commands": list(self.commands),
        }


# -- pool resolution -----------------------------------------------------------


def _observed_contents(
    entry: Mapping[str, object],
) -> tuple[tuple[int, ...], tuple[str, ...]] | None:
    """Slots and labels in this pool, or ``None`` when occupancy is unknown."""
    if entry.get("contents_unavailable"):
        return None
    contents = entry.get("contents")
    if not isinstance(contents, list):
        return None  # the drill never opened this pool — it said nothing at all
    slots: list[int] = []
    labels: list[str] = []
    for child in contents:
        if not isinstance(child, Mapping):
            return None
        number = child.get("no")
        if number is None:
            # Some slot in here is taken and the responder could not say which,
            # so no slot in this pool can be claimed free.
            return None
        slots.append(int(number))
        labels.append(str(child.get("name", "")))
    return tuple(slots), tuple(labels)


def resolve_pools(preset_pools_section: Mapping[str, object]) -> PoolIndex:
    """Bind each in-scope attribute family to the rig's own preset pool.

    Pool NUMBERS are read from the section, never assumed: ``Preset 4.1 = Color``
    is example prose in the rulebook (``00_grammar.md:18``), not this showfile's
    contract, and the pool names it keys on are user-editable (design.md AP-16).
    """
    unavailable = preset_pools_section.get("reason")
    if isinstance(unavailable, str):
        return PoolIndex(
            bindings={
                family: PoolBinding(family=family, reason=unavailable)
                for family in IN_SCOPE_POOL_FAMILIES
            },
            unavailable_reason=unavailable,
        )

    objects = preset_pools_section.get("objects")
    listed: Sequence[object] = objects if isinstance(objects, list) else ()

    bindings: dict[str, PoolBinding] = {}
    for family in IN_SCOPE_POOL_FAMILIES:
        numbered: Mapping[str, object] | None = None
        named: Mapping[str, object] | None = None
        for entry in listed:
            if not isinstance(entry, Mapping):
                continue
            # Whole-name match only. "Color Fx Backup" is not the Color pool,
            # and a substring rule would aim stores at whatever sat nearby.
            if str(entry.get("name", "")).strip().casefold() != family.casefold():
                continue
            if entry.get("no") is None:
                named = named or entry
            else:
                numbered = numbered or entry
        if numbered is not None:
            observed = _observed_contents(numbered)
            bindings[family] = PoolBinding(
                family=family,
                number=int(numbered["no"]),  # type: ignore[arg-type]
                name=str(numbered.get("name", "")),
                occupied=None if observed is None else observed[0],
                labels=() if observed is None else observed[1],
            )
        elif named is not None:
            # The pool IS there; the responder just could not number it. Folding
            # this into "no such pool" would erase a fact with a different fix
            # (give the pool a slot) — the same split M3 made for groups.
            bindings[family] = PoolBinding(
                family=family,
                name=str(named.get("name", "")),
                reason=POOL_UNADDRESSABLE,
            )
        else:
            bindings[family] = PoolBinding(family=family, reason=POOL_UNRESOLVED)

    return PoolIndex(
        bindings=bindings,
        drilldown_capped=bool(preset_pools_section.get("drilldown_capped", False)),
    )


# -- bundle construction -------------------------------------------------------


def _format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _values_line(values: Sequence[AttributeValue]) -> str:
    # Independent sets chain on ONE line with ';' (31_choreography_patterns.md).
    return " ; ".join(f"Attribute '{v.name}' At {_format_value(v.value)}" for v in values)


# @MX:WARN: [AUTO] every number this function puts on the command line must have
#   come from the rig — group numbers from the resolver, pool numbers and free
#   slots from the drilled preset_pools section.
# @MX:REASON: REQ-LOOKLIB-008/012 + AP-16. The tempting repairs all write to the
#   wrong place silently: substituting a group for an unmapped role, assuming an
#   unopened pool is empty, hardcoding `Preset 4.x` because the rulebook prose
#   uses it, or reaching for `/Overwrite` when a slot is taken. A store aimed at
#   a wrong slot destroys a preset the operator built by hand, and MA3 reports
#   it as success.
def _selection_line(groups: Sequence[GroupCandidate]) -> str:
    # Additive object selection (00_grammar.md "Object references"). The single
    # form `Group 11` is live-validated; the additive form is grammar-derived
    # and awaits the M7 live session.
    return "Group " + " + ".join(str(g.number) for g in groups)


def _first_free_slot(occupied: Sequence[int]) -> int:
    taken = set(occupied)
    slot = 1
    while slot in taken:
        slot += 1
    return slot


def _label_of(look: Look) -> str:
    label = look.display_name
    if "'" in label or "\n" in label:
        raise LookInstantiationError(
            f"look {look.look_id!r} has a display name that cannot be quoted on the "
            f"MA3 command line: {label!r}"
        )
    return label


def _plan_stores(
    look: Look, label: str, pools: PoolIndex
) -> tuple[list[tuple[str, CreatedPreset, tuple[AttributeValue, ...]]], list[SkippedStore]]:
    """Decide, per family the look has values in, whether a store can happen."""
    planned: list[tuple[str, CreatedPreset, tuple[AttributeValue, ...]]] = []
    skipped: list[SkippedStore] = []
    for family in IN_SCOPE_POOL_FAMILIES:
        values = payload_for_family(look, family)
        if not values:
            continue  # this look simply has nothing for this family
        binding = pools.bindings[family]
        if binding.reason is not None:
            skipped.append(
                SkippedStore(
                    family=family,
                    reason=binding.reason,
                    pool=binding.number,
                    detail=f"no addressable {family} pool in this rig",
                )
            )
            continue
        if binding.occupied is None:
            skipped.append(
                SkippedStore(
                    family=family,
                    reason=NO_FREE_SLOT,
                    pool=binding.number,
                    detail=(
                        "pool occupancy was not observed, so no slot in it can be claimed free"
                    ),
                )
            )
            continue
        slot = _first_free_slot(binding.occupied)
        if any(
            existing.strip().casefold() == label.strip().casefold() for existing in binding.labels
        ):
            skipped.append(
                SkippedStore(
                    family=family,
                    reason=CONFLICT,
                    pool=binding.number,
                    slot=slot,
                    detail=f"pool {binding.number} already holds a preset named {label!r}",
                )
            )
            continue
        planned.append(
            (
                family,
                CreatedPreset(
                    family=family,
                    pool=binding.number,  # type: ignore[arg-type]
                    slot=slot,
                    label=label,
                ),
                values,
            )
        )
    return planned, skipped


def _bundle(
    shape: str,
    selection: str,
    planned: Sequence[tuple[str, CreatedPreset, tuple[AttributeValue, ...]]],
    look: Look,
) -> tuple[str, ...]:
    if not planned:
        return ()
    commands: list[str] = [_DESTINATION]
    if shape == CAPTURE_SHARED:
        commands.append(_CLEAR)
        commands.append(selection)
        commands.append(_values_line(look.attributes))
        for _family, preset, _values in planned:
            commands.append(f"Store Preset {preset.pool}.{preset.slot}")
            commands.append(f"Label Preset {preset.pool}.{preset.slot} '{preset.label}'")
        commands.append(_CLEAR)
        return tuple(commands)

    for _family, preset, values in planned:
        commands.append(_CLEAR)
        commands.append(selection)
        commands.append(_values_line(values))
        commands.append(f"Store Preset {preset.pool}.{preset.slot}")
        commands.append(f"Label Preset {preset.pool}.{preset.slot} '{preset.label}'")
    commands.append(_CLEAR)
    return tuple(commands)


def build_instantiation(
    look: Look,
    *,
    resolution: RoleResolution,
    pools: PoolIndex,
    shape: str = CAPTURE_SHARED,
) -> LookInstantiation:
    """Build the bundle and report for one look against one resolved rig."""
    if shape not in CAPTURE_SHAPES:
        raise LookInstantiationError(
            f"unknown capture shape {shape!r}; expected one of {list(CAPTURE_SHAPES)}"
        )
    label = _label_of(look)

    bound: dict[str, tuple[GroupCandidate, ...]] = {}
    unmapped: list[UnmappedRole] = []
    for role in look.roles:
        candidates = resolution.groups_for(role)
        if candidates:
            bound[role] = candidates
            continue
        entry = resolution.unmapped_for(role)
        # A role the rig could not address contributes NO group and no
        # substitute (REQ-LOOKLIB-009, AP-2). The resolver's contract is that
        # every mapped candidate carries its number, so there is no shape here
        # that could emit an address the rig did not supply.
        if entry is not None:
            unmapped.append(entry)

    selected = sorted({g.number: g for gs in bound.values() for g in gs}.items())
    groups = tuple(g for _number, g in selected)

    empty = LookInstantiation(
        look_id=look.look_id,
        display_name=label,
        capture_shape=shape,
        unmapped=tuple(unmapped),
        drilldown_capped=pools.drilldown_capped,
        bound=bound,
    )
    if not groups:
        # Nothing to select means nothing to capture. An empty bundle is the
        # honest output; a smaller one aimed at whatever else is lying around
        # is not.
        return empty

    planned, skipped = _plan_stores(look, label, pools)
    return LookInstantiation(
        look_id=look.look_id,
        display_name=label,
        capture_shape=shape,
        commands=_bundle(shape, _selection_line(groups), planned, look),
        created=tuple(preset for _family, preset, _values in planned),
        unmapped=tuple(unmapped),
        skipped=tuple(skipped),
        drilldown_capped=pools.drilldown_capped,
        bound=bound,
    )


def instantiate_look(
    look: Look,
    *,
    groups_section: Mapping[str, object],
    preset_pools_section: Mapping[str, object],
    shape: str = CAPTURE_SHARED,
) -> LookInstantiation:
    """Resolve roles and pools from raw rig-context sections, then build."""
    return build_instantiation(
        look,
        resolution=resolve_roles(groups_section),
        pools=resolve_pools(preset_pools_section),
        shape=shape,
    )
