"""FX library loader + schema validation (REQ-FXLIB-005).

A partially broken library is never served quietly: every violation raises
``FxSchemaError`` naming what failed and where. The schema is CLOSED — unknown
keys are rejected rather than ignored — which is what keeps a per-show binding
(a group number, a sequence number, an executor) from being smuggled in as an
extra field (REQ-FXLIB-004).

Four of the checks guard the step axis (design.md §2.1):

1. ``len(steps) >= 2`` — the phaser creation condition itself.
2. every step declares the same attribute set — an authoring discipline, so a
   step run cannot silently change shape halfway through.
3. no attribute repeats a value across steps — a repeated value emits an
   identical command line, the instruction-scoped dedupe drops the second one,
   and ``Store`` then runs against a ONE-step programmer (design.md §5).
4. a modifier axis without steps is refused — ``Phase``/``Speed``/``Relative``
   modify an existing phaser and cannot create one.

Checks 1 and 3 are load-bearing beyond ordinary validation: M0 measured that the
effect is not machine-readable (a cue holding a phaser is indistinguishable from
an empty cue), so both violations would reach the stage as silence with
``ok:true`` on every line and no runtime signal at all.

Storage follows the looks library: static, repo-shipped YAML assets. PyYAML is
already a runtime dependency.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from server.fx.schema import (
    ATTRIBUTE_VALUE_RANGE,
    FX_SCHEMA_VERSION,
    GATED_CURVE_AXES,
    KNOWN_ATTRIBUTES,
    MATRICKS_AXES,
    MIN_STEPS,
    PATTERN_KINDS,
    PHASE_MAX,
    PHASE_MIN,
    PHASER_MODIFIER_AXES,
    Fx,
    FxLibrary,
    FxStep,
    StepValue,
)

DEFAULT_LIBRARY_DIR = Path(__file__).resolve().parent / "library"

_LIBRARY_KEYS = frozenset({"schema_version", "fx"})
_FX_REQUIRED = ("fx_id", "display_name", "pattern", "steps")
_MODIFIER_KEYS = PHASER_MODIFIER_AXES + MATRICKS_AXES + GATED_CURVE_AXES
_FX_OPTIONAL = ("aliases", "mood_keywords") + _MODIFIER_KEYS
_FX_KEYS = frozenset(_FX_REQUIRED + _FX_OPTIONAL)
_INTEGER_MATRICKS_AXES = ("x", "x_wings", "x_shuffle")


class FxSchemaError(ValueError):
    """Raised when an fx library is missing, malformed, or violates the schema."""


def _number(value: object, *, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FxSchemaError(f"{where} must be a number, got {value!r}")
    return value


def _in_range(value: float, low: float, high: float, *, where: str) -> float:
    if not low <= value <= high:
        raise FxSchemaError(f"{where} is out of range: {value} (expected {low} <= value <= {high})")
    return value


def _text(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FxSchemaError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _string_tuple(value: object, *, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise FxSchemaError(f"{where} must be a list, got {value!r}")
    return tuple(_text(item, where=f"{where} entry") for item in value)


def _pattern(value: object, *, where: str) -> str:
    kind = _text(value, where=f"{where} pattern")
    if kind not in PATTERN_KINDS:
        raise FxSchemaError(
            f"{where} uses a pattern kind outside the closed vocabulary: {kind!r} "
            f"(expected one of {list(PATTERN_KINDS)})"
        )
    return kind


def _step(raw: object, *, where: str) -> FxStep:
    if not isinstance(raw, Mapping):
        raise FxSchemaError(f"{where} must be a mapping of attribute -> value, got {raw!r}")
    if not raw:
        raise FxSchemaError(f"{where} must be a non-empty mapping of attribute -> value")
    values: list[StepValue] = []
    for name, value in raw.items():
        name = _text(name, where=f"{where} attribute name")
        if name not in KNOWN_ATTRIBUTES:
            raise FxSchemaError(
                f"{where} uses an unknown attribute name: {name!r} "
                f"(expected one of {sorted(KNOWN_ATTRIBUTES)})"
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            # `At Relative <n>` as a step value is unmeasured (ASSUMPTION-40),
            # so there is no non-numeric step value v1 knows how to emit.
            raise FxSchemaError(f"{where} {name} must be an absolute number, got {value!r}")
        low, high = ATTRIBUTE_VALUE_RANGE[name]
        _in_range(value, low, high, where=f"{where} {name}")
        values.append(StepValue(attribute=name, value=value))
    return FxStep(values=tuple(values))


def _steps(raw: object, *, where: str) -> tuple[FxStep, ...]:
    if not isinstance(raw, list):
        raise FxSchemaError(f"{where} steps must be a list, got {raw!r}")
    if len(raw) < MIN_STEPS:
        # Check ① — the phaser creation condition (M0, progress.md §E.2).
        raise FxSchemaError(
            f"{where} declares {len(raw)} step(s); a phaser needs at least "
            f"{MIN_STEPS} steps, because `Relative`/`Phase`/`Speed` modify an "
            "existing phaser and cannot create one"
        )
    steps = tuple(_step(item, where=f"{where} steps[{index}]") for index, item in enumerate(raw))

    # Check ② — one attribute set for the whole run.
    first = frozenset(steps[0].attributes)
    for index, step in enumerate(steps[1:], start=1):
        if frozenset(step.attributes) != first:
            raise FxSchemaError(
                f"{where} steps[{index}] does not declare the same attribute set as "
                f"steps[0]: {sorted(step.attributes)} vs {sorted(first)}"
            )

    # Check ③ — a repeated value emits a duplicate command line, the second one
    # is dropped by the dedupe, and the phaser silently loses a step.
    for attribute in steps[0].attributes:
        seen: dict[float, int] = {}
        for index, step in enumerate(steps):
            value = step.value_of(attribute)
            if value in seen:
                raise FxSchemaError(
                    f"{where} steps[{index}] repeats the value {value} for {attribute!r} "
                    f"already set by steps[{seen[value]}]; the duplicate command line is "
                    "dropped by the run_commands dedupe, so the phaser would silently "
                    "lose a step"
                )
            seen[value] = index
    return steps


def _optional_number(raw: Mapping[str, Any], key: str, *, where: str) -> float | None:
    if raw.get(key) is None:
        return None
    return _number(raw[key], where=f"{where} {key}")


def _phase(raw: Mapping[str, Any], key: str, *, where: str) -> float | None:
    value = _optional_number(raw, key, where=where)
    if value is None:
        return None
    return _in_range(value, PHASE_MIN, PHASE_MAX, where=f"{where} {key}")


def _speed(raw: Mapping[str, Any], *, where: str) -> float | None:
    value = _optional_number(raw, "speed", where=where)
    if value is None:
        return None
    if value <= 0:
        # BPM (ASSUMPTION-38 GO). No upper bound is asserted: the repository
        # carries no measured console maximum, and inventing one would be a
        # fabricated constant.
        raise FxSchemaError(f"{where} speed must be a positive BPM value, got {value}")
    return value


def _reverse(raw: Mapping[str, Any], *, where: str) -> bool:
    value = raw.get("reverse", False)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise FxSchemaError(f"{where} reverse must be true or false, got {value!r}")
    return value


def _integer_axis(raw: Mapping[str, Any], key: str, *, minimum: int, where: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise FxSchemaError(f"{where} {key} must be an integer, got {value!r}")
    if value < minimum:
        raise FxSchemaError(f"{where} {key} must be >= {minimum}, got {value}")
    return value


def _gated_curve(raw: Mapping[str, Any], key: str, *, where: str) -> None:
    if raw.get(key) is None:
        return
    # M0 fired `At Accel -100` / `At Decel -100` and got `ok:true` with NO
    # observed effect (SKIP). Unmeasured vocabulary does not enter the library.
    raise FxSchemaError(
        f"{where} sets {key}={raw[key]!r}, but the {key} curve is probe-pending: M0 "
        "recorded ok:true with no observed effect, so v1 defines the field and "
        "never carries a value in it"
    )


def _fx(raw: object, *, source: str) -> Fx:
    if not isinstance(raw, Mapping):
        raise FxSchemaError(f"{source}: each fx must be a mapping, got {raw!r}")
    unknown = set(raw) - _FX_KEYS
    if unknown:
        raise FxSchemaError(f"{source}: fx has unknown key(s): {sorted(unknown)}")
    if "steps" not in raw:
        declared = sorted(set(raw) & set(_MODIFIER_KEYS))
        if declared:
            # Check ④ — a modifier-only entry. Every line would be accepted and
            # nothing on stage would move (M0 §3, three failed attempts).
            raise FxSchemaError(
                f"{source}: fx declares modifier axis/axes {declared} without a step "
                "axis; those commands modify an existing phaser and cannot create one"
            )
    for key in _FX_REQUIRED:
        if key not in raw:
            raise FxSchemaError(f"{source}: fx is missing required field {key!r}")

    fx_id = _text(raw["fx_id"], where=f"{source} fx_id")
    where = f"{source}: fx {fx_id!r}"
    for key in GATED_CURVE_AXES:
        _gated_curve(raw, key, where=where)
    return Fx(
        fx_id=fx_id,
        display_name=_text(raw["display_name"], where=f"{where} display_name"),
        pattern=_pattern(raw["pattern"], where=where),
        steps=_steps(raw["steps"], where=where),
        aliases=_string_tuple(raw.get("aliases"), where=f"{where} aliases"),
        mood_keywords=_string_tuple(raw.get("mood_keywords"), where=f"{where} mood_keywords"),
        phase_from=_phase(raw, "phase_from", where=where),
        phase_to=_phase(raw, "phase_to", where=where),
        speed=_speed(raw, where=where),
        relative=_optional_number(raw, "relative", where=where),
        reverse=_reverse(raw, where=where),
        phase_from_x=_phase(raw, "phase_from_x", where=where),
        phase_to_x=_phase(raw, "phase_to_x", where=where),
        x=_integer_axis(raw, "x", minimum=1, where=where),
        x_wings=_integer_axis(raw, "x_wings", minimum=1, where=where),
        # XShuffle carries a SEED, not a count (31_choreography_patterns.md:89),
        # so it has no upper bound and 0 is a legal seed.
        x_shuffle=_integer_axis(raw, "x_shuffle", minimum=0, where=where),
    )


def _entries_of(data: object, *, source: str) -> list[Fx]:
    if not isinstance(data, Mapping):
        raise FxSchemaError(f"{source}: fx library must be a mapping, got {type(data).__name__}")
    unknown = set(data) - _LIBRARY_KEYS
    if unknown:
        raise FxSchemaError(f"{source}: unknown top-level key(s): {sorted(unknown)}")
    version = data.get("schema_version")
    if version != FX_SCHEMA_VERSION:
        raise FxSchemaError(
            f"{source}: schema_version must be {FX_SCHEMA_VERSION}, got {version!r}"
        )
    entries = data.get("fx")
    if not isinstance(entries, list) or not entries:
        raise FxSchemaError(f"{source}: fx must be a non-empty list")
    return [_fx(entry, source=source) for entry in entries]


def _library_of(entries: list[Fx]) -> FxLibrary:
    seen: set[str] = set()
    for entry in entries:
        if entry.fx_id in seen:
            raise FxSchemaError(f"duplicate fx id: {entry.fx_id!r}")
        seen.add(entry.fx_id)
    return FxLibrary(schema_version=FX_SCHEMA_VERSION, fx=tuple(entries))


def load_library(data: Any, *, source: str = "<mapping>") -> FxLibrary:
    """Load and validate one fx library from an already-parsed mapping."""
    return _library_of(_entries_of(data, source=source))


def load_library_from_dir(directory: Path | str = DEFAULT_LIBRARY_DIR) -> FxLibrary:
    """Load every ``*.yaml`` in a directory and merge them into one library.

    Fx ids must be unique across the whole set, not just within one file — the
    cross-file collision is the one a per-file loader would never see.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise FxSchemaError(f"fx library directory not found: {directory}")
    merged: list[Fx] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise FxSchemaError(f"{path.name} is not valid YAML: {error}") from error
        merged.extend(_entries_of(data, source=path.name))
    if not merged:
        raise FxSchemaError(f"no fx assets found in {directory}")
    return _library_of(merged)
