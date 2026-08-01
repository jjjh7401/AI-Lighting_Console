"""M4 — scene combination + bundle builder + guards + number acquisition.

AC-SCENE-005 (collided-attribute enumeration) · AC-SCENE-009 (bundle shape +
combination order + zero Store flags) · AC-SCENE-010 (no /Overwrite, no
/Merge) · AC-SCENE-011 (value-line collision guard, both boundaries) ·
AC-SCENE-012 (the forbidden `At Step <k>` form) · AC-SCENE-013 (number
acquisition safety) · AC-SCENE-014 (trigger shape + executor never automatic)
· AC-SCENE-023 (uniform attribute set ordering, full 32-look sweep).

Console contact: zero. Every assertion is at the STRING level over the exact
commands the gate would see. Fx/look entries are built in memory (M2's scene
library is a sibling milestone's deliverable, not yet available in this
parallel window) EXCEPT for AC-SCENE-023, which the shared brief requires to
sweep the real, already-existing `server/looks/library/**` (PRESERVE, read
import only) in full — that asset set already exists and is not a sibling
milestone's output.
"""

from __future__ import annotations

import inspect
import re

import pytest

from server.fx.instantiate import (
    CIRCLE_PHASE_CONFLICT as fx_circle_phase_conflict,
)
from server.fx.instantiate import (
    GATED_AXIS_NOT_EMITTED as fx_gated_axis_not_emitted,
)
from server.fx.instantiate import (
    RELATIVE_NOT_EMITTED as fx_relative_not_emitted,
)
from server.fx.instantiate import (
    SEQUENCE_NUMBER_UNAVAILABLE as fx_sequence_number_unavailable,
)
from server.fx.instantiate import SEQUENCE_OCCUPIED as fx_sequence_occupied
from server.fx.instantiate import (
    SEQUENCE_TRUNCATED as fx_sequence_truncated,
)
from server.fx.instantiate import (
    SEQUENCE_UNAVAILABLE as fx_sequence_unavailable,
)
from server.fx.instantiate import (
    SKIPPED_ALREADY_EXECUTED,
    FxInstantiationError,
    build_fx_bundle,
)
from server.fx.instantiate import (
    STEP_AXIS_TOO_SHORT as fx_step_axis_too_short,
)
from server.fx.instantiate import (
    _refuse_unemitted_axes as fx_refuse_unemitted_axes,
)
from server.fx.instantiate import (
    collided_lines as fx_collided_lines,
)
from server.fx.instantiate import (
    is_programmer_state as fx_is_programmer_state,
)
from server.fx.instantiate import (
    select_sequence_number as fx_select_sequence_number,
)
from server.fx.schema import Fx, FxStep, StepValue
from server.looks.loader import load_library_from_dir
from server.looks.schema import KNOWN_ATTRIBUTES, AttributeValue, Look
from server.orchestrator.tools import rig_object, rig_section
from server.scene.compile import (
    CUE_NUMBER_UNAVAILABLE,
    CUE_OCCUPIED,
    CUE_SECTION_UNAVAILABLE,
    CUE_TRUNCATED,
    INVALID_TRIGGER_TIME,
    INVALID_TRIGGER_TOKEN,
    NO_COMPOSITION_SOURCE,
    SCENE_UNIFORM_ATTRIBUTES,
    TRIGGER_INCOMPLETE,
    UNIFORM_ATTRIBUTES_INCOMPLETE,
    VALUE_LINE_COLLISION,
    SceneCompilation,
    SceneCompilationError,
    _guard_collision,
    collided_lines,
    compile_scene,
    is_programmer_state,
    select_sequence_number,
)
from server.scene.compile import (
    _refuse_unemitted_axes as scene_refuse_unemitted_axes,
)
from server.scene.loader import SceneSchemaError, parse_timing
from server.scene.schema import Scene

# -- fixtures -------------------------------------------------------------


def _look(look_id: str, *, dimmer=80, r=10, g=20, b=30, extra: dict | None = None) -> Look:
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", r),
        AttributeValue("ColorRGB_G", g),
        AttributeValue("ColorRGB_B", b),
    ]
    if extra:
        attributes.extend(AttributeValue(name, value) for name, value in extra.items())
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="test",
        dynamics=3,
        roles=("백라이트",),
        attributes=tuple(attributes),
    )


def _fx(pattern: str, *, steps: list[dict], fx_id: str | None = None, **axes) -> Fx:
    return Fx(
        fx_id=fx_id or f"{pattern}_fixture",
        display_name=f"{pattern.title()} Fixture",
        pattern=pattern,
        steps=tuple(
            FxStep(values=tuple(StepValue(attribute=a, value=v) for a, v in step.items()))
            for step in steps
        ),
        **axes,
    )


def _scene(
    scene_id: str,
    *,
    look_id: str | None = None,
    fx_id: str | None = None,
    label: str | None = None,
    trig_type: str | None = None,
    trig_time: float | None = None,
) -> Scene:
    return Scene(
        scene_id=scene_id,
        display_name=scene_id,
        label=label or scene_id,
        look_id=look_id,
        fx_id=fx_id,
        trig_type=trig_type,
        trig_time=trig_time,
    )


def _sequences(*numbers: int, truncated: bool = False, unnumbered: int = 0) -> dict:
    children: list[dict] = [{"i": number, "name": f"Sequence {number}"} for number in numbers]
    children.extend({"name": "unnumbered"} for _ in range(unnumbered))
    objects = [rig_object(child) for child in children]
    return rig_section(objects, {"truncated": truncated, "node": {"childCount": len(children)}})


def _cues(*numbers: int, truncated: bool = False, unnumbered: int = 0) -> dict:
    children: list[dict] = [{"i": number, "name": f"Cue {number}"} for number in numbers]
    children.extend({"name": "unnumbered"} for _ in range(unnumbered))
    objects = [rig_object(child) for child in children]
    return rig_section(objects, {"truncated": truncated, "node": {"childCount": len(children)}})


