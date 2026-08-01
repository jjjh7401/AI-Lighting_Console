"""M4 — the fx instantiation bundle builder, collision guards and report.

AC-FXLIB-008 (bundle shape + programming discipline) · AC-FXLIB-009 (value-line
collision, both boundaries) · AC-FXLIB-010 (Store safety) · AC-FXLIB-011
(executor is never automatic) · AC-FXLIB-012 (Korean two-tier report) ·
AC-FXLIB-023 (the forbidden ``At Step <k>`` form).

Console contact: zero. Every assertion below is at the STRING level, on the
exact text the dedupe and the gate would see — no normalising, no re-parsing.

The fx entries are built in memory rather than loaded from ``server/fx/library``
because the library is a sibling milestone's deliverable. That is not a
shortcut: the bundle builder's contract is with the SCHEMA, and an in-memory
entry exercises it without coupling this file to another milestone's authoring
choices.
"""

from __future__ import annotations

import re

import pytest

from server.fx.instantiate import (
    CIRCLE_PHASE_CONFLICT,
    CROSS_CALL_COLLISION,
    GATED_AXIS_NOT_EMITTED,
    RELATIVE_NOT_EMITTED,
    SEQUENCE_NUMBER_UNAVAILABLE,
    SEQUENCE_OCCUPIED,
    SEQUENCE_TRUNCATED,
    SEQUENCE_UNAVAILABLE,
    STEP_AXIS_TOO_SHORT,
    VALUE_LINE_COLLISION,
    FxInstantiationError,
    build_fx_bundle,
    collided_lines,
    instantiate_fx,
    is_programmer_state,
    select_sequence_number,
)
from server.fx.report import (
    COMPLETE,
    EFFECT_EVIDENCE_NOTICE,
    PARTIAL,
    PLANNED,
    build_report,
    to_korean,
)
from server.fx.schema import PATTERN_KINDS, Fx, FxStep, StepValue
from server.orchestrator.tools import rig_object, rig_section

# -- fx assembly ---------------------------------------------------------------


def _fx(pattern: str, *, steps, fx_id: str | None = None, name: str | None = None, **axes) -> Fx:
    return Fx(
        fx_id=fx_id or f"{pattern}_fixture",
        display_name=name or f"{pattern.title()} Fixture",
        pattern=pattern,
        steps=tuple(
            FxStep(values=tuple(StepValue(attribute=a, value=v) for a, v in step.items()))
            for step in steps
        ),
        **axes,
    )


# One entry per pattern kind in the closed vocabulary. `pulse` is the M0 [실측]
# anchor; the other five are shaped after design.md §4.1/§4.2.
PATTERNS: dict[str, Fx] = {
    "sweep": _fx(
        "sweep",
        steps=[{"Pan": -20}, {"Pan": 20}],
        phase_from=0,
        phase_to=360,
        speed=60,
    ),
    "wave": _fx(
        "wave",
        steps=[{"Tilt": -10}, {"Tilt": 10}],
        phase_from=0,
        phase_to=360,
        speed=45,
    ),
    # `circle` and `diagonal` carry phase_from ONLY, matching how the library
    # assets author them: a circle's quarter-cycle offset belongs to the pattern
    # kind, and a diagonal's in-phase/anti-phase distinction lives in its step
    # values (both axes rising, or one rising while the other falls).
    "circle": _fx(
        "circle",
        steps=[{"Pan": -20, "Tilt": -10}, {"Pan": 20, "Tilt": 10}],
        phase_from=0,
        speed=45,
        x_wings=2,
    ),
    "diagonal": _fx(
        "diagonal",
        steps=[{"Pan": -30, "Tilt": -15}, {"Pan": 30, "Tilt": 15}],
        phase_from=0,
        speed=40,
    ),
    "pulse": _fx(
        "pulse",
        steps=[{"Dimmer": 100}, {"Dimmer": 0}],
        phase_from=0,
        phase_to=360,
        speed=60,
    ),
    "chase": _fx(
        "chase",
        steps=[
            {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 100},
        ],
        phase_from=0,
        phase_to=240,
        speed=120,
    ),
}

# progress.md §E.2 — the only bundle shape a live console has been observed to
# turn into a phaser AND capture into a stored cue. It is the regression
# baseline, quoted here verbatim rather than rebuilt from the builder's own
# helpers (which would make the comparison circular).
M0_ANCHOR = (
    "ChangeDestination Root",
    "ClearAll",
    "Group 11",
    "Attribute 'Dimmer' At 100",
    "Step 2",
    "Attribute 'Dimmer' At 0",
    "Attribute 'Dimmer' At Phase 0 Thru 360",
    "Attribute 'Dimmer' At Speed 60",
    "Store Sequence 12 Cue 1 'Dimmer Pulse'",
    "ClearAll",
)

