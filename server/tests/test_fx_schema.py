"""FX schema + loader tests (M1 — AC-FXLIB-001).

Covers REQ-FXLIB-001 (schema axes, with the step axis as a required first-class
field), REQ-FXLIB-003 (the attribute vocabulary bands), REQ-FXLIB-004 (no
per-show binding field exists) and REQ-FXLIB-005 (explicit loader errors,
including the four step-axis validations).

Every failure mode is a SEPARATE test on purpose (design.md §7 — merging them
hides which rejection actually fired). The step-axis tests carry extra weight:
M0 measured that an effect's motion is NOT machine-readable (progress.md §E.2 —
a cue holding a phaser is indistinguishable from an empty cue), so a malformed
step axis emits no runtime signal whatsoever. The loader and these tests are the
only net under it.

Nothing here touches a console: pure functions over in-memory data, plus the one
tmp_path group that exercises the YAML directory wrapper.
"""

from __future__ import annotations

import pytest
import yaml

from server.fx.loader import FxSchemaError, load_library, load_library_from_dir
from server.fx.schema import (
    FX_SCHEMA_VERSION,
    GATED_CURVE_AXES,
    KNOWN_ATTRIBUTES,
    MATRICKS_AXES,
    MEASURED_ATTRIBUTES,
    MIN_STEPS,
    MOVEMENT_ATTRIBUTES,
    PATTERN_KINDS,
    PHASER_MODIFIER_AXES,
    Fx,
    FxStep,
    StepValue,
    fx_to_dict,
)

# Read-only import of the looks vocabulary. server/looks/** is PRESERVE
# (plan.md §A.5): this is a drift guard, never a definition hand-off — fx owns
# its own closed sets (design.md §3).
from server.looks.schema import KNOWN_ATTRIBUTES as LOOKS_KNOWN_ATTRIBUTES

# spec.md §A — the closed pattern vocabulary: 4 unconditional + 2 that entered
# on the ASSUMPTION-37 GO recorded by M0.
UNCONDITIONAL_PATTERNS = ("sweep", "wave", "circle", "diagonal")
GATED_PATTERNS = ("pulse", "chase")


def _fx(**overrides) -> dict:
    """A minimal valid fx dict; overrides replace individual keys."""
    entry = {
        "fx_id": "pan-sweep-wide",
        "display_name": "좌우 스윕",
        "pattern": "sweep",
        "aliases": ["스윕"],
        "mood_keywords": ["부드러운", "넓게"],
        "steps": [{"Pan": -20}, {"Pan": 20}],
        "phase_from": 0,
        "phase_to": 360,
        "speed": 60,
    }
    entry.update(overrides)
    return entry


def _library(*entries: dict) -> dict:
    return {"schema_version": FX_SCHEMA_VERSION, "fx": list(entries or (_fx(),))}


class TestPatternVocabularyIsClosed:
    """REQ-FXLIB-002 — the pattern set is enumerated, not open."""

    def test_the_set_is_exactly_the_four_unconditional_plus_two_gated_patterns(self):
        assert PATTERN_KINDS == UNCONDITIONAL_PATTERNS + GATED_PATTERNS

    def test_the_gated_patterns_are_present_because_m0_recorded_assumption_37_go(self):
        # If ASSUMPTION-37 had come back NEGATIVE these two would be absent.
        # progress.md §E.2 records `GO:` for it, so the 6-kind set is the live
        # branch — pinning it keeps a later edit from silently re-closing them.
        for pattern in GATED_PATTERNS:
            assert pattern in PATTERN_KINDS


