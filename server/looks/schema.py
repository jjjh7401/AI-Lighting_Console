"""Look schema — the shared data shape of the choreography layer (REQ-LOOKLIB-001/003/004).

A look is one stage picture: which position roles are lit, at which colour and
intensity (and, where the console accepts them, beam values), at which point on
the section-dynamics scale. Rig binding happens at instantiation time, never
here.

The attribute vocabulary is split into three bands (REQ-LOOKLIB-003):

1. Repository-measured, unconditionally allowed — ``Dimmer`` and the three
   ``ColorRGB_*`` channels.
2. Use-qualified — ``Pan`` / ``Tilt``, legal ONLY inside a movement spec. As a
   static value they are exactly the hard pan/tilt the SPEC forbids, so they
   belong to no preset pool and the loader rejects them in the payload.
3. Probe-gated beam vocabulary — resolved by the M0 live probe to ``Zoom`` and
   ``Iris``. ``Focus`` / ``Frost`` / ``Prism1`` / ``Shutter`` were rejected by
   the console and never entered. Strobe and shutter are out of scope
   regardless: ``server/web/preview.py:131-139`` classifies them ``danger``.

# @MX:NOTE: [AUTO] this schema is the common foundation P1-1 (song-structure
#   cuelist generator) and P1-2 (busking wizard) are both specified to consume,
#   so a breaking change here breaks two downstream SPECs at once. The closed
#   field set is also the mechanism enforcing REQ-LOOKLIB-004: there is no
#   group number, preset slot, FID or executor field to put a per-show value in,
#   and the loader rejects unknown keys so one cannot be added by accident.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

SCHEMA_VERSION = 1

DYNAMICS_MIN = 1
DYNAMICS_MAX = 5

# Band 1 — measured present in this repository.
CONFIRMED_ATTRIBUTES: tuple[str, ...] = (
    "Dimmer",
    "ColorRGB_R",
    "ColorRGB_G",
    "ColorRGB_B",
)

# Band 2 — movement-only (31_choreography_patterns.md:69).
MOVEMENT_ONLY_ATTRIBUTES: tuple[str, ...] = ("Pan", "Tilt")

# Band 3 — the M0 probe accepted exactly these (progress.md §E.2 measurement 1).
PROBE_GATED_ATTRIBUTES: tuple[str, ...] = ("Zoom", "Iris")

KNOWN_ATTRIBUTES = frozenset(
    CONFIRMED_ATTRIBUTES + MOVEMENT_ONLY_ATTRIBUTES + PROBE_GATED_ATTRIBUTES
)

# The pools v1 writes into. Position/All/Gobo/Control/Shapers/Video are out of
# scope (spec.md §D), so no attribute may route to them.
IN_SCOPE_POOL_FAMILIES: tuple[str, ...] = ("Dimmer", "Color", "Beam", "Focus")

# Family boundaries per 10_object_model.md:38-40 — Beam = iris/prism/frost,
# Focus = zoom/focus. Pan/Tilt are absent by design: they have no pool.
ATTRIBUTE_POOL_FAMILY: Mapping[str, str] = {
    "Dimmer": "Dimmer",
    "ColorRGB_R": "Color",
    "ColorRGB_G": "Color",
    "ColorRGB_B": "Color",
    "Iris": "Beam",
    "Zoom": "Focus",
}


def pool_family(attribute: str) -> str | None:
    """Return the preset pool family for an attribute, or ``None`` if it has none."""
    return ATTRIBUTE_POOL_FAMILY.get(attribute)


@dataclass(frozen=True)
class AttributeValue:
    """One concrete attribute value, e.g. ``Attribute 'Dimmer' At 80``."""

    name: str
    value: float


@dataclass(frozen=True)
class MovementSpec:
    """A phaser specification, shaped after the validated phaser grammar.

    ``Attribute 'Pan' At Relative 30`` / ``At Phase 0 Thru 360`` / ``At Speed 60``
    (31_choreography_patterns.md:61-94).

    v1 defines this field but does not emit it, and the v1 library carries no
    movement at all — the same "field defined, library unused" shape the beam
    DESCOPE branch would have taken.
    """

    attribute: str
    phase_from: float
    phase_to: float | None = None
    speed: float | None = None
    relative: float | None = None


@dataclass(frozen=True)
class Look:
    """One look. Carries no rig binding — see the module @MX:NOTE."""

    look_id: str
    display_name: str
    genre: str
    dynamics: int
    roles: tuple[str, ...]
    attributes: tuple[AttributeValue, ...]
    aliases: tuple[str, ...] = ()
    mood_keywords: tuple[str, ...] = ()
    movement: tuple[MovementSpec, ...] = ()


@dataclass(frozen=True)
class LookLibrary:
    """The loaded, validated set of looks."""

    schema_version: int
    looks: tuple[Look, ...] = field(default_factory=tuple)

    def by_id(self, look_id: str) -> Look:
        for look in self.looks:
            if look.look_id == look_id:
                return look
        raise KeyError(look_id)


def payload_for_family(look: Look, family: str) -> tuple[AttributeValue, ...]:
    """Return only this look's values belonging to one preset pool family.

    The bundle builder needs this if the M0 ASSUMPTION-14 FALLBACK branch is
    ever taken: an isolated per-family capture cycle can only be generated from
    the same look data if the payload splits cleanly by family. Because the
    loader rejects any attribute without a family, the union of all four family
    subsets is always the whole payload.
    """
    if family not in IN_SCOPE_POOL_FAMILIES:
        raise ValueError(
            f"{family!r} is not an in-scope preset pool family; "
            f"expected one of {list(IN_SCOPE_POOL_FAMILIES)}"
        )
    return tuple(a for a in look.attributes if ATTRIBUTE_POOL_FAMILY.get(a.name) == family)


def movement_to_dict(spec: MovementSpec) -> dict:
    """Serialise a movement spec, omitting the parts that were not set."""
    data: dict = {"attribute": spec.attribute, "phase_from": spec.phase_from}
    for key in ("phase_to", "speed", "relative"):
        value = getattr(spec, key)
        if value is not None:
            data[key] = value
    return data


def look_to_dict(look: Look) -> dict:
    """Serialise a look back to its wire form; ``load`` of this is the same look."""
    return {
        "look_id": look.look_id,
        "display_name": look.display_name,
        "genre": look.genre,
        "dynamics": look.dynamics,
        "roles": list(look.roles),
        "aliases": list(look.aliases),
        "mood_keywords": list(look.mood_keywords),
        "attributes": {a.name: a.value for a in look.attributes},
        "movement": [movement_to_dict(m) for m in look.movement],
    }