M0_ANCHOR_FX = _fx(
    "pulse",
    fx_id="dimmer_pulse",
    name="Dimmer Pulse",
    steps=[{"Dimmer": 100}, {"Dimmer": 0}],
    phase_from=0,
    phase_to=360,
    speed=60,
)

_STEP_LINE = re.compile(r"^Step (\d+)$")


def _bundle(pattern: str, *, group: int = 11, sequence: int = 12, **kwargs) -> tuple[str, ...]:
    return build_fx_bundle(PATTERNS[pattern], group=group, sequence=sequence, **kwargs).commands


def test_the_pattern_fixtures_cover_the_closed_vocabulary():
    # Every parametrised assert below is only worth its name if it runs over all
    # six kinds; a fixture set that quietly lost one would still pass.
    assert set(PATTERNS) == set(PATTERN_KINDS)
    assert len(PATTERN_KINDS) == 6


# -- rig assembly (the sequences re-query) -------------------------------------
#
# Built by the PRODUCER's own helpers, as `test_looks_instantiate.py` established:
# a hand-written dict keeps passing after the console shape changes, which makes
# it a fixture rather than a boundary test.


def _sequences(*numbers: int, truncated: bool = False, unnumbered: int = 0) -> dict:
    children: list[dict] = [{"i": number, "name": f"Sequence {number}"} for number in numbers]
    children.extend({"name": "unnumbered"} for _ in range(unnumbered))
    objects = [rig_object(child) for child in children]
    return rig_section(objects, {"truncated": truncated, "node": {"childCount": len(children)}})


# -- outcome assembly (what run_commands reports back) -------------------------


class _Outcome:
    """The per-command outcome shape `run_commands` returns (tools.CommandOutcome).

    Duck-typed rather than imported: `server/fx/` may not import the tool layer
    (that import would be circular — tools imports fx at registration time), so
    the report layer reads `.command` / `.status` off whatever it is handed.
    """

    def __init__(self, command: str, status: str, detail: str = "") -> None:
        self.command = command
        self.status = status
        self.detail = detail


def _all_ok(commands) -> list[_Outcome]:
    return [_Outcome(command, "executed_ok") for command in commands]


# =============================================================================
# AC-FXLIB-008 — bundle shape + programming discipline
# =============================================================================


def test_the_pulse_bundle_is_byte_identical_to_the_m0_measured_anchor():
    plan = build_fx_bundle(M0_ANCHOR_FX, group=11, sequence=12)
    assert plan.commands == M0_ANCHOR


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_every_pattern_opens_with_exactly_one_change_destination_root(pattern):
    commands = _bundle(pattern)
    assert commands[0] == "ChangeDestination Root"
    assert commands.count("ChangeDestination Root") == 1


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_a_clear_all_precedes_the_capture_and_follows_the_store(pattern):
    commands = _bundle(pattern)
    store = next(i for i, c in enumerate(commands) if c.startswith("Store Sequence "))
    clears = [i for i, c in enumerate(commands) if c == "ClearAll"]
    assert any(i < store for i in clears), "no ClearAll before the capture"
    assert any(i > store for i in clears), "no ClearAll after the Store"


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_the_group_is_selected_by_bare_number_with_no_select_prefix(pattern):
    commands = _bundle(pattern, group=7)
    assert "Group 7" in commands
    assert not any(c.startswith("Select ") for c in commands)


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_the_store_line_appears_exactly_once_with_the_label_inline(pattern):
    fx = PATTERNS[pattern]
    commands = _bundle(pattern, sequence=31)
    stores = [c for c in commands if c.startswith("Store Sequence ")]
    assert stores == [f"Store Sequence 31 Cue 1 '{fx.display_name}'"]


def test_reset_selection_matricks_follows_the_store_when_matricks_is_used():
    commands = _bundle("circle")
    assert "Set Selection MAtricks 'XWings' 2" in commands
    store = commands.index(next(c for c in commands if c.startswith("Store Sequence ")))
    assert commands.index("Reset Selection MAtricks") > store


def test_no_matricks_lines_when_the_pattern_declares_none():
    commands = _bundle("sweep")
    assert not [c for c in commands if "MAtricks" in c]