class TestAttributeVocabularyBands:
    """REQ-FXLIB-003 — bands 1 and 2; band 3 (Accel/Decel) is not an attribute."""

    def test_band_one_is_the_measured_and_literal_backed_vocabulary(self):
        # Dimmer is the M0 [실측] anchor; the ColorRGB channels back `chase`
        # (31_choreography_patterns.md:75 multi-step colours).
        assert MEASURED_ATTRIBUTES == ("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

    def test_band_two_is_the_movement_vocabulary(self):
        assert MOVEMENT_ATTRIBUTES == ("Pan", "Tilt")

    def test_the_known_set_is_exactly_the_union_of_the_two_bands(self):
        assert frozenset(MEASURED_ATTRIBUTES + MOVEMENT_ATTRIBUTES) == KNOWN_ATTRIBUTES

    def test_every_fx_attribute_name_also_exists_in_the_looks_vocabulary(self):
        # Drift guard, not a definition hand-off: a typo'd attribute name here
        # would otherwise reach the console as a silently ineffective line.
        assert KNOWN_ATTRIBUTES <= LOOKS_KNOWN_ATTRIBUTES

    def test_the_static_beam_vocabulary_is_not_an_fx_attribute(self):
        # `Zoom`/`Iris` are looks band 3 — static preset values. No repository
        # evidence puts them on a phaser, so they are outside this vocabulary.
        assert "Zoom" not in KNOWN_ATTRIBUTES
        assert "Iris" not in KNOWN_ATTRIBUTES


class TestLoaderAcceptsAValidLibrary:
    """AC-FXLIB-001 happy path."""

    def test_a_minimal_library_loads(self):
        library = load_library(_library())
        assert library.schema_version == FX_SCHEMA_VERSION
        assert len(library.fx) == 1

    def test_the_loaded_entry_exposes_every_schema_axis(self):
        fx = load_library(_library()).fx[0]
        assert fx.fx_id == "pan-sweep-wide"
        assert fx.display_name == "좌우 스윕"
        assert fx.pattern == "sweep"
        assert fx.aliases == ("스윕",)
        assert fx.mood_keywords == ("부드러운", "넓게")
        assert fx.steps == (
            FxStep(values=(StepValue(attribute="Pan", value=-20),)),
            FxStep(values=(StepValue(attribute="Pan", value=20),)),
        )
        assert (fx.phase_from, fx.phase_to, fx.speed) == (0, 360, 60)
        assert fx.relative is None
        assert fx.reverse is False
        assert (fx.accel, fx.decel) == (None, None)

    def test_korean_mood_keywords_survive_verbatim(self):
        fx = load_library(_library(_fx(mood_keywords=["잔잔한", "웨이브"]))).fx[0]
        assert fx.mood_keywords == ("잔잔한", "웨이브")

    def test_the_target_attribute_axis_is_derived_from_the_authored_step_order(self):
        # REQ-FXLIB-001 names "대상 attribute" as an axis. It is derived rather
        # than stored: a second copy could drift out of sync with the steps.
        steps = [{"Pan": -20, "Tilt": -10}, {"Pan": 20, "Tilt": 10}]
        fx = load_library(_library(_fx(pattern="circle", steps=steps))).fx[0]
        assert fx.attributes == ("Pan", "Tilt")

    def test_a_three_step_entry_loads(self):
        steps = [{"Dimmer": 100}, {"Dimmer": 50}, {"Dimmer": 0}]
        fx = load_library(_library(_fx(pattern="pulse", steps=steps))).fx[0]
        assert len(fx.steps) == 3
        assert fx.steps[2].value_of("Dimmer") == 0

    def test_the_matricks_axes_load_when_declared(self):
        entry = _fx(
            pattern="circle", x=2, x_wings=2, x_shuffle=1234, phase_from_x=0, phase_to_x=360
        )
        fx = load_library(_library(entry)).fx[0]
        assert (fx.x, fx.x_wings, fx.x_shuffle) == (2, 2, 1234)
        assert (fx.phase_from_x, fx.phase_to_x) == (0, 360)

    def test_reverse_loads_as_a_parameter_not_a_pattern(self):
        # spec.md §A — reverse is `At Phase 0 Thru -360`, an axis on an existing
        # pattern, so it must never appear as a seventh pattern kind.
        fx = load_library(_library(_fx(reverse=True))).fx[0]
        assert fx.reverse is True
        assert "reverse" not in PATTERN_KINDS

    def test_lookup_by_id_finds_a_loaded_entry(self):
        library = load_library(
            _library(
                _fx(), _fx(fx_id="tilt-wave", pattern="wave", steps=[{"Tilt": -10}, {"Tilt": 10}])
            )
        )
        assert library.by_id("tilt-wave").pattern == "wave"

    def test_lookup_by_an_absent_id_raises(self):
        with pytest.raises(KeyError):
            load_library(_library()).by_id("no-such-fx")


class TestStepAxisIsRequiredAndValidated:
    """REQ-FXLIB-005 ①~④ + design.md §2.1 — the four step-axis validations.

    M0 established that a phaser requires two or more steps and that
    `Relative`/`Phase`/`Speed` MODIFY an existing phaser rather than create one.
    An entry that fails any of these produces `ok:true` on every line and zero
    motion on stage, with no machine-readable signal.
    """

    def test_a_single_step_entry_is_rejected(self):
        # ① len(steps) >= 2 — the phaser creation condition itself.
        with pytest.raises(FxSchemaError, match="at least 2 steps"):
            load_library(_library(_fx(steps=[{"Pan": -20}])))

    def test_an_empty_step_list_is_rejected(self):
        with pytest.raises(FxSchemaError, match="at least 2 steps"):
            load_library(_library(_fx(steps=[])))

    def test_the_minimum_step_count_is_two(self):
        assert MIN_STEPS == 2

    def test_a_non_list_steps_value_is_rejected(self):
        with pytest.raises(FxSchemaError, match="steps must be a list"):
            load_library(_library(_fx(steps={"Pan": -20})))

    def test_a_step_that_is_not_a_mapping_is_rejected(self):
        with pytest.raises(FxSchemaError, match="must be a mapping"):
            load_library(_library(_fx(steps=[["Pan", -20], {"Pan": 20}])))

    def test_an_empty_step_mapping_is_rejected(self):
        with pytest.raises(FxSchemaError, match="non-empty"):
            load_library(_library(_fx(steps=[{}, {"Pan": 20}])))

    def test_steps_with_differing_attribute_sets_are_rejected(self):
        # ② the attribute set must be identical across every step.
        steps = [{"Pan": -20}, {"Pan": 20, "Tilt": 10}]
        with pytest.raises(FxSchemaError, match="same attribute set"):
            load_library(_library(_fx(steps=steps)))

    def test_two_steps_carrying_the_same_value_for_one_attribute_are_rejected(self):
        # ③ the silent-failure case: the second `Attribute 'Pan' At 20` line is
        # dropped by the instruction-scoped dedupe, leaving a ONE-step
        # programmer, and `Store` still runs (design.md §5).
        steps = [{"Pan": 20}, {"Pan": 20}]
        with pytest.raises(FxSchemaError, match="repeats the value"):
            load_library(_library(_fx(steps=steps)))

    def test_a_repeated_value_in_a_non_adjacent_step_is_rejected(self):
        # Dedupe compares the whole emitted set, not just neighbours, so step 3
        # collapses into step 1 exactly the same way.
        steps = [{"Dimmer": 100}, {"Dimmer": 0}, {"Dimmer": 100}]
        with pytest.raises(FxSchemaError, match="repeats the value"):
            load_library(_library(_fx(pattern="pulse", steps=steps)))

    def test_one_attribute_repeating_while_another_varies_is_still_rejected(self):
        steps = [{"Pan": -20, "Tilt": 10}, {"Pan": 20, "Tilt": 10}]
        with pytest.raises(FxSchemaError, match="repeats the value"):
            load_library(_library(_fx(pattern="circle", steps=steps)))

    def test_a_modifier_axis_declared_without_steps_is_rejected(self):
        # ④ `Phase`/`Speed`/`Relative` modify an existing phaser; alone they
        # produce `ok:true` on every line and zero motion (M0 failure ×3).
        entry = _fx()
        del entry["steps"]
        with pytest.raises(FxSchemaError, match="without a step axis"):
            load_library(_library(entry))

    def test_a_matricks_axis_declared_without_steps_is_rejected(self):
        entry = _fx(x_wings=2)
        del entry["steps"]
        for key in ("phase_from", "phase_to", "speed"):
            del entry[key]
        with pytest.raises(FxSchemaError, match="without a step axis"):
            load_library(_library(entry))

    def test_an_entry_with_no_steps_and_no_modifiers_reports_the_missing_field(self):
        # The plain missing-field path stays distinguishable from ④.
        entry = _fx()
        for key in ("steps", "phase_from", "phase_to", "speed"):
            del entry[key]
        with pytest.raises(FxSchemaError, match="missing required field 'steps'"):
            load_library(_library(entry))


class TestLoaderRejectsSchemaViolations:
    """AC-FXLIB-001 / REQ-FXLIB-005 — each violation is its own test."""

    def test_an_unknown_pattern_kind_is_rejected(self):
        with pytest.raises(FxSchemaError, match="pattern kind outside the closed vocabulary"):
            load_library(_library(_fx(pattern="strobe")))

    def test_a_pattern_kind_differing_only_in_case_is_rejected(self):
        with pytest.raises(FxSchemaError, match="pattern kind outside the closed vocabulary"):
            load_library(_library(_fx(pattern="Sweep")))

    def test_an_unknown_attribute_name_in_a_step_is_rejected(self):
        with pytest.raises(FxSchemaError, match="unknown attribute name"):
            load_library(_library(_fx(steps=[{"Gobo1": 1}, {"Gobo1": 2}])))

    def test_a_static_beam_attribute_in_a_step_is_rejected(self):
        with pytest.raises(FxSchemaError, match="unknown attribute name"):
            load_library(_library(_fx(steps=[{"Zoom": 10}, {"Zoom": 20}])))

    def test_a_shutter_attribute_is_rejected(self):
        # spec.md §D — strobe/shutter are out of scope regardless of band.
        with pytest.raises(FxSchemaError, match="unknown attribute name"):
            load_library(_library(_fx(steps=[{"Shutter": 10}, {"Shutter": 50}])))

    def test_a_duplicate_fx_id_is_rejected(self):
        with pytest.raises(FxSchemaError, match="duplicate"):
            load_library(_library(_fx(), _fx()))

    def test_an_unknown_entry_field_is_rejected(self):
        # The closed schema is the mechanism enforcing REQ-FXLIB-004: this is
        # what stops a per-show binding being smuggled in as an extra key.
        with pytest.raises(FxSchemaError, match="unknown"):
            load_library(_library(_fx(group_number=11)))

    def test_a_smuggled_sequence_number_field_is_rejected(self):
        with pytest.raises(FxSchemaError, match="unknown"):
            load_library(_library(_fx(sequence=12)))

    def test_a_smuggled_executor_number_field_is_rejected(self):
        with pytest.raises(FxSchemaError, match="unknown"):
            load_library(_library(_fx(executor=191)))

    def test_a_missing_required_field_is_rejected(self):
        broken = _fx()
        del broken["display_name"]
        with pytest.raises(FxSchemaError, match="display_name"):
            load_library(_library(broken))

    def test_an_empty_fx_id_is_rejected(self):
        with pytest.raises(FxSchemaError, match="fx_id"):
            load_library(_library(_fx(fx_id="  ")))

    def test_an_unknown_library_level_key_is_rejected(self):
        with pytest.raises(FxSchemaError, match="unknown"):
            load_library({"schema_version": FX_SCHEMA_VERSION, "fx": [_fx()], "rig": {}})

    def test_a_foreign_schema_version_is_rejected(self):
        with pytest.raises(FxSchemaError, match="schema_version"):
            load_library({"schema_version": FX_SCHEMA_VERSION + 1, "fx": [_fx()]})

    def test_a_non_mapping_library_is_rejected(self):
        with pytest.raises(FxSchemaError, match="mapping"):
            load_library([_fx()])

    def test_an_empty_fx_list_is_rejected(self):
        with pytest.raises(FxSchemaError, match="non-empty list"):
            load_library({"schema_version": FX_SCHEMA_VERSION, "fx": []})


class TestLoaderRejectsOutOfRangeValues:
    """REQ-FXLIB-005 — numeric range violations, one test per axis."""

    def test_a_dimmer_step_value_above_full_is_rejected(self):
        with pytest.raises(FxSchemaError, match="out of range"):
            load_library(_library(_fx(pattern="pulse", steps=[{"Dimmer": 101}, {"Dimmer": 0}])))

    def test_a_negative_dimmer_step_value_is_rejected(self):
        with pytest.raises(FxSchemaError, match="out of range"):
            load_library(_library(_fx(pattern="pulse", steps=[{"Dimmer": -1}, {"Dimmer": 50}])))

    def test_dimmer_boundary_values_are_accepted(self):
        # The M0 anchor itself is 100 / 0 — a tighter bound would reject it.
        entry = _fx(pattern="pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}])
        assert load_library(_library(entry)).fx[0].steps[0].value_of("Dimmer") == 100

    def test_a_pan_step_value_outside_the_authoring_envelope_is_rejected(self):
        with pytest.raises(FxSchemaError, match="out of range"):
            load_library(_library(_fx(steps=[{"Pan": -20}, {"Pan": 2000}])))

    def test_a_non_numeric_step_value_is_rejected(self):
        # Step values are ABSOLUTE numbers. `At Relative <n>` as a step value is
        # unmeasured (ASSUMPTION-40) and v1 never emits it.
        with pytest.raises(FxSchemaError, match="absolute number"):
            load_library(_library(_fx(steps=[{"Pan": "Relative 30"}, {"Pan": 20}])))

    def test_a_boolean_step_value_is_rejected(self):
        # bool is an int subclass in Python — the check must exclude it.
        with pytest.raises(FxSchemaError, match="absolute number"):
            load_library(_library(_fx(steps=[{"Pan": True}, {"Pan": 20}])))

    def test_a_phase_beyond_a_full_turn_is_rejected(self):
        with pytest.raises(FxSchemaError, match="out of range"):
            load_library(_library(_fx(phase_to=720)))

    def test_the_reverse_phase_literal_is_accepted(self):
        # `Attribute 'Pan' At Phase 0 Thru -360` (31_choreography_patterns.md:80).
        fx = load_library(_library(_fx(phase_to=-360, reverse=True))).fx[0]
        assert fx.phase_to == -360

    def test_a_zero_speed_is_rejected(self):
        with pytest.raises(FxSchemaError, match="positive BPM"):
            load_library(_library(_fx(speed=0)))

    def test_a_negative_speed_is_rejected(self):
        with pytest.raises(FxSchemaError, match="positive BPM"):
            load_library(_library(_fx(speed=-60)))

    def test_a_non_boolean_reverse_is_rejected(self):
        with pytest.raises(FxSchemaError, match="reverse must be true or false"):
            load_library(_library(_fx(reverse="yes")))

    def test_a_zero_matricks_block_size_is_rejected(self):
        # `Set Selection MAtricks 'X' 2` acts on every 2nd fixture; 0 is not a
        # division count.
        with pytest.raises(FxSchemaError, match=r"x must be >= 1"):
            load_library(_library(_fx(x=0)))

    def test_a_fractional_matricks_block_size_is_rejected(self):
        with pytest.raises(FxSchemaError, match=r"x must be an integer"):
            load_library(_library(_fx(x=1.5)))

    def test_a_zero_wing_count_is_rejected(self):
        with pytest.raises(FxSchemaError, match=r"x_wings must be >= 1"):
            load_library(_library(_fx(x_wings=0)))

    def test_a_negative_shuffle_seed_is_rejected(self):
        with pytest.raises(FxSchemaError, match=r"x_shuffle must be >= 0"):
            load_library(_library(_fx(x_shuffle=-1)))

    def test_a_large_shuffle_seed_is_accepted(self):
        # `XShuffle 1234` is a SEED, not a count — it carries no upper bound.
        fx = load_library(_library(_fx(x_shuffle=987654))).fx[0]
        assert fx.x_shuffle == 987654

    def test_a_non_numeric_relative_amplitude_is_rejected(self):
        with pytest.raises(FxSchemaError, match="relative must be a number"):
            load_library(_library(_fx(relative="wide")))


class TestOptionalAxesAndMalformedShapes:
    """REQ-FXLIB-005 — the remaining explicit-error and omission paths."""

    def test_an_omitted_optional_axis_loads_as_unset(self):
        entry = _fx()
        for key in ("phase_from", "phase_to", "speed", "aliases", "mood_keywords"):
            del entry[key]
        fx = load_library(_library(entry)).fx[0]
        assert (fx.phase_from, fx.phase_to, fx.speed) == (None, None, None)
        assert (fx.aliases, fx.mood_keywords) == ((), ())

    def test_an_explicitly_null_optional_axis_loads_as_unset(self):
        entry = _fx(aliases=None, mood_keywords=None, speed=None, reverse=None)
        fx = load_library(_library(entry)).fx[0]
        assert (fx.aliases, fx.mood_keywords, fx.speed) == ((), (), None)
        assert fx.reverse is False

    def test_a_scalar_alias_list_is_rejected(self):
        # A bare string is iterable, so accepting it would silently split the
        # word into one alias per character.
        with pytest.raises(FxSchemaError, match="aliases must be a list"):
            load_library(_library(_fx(aliases="스윕")))

    def test_a_non_string_alias_entry_is_rejected(self):
        with pytest.raises(FxSchemaError, match="aliases entry"):
            load_library(_library(_fx(aliases=[12])))

    def test_an_fx_entry_that_is_not_a_mapping_is_rejected(self):
        with pytest.raises(FxSchemaError, match="each fx must be a mapping"):
            load_library({"schema_version": FX_SCHEMA_VERSION, "fx": ["pan-sweep-wide"]})

    def test_asking_a_step_for_an_attribute_it_does_not_set_raises(self):
        fx = load_library(_library()).fx[0]
        with pytest.raises(KeyError):
            fx.steps[0].value_of("Tilt")


class TestAccelDecelAreDefinedButGated:
    """REQ-FXLIB-001 gate clause — M0 returned `ok:true` with no observed effect.

    The LOOKLIB `MovementSpec` shape ("v1 defines this field but does not emit
    it", server/looks/schema.py:86-102) applies to this axis only, with one
    tightening the SPEC asks for: the loader also REFUSES a value, so the
    unmeasured vocabulary cannot enter the library by accident.
    """

    def test_the_curve_axes_are_declared_on_the_schema(self):
        assert GATED_CURVE_AXES == ("accel", "decel")
        assert {"accel", "decel"} <= set(Fx.__dataclass_fields__)

    def test_the_dataclass_can_still_carry_a_curve_value(self):
        # Definition present: the DESCOPE shape is "defined, unused", NOT
        # "deleted". A later probe that turns the gate GO must find the field.
        fx = Fx(fx_id="x", display_name="x", pattern="pulse", steps=(), accel=-100, decel=-100)
        assert (fx.accel, fx.decel) == (-100, -100)

    def test_the_loader_rejects_an_accel_value(self):
        with pytest.raises(FxSchemaError, match="accel curve is probe-pending"):
            load_library(_library(_fx(accel=-100)))

    def test_the_loader_rejects_a_decel_value(self):
        with pytest.raises(FxSchemaError, match="decel curve is probe-pending"):
            load_library(_library(_fx(decel=-100)))

    def test_a_curve_free_entry_round_trips_with_the_axes_unset(self):
        original = load_library(_library()).fx[0]
        reparsed = load_library(_library(fx_to_dict(original))).fx[0]
        assert reparsed == original
        assert (reparsed.accel, reparsed.decel) == (None, None)


class TestSerialisationRoundTrip:
    """AC-FXLIB-001 — `load(fx_to_dict(fx))` is the same fx."""

    def test_a_minimal_entry_round_trips_without_loss(self):
        original = load_library(_library()).fx[0]
        assert load_library(_library(fx_to_dict(original))).fx[0] == original

    def test_a_multi_attribute_multi_step_entry_round_trips_without_loss(self):
        steps = [{"Pan": -20, "Tilt": -10}, {"Pan": 0, "Tilt": 0}, {"Pan": 20, "Tilt": 10}]
        entry = _fx(fx_id="circle-wings", pattern="circle", steps=steps, x_wings=2)
        original = load_library(_library(entry)).fx[0]
        reparsed = load_library(_library(fx_to_dict(original))).fx[0]
        assert reparsed == original
        assert reparsed.attributes == ("Pan", "Tilt")

    def test_reverse_survives_the_round_trip(self):
        original = load_library(_library(_fx(reverse=True, phase_to=-360))).fx[0]
        assert load_library(_library(fx_to_dict(original))).fx[0].reverse is True

    def test_the_serialised_step_form_is_the_wire_mapping_form(self):
        original = load_library(_library()).fx[0]
        assert fx_to_dict(original)["steps"] == [{"Pan": -20}, {"Pan": 20}]


class TestNoPerShowBindingFieldsExist:
    """REQ-FXLIB-004 — the schema simply has no place to put a rig binding."""

    def test_the_fx_dataclass_has_no_rig_binding_field(self):
        forbidden = ("group", "sequence", "cue", "fid", "executor", "slot", "preset")
        for token in forbidden:
            assert not any(token in name for name in Fx.__dataclass_fields__), token

    def test_the_step_value_dataclass_has_no_rig_binding_field(self):
        assert tuple(StepValue.__dataclass_fields__) == ("attribute", "value")

    def test_the_modifier_axis_list_holds_no_rig_binding(self):
        for axis in PHASER_MODIFIER_AXES + MATRICKS_AXES:
            assert "group" not in axis and "executor" not in axis


class TestYamlDirectoryLoading:
    """Storage mirrors the looks library: YAML repo assets, merged by directory."""

    @staticmethod
    def _write(directory, stem: str, *entries: dict) -> None:
        (directory / f"{stem}.yaml").write_text(
            yaml.safe_dump(_library(*entries), allow_unicode=True), encoding="utf-8"
        )

    def test_entries_merge_across_files_in_the_directory(self, tmp_path):
        self._write(tmp_path, "position", _fx())
        self._write(
            tmp_path,
            "intensity",
            _fx(fx_id="dimmer-pulse", pattern="pulse", steps=[{"Dimmer": 100}, {"Dimmer": 0}]),
        )
        library = load_library_from_dir(tmp_path)
        assert {fx.fx_id for fx in library.fx} == {"pan-sweep-wide", "dimmer-pulse"}

    def test_korean_content_survives_a_yaml_round_trip(self, tmp_path):
        self._write(tmp_path, "position", _fx())
        fx = load_library_from_dir(tmp_path).fx[0]
        assert fx.display_name == "좌우 스윕"
        assert fx.mood_keywords == ("부드러운", "넓게")

    def test_an_fx_id_duplicated_across_files_is_rejected(self, tmp_path):
        # The cross-file collision is the one a per-file loader would never see.
        self._write(tmp_path, "position", _fx())
        self._write(tmp_path, "intensity", _fx())
        with pytest.raises(FxSchemaError, match="duplicate"):
            load_library_from_dir(tmp_path)

    def test_a_step_axis_violation_inside_a_file_names_that_file(self, tmp_path):
        self._write(tmp_path, "position", _fx(steps=[{"Pan": 20}]))
        with pytest.raises(FxSchemaError, match="position.yaml"):
            load_library_from_dir(tmp_path)

    def test_a_missing_directory_is_reported_explicitly(self, tmp_path):
        with pytest.raises(FxSchemaError, match="not found"):
            load_library_from_dir(tmp_path / "nope")

    def test_a_directory_with_no_assets_is_reported_explicitly(self, tmp_path):
        # An empty library must not load as a valid empty one — that is the
        # "silently serving a broken library" failure REQ-FXLIB-005 exists to stop.
        with pytest.raises(FxSchemaError, match="no fx assets"):
            load_library_from_dir(tmp_path)

    def test_malformed_yaml_names_the_offending_file(self, tmp_path):
        (tmp_path / "position.yaml").write_text("fx: [{unclosed", encoding="utf-8")
        with pytest.raises(FxSchemaError, match="position.yaml"):
            load_library_from_dir(tmp_path)
