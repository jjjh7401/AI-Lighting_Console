"""Scene schema — the shared data shape of the scene layer (REQ-SCENE-001/003/004).

A scene is ONE cue. It carries three things and owns only the third:

1. a look REFERENCE (``look_id``) — the static value axis, owned by LOOKLIB;
2. an fx REFERENCE (``fx_id``) — the step axis, owned by FXLIB;
3. the composition axes the scene itself owns — identity, label and timing.

Both references are optional individually and at least one is required
(REQ-SCENE-003): a look-only scene and an fx-only scene are both legal, a scene
with neither has nothing to compose. That rule is enforced by the loader, which
is where the explicit error belongs.

The scene NEVER copies a value axis. There is no attribute, no step and no
colour field here — those live upstream and are read at compile time through the
single-source-of-truth line builders (design.md §2.2). A second copy of a value
would be a second place for it to drift, and the drift is silent: the effect of
a stored cue is not machine-readable at all (spec.md §C.1).

# @MX:NOTE: [AUTO] the closed field set is the mechanism enforcing
#   REQ-SCENE-004: there is no group, FID, executor, sequence or cue field on
#   `Scene` to put a per-show value in, and the loader rejects unknown keys so
#   one cannot be added by accident. The timing axes DO exist — on `SceneTiming`,
#   which is a CALL argument, never a static asset field. `server/fx/schema.py`
#   is the mirror original; this package deliberately owns its own definitions
#   rather than extending that one, which is PRESERVE (plan.md §A.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCENE_SCHEMA_VERSION = 1

# The closed trigger vocabulary (REQ-SCENE-016). Capitalized is the console form
# (31_choreography_patterns.md:106-117); this repository has no measurement in
# which a lowercase token was refused, so the loader check is the only net —
# see the module docstring of `server/tests/test_scene_schema.py`.
TRIGGER_TOKENS: tuple[str, ...] = ("Go", "Time", "Follow", "Sound", "BPM")


@dataclass(frozen=True)
class Scene:
    """One authored scene: two references plus the axes the scene owns.

    ``label`` is required and ASCII: it is inlined between single quotes into the
    ``Store Sequence <s> Cue <c> '<label>'`` literal, while ``display_name``
    carries the Korean name the matcher and the report speak in.
    """

    scene_id: str
    display_name: str
    label: str
    look_id: str | None = None
    fx_id: str | None = None
    aliases: tuple[str, ...] = ()
    mood_keywords: tuple[str, ...] = ()
    # Authored trigger intent. Not per-show: a trigger token says how the cue
    # advances, not which rig it advances on. The caller may still override it
    # through `SceneTiming`.
    trig_type: str | None = None
    trig_time: float | None = None


@dataclass(frozen=True)
class SceneTiming:
    """The timing a CALLER supplies — never a static asset field (REQ-SCENE-004).

    Sequence and cue numbers are measured against a re-queried console at compile
    time (design.md §5). Storing either one in a repo asset would freeze a
    per-show fact into a shipped file, and nothing downstream would object.
    """

    sequence_number: int | None = None
    cue_number: int | None = None
    trig_type: str | None = None
    trig_time: float | None = None


@dataclass(frozen=True)
class SceneLibrary:
    """The loaded, validated set of scenes."""

    schema_version: int
    scenes: tuple[Scene, ...] = field(default_factory=tuple)

    def by_id(self, scene_id: str) -> Scene:
        for entry in self.scenes:
            if entry.scene_id == scene_id:
                return entry
        raise KeyError(scene_id)


def scene_to_dict(scene: Scene) -> dict:
    """Serialise a scene back to its wire form; ``load`` of this is the same scene."""
    data: dict = {
        "scene_id": scene.scene_id,
        "display_name": scene.display_name,
        "label": scene.label,
        "aliases": list(scene.aliases),
        "mood_keywords": list(scene.mood_keywords),
    }
    for key in ("look_id", "fx_id", "trig_type", "trig_time"):
        value = getattr(scene, key)
        if value is None:
            continue
        data[key] = value
    return data