# -- the five step-run asserts (AC-FXLIB-008) ---------------------------------


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_the_count_of_standalone_step_lines_is_one_less_than_the_step_count(pattern):
    fx = PATTERNS[pattern]
    commands = _bundle(pattern)
    step_lines = [c for c in commands if _STEP_LINE.match(c)]
    assert step_lines == [f"Step {n}" for n in range(2, len(fx.steps) + 1)]


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_no_step_1_line_is_emitted_because_the_first_step_is_the_current_one(pattern):
    assert "Step 1" not in _bundle(pattern)


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_each_step_line_precedes_the_value_lines_of_its_own_step(pattern):
    fx = PATTERNS[pattern]
    commands = _bundle(pattern)
    for index, step in enumerate(fx.steps):
        first = step.values[0]
        shown = int(first.value) if float(first.value).is_integer() else first.value
        first_value = commands.index(f"Attribute '{first.attribute}' At {shown}")
        if index == 0:
            assert not any(_STEP_LINE.match(c) for c in commands[:first_value])
        else:
            assert commands[first_value - 1] == f"Step {index + 1}"


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_modifier_lines_come_after_the_entire_step_run(pattern):
    commands = _bundle(pattern)
    last_step_value = max(
        i
        for i, c in enumerate(commands)
        if c.startswith("Attribute '") and " At Phase " not in c and " At Speed " not in c
    )
    modifiers = [i for i, c in enumerate(commands) if " At Phase " in c or " At Speed " in c]
    assert modifiers, "the fixtures all declare a phase and a speed"
    assert min(modifiers) > last_step_value


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_step_value_lines_are_never_chained_with_a_semicolon(pattern):
    commands = _bundle(pattern)
    for command in commands:
        if command.startswith("Attribute '") and " At Phase " not in command:
            if " At Speed " in command:
                continue  # the Speed line MAY chain (design.md §4.3)
            assert ";" not in command


def test_a_three_step_pattern_emits_step_2_and_step_3_as_standalone_lines():
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 50}, {"Dimmer": 0}], speed=60)
    commands = build_fx_bundle(fx, group=11, sequence=12).commands
    assert [c for c in commands if _STEP_LINE.match(c)] == ["Step 2", "Step 3"]
    assert commands[commands.index("Step 2") + 1] == "Attribute 'Dimmer' At 50"
    assert commands[commands.index("Step 3") + 1] == "Attribute 'Dimmer' At 0"


def test_reverse_changes_only_the_thru_value_of_the_phase_line():
    forward = _bundle("sweep")
    reversed_fx = _fx(
        "sweep",
        steps=[{"Pan": -20}, {"Pan": 20}],
        phase_from=0,
        phase_to=360,
        speed=60,
        reverse=True,
    )
    backward = build_fx_bundle(reversed_fx, group=11, sequence=12).commands
    assert "Attribute 'Pan' At Phase 0 Thru 360" in forward
    assert "Attribute 'Pan' At Phase 0 Thru -360" in backward
    assert [c for c in forward if " At Phase " not in c] == [
        c for c in backward if " At Phase " not in c
    ]


def test_a_circle_puts_its_two_axes_a_quarter_cycle_apart():
    # 31_choreography_patterns.md:78-79 + spec.md §A: Pan At Phase 0 + Tilt At
    # Phase 90 IS the circle. The offset comes from the pattern kind because the
    # schema holds one phase pair for the whole entry.
    commands = _bundle("circle")
    assert "Attribute 'Pan' At Phase 0" in commands
    assert "Attribute 'Tilt' At Phase 90" in commands
    assert not [c for c in commands if " At Phase " in c and " Thru " in c]


def test_a_diagonal_puts_both_axes_at_the_same_phase():
    commands = _bundle("diagonal")
    assert "Attribute 'Pan' At Phase 0" in commands
    assert "Attribute 'Tilt' At Phase 0" in commands


def test_a_circle_and_a_diagonal_do_not_emit_the_same_phase_lines():
    # The regression this guards: with the quarter-cycle offset gone, both
    # patterns emit Pan/Tilt At Phase 0 and the closed vocabulary silently
    # loses one of its four unconditional patterns. Nothing at runtime would
    # say so — the effect is not machine-readable.
    circle = [c for c in _bundle("circle") if " At Phase " in c]
    diagonal = [c for c in _bundle("diagonal") if " At Phase " in c]
    assert circle != diagonal


def test_a_reversed_circle_offsets_its_second_axis_the_other_way():
    fx = _fx(
        "circle",
        steps=[{"Pan": -20, "Tilt": -10}, {"Pan": 20, "Tilt": 10}],
        phase_from=0,
        speed=45,
        reverse=True,
    )
    commands = build_fx_bundle(fx, group=11, sequence=12).commands
    assert "Attribute 'Pan' At Phase 0" in commands
    assert "Attribute 'Tilt' At Phase -90" in commands


