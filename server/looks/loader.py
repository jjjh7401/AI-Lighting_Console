"""Look library loader + schema validation (REQ-LOOKLIB-005).

A partially broken library is never served quietly: every violation raises
``LookSchemaError`` naming what failed and where. The schema is CLOSED — unknown
keys are rejected rather than ignored — which is what keeps a per-show binding
(a group number, a preset slot, an FID) from being smuggled in as an extra field
(REQ-LOOKLIB-004).

Storage is YAML repo assets, following ``server/safety/blacklist.yaml``: static,
repo-shipped, comment-bearing rule data. PyYAML is already a runtime dependency.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from server.looks.roles import ROLE_NAMES
from server.looks.schema import (
    DYNAMICS_MAX,
    DYNAMICS_MIN,
    KNOWN_ATTRIBUTES,
    SCHEMA_VERSION,
    AttributeValue,
    Look,
    LookLibrary,
    MovementSpec,
    pool_family,
)

DEFAULT_LIBRARY_DIR = Path(__file__).resolve().parent / "library"

_LIBRARY_KEYS = frozenset({"schema_version", "looks"})
_LOOK_REQUIRED = ("look_id", "display_name", "genre", "dynamics", "roles", "attributes")
_LOOK_OPTIONAL = ("aliases", "mood_keywords", "movement")
_LOOK_KEYS = frozenset(_LOOK_REQUIRED + _LOOK_OPTIONAL)
_MOVEMENT_REQUIRED = ("attribute", "phase_from")
_MOVEMENT_KEYS = frozenset(_MOVEMENT_REQUIRED + ("phase_to", "speed", "relative"))


class LookSchemaError(ValueError):
    """Raised when a look library is missing, malformed, or violates the schema."""


def _number(value: object, *, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LookSchemaError(f"{where} must be a number, got {value!r}")
    return value


def _text(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LookSchemaError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _string_tuple(value: object, *, where: str, allow_empty: bool) -> tuple[str, ...]:
    if value is None and allow_empty:
        return ()
    if not isinstance(value, list):
        raise LookSchemaError(f"{where} must be a list, got {value!r}")
    if not value and not allow_empty:
        raise LookSchemaError(f"{where} must be a non-empty list")
    return tuple(_text(item, where=f"{where} entry") for item in value)


def _dynamics(value: object, *, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LookSchemaError(f"{where} dynamics must be an integer, got {value!r}")
    if not DYNAMICS_MIN <= value <= DYNAMICS_MAX:
        raise LookSchemaError(
            f"{where} dynamics out of range: {value} "
            f"(expected {DYNAMICS_MIN} <= level <= {DYNAMICS_MAX})"
        )
    return value


def _roles(value: object, *, where: str) -> tuple[str, ...]:
    names = _string_tuple(value, where=f"{where} roles", allow_empty=False)
    for name in names:
        if name not in ROLE_NAMES:
            raise LookSchemaError(
                f"{where} uses a role outside the closed vocabulary: {name!r} "
                f"(expected one of {sorted(ROLE_NAMES)})"
            )
    return names


def _attributes(value: object, *, where: str) -> tuple[AttributeValue, ...]:
    if not isinstance(value, Mapping):
        raise LookSchemaError(f"{where} attributes must be a mapping, got {value!r}")
    if not value:
        raise LookSchemaError(f"{where} attributes must be a non-empty mapping")
    payload: list[AttributeValue] = []
    for name, raw in value.items():
        name = _text(name, where=f"{where} attribute name")
        if name not in KNOWN_ATTRIBUTES:
            raise LookSchemaError(
                f"{where} uses an unknown attribute name: {name!r} "
                f"(expected one of {sorted(KNOWN_ATTRIBUTES)})"
            )
        if pool_family(name) is None:
            raise LookSchemaError(
                f"{where} attribute {name!r} has no in-scope pool family, so it "
                "cannot be stored as a static value; movement-only attributes "
                "may appear inside a movement spec only"
            )
        payload.append(AttributeValue(name=name, value=_number(raw, where=f"{where} {name}")))
    return tuple(payload)


def _movement(value: object, *, where: str) -> tuple[MovementSpec, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise LookSchemaError(f"{where} movement must be a list, got {value!r}")
    specs: list[MovementSpec] = []
    for index, raw in enumerate(value):
        at = f"{where} movement[{index}]"
        if not isinstance(raw, Mapping):
            raise LookSchemaError(f"{at} must be a mapping, got {raw!r}")
        unknown = set(raw) - _MOVEMENT_KEYS
        if unknown:
            raise LookSchemaError(f"{at} has unknown key(s): {sorted(unknown)}")
        for key in _MOVEMENT_REQUIRED:
            if key not in raw:
                raise LookSchemaError(f"{at} is missing required field {key!r}")
        attribute = _text(raw["attribute"], where=f"{at} attribute")
        if attribute not in KNOWN_ATTRIBUTES:
            raise LookSchemaError(
                f"{at} uses an unknown attribute name: {attribute!r} "
                f"(expected one of {sorted(KNOWN_ATTRIBUTES)})"
            )
        specs.append(
            MovementSpec(
                attribute=attribute,
                phase_from=_number(raw["phase_from"], where=f"{at} phase_from"),
                phase_to=(
                    None
                    if raw.get("phase_to") is None
                    else _number(raw["phase_to"], where=f"{at} phase_to")
                ),
                speed=(
                    None if raw.get("speed") is None else _number(raw["speed"], where=f"{at} speed")
                ),
                relative=(
                    None
                    if raw.get("relative") is None
                    else _number(raw["relative"], where=f"{at} relative")
                ),
            )
        )
    return tuple(specs)


def _look(raw: object, *, source: str) -> Look:
    if not isinstance(raw, Mapping):
        raise LookSchemaError(f"{source}: each look must be a mapping, got {raw!r}")
    unknown = set(raw) - _LOOK_KEYS
    if unknown:
        raise LookSchemaError(f"{source}: look has unknown key(s): {sorted(unknown)}")
    for key in _LOOK_REQUIRED:
        if key not in raw:
            raise LookSchemaError(f"{source}: look is missing required field {key!r}")

    look_id = _text(raw["look_id"], where=f"{source} look_id")
    where = f"{source}: look {look_id!r}"
    return Look(
        look_id=look_id,
        display_name=_text(raw["display_name"], where=f"{where} display_name"),
        genre=_text(raw["genre"], where=f"{where} genre"),
        dynamics=_dynamics(raw["dynamics"], where=where),
        roles=_roles(raw["roles"], where=where),
        attributes=_attributes(raw["attributes"], where=where),
        aliases=_string_tuple(raw.get("aliases"), where=f"{where} aliases", allow_empty=True),
        mood_keywords=_string_tuple(
            raw.get("mood_keywords"), where=f"{where} mood_keywords", allow_empty=True
        ),
        movement=_movement(raw.get("movement"), where=where),
    )


def _looks_of(data: object, *, source: str) -> list[Look]:
    if not isinstance(data, Mapping):
        raise LookSchemaError(
            f"{source}: look library must be a mapping, got {type(data).__name__}"
        )
    unknown = set(data) - _LIBRARY_KEYS
    if unknown:
        raise LookSchemaError(f"{source}: unknown top-level key(s): {sorted(unknown)}")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise LookSchemaError(f"{source}: schema_version must be {SCHEMA_VERSION}, got {version!r}")
    entries = data.get("looks")
    if not isinstance(entries, list) or not entries:
        raise LookSchemaError(f"{source}: looks must be a non-empty list")
    return [_look(entry, source=source) for entry in entries]


def _library_of(looks: list[Look]) -> LookLibrary:
    seen: dict[str, str] = {}
    for look in looks:
        if look.look_id in seen:
            raise LookSchemaError(f"duplicate look id: {look.look_id!r}")
        seen[look.look_id] = look.look_id
    return LookLibrary(schema_version=SCHEMA_VERSION, looks=tuple(looks))


def load_library(data: Any, *, source: str = "<mapping>") -> LookLibrary:
    """Load and validate one look library from an already-parsed mapping."""
    return _library_of(_looks_of(data, source=source))


def load_library_from_dir(directory: Path | str = DEFAULT_LIBRARY_DIR) -> LookLibrary:
    """Load every ``*.yaml`` in a directory and merge them into one library.

    Look ids must be unique across the whole set, not just within one file —
    the cross-file collision is the one a per-file loader would never see.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise LookSchemaError(f"look library directory not found: {directory}")
    merged: list[Look] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise LookSchemaError(f"{path.name} is not valid YAML: {error}") from error
        merged.extend(_looks_of(data, source=path.name))
    if not merged:
        raise LookSchemaError(f"no look assets found in {directory}")
    return _library_of(merged)
