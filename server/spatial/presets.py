"""Preset geometry — the target coordinates a WRITE arranges fixtures onto
(REQ-SPATIAL-019, design.md §6.6, AC-SPATIAL-018).

Three shapes, ``grid`` / ``row`` / ``circle``, computed from standard-library
arithmetic only. Like the rest of this package the layer is PURE: it reads no
console, sends nothing, and knows nothing about how a coordinate eventually
reaches a fixture. It answers one question — *where should fixture N end up* —
and the answer is a number, deterministic for a given request.

**The origin is the centre of the stage, so negative coordinates are normal.**
Every shape here is centred on ``origin``: an 8-fixture row at the default 1.0 m
spacing lands on x = -3.5 .. +3.5, which is not a synthetic example but the exact
placement the M0 P8 live probe wrote and read back on onPC 2.4.2
(progress.md §E.2.7). A preset layer that could not produce a negative number
would have failed that probe, so the sign discipline is golden-tested rather
than assumed (acceptance.md §D — negative coordinates).

**Defaults are documented, not implicit.** ``spacing``, ``origin`` and
``orientation`` are parsed from the user's request; what the user did not say
comes from :data:`SPATIAL_PRESET_DEFAULTS` and is echoed back on the plan as
``resolved`` — a report that states "1.0 m spacing about (0,0,0)" is auditable,
one that silently applied it is not. The parameter vocabulary is CLOSED per
preset: an unrecognised key raises rather than being ignored, because a
misspelled ``radius`` that is quietly dropped writes a rig to the wrong size and
answers OK.

Shape parameters are NOT defaulted. ``rows``/``columns`` are the shape the user
named; guessing them would be inventing the arrangement rather than computing
it. ``radius`` is a size like ``spacing`` and does carry a default.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

#: The three preset shapes, in the order spec.md §B.4 names them. A tuple, not
#: a set: the order is the canonical order for reports and for the
#: exhaustiveness assertions that pin the vocabulary shut.
SPATIAL_PRESETS: tuple[str, ...] = ("grid", "row", "circle")

#: Which plane/axis each preset may be laid out on, per preset. ``row`` spreads
#: along ONE axis; ``grid`` and ``circle`` occupy a PLANE — ``xy`` is the floor
#: plan (x left-right, y upstage depth), ``xz`` is a vertical wall or truss
#: array (x left-right, z height). Closed per preset: "diagonal" or "yz" are not
#: silently accepted and then ignored.
SPATIAL_PRESET_ORIENTATIONS: dict[str, tuple[str, ...]] = {
    "grid": ("xy", "xz"),
    "row": ("x", "y", "z"),
    "circle": ("xy", "xz"),
}

#: The documented defaults, pinned by golden tests (AC-SPATIAL-018 judges
#: "spacing and origin included", so the numbers are part of the contract and
#: cannot be tuned without a failing test):
#:
#:   spacing      1.0 m   - the pitch the M0 P8 live probe used (§E.2.7)
#:   origin       centre  - the stage origin; every shape is centred on it
#:   orientation  per preset, above
#:   radius       3.0 m   - circle only; a ring that fits a small stage
#:   start_angle  0.0 deg - circle only; measured counter-clockwise from +X, so
#:                          fixture 1 sits at (origin.x + radius, origin.y)
SPATIAL_PRESET_DEFAULTS: dict[str, object] = {
    "spacing": 1.0,
    "origin": (0.0, 0.0, 0.0),
    "orientation": {"grid": "xy", "row": "x", "circle": "xy"},
    "radius": 3.0,
    "start_angle": 0.0,
}

#: Computed coordinates are quantised to this many decimals — 0.1 mm, far below
#: both float32 storage on the console and any physical relevance on a stage.
#: Quantising is what turns ``cos(pi/2)`` = 6.1e-17 into a clean 0.0 and keeps
#: every emitted value inside plain decimal notation; a value in scientific
#: notation would reach the command line as ``1e-05`` and be mis-parsed.
SPATIAL_PRESET_DECIMALS = 4

#: Refuse a coordinate beyond this magnitude (metres). A stage half a mile wide
#: is a typo or a unit mix-up, and past ~1e16 ``repr`` switches to scientific
#: notation, which the console would not read as the number meant.
SPATIAL_PRESET_MAX_ABS = 1000.0

#: Which parameter keys each preset accepts. Closed — see the module docstring.
_PRESET_PARAMS: dict[str, frozenset[str]] = {
    "grid": frozenset({"rows", "columns", "spacing", "origin", "orientation"}),
    "row": frozenset({"spacing", "origin", "orientation"}),
    "circle": frozenset({"radius", "start_angle", "origin", "orientation"}),
}

_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


class SpatialPresetError(ValueError):
    """A preset request is malformed, or names something outside a closed set."""


@dataclass(frozen=True)
class SpatialPlacement:
    """One fixture's target position in stage coordinates (metres)."""

    fid: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class SpatialPresetPlan:
    """The placements one preset request produced, plus the parameters used.

    ``resolved`` holds the EFFECTIVE parameters — the user's values merged over
    the documented defaults. It exists so a report can state what was applied
    instead of leaving the reader to infer it from the coordinates.
    """

    preset: str
    placements: tuple[SpatialPlacement, ...]
    resolved: dict[str, object]

    @property
    def fids(self) -> tuple[int, ...]:
        """The target fids, in placement order."""
        return tuple(placement.fid for placement in self.placements)