def test_a_circle_that_also_declares_phase_to_is_refused():
    fx = _fx(
        "circle",
        steps=[{"Pan": -20, "Tilt": -10}, {"Pan": 20, "Tilt": 10}],
        phase_from=0,
        phase_to=360,
        speed=45,
    )
    with pytest.raises(FxInstantiationError) as excinfo:
        build_fx_bundle(fx, group=11, sequence=12)
    assert excinfo.value.reason == CIRCLE_PHASE_CONFLICT
    assert "a circle's axes are a quarter cycle apart by definition" in str(excinfo.value)


def test_a_multi_attribute_pattern_with_a_phase_span_walks_it_across_the_attributes():
    # The one rule here the SPEC left open: a non-circle pattern driving several
    # attributes spends phase_from..phase_to across them, endpoints included.
    commands = _bundle("chase")
    assert "Attribute 'ColorRGB_R' At Phase 0" in commands
    assert "Attribute 'ColorRGB_G' At Phase 120" in commands
    assert "Attribute 'ColorRGB_B' At Phase 240" in commands


def test_the_speed_line_chains_every_target_attribute():
    assert "Attribute 'Pan' At Speed 45 ; Attribute 'Tilt' At Speed 45" in _bundle("circle")


def test_a_one_step_fx_is_refused_by_the_builder_not_only_by_the_loader():
    # The loader is not the only door into the builder: an `Fx` constructed
    # directly never met it. Left through, this builds the exact bundle M0 fired
    # three times — no `Step` line, no phaser, every line ok:true.
    fx = Fx(
        fx_id="one_step",
        display_name="One Step",
        pattern="pulse",
        steps=(FxStep(values=(StepValue(attribute="Dimmer", value=100),)),),
        phase_from=0,
        phase_to=360,
        speed=60,
    )
    with pytest.raises(FxInstantiationError) as excinfo:
        build_fx_bundle(fx, group=11, sequence=12)
    assert excinfo.value.reason == STEP_AXIS_TOO_SHORT
    assert "carries 1 step(s); a phaser needs at least 2" in str(excinfo.value)


def test_a_pattern_declaring_only_a_start_phase_gets_a_bare_phase_line():
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], phase_from=90, speed=60)
    commands = build_fx_bundle(fx, group=11, sequence=12).commands
    assert "Attribute 'Dimmer' At Phase 90" in commands
    assert not [c for c in commands if " Thru " in c]


def test_a_pattern_declaring_no_speed_emits_no_speed_line():
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], phase_from=0, phase_to=360)
    commands = build_fx_bundle(fx, group=11, sequence=12).commands
    assert not [c for c in commands if " At Speed " in c]


def test_a_label_that_cannot_be_quoted_on_the_command_line_is_refused():
    fx = _fx("pulse", name="Don't", steps=[{"Dimmer": 100}, {"Dimmer": 0}], speed=60)
    with pytest.raises(FxInstantiationError, match="cannot be quoted on the MA3 command line"):
        build_fx_bundle(fx, group=11, sequence=12)


def test_an_empty_label_is_refused_rather_than_stored_as_a_nameless_sequence():
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], speed=60)
    with pytest.raises(FxInstantiationError, match="has an empty label to store under"):
        build_fx_bundle(fx, group=11, sequence=12, label="   ")


def test_an_explicit_label_overrides_the_display_name():
    plan = build_fx_bundle(PATTERNS["pulse"], group=11, sequence=12, label="Chorus Pulse")
    assert plan.label == "Chorus Pulse"
    assert "Store Sequence 12 Cue 1 'Chorus Pulse'" in plan.commands


def test_the_plan_exposes_the_lines_the_dedupe_will_compare():
    plan = build_fx_bundle(PATTERNS["pulse"], group=11, sequence=12)
    assert "ClearAll" not in plan.non_exempt_commands
    assert "Group 11" not in plan.non_exempt_commands
    assert "Step 2" in plan.non_exempt_commands
    assert "Attribute 'Dimmer' At 100" in plan.non_exempt_commands


def test_the_structured_plan_names_what_it_will_create():
    data = build_fx_bundle(PATTERNS["circle"], group=11, sequence=12, executor=191).to_dict()
    assert data["pattern"] == "circle"
    assert data["group"] == 11
    assert data["sequence"] == 12
    assert data["cue"] == 1
    assert data["executor"] == 191
    assert data["attributes"] == ["Pan", "Tilt"]
    assert data["step_count"] == 2
    assert data["matricks"] == [{"axis": "XWings", "value": 2}]
    assert data["commands"] == list(_bundle("circle", executor=191))


def test_an_fx_declaring_relative_is_refused_because_v1_never_emits_it():
    fx = _fx("sweep", steps=[{"Pan": -20}, {"Pan": 20}], speed=60, relative=30)
    with pytest.raises(FxInstantiationError) as excinfo:
        build_fx_bundle(fx, group=11, sequence=12)
    assert excinfo.value.reason == RELATIVE_NOT_EMITTED
    assert "declares relative=30" in str(excinfo.value)