CORE4_LOOK = _look("core4-look")
ZOOM_LOOK = _look("zoom-look", extra={"Zoom": 40})
DIMMER_FX = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}])
COLOR_FX = _fx(
    "chase",
    steps=[
        {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 10},
        {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 50},
    ],
)
MOVEMENT_FX = _fx(
    "wave",
    steps=[{"Pan": -20, "Tilt": 10}, {"Pan": 20, "Tilt": -10}],
    phase_from=0,
    phase_to=360,
    speed=60,
)
# Three steps where step 1 and step 3 emit the IDENTICAL value line — a
# genuine intra-bundle duplicate, no mutation required to exercise the guard.
DUPLICATE_FX = _fx("pulse", steps=[{"Dimmer": 50}, {"Dimmer": 80}, {"Dimmer": 50}])

REAL_LOOKS = load_library_from_dir().looks


def _compile(scene, *, look=None, fx=None, group=11, sequence_number=None, cue_number=None, **kw):
    return compile_scene(
        scene,
        look=look,
        fx=fx,
        group=group,
        sequences_section=_sequences(),
        cues_section=_cues(),
        sequence_number=sequence_number,
        cue_number=cue_number,
        **kw,
    )


# =============================================================================
# reuse — decisions E/G/H (no second implementation)
# =============================================================================


def test_select_sequence_number_is_the_fx_module_object_not_a_copy():
    assert select_sequence_number is fx_select_sequence_number


def test_collided_lines_is_the_fx_module_object_not_a_copy():
    assert collided_lines is fx_collided_lines


def test_is_programmer_state_is_the_fx_module_object_not_a_copy():
    assert is_programmer_state is fx_is_programmer_state


def test_compile_module_owns_no_second_exemption_regex():
    # AC-SCENE-011 side assertion (decision E): the exemption call is reused,
    # never re-implemented as a scene-local regex.
    source = inspect.getsource(__import__("server.scene.compile", fromlist=["_"]))
    assert "re.compile" not in source
    assert "import re" not in source