def spatial_placements_to_records(
    placements: Sequence[SpatialPlacement],
) -> list[dict[str, object]]:
    """Serialise placements for a tool reply, in the read schema's key order."""
    return [
        {"fid": placement.fid, "x": placement.x, "y": placement.y, "z": placement.z}
        for placement in placements
    ]


def _quantise(value: float) -> float:
    """Round to :data:`SPATIAL_PRESET_DECIMALS` and normalise negative zero.

    ``-0.0`` is numerically equal to ``0.0`` but renders as ``'-0.0'``; adding
    ``0.0`` collapses it under IEEE-754 so the emitted text never carries a sign
    the geometry did not mean.
    """
    if not math.isfinite(value):
        raise SpatialPresetError(f"computed coordinate is not a finite number: {value!r}")
    rounded = round(value, SPATIAL_PRESET_DECIMALS) + 0.0
    if abs(rounded) > SPATIAL_PRESET_MAX_ABS:
        raise SpatialPresetError(
            f"computed coordinate {rounded} m exceeds the {SPATIAL_PRESET_MAX_ABS} m "
            f"sanity bound — check the spacing/radius units"
        )
    return rounded


def _positive_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialPresetError(f"{field} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise SpatialPresetError(f"{field} must be a positive finite number, got {value!r}")
    return number


def _number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialPresetError(f"{field} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise SpatialPresetError(f"{field} must be a finite number, got {value!r}")
    return number


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpatialPresetError(f"{field} must be an integer, got {value!r}")
    if value <= 0:
        raise SpatialPresetError(f"{field} must be a positive integer, got {value}")
    return value


def _origin(value: object) -> tuple[float, float, float]:
    """Parse ``origin`` from a 3-sequence or an ``{"x","y","z"}`` mapping."""
    if isinstance(value, Mapping):
        unknown = set(value) - set(_AXIS_INDEX)
        if unknown:
            raise SpatialPresetError(f"origin has unknown axis keys: {sorted(unknown)}")
        return (
            _number(value.get("x", 0.0), field="origin.x"),
            _number(value.get("y", 0.0), field="origin.y"),
            _number(value.get("z", 0.0), field="origin.z"),
        )
    if isinstance(value, (list, tuple)):
        if len(value) != 3:
            raise SpatialPresetError(f"origin must hold exactly 3 numbers, got {len(value)}")
        return (
            _number(value[0], field="origin.x"),
            _number(value[1], field="origin.y"),
            _number(value[2], field="origin.z"),
        )
    raise SpatialPresetError(f"origin must be [x, y, z] or {{'x':..,'y':..,'z':..}}, got {value!r}")


def _target_fids(fids: Sequence[int]) -> tuple[int, ...]:
    """The explicit target set, order-preserving and duplicate-free.

    Order is meaningful: it decides WHICH fixture lands on which slot of the
    shape, so it is the caller's (the user's named order, or a spatial sort),
    never re-sorted here.
    """
    if not fids:
        raise SpatialPresetError("a preset needs at least one target fid")
    resolved: list[int] = []
    for entry in fids:
        if isinstance(entry, bool) or not isinstance(entry, int):
            raise SpatialPresetError(f"fid must be an integer, got {entry!r}")
        if entry <= 0:
            raise SpatialPresetError(f"fid must be a positive integer, got {entry}")
        if entry in resolved:
            raise SpatialPresetError(f"fid {entry} appears twice in the target list")
        resolved.append(entry)
    return tuple(resolved)


def _centred_offsets(count: int, spacing: float) -> list[float]:
    """``count`` positions of pitch ``spacing``, centred on 0.

    Even counts straddle the centre (8 at 1.0 m -> -3.5 .. +3.5), odd counts put
    one fixture ON it (5 at 1.0 m -> -2.0 .. +2.0). One fixture lands at 0.
    """
    middle = (count - 1) / 2.0
    return [(index - middle) * spacing for index in range(count)]


def _grid_shape(params: Mapping[str, object], count: int) -> tuple[int, int]:
    """Resolve ``rows``/``columns`` so their product is EXACTLY ``count``.

    One of the two may be omitted and is derived. Neither is defaulted: a grid
    with no shape is not a grid, and picking one would be inventing the
    arrangement the user came to specify. A product that does not match refuses
    rather than leaving a ragged last row nobody asked for.
    """
    has_rows = "rows" in params
    has_columns = "columns" in params
    if not has_rows and not has_columns:
        raise SpatialPresetError(
            "grid needs 'rows' and/or 'columns' — the shape is the request, "
            "it is never guessed from the fixture count"
        )
    rows = _positive_int(params["rows"], field="rows") if has_rows else 0
    columns = _positive_int(params["columns"], field="columns") if has_columns else 0
    if not has_columns:
        columns, remainder = divmod(count, rows)
        if remainder or columns == 0:
            raise SpatialPresetError(f"{count} fixtures do not divide into {rows} equal rows")
    elif not has_rows:
        rows, remainder = divmod(count, columns)
        if remainder or rows == 0:
            raise SpatialPresetError(f"{count} fixtures do not divide into columns of {columns}")
    elif rows * columns != count:
        raise SpatialPresetError(
            f"a {rows}x{columns} grid holds {rows * columns} fixtures, but {count} were named"
        )
    return rows, columns


def _place(origin: tuple[float, float, float], **offsets: float) -> tuple[float, float, float]:
    """Apply per-axis offsets to the origin and quantise the result."""
    coordinates = list(origin)
    for axis, offset in offsets.items():
        coordinates[_AXIS_INDEX[axis]] += offset
    return (_quantise(coordinates[0]), _quantise(coordinates[1]), _quantise(coordinates[2]))


def spatial_preset_placements(
    preset: str,
    fids: Sequence[int],
    params: Mapping[str, object] | None = None,
) -> SpatialPresetPlan:
    """Compute the target coordinate of every named fid for one preset shape.

    ``fids`` is the EXPLICIT target set in the order they should occupy the
    shape; ``params`` is the user's request, validated against the closed
    per-preset vocabulary and merged over :data:`SPATIAL_PRESET_DEFAULTS`.

    Deterministic: the same request always yields the same coordinates, which
    is what makes the write verifiable by re-query at all (REQ-SPATIAL-021).
    """
    if preset not in SPATIAL_PRESETS:
        raise SpatialPresetError(f"{preset!r} is not a spatial preset (allowed: {SPATIAL_PRESETS})")
    supplied = dict(params or {})
    unknown = set(supplied) - _PRESET_PARAMS[preset]
    if unknown:
        raise SpatialPresetError(
            f"preset {preset!r} does not take {sorted(unknown)} "
            f"(allowed: {sorted(_PRESET_PARAMS[preset])})"
        )
    targets = _target_fids(fids)

    origin = (
        _origin(supplied["origin"]) if "origin" in supplied else SPATIAL_PRESET_DEFAULTS["origin"]  # type: ignore[assignment]
    )
    allowed_orientations = SPATIAL_PRESET_ORIENTATIONS[preset]
    orientation = supplied.get(
        "orientation",
        SPATIAL_PRESET_DEFAULTS["orientation"][preset],  # type: ignore[index]
    )
    if orientation not in allowed_orientations:
        raise SpatialPresetError(
            f"preset {preset!r} orientation must be one of {list(allowed_orientations)}, "
            f"not {orientation!r}"
        )

    resolved: dict[str, object] = {
        "origin": list(origin),
        "orientation": orientation,
        "fid_order": list(targets),
    }
    placements: list[SpatialPlacement] = []

    if preset == "row":
        spacing = _positive_number(
            supplied.get("spacing", SPATIAL_PRESET_DEFAULTS["spacing"]), field="spacing"
        )
        resolved["spacing"] = spacing
        resolved["count"] = len(targets)
        for fid, offset in zip(targets, _centred_offsets(len(targets), spacing), strict=True):
            x, y, z = _place(origin, **{str(orientation): offset})
            placements.append(SpatialPlacement(fid=fid, x=x, y=y, z=z))

    elif preset == "grid":
        spacing = _positive_number(
            supplied.get("spacing", SPATIAL_PRESET_DEFAULTS["spacing"]), field="spacing"
        )
        rows, columns = _grid_shape(supplied, len(targets))
        resolved["spacing"] = spacing
        resolved["rows"] = rows
        resolved["columns"] = columns
        # Row-major fill: row 0 first, left to right inside it. Row 0 is the
        # LOW end of the row axis — for the default "xy" that is the smallest
        # y, i.e. stage front, matching the analysis layer's row order
        # (SPATIAL_ROW_ORDER = "y_ascending"). The two layers therefore agree
        # on what "the first row" means, which is what lets a rig this preset
        # wrote be read back and sorted without an off-by-one row flip.
        row_axis = orientation[1]
        column_axis = orientation[0]
        row_offsets = _centred_offsets(rows, spacing)
        column_offsets = _centred_offsets(columns, spacing)
        for index, fid in enumerate(targets):
            row_index, column_index = divmod(index, columns)
            x, y, z = _place(
                origin,
                **{
                    column_axis: column_offsets[column_index],
                    row_axis: row_offsets[row_index],
                },
            )
            placements.append(SpatialPlacement(fid=fid, x=x, y=y, z=z))

    else:  # circle
        radius = _positive_number(
            supplied.get("radius", SPATIAL_PRESET_DEFAULTS["radius"]), field="radius"
        )
        start_angle = _number(
            supplied.get("start_angle", SPATIAL_PRESET_DEFAULTS["start_angle"]),
            field="start_angle",
        )
        resolved["radius"] = radius
        resolved["start_angle"] = start_angle
        resolved["count"] = len(targets)
        # Angles run counter-clockwise from the +X axis, evenly spaced, first
        # fixture at start_angle. Stated here and in SPATIAL_PRESET_DEFAULTS
        # because "where does a circle start" has no natural answer — only a
        # documented one.
        step = 360.0 / len(targets)
        first_axis = orientation[0]
        second_axis = orientation[1]
        for index, fid in enumerate(targets):
            angle = math.radians(start_angle + index * step)
            x, y, z = _place(
                origin,
                **{
                    first_axis: radius * math.cos(angle),
                    second_axis: radius * math.sin(angle),
                },
            )
            placements.append(SpatialPlacement(fid=fid, x=x, y=y, z=z))

    return SpatialPresetPlan(preset=preset, placements=tuple(placements), resolved=resolved)