@pytest.mark.parametrize("axis", ["accel", "decel"])
def test_an_fx_declaring_a_gated_curve_axis_is_refused(axis):
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], speed=60, **{axis: -100})
    with pytest.raises(FxInstantiationError) as excinfo:
        build_fx_bundle(fx, group=11, sequence=12)
    assert excinfo.value.reason == GATED_AXIS_NOT_EMITTED
    assert f"declares {axis}=-100" in str(excinfo.value)


# =============================================================================
# AC-FXLIB-023 — the forbidden `Attribute '<attr>' At Step <k>` form
# =============================================================================

_FORBIDDEN_AT_STEP = re.compile(r"\bAt\s+Step\s+\d+", re.IGNORECASE)


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_no_bundle_emits_the_forbidden_attribute_at_step_form(pattern):
    for command in _bundle(pattern, executor=191):
        assert not _FORBIDDEN_AT_STEP.search(command), command


def test_the_forbidden_form_scan_is_not_vacuous():
    assert _FORBIDDEN_AT_STEP.search("Attribute 'Dimmer' At Step 2")
    assert _FORBIDDEN_AT_STEP.search("attribute 'dimmer' at step 2")
    assert not _FORBIDDEN_AT_STEP.search("Step 2")


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_a_step_transition_appears_only_as_a_standalone_line(pattern):
    for command in _bundle(pattern):
        if re.search(r"\bStep\b", command, re.IGNORECASE):
            assert _STEP_LINE.match(command), command


# =============================================================================
# AC-FXLIB-009 (a) — the in-bundle value-line collision guard
# =============================================================================


def test_the_exemption_classifier_matches_the_three_exempt_shapes():
    assert is_programmer_state("Clear")
    assert is_programmer_state("ClearAll")
    assert is_programmer_state("clearall")
    assert is_programmer_state("Group 11")
    assert is_programmer_state("Fixture 1 Thru 4")
    assert is_programmer_state("Group 1 + 2")


def test_the_exemption_classifier_refuses_the_lines_that_actually_collide():
    assert not is_programmer_state("Step 2")
    assert not is_programmer_state("Attribute 'Dimmer' At 100")
    assert not is_programmer_state("Attribute 'Pan' At Phase 0 Thru 360")
    assert not is_programmer_state("Store Sequence 12 Cue 1 'X'")
    assert not is_programmer_state("Select Group 11")


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_every_pattern_bundle_carries_unique_non_exempt_lines(pattern):
    commands = _bundle(pattern, executor=191)
    non_exempt = [c for c in commands if not is_programmer_state(c)]
    assert len(non_exempt) == len(set(non_exempt))
    assert non_exempt, "a bundle of nothing but exempt lines would pass vacuously"


def test_a_pattern_repeating_a_step_value_is_refused_before_the_bundle_exists():
    # The M0-era failure shape made silent: the second `At 100` is dropped by the
    # dedupe, `Store` then runs against a ONE-step programmer, and nothing on
    # stage moves while every line reports ok.
    fx = Fx(
        fx_id="broken_pulse",
        display_name="Broken Pulse",
        pattern="pulse",
        steps=(
            FxStep(values=(StepValue(attribute="Dimmer", value=100),)),
            FxStep(values=(StepValue(attribute="Dimmer", value=100),)),
        ),
        speed=60,
    )
    with pytest.raises(FxInstantiationError) as excinfo:
        build_fx_bundle(fx, group=11, sequence=12)
    assert excinfo.value.reason == VALUE_LINE_COLLISION
    assert "Attribute 'Dimmer' At 100" in str(excinfo.value)


def test_duplicate_exempt_lines_do_not_trigger_the_in_bundle_guard():
    # The control group: every bundle carries ClearAll twice by design.
    commands = _bundle("pulse")
    assert commands.count("ClearAll") == 2


# =============================================================================
# AC-FXLIB-009 (b) — the cross-call (instruction-scoped) collision
# =============================================================================


def test_a_non_exempt_line_skipped_as_already_executed_is_a_cross_call_collision():
    commands = _bundle("pulse")
    outcomes = _all_ok(commands)
    outcomes[commands.index("Step 2")] = _Outcome("Step 2", "skipped_already_executed")
    assert collided_lines(outcomes) == ("Step 2",)


def test_an_exempt_line_skipped_as_already_executed_is_not_a_collision():
    outcomes = [
        _Outcome("ClearAll", "skipped_already_executed"),
        _Outcome("Group 11", "skipped_already_executed"),
        _Outcome("Attribute 'Dimmer' At 100", "executed_ok"),
    ]
    assert collided_lines(outcomes) == ()


