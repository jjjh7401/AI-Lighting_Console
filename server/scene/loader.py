"""Scene library loader + schema validation (REQ-SCENE-006).

A partially broken library is never served quietly: every violation raises
``SceneSchemaError`` naming what failed and where. The schema is CLOSED —
unknown keys are rejected rather than ignored — which is what keeps a per-show
binding (a group number, an FID, an executor, a cue number) from being smuggled
in as an extra field (REQ-SCENE-004). There is no separate per-show blocklist:
the closed key set IS the enforcement, so it cannot fall out of date with the
dataclass.

Five checks (plan.md §B M1):

1. unknown field — top-level and per-entry;
2. duplicate scene id — across the whole directory, not just within one file;
3. ``look_id`` and ``fx_id`` both absent — a scene with nothing to compose is not
   a scene (REQ-SCENE-003);
4. numeric range — ``cue_number``/``sequence_number`` positive integers,
   ``trig_time`` >= 0;
5. unknown ``trig_type`` — the Capitalized closed set, lowercase included.

Checks 4 and 5 also guard the CALL surface, not only assets: ``parse_timing``
validates the timing a caller supplies. That split is required by the SPEC
itself — REQ-SCENE-006 assigns ``cue_number`` range validation to the loader
while REQ-SCENE-004 forbids ``cue_number`` from ever being an asset field, so the
one module owns both the asset schema and the timing-argument schema.

Check 5 is load-bearing beyond ordinary validation: a lowercase trigger token
produces no observable rejection anywhere this repository can reach, so it would
reach the console as silence.

Storage follows the looks and fx libraries: static, repo-shipped YAML assets.
PyYAML is already a runtime dependency.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from server.scene.schema import (
    SCENE_SCHEMA_VERSION,
    TRIGGER_TOKENS,
    Scene,
    SceneLibrary,
    SceneTiming,
)

DEFAULT_LIBRARY_DIR = Path(__file__).resolve().parent / "library"

_LIBRARY_KEYS = frozenset({"schema_version", "scenes"})
_SCENE_REQUIRED = ("scene_id", "display_name", "label")
_SCENE_OPTIONAL = ("look_id", "fx_id", "aliases", "mood_keywords", "trig_type", "trig_time")
_SCENE_KEYS = frozenset(_SCENE_REQUIRED + _SCENE_OPTIONAL)
_TIMING_KEYS = frozenset({"sequence_number", "cue_number", "trig_type", "trig_time"})


class SceneSchemaError(ValueError):
    """Raised when a scene library or timing argument violates the schema."""


def _text(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SceneSchemaError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _optional_text(value: object, *, where: str) -> str | None:
    if value is None:
        return None
    return _text(value, where=where)


def _string_tuple(value: object, *, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise SceneSchemaError(f"{where} must be a list, got {value!r}")
    return tuple(_text(item, where=f"{where} entry") for item in value)


def _label(value: object, *, where: str) -> str:
    text = _text(value, where=f"{where} label")
    if "'" in text or "\n" in text:
        raise SceneSchemaError(f"{where} label cannot be quoted on the MA3 command line: {text!r}")
    if not text.isascii():
        # spec.md §A — the stored label is ASCII; the Korean name lives on
        # `display_name`.
        raise SceneSchemaError(f"{where} label must be ASCII, got {text!r}")
    return text


def _trig_type(value: object, *, where: str) -> str | None:
    if value is None:
        return None
    token = _text(value, where=f"{where} trig_type")
    if token not in TRIGGER_TOKENS:
        raise SceneSchemaError(
            f"{where} trig_type must be one of {list(TRIGGER_TOKENS)}, got {token!r}"
        )
    return token


def _trig_time(value: object, *, where: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SceneSchemaError(f"{where} trig_time must be a number, got {value!r}")
    if value < 0:
        raise SceneSchemaError(f"{where} trig_time must be >= 0, got {value}")
    return float(value)


def _positive_int(value: object, key: str, *, where: str) -> int | None:
    if value is None:
        return None
    # bool is an int subclass, so it has to be excluded by name.
    if isinstance(value, bool) or not isinstance(value, int):
        raise SceneSchemaError(f"{where} {key} must be an integer, got {value!r}")
    if value <= 0:
        raise SceneSchemaError(f"{where} {key} must be > 0, got {value}")
    return value


def _scene(raw: object, *, source: str) -> Scene:
    if not isinstance(raw, Mapping):
        raise SceneSchemaError(f"{source}: each scene must be a mapping, got {raw!r}")
    unknown = set(raw) - _SCENE_KEYS
    if unknown:
        raise SceneSchemaError(f"{source}: scene has unknown key(s): {sorted(unknown)}")
    for key in _SCENE_REQUIRED:
        if key not in raw:
            raise SceneSchemaError(f"{source}: scene is missing required field {key!r}")

    scene_id = _text(raw["scene_id"], where=f"{source} scene_id")
    where = f"{source}: scene {scene_id!r}"
    look_id = _optional_text(raw.get("look_id"), where=f"{where} look_id")
    fx_id = _optional_text(raw.get("fx_id"), where=f"{where} fx_id")
    if look_id is None and fx_id is None:
        raise SceneSchemaError(
            f"{where} declares neither look_id nor fx_id; a scene with nothing to "
            "compose is not a scene"
        )
    return Scene(
        scene_id=scene_id,
        display_name=_text(raw["display_name"], where=f"{where} display_name"),
        label=_label(raw["label"], where=where),
        look_id=look_id,
        fx_id=fx_id,
        aliases=_string_tuple(raw.get("aliases"), where=f"{where} aliases"),
        mood_keywords=_string_tuple(raw.get("mood_keywords"), where=f"{where} mood_keywords"),
        trig_type=_trig_type(raw.get("trig_type"), where=where),
        trig_time=_trig_time(raw.get("trig_time"), where=where),
    )


def _entries_of(data: object, *, source: str) -> list[Scene]:
    if not isinstance(data, Mapping):
        raise SceneSchemaError(
            f"{source}: scene library must be a mapping, got {type(data).__name__}"
        )
    unknown = set(data) - _LIBRARY_KEYS
    if unknown:
        raise SceneSchemaError(f"{source}: unknown top-level key(s): {sorted(unknown)}")
    version = data.get("schema_version")
    if version != SCENE_SCHEMA_VERSION:
        raise SceneSchemaError(
            f"{source}: schema_version must be {SCENE_SCHEMA_VERSION}, got {version!r}"
        )
    entries = data.get("scenes")
    if not isinstance(entries, list) or not entries:
        raise SceneSchemaError(f"{source}: scenes must be a non-empty list")
    return [_scene(entry, source=source) for entry in entries]


def _library_of(entries: list[Scene]) -> SceneLibrary:
    seen: set[str] = set()
    for entry in entries:
        if entry.scene_id in seen:
            raise SceneSchemaError(f"duplicate scene id: {entry.scene_id!r}")
        seen.add(entry.scene_id)
    return SceneLibrary(schema_version=SCENE_SCHEMA_VERSION, scenes=tuple(entries))


def load_library(data: Any, *, source: str = "<mapping>") -> SceneLibrary:
    """Load and validate one scene library from an already-parsed mapping."""
    return _library_of(_entries_of(data, source=source))


def load_library_from_dir(directory: Path | str = DEFAULT_LIBRARY_DIR) -> SceneLibrary:
    """Load every ``*.yaml`` in a directory and merge them into one library.

    Scene ids must be unique across the whole set, not just within one file — the
    cross-file collision is the one a per-file loader would never see.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise SceneSchemaError(f"scene library directory not found: {directory}")
    merged: list[Scene] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise SceneSchemaError(f"{path.name} is not valid YAML: {error}") from error
        merged.extend(_entries_of(data, source=path.name))
    if not merged:
        raise SceneSchemaError(f"no scene assets found in {directory}")
    return _library_of(merged)


def parse_timing(raw: object, *, source: str = "<timing>") -> SceneTiming:
    """Validate the timing a CALLER supplies (REQ-SCENE-004, REQ-SCENE-006).

    Separate from the asset path on purpose: sequence and cue numbers are never
    asset fields, but their range check belongs to the same module so there is
    one definition of "a legal cue number" in the package.
    """
    if not isinstance(raw, Mapping):
        raise SceneSchemaError(f"{source}: timing must be a mapping, got {raw!r}")
    unknown = set(raw) - _TIMING_KEYS
    if unknown:
        raise SceneSchemaError(f"{source}: timing has unknown key(s): {sorted(unknown)}")
    return SceneTiming(
        sequence_number=_positive_int(raw.get("sequence_number"), "sequence_number", where=source),
        cue_number=_positive_int(raw.get("cue_number"), "cue_number", where=source),
        trig_type=_trig_type(raw.get("trig_type"), where=source),
        trig_time=_trig_time(raw.get("trig_time"), where=source),
    )