def test_the_collision_guard_calls_the_shared_exemption_for_every_line(monkeypatch):
    """Decision E asserted as a CALL, not as the absence of a second regex.

    The grep test above only proves this module owns no `re.compile`. A copy
    that is not a regex passes it untouched: replacing the `is_programmer_state`
    call with the literal set `{"ClearAll", "Clear", "ChangeDestination Root"}`
    killed 0 of the 135 tests this file had before this test existed (measured,
    pre-merge review). What decision E actually forbids is a second DEFINITION
    of "which line the dedupe exempts" — so the observable to pin is that the
    guard consults the shared one for every line it classifies.
    """
    observed: list[str] = []

    def _recording(command: str) -> bool:
        observed.append(command)
        return fx_is_programmer_state(command)

    monkeypatch.setattr("server.scene.compile.is_programmer_state", _recording)
    scene = _scene("s41", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    assert observed == list(result.commands)


@pytest.mark.parametrize(
    "exempt_line",
    ["Group 11", "Group 5 Thru 9", "Fixture 1 + 2", "clearall", "CLEAR"],
    ids=["group", "group_thru", "fixture_range", "lowercase_clearall", "uppercase_clear"],
)
def test_a_line_exempt_only_by_the_shared_pattern_is_not_refused(exempt_line):
    # Each form is exempt because `is_programmer_state` matches a PATTERN — a
    # selection operand, or a case-insensitive keyword. A hand-written set of
    # the exact strings this module happens to emit misses every one of them,
    # so these are the behavioural net the source-grep test cannot be.
    # `Group 11` is not hypothetical: it is line 3 of every bundle this module
    # builds.
    assert fx_is_programmer_state(exempt_line)  # control on the premise itself
    _guard_collision([exempt_line, exempt_line], scene_id="pattern-exempt")


def test_a_duplicate_no_pattern_exempts_is_still_refused():
    # Control: without this, the test above is satisfied by a guard that never
    # raises at all.
    line = "Attribute 'Dimmer' At 50"
    assert not fx_is_programmer_state(line)
    with pytest.raises(SceneCompilationError) as excinfo:
        _guard_collision([line, line], scene_id="not-exempt")
    assert excinfo.value.reason == VALUE_LINE_COLLISION


# =============================================================================
# AC-SCENE-009 — bundle shape + combination order + zero Store flags
# =============================================================================


def test_look_and_fx_combine_with_the_look_before_the_first_step_line():
    scene = _scene("s1", look_id=CORE4_LOOK.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=MOVEMENT_FX)
    look_line = _values_line_of(result)
    assert result.commands.index(look_line) < result.commands.index("Step 2")


def test_step_1_is_never_emitted():
    scene = _scene("s2", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    assert "Step 1" not in result.commands
    assert all(not re.fullmatch(r"Step 1", c) for c in result.commands)


def test_standalone_step_lines_equal_step_count_minus_one():
    three_step_fx = _fx("pulse", steps=[{"Dimmer": 10}, {"Dimmer": 20}, {"Dimmer": 30}])
    scene = _scene("s3", fx_id=three_step_fx.fx_id)
    result = _compile(scene, fx=three_step_fx)
    step_lines = [c for c in result.commands if re.fullmatch(r"Step \d+", c)]
    assert step_lines == ["Step 2", "Step 3"]


def test_transformation_lines_come_after_the_entire_step_column():
    scene = _scene("s4", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    last_step_index = max(i for i, c in enumerate(result.commands) if re.fullmatch(r"Step \d+", c))
    phase_or_speed_indexes = [
        i for i, c in enumerate(result.commands) if "At Phase" in c or "At Speed" in c
    ]
    assert phase_or_speed_indexes
    assert min(phase_or_speed_indexes) > last_step_index


def test_look_line_is_one_semicolon_chain_and_step_lines_never_chain():
    # design.md §3.4: `;` chaining is validated ONLY on the look line and the
    # fx Speed line (`_speed_line`'s own docstring) — STEP value lines never
    # chain, which is the property this test actually guards.
    scene = _scene("s5", look_id=CORE4_LOOK.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=MOVEMENT_FX)
    look_line = _values_line_of(result)
    assert look_line.count(";") == 3  # 4 attributes chained -> 3 separators
    for command in result.commands:
        if command == look_line or "At Speed" in command:
            continue
        if command.startswith("Attribute"):
            assert ";" not in command


def test_no_store_flag_survives_across_a_fixture_matrix():
    matrix = [
        _compile(_scene("look-only", look_id=CORE4_LOOK.look_id), look=CORE4_LOOK),
        _compile(_scene("fx-only", fx_id=DIMMER_FX.fx_id), fx=DIMMER_FX),
        _compile(
            _scene("both", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id),
            look=CORE4_LOOK,
            fx=DIMMER_FX,
        ),
        _compile(
            _scene("triggered", fx_id=DIMMER_FX.fx_id, trig_type="Go", trig_time=1.5),
            fx=DIMMER_FX,
        ),
        _compile(_scene("assigned", fx_id=DIMMER_FX.fx_id), fx=DIMMER_FX, executor=7),
    ]
    for result in matrix:
        store_line = next(c for c in result.commands if c.startswith("Store"))
        after_quote = store_line.split("'")[-1]
        assert not re.search(r"/\S", after_quote, re.IGNORECASE), store_line


# @MX:ANCHOR: [AUTO] `;` alone does NOT identify the look value line.
# @MX:REASON: `_speed_line` chains too as soon as an fx carries two attributes
#   and a speed (`Attribute 'Pan' At Speed 60 ; Attribute 'Tilt' At Speed 60`),
#   so "the chained line" is ambiguous in any bundle that carries a movement fx.
#   What separates them is the value FORM: the look emits one `;` chain of bare
#   absolute values (design.md §3.4), step value lines never chain, and the
#   modifier lines carry a keyword (`At Speed` / `At Phase`) where the number
#   would be. A shipped look always carries at least the uniform four, so a
#   look-bearing bundle has exactly one such line and an fx-only bundle has none.
_ABSOLUTE_VALUE = re.compile(r"^Attribute '[^']+' At -?\d+(?:\.\d+)?$")


def _chained_value_lines(commands) -> list[str]:
    """Every ``;``-chained line whose segments are all ABSOLUTE attribute values."""
    chained = [line for line in commands if ";" in line]
    return [
        line
        for line in chained
        if all(_ABSOLUTE_VALUE.match(part.strip()) for part in line.split(";"))
    ]


def _values_line_of(result: SceneCompilation) -> str:
    """The one LOOK value line of a look-bearing bundle.

    The unpack is the assertion: if the discriminant ever widened back to "any
    `;` chain", a bundle carrying both a look and a speed-chaining fx would
    yield two and every caller of this helper would fail loudly instead of
    silently reading the wrong line.
    """
    (line,) = _chained_value_lines(result.commands)
    return line


# =============================================================================
# AC-SCENE-010 — /Overwrite and /Merge absence, case-insensitive
# =============================================================================


@pytest.mark.parametrize(
    "token", ["/Merge", "/merge", "/MERGE", "/mErGe", "/Overwrite", "/overwrite"]
)
def test_store_line_never_carries_merge_or_overwrite(token):
    scene = _scene("s6", look_id=CORE4_LOOK.look_id)
    result = _compile(scene, look=CORE4_LOOK)
    store_line = next(c for c in result.commands if c.startswith("Store"))
    assert token.lower() not in store_line.lower()


# =============================================================================
# AC-SCENE-011 — value-line collision guard, both boundaries
# =============================================================================


def test_genuine_intra_bundle_duplicate_is_refused():
    scene = _scene("s7", fx_id=DUPLICATE_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DUPLICATE_FX)
    assert excinfo.value.reason == VALUE_LINE_COLLISION


@pytest.mark.parametrize(
    "look,fx",
    [
        (CORE4_LOOK, DIMMER_FX),
        (None, DIMMER_FX),
        (CORE4_LOOK, MOVEMENT_FX),
    ],
)
def test_ordinary_scenes_have_no_intra_bundle_duplicate(look, fx):
    scene = _scene("s8", look_id=look.look_id if look else None, fx_id=fx.fx_id if fx else None)
    result = _compile(scene, look=look, fx=fx)
    non_exempt = result.non_exempt_commands
    assert len(non_exempt) == len(set(non_exempt))


def test_exempt_lines_repeat_without_raising():
    scene = _scene("s9", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    assert result.commands.count("ClearAll") == 2  # exempt: allowed to repeat


class _Outcome:
    def __init__(self, command: str, status: str) -> None:
        self.command = command
        self.status = status


def test_cross_call_collision_is_detected_via_the_reused_function():
    scene = _scene("s10", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    outcomes = [_Outcome(c, "executed_ok") for c in result.commands]
    step_2_index = result.commands.index("Step 2")
    outcomes[step_2_index] = _Outcome("Step 2", SKIPPED_ALREADY_EXECUTED)
    assert collided_lines(outcomes) == ("Step 2",)


def test_a_clean_execution_reports_no_cross_call_collision():
    scene = _scene("s11", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    outcomes = [_Outcome(c, "executed_ok") for c in result.commands]
    assert collided_lines(outcomes) == ()


# =============================================================================
# AC-SCENE-012 — the forbidden `At Step <k>` form
# =============================================================================


@pytest.mark.parametrize(
    "look,fx", [(CORE4_LOOK, MOVEMENT_FX), (None, DIMMER_FX), (CORE4_LOOK, None)]
)
def test_forbidden_at_step_form_never_appears(look, fx):
    scene = _scene("s12", look_id=look.look_id if look else None, fx_id=fx.fx_id if fx else None)
    result = _compile(scene, look=look, fx=fx)
    pattern = re.compile(r"At\s+Step\s+\d+", re.IGNORECASE)
    assert not any(pattern.search(c) for c in result.commands)


# =============================================================================
# AC-SCENE-013 — number acquisition safety
# =============================================================================


def test_sequence_number_is_measured_free():
    scene = _scene("s13", fx_id=DIMMER_FX.fx_id)
    result = compile_scene(
        scene,
        look=None,
        fx=DIMMER_FX,
        group=11,
        sequences_section=_sequences(1, 2, 3),
        cues_section=_cues(),
    )
    assert result.sequence == 4


def test_requested_free_sequence_number_is_honoured():
    scene = _scene("s14", fx_id=DIMMER_FX.fx_id)
    result = compile_scene(
        scene,
        look=None,
        fx=DIMMER_FX,
        group=11,
        sequences_section=_sequences(1, 2),
        cues_section=_cues(),
        sequence_number=9,
    )
    assert result.sequence == 9


def test_cue_number_is_measured_free():
    scene = _scene("s15", fx_id=DIMMER_FX.fx_id)
    result = compile_scene(
        scene,
        look=None,
        fx=DIMMER_FX,
        group=11,
        sequences_section=_sequences(),
        cues_section=_cues(1, 2),
    )
    assert result.cue == 3


def test_requested_free_cue_number_is_honoured():
    scene = _scene("s16", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX, cue_number=42)
    assert result.cue == 42


def test_requested_occupied_cue_number_is_refused():
    scene = _scene("s17", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section=_cues(5),
            cue_number=5,
        )
    assert excinfo.value.reason == CUE_OCCUPIED


def test_truncated_cue_listing_refuses_automatic_assignment():
    scene = _scene("s18", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section=_cues(1, truncated=True),
        )
    assert excinfo.value.reason == CUE_TRUNCATED


@pytest.mark.parametrize("reason", ["path_not_resolved", "console_unreachable"])
def test_an_unarrived_cue_section_refuses_and_propagates_the_reason(reason):
    scene = _scene("s19", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section={"reason": reason},
        )
    assert excinfo.value.reason == CUE_SECTION_UNAVAILABLE
    assert reason in str(excinfo.value)


def test_a_cue_the_console_could_not_number_refuses_assignment():
    scene = _scene("s20", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section=_cues(1, unnumbered=1),
        )
    assert excinfo.value.reason == CUE_NUMBER_UNAVAILABLE


# The sequence side of the SAME four refusals the cue side is swept for above.
# `select_sequence_number` is fx's (decision H) and raises `FxInstantiationError`;
# only `SEQUENCE_OCCUPIED` had a scene-side test, so three of the four reason
# codes crossed this package's boundary with nothing asserting that the
# translation happens at all. A caller that catches `SceneCompilationError` —
# which is the whole contract of that translation — would have crashed instead
# of refusing on any of the three.


def test_truncated_sequence_listing_refuses_automatic_assignment():
    scene = _scene("s18b", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(1, truncated=True),
            cues_section=_cues(),
        )
    assert excinfo.value.reason == fx_sequence_truncated
    assert not isinstance(excinfo.value, FxInstantiationError)


@pytest.mark.parametrize("reason", ["path_not_resolved", "console_unreachable"])
def test_an_unarrived_sequence_section_refuses_and_propagates_the_reason(reason):
    scene = _scene("s19b", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section={"reason": reason},
            cues_section=_cues(),
        )
    assert excinfo.value.reason == fx_sequence_unavailable
    assert reason in str(excinfo.value)
    assert not isinstance(excinfo.value, FxInstantiationError)


def test_a_sequence_the_console_could_not_number_refuses_assignment():
    scene = _scene("s20b", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(1, unnumbered=1),
            cues_section=_cues(),
        )
    assert excinfo.value.reason == fx_sequence_number_unavailable
    assert not isinstance(excinfo.value, FxInstantiationError)


def test_the_sequence_refusal_happens_before_any_cue_question_is_asked():
    # Ordering control: an unreadable sequence pool must refuse even when the
    # cue pool is ALSO unreadable, or the two reasons would race and the caller
    # would be told to repair the wrong half of the rig.
    scene = _scene("s20c", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section={"reason": "console_unreachable"},
            cues_section={"reason": "console_unreachable"},
        )
    assert excinfo.value.reason == fx_sequence_unavailable


# =============================================================================
# AC-SCENE-014 — trigger shape + executor never automatic
# =============================================================================


def test_trigger_emits_exactly_two_property_lines_after_the_clear():
    scene = _scene("s21", fx_id=DIMMER_FX.fx_id, trig_type="Follow", trig_time=12.5)
    result = _compile(scene, fx=DIMMER_FX)
    trig_type_line = f"Set Cue {result.cue} Sequence {result.sequence} Property 'TrigType' 'Follow'"
    trig_time_line = f"Set Cue {result.cue} Sequence {result.sequence} Property 'TrigTime' 12.5"
    assert trig_type_line in result.commands
    assert trig_time_line in result.commands
    last_clear_index = max(i for i, c in enumerate(result.commands) if c == "ClearAll")
    assert result.commands.index(trig_type_line) > last_clear_index
    assert result.commands.index(trig_time_line) > result.commands.index(trig_type_line)


def test_caller_supplied_trigger_overrides_the_scene_authored_one():
    scene = _scene("s22", fx_id=DIMMER_FX.fx_id, trig_type="Go", trig_time=1.0)
    result = _compile(scene, fx=DIMMER_FX, trig_type="Sound", trig_time=3.0)
    assert result.trig_type == "Sound"
    assert result.trig_time == 3.0


def test_lowercase_trigger_token_is_refused():
    scene = _scene("s23", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX, trig_type="follow", trig_time=1.0)
    assert excinfo.value.reason == INVALID_TRIGGER_TOKEN


def test_a_trigger_needs_both_type_and_time():
    scene = _scene("s24", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX, trig_type="Go")
    assert excinfo.value.reason == TRIGGER_INCOMPLETE


@pytest.mark.parametrize("bad_time", [-0.001, -1, -5.0, -1000.0])
def test_a_negative_trigger_time_is_refused(bad_time):
    # `_effective_trigger` re-validated the trigger TOKEN against the closed set
    # while never looking at its paired TIME. The pair is authored, overridden
    # and emitted together, so guarding one half is the defect: a negative was
    # emitted verbatim as `Property 'TrigTime' -5`.
    scene = _scene("s24b", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX, trig_type="Go", trig_time=bad_time)
    assert excinfo.value.reason == INVALID_TRIGGER_TIME


def test_a_negative_trigger_time_authored_on_the_scene_is_refused_too():
    # The caller override is not the only door: `Scene` carries the pair itself
    # and `_effective_trigger` reads the authored value when no override comes.
    scene = _scene("s24c", fx_id=DIMMER_FX.fx_id, trig_type="Go", trig_time=-0.5)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX)
    assert excinfo.value.reason == INVALID_TRIGGER_TIME


def test_a_refused_trigger_time_never_reaches_a_bundle():
    # Under this SPEC's ceiling the console answers ok:true on the property line
    # and a stored cue's content is not readable back (spec.md §C.1), so nothing
    # downstream would ever have reported the nonsense value. Refusing before a
    # bundle exists is the only net.
    scene = _scene("s24d", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX, trig_type="Go", trig_time=-5.0)
    assert not hasattr(excinfo.value, "commands")


@pytest.mark.parametrize("good_time", [0.0, 0, 0.5, 12.5])
def test_a_non_negative_trigger_time_still_compiles(good_time):
    # Control: the refusal is a RANGE check, not a ban on falsy times — `BPM 0`
    # is already an authored shape (`test_trig_equals_form_never_appears`).
    scene = _scene("s24e", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX, trig_type="Go", trig_time=good_time)
    assert result.trig_time == good_time
    assert any("Property 'TrigTime'" in command for command in result.commands)


def test_the_two_timing_doors_agree_on_a_negative_trigger_time():
    # `parse_timing` is the tool-layer door and already refused this; `compile_scene`
    # is an `__all__` builder any caller may reach directly and did not. One value,
    # one verdict — the asymmetry was the defect, not the missing check.
    with pytest.raises(SceneSchemaError):
        parse_timing({"trig_type": "Go", "trig_time": -5.0})
    scene = _scene("s24f", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=DIMMER_FX, trig_type="Go", trig_time=-5.0)
    assert excinfo.value.reason == INVALID_TRIGGER_TIME


def test_trig_equals_form_never_appears():
    scene = _scene("s25", fx_id=DIMMER_FX.fx_id, trig_type="BPM", trig_time=0.0)
    result = _compile(scene, fx=DIMMER_FX)
    assert not any("/trig=" in c for c in result.commands)


def test_executor_is_never_automatic():
    scene = _scene("s26", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX)
    assert not any(c.startswith("Assign") for c in result.commands)


def test_explicit_executor_appends_exactly_one_final_assign_line():
    scene = _scene("s27", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX, executor=7)
    assign_lines = [c for c in result.commands if c.startswith("Assign")]
    assert assign_lines == [f"Assign Sequence {result.sequence} At Executor 7"]
    assert result.commands[-1] == assign_lines[0]


# =============================================================================
# AC-SCENE-005 — collided-attribute enumeration
# =============================================================================


def test_dimmer_conflict_is_enumerated_exactly():
    scene = _scene("s28", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    assert result.collided_attributes == ("Dimmer",)


def test_color_conflict_is_enumerated_exactly():
    scene = _scene("s29", look_id=CORE4_LOOK.look_id, fx_id=COLOR_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=COLOR_FX)
    assert result.collided_attributes == ("ColorRGB_B", "ColorRGB_G", "ColorRGB_R")


def test_movement_fx_never_conflicts_with_a_look_false_positive_control():
    scene = _scene("s30", look_id=CORE4_LOOK.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=MOVEMENT_FX)
    assert result.collided_attributes == ()


def test_effect_lines_come_after_the_look_line_in_a_collided_scene():
    scene = _scene("s31", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    look_line = _values_line_of(result)
    first_fx_line = next(c for c in result.commands if c.startswith("Attribute") and c != look_line)
    assert result.commands.index(look_line) < result.commands.index(first_fx_line)


# =============================================================================
# AC-SCENE-023 — uniform attribute set ordering (full 32-look sweep)
# =============================================================================


def test_the_real_library_has_thirty_two_looks():
    assert len(REAL_LOOKS) == 32


@pytest.mark.parametrize("look", REAL_LOOKS, ids=[look.look_id for look in REAL_LOOKS])
def test_every_real_look_emits_the_uniform_set_first_in_order(look):
    scene = _scene(f"scene-{look.look_id}", look_id=look.look_id)
    result = _compile(scene, look=look)
    names = re.findall(r"Attribute '([^']+)' At", _values_line_of(result))
    # POSITION, not membership: filtering the names down to the uniform four
    # before comparing makes `[Zoom, Dimmer, R, G, B]` satisfy the assertion too,
    # which is exactly what `_ordered_look_values` exists to prevent.
    assert tuple(names[:4]) == SCENE_UNIFORM_ATTRIBUTES
    assert set(names) - set(SCENE_UNIFORM_ATTRIBUTES) <= {"Zoom", "Iris"}


@pytest.mark.parametrize("fx", [DIMMER_FX, MOVEMENT_FX], ids=["no_chain", "speed_chain"])
def test_fx_only_scene_is_not_subject_to_the_uniform_set(fx):
    scene = _scene("s32", fx_id=fx.fx_id)
    result = _compile(scene, fx=fx)
    # No LOOK value line at all. The `MOVEMENT_FX` case is the one that matters:
    # this test used to assert `not any(c.count(";") ...)`, which is FALSE for
    # any fx with 2+ attributes and a speed and passed only because `DIMMER_FX`
    # happens to be one attribute with no speed.
    assert _chained_value_lines(result.commands) == []


def test_a_speed_chain_is_never_mistaken_for_a_look_value_line():
    # Non-vacuity for the case above: the chain really is there, it is just not
    # a look value line. Its segments carry the keyword `At Speed` where an
    # absolute value would be.
    scene = _scene("s32b", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    assert [c for c in result.commands if ";" in c] == [
        "Attribute 'Pan' At Speed 60 ; Attribute 'Tilt' At Speed 60"
    ]
    assert _chained_value_lines(result.commands) == []


def test_an_fx_only_bundle_offers_no_look_value_line_to_read():
    # The discriminant has to be a DEFINITION, not a lucky ordering. In every
    # look-bearing bundle the look line happens to precede the speed line, so a
    # "first `;` chain that starts with Attribute" copy returns the right string
    # by accident and nothing notices. Here there is no look line at all and
    # that copy hands back the SPEED line instead — a wrong answer, silently.
    scene = _scene("s32d", fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, fx=MOVEMENT_FX)
    with pytest.raises(ValueError):
        _values_line_of(result)


def test_a_look_bearing_bundle_with_a_speed_chain_still_has_exactly_one_value_line():
    # The pair of the case above: two `;` chains in one bundle, only one of
    # which is the look's. `_values_line_of`'s unpack is what enforces it.
    scene = _scene("s32c", look_id=ZOOM_LOOK.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=ZOOM_LOOK, fx=MOVEMENT_FX)
    assert len([c for c in result.commands if ";" in c]) == 2
    names = re.findall(r"Attribute '([^']+)' At", _values_line_of(result))
    assert tuple(names) == (*SCENE_UNIFORM_ATTRIBUTES, "Zoom")


def test_undeclared_zoom_is_never_invented():
    no_zoom_looks = [
        look for look in REAL_LOOKS if not any(a.name == "Zoom" for a in look.attributes)
    ]
    assert no_zoom_looks  # control: at least one such look must exist in the fixture
    look = no_zoom_looks[0]
    scene = _scene(f"no-zoom-{look.look_id}", look_id=look.look_id)
    result = _compile(scene, look=look)
    assert "Attribute 'Zoom'" not in _values_line_of(result)


def test_a_look_missing_a_uniform_attribute_is_refused():
    incomplete = Look(
        look_id="incomplete",
        display_name="incomplete",
        genre="test",
        dynamics=1,
        roles=("탑",),
        attributes=(AttributeValue("Dimmer", 50), AttributeValue("ColorRGB_R", 10)),
    )
    scene = _scene("s33", look_id=incomplete.look_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, look=incomplete)
    assert excinfo.value.reason == UNIFORM_ATTRIBUTES_INCOMPLETE


def test_a_reversed_declaration_order_look_is_still_reordered_to_uniform_first():
    # Today's 32/32 assets are already sorted, so this reversed-declaration
    # fixture is required to prove the sort is doing real work. The NON-uniform
    # `Zoom` is load-bearing: without it `rest` is empty and `uniform + rest`
    # and `rest + uniform` produce the identical line, which is why swapping
    # them killed 0 of 118 tests (measured, pre-merge review).
    reversed_look = Look(
        look_id="reversed",
        display_name="reversed",
        genre="test",
        dynamics=1,
        roles=("탑",),
        attributes=(
            AttributeValue("Zoom", 40),
            AttributeValue("ColorRGB_B", 3),
            AttributeValue("ColorRGB_G", 2),
            AttributeValue("ColorRGB_R", 1),
            AttributeValue("Dimmer", 99),
        ),
    )
    scene = _scene("s34", look_id=reversed_look.look_id)
    result = _compile(scene, look=reversed_look)
    names = re.findall(r"Attribute '([^']+)' At", _values_line_of(result))
    # The core-4 come FIRST, in order, and the declared remainder follows.
    assert tuple(names[:4]) == SCENE_UNIFORM_ATTRIBUTES
    assert tuple(names) == (*SCENE_UNIFORM_ATTRIBUTES, "Zoom")


# =============================================================================
# AC-SCENE-024 — unclaimed-attribute enumeration (full차집합, deterministic)
# =============================================================================


def test_core4_look_plus_dimmer_fx_unclaimed_is_exactly_zoom_iris_pan_tilt():
    scene = _scene("s35", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    assert set(result.unclaimed_attributes) == {"Zoom", "Iris", "Pan", "Tilt"}
    assert result.unclaimed_attributes == tuple(sorted(result.unclaimed_attributes))


def test_zoom_only_look_plus_movement_fx_unclaimed_is_exactly_iris():
    zoom_only = [
        look
        for look in REAL_LOOKS
        if any(a.name == "Zoom" for a in look.attributes)
        and not any(a.name == "Iris" for a in look.attributes)
    ]
    assert zoom_only  # control: the "Zoom-only 9" band must be non-empty
    look = zoom_only[0]
    scene = _scene(f"s36-{look.look_id}", look_id=look.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=look, fx=MOVEMENT_FX)
    assert set(result.unclaimed_attributes) == {"Iris"}


def test_fx_only_scene_unclaimed_is_nearly_the_whole_universe():
    scene = _scene("s37", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX)
    assert set(result.unclaimed_attributes) == set(KNOWN_ATTRIBUTES) - {"Dimmer"}


def test_known_attributes_universe_is_exactly_eight_today():
    assert (
        frozenset(
            {"Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Zoom", "Iris", "Pan", "Tilt"}
        )
        == KNOWN_ATTRIBUTES
    )


# =============================================================================
# constructor guard — no composition source (defence in depth for REQ-SCENE-003)
# =============================================================================


def test_a_scene_with_neither_look_nor_fx_is_refused():
    scene = _scene("s38")
    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, look=None, fx=None)
    assert excinfo.value.reason == NO_COMPOSITION_SOURCE


def test_to_dict_carries_the_public_fields():
    scene = _scene("s39", look_id=CORE4_LOOK.look_id, fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=DIMMER_FX)
    payload = result.to_dict()
    for key in (
        "scene_id",
        "commands",
        "collided_attributes",
        "unclaimed_attributes",
        "cue",
        "sequence",
    ):
        assert key in payload


# =============================================================================
# SEAM — the real M2 scene assets through this builder (orchestrator-added)
#
# The parallel wave left this hole on purpose: M2's assets did not exist while
# this slice was written, so every assertion above runs on in-memory fixtures.
# `TEMPLATE-병렬웨이브-파이프라인.md:37` names the seam as the coordinator's own
# duty — the slices each verify their half and nobody looks at the join. These
# tests close AC-SCENE-009/010/012/023 over the SHIPPED assets rather than
# over fixtures, which is what those ACs actually say ("라이브러리 전 씬 전수").
# =============================================================================

from server.fx.loader import load_library_from_dir as load_fx_library  # noqa: E402
from server.scene.loader import load_library_from_dir as load_scene_library  # noqa: E402

REAL_SCENES = load_scene_library().scenes
_REAL_LOOK_LIBRARY = load_library_from_dir()
_REAL_FX_LIBRARY = load_fx_library()


def _resolve(scene):
    look = _REAL_LOOK_LIBRARY.by_id(scene.look_id) if scene.look_id else None
    fx = _REAL_FX_LIBRARY.by_id(scene.fx_id) if scene.fx_id else None
    return look, fx


def _compiled_assets():
    return [
        (scene, _compile(scene, look=look, fx=fx))
        for scene in REAL_SCENES
        for look, fx in [_resolve(scene)]
    ]


def test_the_shipped_library_is_not_empty():
    # Non-vacuity: every sweep below is worthless if the asset set is empty.
    assert len(REAL_SCENES) >= 5


@pytest.mark.parametrize("scene", REAL_SCENES, ids=lambda s: s.scene_id)
def test_every_shipped_scene_compiles_against_the_real_upstream_libraries(scene):
    look, fx = _resolve(scene)
    result = _compile(scene, look=look, fx=fx)
    assert result.scene_id == scene.scene_id
    assert result.commands[0] == "ChangeDestination Root"


@pytest.mark.parametrize("scene", REAL_SCENES, ids=lambda s: s.scene_id)
def test_every_shipped_scene_stores_exactly_once_without_a_flag(scene):
    look, fx = _resolve(scene)
    commands = _compile(scene, look=look, fx=fx).commands
    stores = [line for line in commands if line.startswith("Store ")]
    assert len(stores) == 1
    # Nothing follows the label's closing quote — the only net under a typo'd
    # flag, which the console accepts silently (spec.md §C.1).
    assert re.fullmatch(r"Store Sequence \d+ Cue \d+ '[^']+'", stores[0])
    blob = "\n".join(commands).lower()
    assert "/merge" not in blob
    assert "/overwrite" not in blob
    assert "/cueonly" not in blob
    assert "/trig=" not in blob


@pytest.mark.parametrize("scene", REAL_SCENES, ids=lambda s: s.scene_id)
def test_every_shipped_scene_keeps_the_step_discipline(scene):
    look, fx = _resolve(scene)
    commands = _compile(scene, look=look, fx=fx).commands
    assert "Step 1" not in commands
    assert not [line for line in commands if re.search(r"At Step \d", line, re.IGNORECASE)]
    if fx is not None:
        steps = [line for line in commands if re.fullmatch(r"Step \d+", line)]
        assert len(steps) == len(fx.steps) - 1


@pytest.mark.parametrize("scene", REAL_SCENES, ids=lambda s: s.scene_id)
def test_every_shipped_look_bearing_scene_carries_the_uniform_set(scene):
    look, fx = _resolve(scene)
    chained = _chained_value_lines(_compile(scene, look=look, fx=fx).commands)
    if look is None:
        # An fx-only scene has no look value line at all — legal, and this AC
        # does not reach it (REQ-SCENE-012 (a)).
        assert chained == []
        return
    assert len(chained) == 1
    names = re.findall(r"Attribute '([^']+)' At", chained[0])
    assert tuple(names[:4]) == SCENE_UNIFORM_ATTRIBUTES
    assert set(names) - set(SCENE_UNIFORM_ATTRIBUTES) <= {"Zoom", "Iris"}


@pytest.mark.parametrize("scene", REAL_SCENES, ids=lambda s: s.scene_id)
def test_every_shipped_scene_enumerates_exactly_the_static_sets(scene):
    look, fx = _resolve(scene)
    result = _compile(scene, look=look, fx=fx)
    look_attrs = frozenset(v.name for v in look.attributes) if look else frozenset()
    fx_attrs = frozenset(fx.attributes) if fx else frozenset()
    assert result.collided_attributes == tuple(sorted(look_attrs & fx_attrs))
    assert result.unclaimed_attributes == tuple(sorted(KNOWN_ATTRIBUTES - (look_attrs | fx_attrs)))


def test_the_shipped_library_contains_a_real_collision_witness():
    # AC-SCENE-003 requires a collision scene in the ASSETS, and AC-SCENE-005's
    # enumeration must be non-vacuous there too — a movement fx can never
    # produce one (design.md §3.3 footnote), so this proves the authored scene
    # is a dimmer/colour one.
    witnesses = [
        (s.scene_id, r.collided_attributes) for s, r in _compiled_assets() if r.collided_attributes
    ]
    assert witnesses


def test_the_shipped_library_contains_a_scene_that_leaves_pan_tilt_unclaimed():
    # spec.md §D — Pan/Tilt carry-over is not hidden; it is enumerated.
    assert [
        s.scene_id for s, r in _compiled_assets() if {"Pan", "Tilt"} <= set(r.unclaimed_attributes)
    ]


def test_an_occupied_sequence_surfaces_as_a_scene_error_not_an_fx_one():
    """The upstream exception TYPE stops at this package's boundary.

    `select_sequence_number` is fx's (decision H) and raises
    `FxInstantiationError`. Letting that class travel would force every caller
    of a scene to catch an fx exception to stay correct — the tool layer did not
    know to, and crashed instead of refusing. The reason code travels unchanged
    so the two layers keep ONE vocabulary.
    """
    scene = _scene("s40", look_id=CORE4_LOOK.look_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=CORE4_LOOK,
            fx=None,
            group=11,
            sequences_section=_sequences(1, 2),
            cues_section=_cues(),
            sequence_number=1,
        )
    assert excinfo.value.reason == fx_sequence_occupied
    assert not isinstance(excinfo.value, FxInstantiationError)


# =============================================================================
# fx refusal gate — the scene path must refuse what the fx path refuses
#
# Found by independent pre-merge review, NOT by this suite: `compile_scene`
# reused fx's line BUILDERS but skipped `_refuse_unemitted_axes`, which
# `build_fx_bundle` runs first (`server/fx/instantiate.py:472`). One asset
# therefore behaved differently on the two console routes — refused by
# `instantiate_fx`, silently compiled here with the declared axis DROPPED.
#
# Why nothing else catches it: under this SPEC's verification ceiling the
# console returns ok:true on every line and cue content is not readable at all
# (spec.md §C.1), so the defect emits NO runtime signal. These tests are the
# only net. The fixtures below deliberately do NOT appear in the shipped fx
# library — the whole point is that the gate must hold for assets the fx
# loader accepts but this version cannot faithfully emit.
# =============================================================================


_UNEMITTED_AXIS_FX = {
    # Reachable through the SHIPPED fx loader: it accepts `relative` and never
    # cross-checks `circle` against `phase_to`.
    "relative": (
        _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], relative=30),
        fx_relative_not_emitted,
    ),
    "circle_phase": (
        _fx(
            "circle",
            steps=[{"Pan": -20, "Tilt": -10}, {"Pan": 20, "Tilt": 10}],
            phase_from=0,
            phase_to=180,
        ),
        fx_circle_phase_conflict,
    ),
    # Reachable by constructing an `Fx` directly — the loader is not the only
    # door, which is exactly why fx guards it a second time.
    "one_step": (
        _fx("pulse", steps=[{"Dimmer": 100}]),
        fx_step_axis_too_short,
    ),
    "accel": (
        _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], accel=25),
        fx_gated_axis_not_emitted,
    ),
    "decel": (
        _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], decel=25),
        fx_gated_axis_not_emitted,
    ),
}


@pytest.mark.parametrize("case", sorted(_UNEMITTED_AXIS_FX))
def test_an_fx_with_an_unemitted_axis_is_refused_by_the_scene_path_too(case):
    fx, expected_reason = _UNEMITTED_AXIS_FX[case]
    scene = _scene(f"unemitted-{case}", fx_id=fx.fx_id)

    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, fx=fx)

    # The reason code travels unchanged — the two layers keep ONE vocabulary.
    assert excinfo.value.reason == expected_reason
    # ...but the exception TYPE is this package's, or every caller of a scene
    # would have to catch an fx class to stay correct (the boundary contract
    # the `select_sequence_number` translation already established).
    assert not isinstance(excinfo.value, FxInstantiationError)


@pytest.mark.parametrize("case", sorted(_UNEMITTED_AXIS_FX))
def test_the_two_console_routes_agree_on_every_unemitted_axis(case):
    # The property that actually matters: one asset, one verdict. If fx refuses
    # it, the scene path must refuse it — a divergence means the same authored
    # entry fires on one route and is rejected on the other.
    fx, _ = _UNEMITTED_AXIS_FX[case]

    with pytest.raises(FxInstantiationError) as fx_error:
        build_fx_bundle(fx, group=11, sequence=1)
    with pytest.raises(SceneCompilationError) as scene_error:
        _compile(_scene(f"agree-{case}", fx_id=fx.fx_id), fx=fx)

    assert scene_error.value.reason == fx_error.value.reason


@pytest.mark.parametrize("case", sorted(_UNEMITTED_AXIS_FX))
def test_a_refused_fx_never_reaches_the_look_line_or_the_store(case):
    # Non-emptiness with teeth: the refusal has to happen BEFORE anything is
    # built, so a partially-assembled bundle can never escape. A look is
    # supplied precisely so a late refusal would still have produced a value
    # line to leak.
    fx, _ = _UNEMITTED_AXIS_FX[case]
    scene = _scene(f"noleak-{case}", look_id=CORE4_LOOK.look_id, fx_id=fx.fx_id)

    with pytest.raises(SceneCompilationError) as excinfo:
        _compile(scene, look=CORE4_LOOK, fx=fx)

    assert not hasattr(excinfo.value, "commands")


def test_the_refusal_gate_is_the_fx_module_object_not_a_copy():
    # Decision E's rule applied to the gate: reuse, never re-implement. A
    # scene-local copy would drift the moment fx adds a fifth refusal — and
    # the drift would be silent for exactly the reason this section exists.
    assert scene_refuse_unemitted_axes is fx_refuse_unemitted_axes


def test_a_conforming_fx_still_compiles_after_the_gate():
    # Control. Without this the four tests above are satisfied by a compiler
    # that refuses everything.
    scene = _scene("conforming", look_id=CORE4_LOOK.look_id, fx_id=MOVEMENT_FX.fx_id)
    result = _compile(scene, look=CORE4_LOOK, fx=MOVEMENT_FX)
    assert any(command.startswith("Store Sequence ") for command in result.commands)


# =============================================================================
# guard sweep — every refusal needs its OWN net
#
# Found by a systematic sweep after the pre-merge review: each guard clause in
# `server/scene/**` was neutralised in turn (75 clauses, compound conditions
# split per operand) and the scene suites re-run. 68 died. The survivors were
# guards standing with no test of their own — most of them a SECOND door onto a
# refusal whose FIRST door was covered, so a test asserting the reason code
# passed without ever reaching them. That is the same shape as the single-axis
# guard whose LOOK_ONLY half had no net while its FX_ONLY half carried both.
# =============================================================================


def test_a_cue_section_whose_objects_are_not_a_list_is_refused():
    # `_cue_numbers` guards the SHAPE of the listing; `_select_cue_number`
    # guards the section's self-reported failure. Both raise
    # CUE_SECTION_UNAVAILABLE, so the existing reason-code tests were satisfied
    # entirely by the second one. Neutralising this clause killed nothing.
    scene = _scene("shape", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section={"objects": "not-a-list"},
        )
    assert excinfo.value.reason == CUE_SECTION_UNAVAILABLE


def test_a_cue_section_that_reports_not_ok_without_a_reason_is_refused():
    # The refusal is `isinstance(reason, str) or ok is False` — two operands,
    # and only the first had a test. A section can report failure by flag alone
    # (no `reason` string), and that path reached the number picker unguarded.
    scene = _scene("notok", fx_id=DIMMER_FX.fx_id)
    with pytest.raises(SceneCompilationError) as excinfo:
        compile_scene(
            scene,
            look=None,
            fx=DIMMER_FX,
            group=11,
            sequences_section=_sequences(),
            cues_section={"ok": False, "objects": []},
        )
    assert excinfo.value.reason == CUE_SECTION_UNAVAILABLE


def test_a_readable_cue_section_is_still_accepted():
    # Control for both refusals above — without it a compiler that rejects
    # every cue section satisfies them.
    scene = _scene("readable", fx_id=DIMMER_FX.fx_id)
    result = _compile(scene, fx=DIMMER_FX)
    assert any(command.startswith("Store Sequence ") for command in result.commands)