def test_the_same_pattern_on_two_groups_collides_on_its_value_lines():
    first = _bundle("pulse", group=11, sequence=12)
    second = _bundle("pulse", group=12, sequence=13)
    already = {c for c in first if not is_programmer_state(c)}
    outcomes = [
        _Outcome(c, "skipped_already_executed" if c in already else "executed_ok") for c in second
    ]
    collided = collided_lines(outcomes)
    assert "Attribute 'Dimmer' At 100" in collided
    assert "Attribute 'Dimmer' At 0" in collided
    assert "Step 2" in collided


def test_two_different_patterns_collide_on_the_lines_every_bundle_shares():
    # design.md §5 names `Step 2` as the line common to EVERY pattern, so two
    # instantiations in one instruction turn fold even when they share no
    # attribute. The measured set is one line WIDER than that: the opening
    # `ChangeDestination Root` is common to every bundle too, and it is not in
    # the exempt three either — so the fold begins on the bundle's FIRST line.
    first = _bundle("pulse", group=11, sequence=12)
    second = _bundle("sweep", group=12, sequence=13)
    already = {c for c in first if not is_programmer_state(c)}
    shared = already.intersection(second)
    assert shared == {"ChangeDestination Root", "Step 2"}, shared
    outcomes = [
        _Outcome(c, "skipped_already_executed" if c in shared else "executed_ok") for c in second
    ]
    assert collided_lines(outcomes) == ("ChangeDestination Root", "Step 2")


def test_a_clean_run_reports_no_collision():
    commands = _bundle("circle")
    assert collided_lines(_all_ok(commands)) == ()


def test_outcomes_arriving_as_mappings_are_read_the_same_way():
    # `run_commands` returns CommandOutcome objects, but the SAME two fields come
    # back as a mapping in its JSON content. Reading only one shape would make
    # the collision detector depend on which surface the caller happened to hold.
    outcomes = [
        {"command": "ClearAll", "status": "skipped_already_executed"},
        {"command": "Step 2", "status": "skipped_already_executed"},
        {"command": "Attribute 'Dimmer' At 0", "status": "executed_ok"},
    ]
    assert collided_lines(outcomes) == ("Step 2",)


def test_an_outcome_without_a_command_string_is_not_counted_as_a_collision():
    assert collided_lines([{"status": "skipped_already_executed"}]) == ()


def test_no_outcomes_at_all_is_not_a_collision():
    assert collided_lines(None) == ()


# =============================================================================
# AC-FXLIB-010 — Store safety
# =============================================================================


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_no_bundle_emits_overwrite_in_any_case(pattern):
    for command in _bundle(pattern, executor=191):
        assert "overwrite" not in command.casefold(), command


def test_the_sequence_number_is_the_first_free_number_in_the_requery():
    assert select_sequence_number(_sequences(1, 2, 4)) == 3


def test_the_sequence_number_is_one_when_the_pool_is_empty():
    assert select_sequence_number(_sequences()) == 1


def test_a_truncated_sequence_requery_refuses_auto_assignment():
    with pytest.raises(FxInstantiationError) as excinfo:
        select_sequence_number(_sequences(1, 2, truncated=True))
    assert excinfo.value.reason == SEQUENCE_TRUNCATED
    assert "the sequence pool listing was truncated" in str(excinfo.value)


def test_an_unavailable_sequences_section_refuses_auto_assignment():
    with pytest.raises(FxInstantiationError) as excinfo:
        select_sequence_number({"reason": "path_not_resolved"})
    assert excinfo.value.reason == SEQUENCE_UNAVAILABLE
    assert "the sequence pool could not be read" in str(excinfo.value)


def test_a_sequence_child_the_console_could_not_number_refuses_auto_assignment():
    with pytest.raises(FxInstantiationError) as excinfo:
        select_sequence_number(_sequences(1, 2, unnumbered=1))
    assert excinfo.value.reason == SEQUENCE_NUMBER_UNAVAILABLE
    assert "carries no number" in str(excinfo.value)


def test_a_sequences_section_carrying_no_object_list_refuses_auto_assignment():
    with pytest.raises(FxInstantiationError) as excinfo:
        select_sequence_number({"truncated": False, "total": 3})
    assert excinfo.value.reason == SEQUENCE_UNAVAILABLE
    assert "the sequence pool could not be read" in str(excinfo.value)


def test_a_requested_free_sequence_number_is_honoured():
    assert select_sequence_number(_sequences(1, 2), requested=9) == 9


def test_a_requested_occupied_sequence_number_is_refused():
    with pytest.raises(FxInstantiationError) as excinfo:
        select_sequence_number(_sequences(1, 2, 9), requested=9)
    assert excinfo.value.reason == SEQUENCE_OCCUPIED
    assert "sequence 9 is already occupied" in str(excinfo.value)


def test_instantiate_fx_binds_the_sequence_number_the_requery_measured():
    plan = instantiate_fx(PATTERNS["pulse"], group=11, sequences_section=_sequences(1, 2, 3))
    assert plan.sequence == 4
    assert f"Store Sequence 4 Cue 1 '{PATTERNS['pulse'].display_name}'" in plan.commands


def test_instantiate_fx_refuses_a_truncated_requery_rather_than_inventing_a_number():
    with pytest.raises(FxInstantiationError) as excinfo:
        instantiate_fx(PATTERNS["pulse"], group=11, sequences_section=_sequences(1, truncated=True))
    assert excinfo.value.reason == SEQUENCE_TRUNCATED


# =============================================================================
# AC-FXLIB-011 — the executor is never automatic
# =============================================================================


@pytest.mark.parametrize("pattern", sorted(PATTERNS))
def test_no_assign_line_when_no_executor_is_specified(pattern):
    assert not [c for c in _bundle(pattern) if c.startswith("Assign ")]


def test_exactly_one_assign_line_when_an_executor_is_specified():
    commands = _bundle("pulse", sequence=12, executor=191)
    assert [c for c in commands if c.startswith("Assign ")] == [
        "Assign Sequence 12 At Executor 191"
    ]


def test_the_assign_line_follows_the_store_it_binds():
    commands = _bundle("pulse", executor=191)
    store = next(i for i, c in enumerate(commands) if c.startswith("Store Sequence "))
    assert commands.index("Assign Sequence 12 At Executor 191") > store


# =============================================================================
# AC-FXLIB-012 — the Korean two-tier report
# =============================================================================


def _plan(pattern: str = "pulse", **kwargs):
    return build_fx_bundle(PATTERNS[pattern], group=11, sequence=12, **kwargs)


def test_the_report_has_a_summary_tier_and_a_detail_tier():
    plan = _plan()
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert text.splitlines()[0].startswith("[")
    assert "상세:" in text


def test_the_success_report_names_the_created_sequence_cue_label_group_and_pattern():
    plan = _plan()
    report = build_report(plan, _all_ok(plan.commands))
    assert report.verdict == COMPLETE
    assert report.succeeded
    text = to_korean(report)
    assert "시퀀스 12" in text
    assert "큐 1" in text
    assert "Pulse Fixture" in text
    assert "그룹 11" in text
    assert "pulse" in text


def test_the_success_report_still_states_the_effect_is_not_machine_verifiable():
    # Unconditional (REQ-FXLIB-014 (c)): M0 measured that a stored cue holding a
    # phaser is indistinguishable from an empty one, so no report path may imply
    # the effect was confirmed.
    plan = _plan()
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert EFFECT_EVIDENCE_NOTICE in text
    assert "효과는 기계로 확인되지 않습니다" in EFFECT_EVIDENCE_NOTICE
    assert "사람이" in EFFECT_EVIDENCE_NOTICE


def test_the_report_never_offers_the_stored_sequence_as_evidence_of_the_effect():
    plan = _plan()
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert "재조회로 확인할 수 있는 것은 시퀀스·큐의 존재뿐입니다" in text


def test_the_speed_is_reported_in_bpm():
    plan = _plan()
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert "60 BPM" in text


def test_a_plan_level_report_does_not_claim_execution():
    report = build_report(_plan())
    assert report.verdict == PLANNED
    assert not report.executed
    assert not report.succeeded
    assert "실행 결과를 관측하지 않은 계획 단계 보고입니다" in to_korean(report)


def test_not_executed_commands_are_propagated_and_success_is_withheld():
    plan = _plan()
    outcomes = _all_ok(plan.commands)
    store = next(i for i, c in enumerate(plan.commands) if c.startswith("Store Sequence "))
    outcomes[store] = _Outcome(plan.commands[store], "failed", "Illegal object")
    for index in range(store + 1, len(outcomes)):
        outcomes[index] = _Outcome(plan.commands[index], "not_executed")
    report = build_report(plan, outcomes)
    assert report.verdict == PARTIAL
    assert not report.succeeded
    assert report.failed == (plan.commands[store],)
    assert report.not_executed == tuple(plan.commands[store + 1 :])
    text = to_korean(report)
    assert "미실행 1개" in text
    assert "실패 1개" in text


def test_a_cross_call_collision_withholds_success_and_warns_of_an_incomplete_store():
    plan = _plan()
    outcomes = _all_ok(plan.commands)
    outcomes[plan.commands.index("Step 2")] = _Outcome("Step 2", "skipped_already_executed")
    report = build_report(plan, outcomes)
    assert report.verdict == CROSS_CALL_COLLISION
    assert not report.succeeded
    assert report.collided == ("Step 2",)
    text = to_korean(report)
    assert "교차 호출 충돌" in text
    assert "불완전한 시퀀스·큐가 이미 생성됐을 수 있습니다" in text
    assert "v1의 운용 경계는 지시 턴당 인스턴스화 1회입니다" in text


def test_an_exempt_line_skipped_as_already_executed_does_not_spoil_the_report():
    plan = _plan()
    outcomes = _all_ok(plan.commands)
    outcomes[1] = _Outcome("ClearAll", "skipped_already_executed")
    report = build_report(plan, outcomes)
    assert report.collided == ()
    assert report.verdict == COMPLETE


def test_the_detail_tier_names_the_matricks_division_that_was_stored():
    plan = _plan("circle")
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert "MAtricks XWings 2" in text


def test_the_detail_tier_marks_an_executor_binding_as_user_specified():
    plan = _plan(executor=191)
    text = to_korean(build_report(plan, _all_ok(plan.commands)))
    assert "익스큐터 191에 배치 (사용자 명시 지정)" in text


def test_the_report_reads_outcomes_that_arrive_as_mappings():
    plan = _plan()
    outcomes = [{"command": c, "status": "executed_ok"} for c in plan.commands]
    report = build_report(plan, outcomes)
    assert report.verdict == COMPLETE
    assert report.executed_ok == len(plan.commands)


def test_the_structured_report_carries_the_same_facts_as_the_korean_one():
    plan = _plan()
    data = build_report(plan, _all_ok(plan.commands)).to_dict()
    assert data["sequence"] == 12
    assert data["cue"] == 1
    assert data["group"] == 11
    assert data["pattern"] == "pulse"
    assert data["speed_bpm"] == 60
    assert data["effect_evidence"] == EFFECT_EVIDENCE_NOTICE
    assert data["succeeded"] is True


# -- multi-attribute phase distribution ---------------------------------------
#
# Found by the orchestrator at the M5 seam: a chase over three colour attributes
# was emitting 0 / 180 / 360, and phase is cyclic, so 360 == 0 put red and blue
# in phase — a three-colour chase rendering as a two-phase flip. Machine-invisible
# by construction (the effect is not readable back), so it is pinned here.


def _phases(fx: Fx) -> list[str]:
    lines = build_fx_bundle(fx, group=11, sequence=12).commands
    return [line for line in lines if "At Phase" in line]


def test_a_full_cycle_spreads_the_attributes_without_two_sharing_a_phase():
    fx = _fx(
        "chase",
        steps=[
            {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 100},
        ],
        phase_from=0,
        phase_to=360,
    )
    assert _phases(fx) == [
        "Attribute 'ColorRGB_R' At Phase 0",
        "Attribute 'ColorRGB_G' At Phase 120",
        "Attribute 'ColorRGB_B' At Phase 240",
    ]


def test_no_two_attributes_land_on_the_same_point_of_the_cycle():
    # The defect this file exists to keep out, stated as the invariant rather
    # than as the one arithmetic that happened to produce it.
    fx = _fx(
        "chase",
        steps=[
            {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 100},
        ],
        phase_from=0,
        phase_to=360,
    )
    emitted = [float(line.rsplit(" ", 1)[1]) for line in _phases(fx)]
    on_the_cycle = [value % 360.0 for value in emitted]
    assert len(set(on_the_cycle)) == len(on_the_cycle)


def test_a_partial_arc_still_reaches_its_far_endpoint():
    # The far end of an arc that does NOT close is meaningful, so it stays
    # included — the fix is scoped to the closing case, not applied blanket.
    fx = _fx(
        "chase",
        steps=[
            {"ColorRGB_R": 100, "ColorRGB_G": 0, "ColorRGB_B": 0},
            {"ColorRGB_R": 0, "ColorRGB_G": 100, "ColorRGB_B": 100},
        ],
        phase_from=0,
        phase_to=180,
    )
    assert _phases(fx) == [
        "Attribute 'ColorRGB_R' At Phase 0",
        "Attribute 'ColorRGB_G' At Phase 90",
        "Attribute 'ColorRGB_B' At Phase 180",
    ]


def test_the_single_attribute_spread_keeps_the_measured_rulebook_literal():
    # The one-attribute branch fans across the SELECTION and its `0 Thru 360`
    # is a measured literal (M0 anchor). The fix must not have touched it.
    fx = _fx("pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}], phase_from=0, phase_to=360)
    assert _phases(fx) == ["Attribute 'Dimmer' At Phase 0 Thru 360"]
