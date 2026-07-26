"""Look schema + role vocabulary + loader tests (M1 — AC-LOOKLIB-001 / AC-LOOKLIB-015).

Covers REQ-LOOKLIB-001 (schema axes + family-partitionable payload),
REQ-LOOKLIB-003 (the three attribute vocabulary bands + pool-family attribution),
REQ-LOOKLIB-005 (explicit loader errors) and REQ-LOOKLIB-006/009 (the closed
6-term role vocabulary + its matching discipline).

Every failure mode is a SEPARATE test on purpose (design.md §6.2 — merging them
hides which rejection actually fired). Everything is in-memory: no console, no
OSC, no filesystem except the one tmp_path case that exercises the YAML wrapper.
"""

from __future__ import annotations

import pytest
import yaml

from server.looks.loader import LookSchemaError, load_library, load_library_from_dir
from server.looks.roles import (
    AMBIGUOUS,
    NO_MATCH,
    ROLE_NAMES,
    ROLES,
    match_role_by_name,
    role_by_name,
)
from server.looks.schema import (
    CONFIRMED_ATTRIBUTES,
    DYNAMICS_MAX,
    DYNAMICS_MIN,
    IN_SCOPE_POOL_FAMILIES,
    MOVEMENT_ONLY_ATTRIBUTES,
    PROBE_GATED_ATTRIBUTES,
    SCHEMA_VERSION,
    AttributeValue,
    MovementSpec,
    look_to_dict,
    payload_for_family,
    pool_family,
)

# The closed 6-term set, verbatim from spec.md §A (사용자 확정 ⑨ / 결정 J).
EXPECTED_ROLES = ("백라이트", "프론트", "사이드", "탑", "배경", "스페셜")

# AC-LOOKLIB-015 ④ — fixture TYPE-class vocabulary, deliberately excluded from
# every hint set (20_korean_terms.md:12,14,15 — these are not position roles).
EXCLUDED_TYPE_CLASS_TERMS = ("워시", "Wash", "스팟", "Spot", "빔", "Beam")


def _look(**overrides) -> dict:
    """A minimal valid look dict; overrides replace individual keys."""
    look = {
        "look_id": "worship-gold-swell",
        "display_name": "금빛 고조",
        "genre": "worship",
        "dynamics": 4,
        "roles": ["백라이트", "배경"],
        "aliases": ["골드 스웰"],
        "mood_keywords": ["웅장한", "금색"],
        "attributes": {"Dimmer": 80, "ColorRGB_R": 100, "ColorRGB_G": 70},
    }
    look.update(overrides)
    return look


def _library(*looks: dict) -> dict:
    return {"schema_version": SCHEMA_VERSION, "looks": list(looks or (_look(),))}


class TestRoleVocabularyIsClosed:
    """AC-LOOKLIB-015 ① ② ④ — the set, the per-role payload, the exclusion."""

    def test_the_set_is_exactly_the_six_confirmed_roles(self):
        assert tuple(role.name for role in ROLES) == EXPECTED_ROLES
        assert frozenset(EXPECTED_ROLES) == ROLE_NAMES

    def test_every_role_carries_an_english_alias_and_a_mapping_hint(self):
        # AC ② — "한 역할이라도 힌트가 비면 실패". v0.2.0 shipped hints for
        # 백라이트 only; this assert is what mechanically forbids that state.
        for role in ROLES:
            assert role.aliases, f"{role.name} has no English alias"
            assert role.hints, f"{role.name} has no mapping hint"

    def test_no_hint_uses_fixture_type_class_vocabulary(self):
        # AC ④ — D3's lesson in mechanical form. One Wash fixture may be a
        # backlight OR a front, so a type-class hint mis-aims systematically.
        offenders = [
            (role.name, hint, term)
            for role in ROLES
            for hint in role.hints
            for term in EXCLUDED_TYPE_CLASS_TERMS
            if term.lower() in hint.lower()
        ]
        assert offenders == []

    def test_abbreviation_hints_are_declared_as_hints(self):
        for role in ROLES:
            assert set(role.abbreviations) <= set(role.hints), role.name

    def test_role_lookup_rejects_a_name_outside_the_set(self):
        assert role_by_name("백라이트").aliases
        with pytest.raises(KeyError):
            role_by_name("무대감독")


class TestRoleNameMatching:
    """AC-LOOKLIB-015 ⑤ + the M0-measured showfile (progress.md §E.2 measurement 3)."""

    def test_measured_showfile_group_back_maps_to_backlight(self):
        assert match_role_by_name("Back").role == "백라이트"

    def test_measured_showfile_group_front_maps_to_front(self):
        assert match_role_by_name("Front").role == "프론트"

    def test_measured_showfile_group_all_matches_no_role(self):
        # M0 recorded `All` as hitting zero roles. Pinning it keeps a future
        # hint extension from quietly claiming a catch-all group name.
        #
        # NOTE: this case does NOT discriminate boundary matching from naive
        # substring matching — no hint is a substring of "all" either, so a
        # substring matcher also returns no match here. progress.md §E.2
        # measurement 3 attributes the pass to token-boundary discipline via a
        # supposed `All`/`BL` collision; that collision does not exist. The
        # cases that actually discriminate are `백색`, `Keys`, `Slash Bar` and
        # `Backdrop` below.
        match = match_role_by_name("All")
        assert match.role is None
        assert match.reason == NO_MATCH

    def test_measured_showfile_group_copilot_grp_matches_no_role(self):
        assert match_role_by_name("Copilot Grp").reason == NO_MATCH

    def test_korean_hint_does_not_match_inside_a_longer_word(self):
        # `백색` (white) must not be claimed by the `백` hint — this is the
        # case a substring matcher actually gets wrong.
        assert match_role_by_name("백색").reason == NO_MATCH

    def test_korean_hint_matches_as_a_standalone_token(self):
        assert match_role_by_name("백 트러스").role == "백라이트"

    def test_abbreviation_hint_requires_an_exact_token(self):
        # `Spc` must not be found inside `Spotlight`; `SL` not inside `Slash`.
        assert match_role_by_name("Spotlight").reason == NO_MATCH
        assert match_role_by_name("Slash Bar").reason == NO_MATCH

    def test_abbreviation_hint_matches_when_it_is_its_own_token(self):
        assert match_role_by_name("SR Wash").role == "사이드"

    def test_underscore_separates_tokens(self):
        # Python's `\b` treats `_` as a word character, so a `\b`-based matcher
        # silently misses `BL_Truss` — the same trap that hid `open_keychain`
        # from an earlier static scan. This pins the explicit word class.
        assert match_role_by_name("BL_Truss").role == "백라이트"
        assert match_role_by_name("Back_Wash").role == "백라이트"

    def test_plural_key_is_not_the_special_hint(self):
        # spec.md §A known-collision (a): `Keys` is the band's keyboard group.
        assert match_role_by_name("Keys").reason == NO_MATCH
        assert match_role_by_name("Key").role == "스페셜"

    def test_longer_hint_wins_over_its_prefix_within_one_role(self):
        # `Backdrop` belongs to 배경, not to 백라이트 via the `Back` prefix.
        assert match_role_by_name("Backdrop").role == "배경"

    def test_a_name_hitting_two_roles_is_reported_ambiguous_not_assigned(self):
        # spec.md §A known-collision (c) — `FrontBack Truss` is intended to
        # fall out as ambiguous rather than be arbitrarily assigned.
        match = match_role_by_name("FrontBack Truss")
        assert match.role is None
        assert match.reason == AMBIGUOUS
        assert set(match.candidates) == {"프론트", "백라이트"}

    def test_matching_is_case_insensitive(self):
        assert match_role_by_name("foh wash").role == "프론트"


class TestAttributeVocabularyBands:
    """REQ-LOOKLIB-003 — the three bands and their pool-family attribution."""

    def test_band_one_is_the_repository_measured_vocabulary(self):
        assert CONFIRMED_ATTRIBUTES == ("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

    def test_band_two_is_the_movement_only_vocabulary(self):
        assert MOVEMENT_ONLY_ATTRIBUTES == ("Pan", "Tilt")

    def test_band_three_is_the_m0_resolved_beam_vocabulary(self):
        # M0 accepted `Zoom` and `Iris`; Focus/Frost/Prism1/Shutter were rejected.
        assert PROBE_GATED_ATTRIBUTES == ("Zoom", "Iris")

    def test_pool_families_are_the_four_in_scope_pools(self):
        assert IN_SCOPE_POOL_FAMILIES == ("Dimmer", "Color", "Beam", "Focus")

    def test_each_confirmed_attribute_is_attributable_to_exactly_one_family(self):
        assert pool_family("Dimmer") == "Dimmer"
        assert pool_family("ColorRGB_R") == "Color"
        assert pool_family("ColorRGB_G") == "Color"
        assert pool_family("ColorRGB_B") == "Color"

    def test_m0_beam_strings_route_by_the_object_model_family_boundary(self):
        # 10_object_model.md:39 — Beam = iris/prism/frost, Focus = zoom/focus.
        assert pool_family("Iris") == "Beam"
        assert pool_family("Zoom") == "Focus"

    def test_movement_only_attributes_belong_to_no_pool(self):
        # Position pool is out of scope, so Pan/Tilt have nowhere to be stored.
        assert pool_family("Pan") is None
        assert pool_family("Tilt") is None


class TestLoaderAcceptsAValidLibrary:
    """AC-LOOKLIB-001 happy path."""

    def test_a_minimal_library_loads(self):
        library = load_library(_library())
        assert library.schema_version == SCHEMA_VERSION
        assert len(library.looks) == 1

    def test_the_loaded_look_exposes_every_schema_axis(self):
        look = load_library(_library()).looks[0]
        assert look.look_id == "worship-gold-swell"
        assert look.display_name == "금빛 고조"
        assert look.genre == "worship"
        assert look.dynamics == 4
        assert look.roles == ("백라이트", "배경")
        assert look.aliases == ("골드 스웰",)
        assert look.mood_keywords == ("웅장한", "금색")
        assert look.attributes[0] == AttributeValue(name="Dimmer", value=80)
        assert look.movement == ()

    def test_korean_mood_keywords_survive_verbatim(self):
        # REQ-LOOKLIB-018 — Korean is first-class, never folded to ASCII.
        look = load_library(_library(_look(mood_keywords=["잔잔한", "새벽"]))).looks[0]
        assert look.mood_keywords == ("잔잔한", "새벽")

    def test_dynamics_boundary_values_are_accepted(self):
        for level in (DYNAMICS_MIN, DYNAMICS_MAX):
            library = load_library(_library(_look(dynamics=level)))
            assert library.looks[0].dynamics == level

    def test_lookup_by_id_finds_a_loaded_look(self):
        library = load_library(_library(_look(), _look(look_id="rock-drop")))
        assert library.by_id("rock-drop").look_id == "rock-drop"


class TestLoaderRejectsSchemaViolations:
    """AC-LOOKLIB-001 / REQ-LOOKLIB-005 — each violation is its own test."""

    def test_dynamics_below_the_range_is_rejected(self):
        with pytest.raises(LookSchemaError, match="dynamics"):
            load_library(_library(_look(dynamics=0)))

    def test_dynamics_above_the_range_is_rejected(self):
        with pytest.raises(LookSchemaError, match="dynamics"):
            load_library(_library(_look(dynamics=6)))

    def test_non_integer_dynamics_is_rejected(self):
        with pytest.raises(LookSchemaError, match="dynamics"):
            load_library(_library(_look(dynamics=3.5)))

    def test_boolean_dynamics_is_rejected(self):
        # bool is an int subclass in Python — the check must exclude it.
        with pytest.raises(LookSchemaError, match="dynamics"):
            load_library(_library(_look(dynamics=True)))

    def test_a_role_outside_the_closed_set_is_rejected(self):
        with pytest.raises(LookSchemaError, match="role"):
            load_library(_library(_look(roles=["백라이트", "무대감독"])))

    def test_an_unknown_attribute_name_is_rejected(self):
        with pytest.raises(LookSchemaError, match="attribute"):
            load_library(_library(_look(attributes={"Gobo1": 3})))

    def test_a_strobe_attribute_is_rejected(self):
        # spec.md §D Out of Scope — strobe/shutter never enter v1 looks.
        with pytest.raises(LookSchemaError, match="attribute"):
            load_library(_library(_look(attributes={"Shutter": 50})))

    def test_a_probe_rejected_beam_string_is_not_in_the_vocabulary(self):
        # M0 rejected `Frost`; only the accepted strings entered band 3.
        with pytest.raises(LookSchemaError, match="attribute"):
            load_library(_library(_look(attributes={"Frost": 20})))

    def test_a_non_family_attributable_attribute_is_rejected_in_the_payload(self):
        # `Pan` is a KNOWN attribute but belongs to no in-scope pool, so it
        # cannot live in the static payload — only inside a movement spec.
        with pytest.raises(LookSchemaError, match="pool family"):
            load_library(_library(_look(attributes={"Dimmer": 50, "Pan": 20})))

    def test_a_duplicate_look_id_is_rejected(self):
        with pytest.raises(LookSchemaError, match="duplicate"):
            load_library(_library(_look(), _look()))

    def test_an_unknown_top_level_look_field_is_rejected(self):
        # Closed schema — this is what keeps per-show bindings (REQ-LOOKLIB-004)
        # from being smuggled in as an extra key.
        with pytest.raises(LookSchemaError, match="unknown"):
            load_library(_library(_look(group_number=11)))

    def test_an_unknown_library_level_key_is_rejected(self):
        with pytest.raises(LookSchemaError, match="unknown"):
            load_library({"schema_version": SCHEMA_VERSION, "looks": [_look()], "rig": {}})

    def test_a_missing_required_field_is_rejected(self):
        broken = _look()
        del broken["genre"]
        with pytest.raises(LookSchemaError, match="genre"):
            load_library(_library(broken))

    def test_an_empty_role_list_is_rejected(self):
        with pytest.raises(LookSchemaError, match="role"):
            load_library(_library(_look(roles=[])))

    def test_an_empty_attribute_payload_is_rejected(self):
        with pytest.raises(LookSchemaError, match="attribute"):
            load_library(_library(_look(attributes={})))

    def test_a_foreign_schema_version_is_rejected(self):
        with pytest.raises(LookSchemaError, match="schema_version"):
            load_library({"schema_version": SCHEMA_VERSION + 1, "looks": [_look()]})

    def test_a_non_mapping_library_is_rejected(self):
        with pytest.raises(LookSchemaError, match="mapping"):
            load_library([_look()])

    def test_a_movement_spec_with_an_unknown_attribute_is_rejected(self):
        movement = [{"attribute": "Whoosh", "phase_from": 0, "phase_to": 360}]
        with pytest.raises(LookSchemaError, match="attribute"):
            load_library(_library(_look(movement=movement)))


class TestFamilyPartitioning:
    """REQ-LOOKLIB-001 — the ASSUMPTION-14 FALLBACK branch depends on this."""

    def test_a_family_subset_contains_only_that_family(self):
        look = load_library(_library()).looks[0]
        colors = payload_for_family(look, "Color")
        assert tuple(a.name for a in colors) == ("ColorRGB_R", "ColorRGB_G")

    def test_the_union_of_all_family_subsets_is_the_whole_payload(self):
        # Without this, a FALLBACK bundle shape would drop values silently.
        look = load_library(_library()).looks[0]
        union: list[AttributeValue] = []
        for family in IN_SCOPE_POOL_FAMILIES:
            union.extend(payload_for_family(look, family))
        assert sorted(union, key=lambda a: a.name) == sorted(look.attributes, key=lambda a: a.name)

    def test_a_family_the_look_does_not_touch_yields_an_empty_subset(self):
        look = load_library(_library()).looks[0]
        assert payload_for_family(look, "Beam") == ()

    def test_asking_for_an_out_of_scope_family_raises(self):
        look = load_library(_library()).looks[0]
        with pytest.raises(ValueError, match="Position"):
            payload_for_family(look, "Position")


class TestMovementFieldIsDefinedButUnusedInV1:
    """REQ-LOOKLIB-003 movement clause — the field survives, the library omits it.

    M2 owns the "zero movement specs in the shipped library" assert
    (AC-LOOKLIB-003 구간 6-i). M1 owns the other half: the field EXISTS and
    round-trips, so 구간 6-i cannot be satisfied by having deleted the field.
    """

    def test_a_look_carrying_a_movement_spec_is_accepted(self):
        movement = [{"attribute": "Pan", "phase_from": 0, "phase_to": 360, "speed": 60}]
        look = load_library(_library(_look(movement=movement))).looks[0]
        assert look.movement == (
            MovementSpec(attribute="Pan", phase_from=0, phase_to=360, speed=60),
        )

    def test_a_movement_bearing_look_round_trips_without_loss(self):
        movement = [
            {"attribute": "Pan", "phase_from": 0, "phase_to": 360, "speed": 60},
            {"attribute": "Tilt", "phase_from": 90, "relative": 30},
        ]
        original = load_library(_library(_look(movement=movement))).looks[0]
        reparsed = load_library(_library(look_to_dict(original))).looks[0]
        assert reparsed == original

    def test_a_movement_free_look_round_trips_without_loss(self):
        original = load_library(_library()).looks[0]
        assert load_library(_library(look_to_dict(original))).looks[0] == original


class TestYamlDirectoryLoading:
    """§A.4a decision A — YAML repo assets, one file per genre."""

    @staticmethod
    def _write(directory, stem: str, *looks: dict) -> None:
        (directory / f"{stem}.yaml").write_text(
            yaml.safe_dump(_library(*looks), allow_unicode=True), encoding="utf-8"
        )

    def test_looks_merge_across_files_in_the_directory(self, tmp_path):
        self._write(tmp_path, "worship", _look())
        self._write(tmp_path, "rock", _look(look_id="rock-drop", genre="rock"))
        library = load_library_from_dir(tmp_path)
        assert {look.look_id for look in library.looks} == {
            "worship-gold-swell",
            "rock-drop",
        }

    def test_korean_content_survives_a_yaml_round_trip(self, tmp_path):
        self._write(tmp_path, "worship", _look())
        look = load_library_from_dir(tmp_path).looks[0]
        assert look.display_name == "금빛 고조"
        assert look.roles == ("백라이트", "배경")

    def test_a_look_id_duplicated_across_files_is_rejected(self, tmp_path):
        # The cross-file collision is the one a per-file loader would never see.
        self._write(tmp_path, "worship", _look())
        self._write(tmp_path, "rock", _look())
        with pytest.raises(LookSchemaError, match="duplicate"):
            load_library_from_dir(tmp_path)

    def test_a_missing_directory_is_reported_explicitly(self, tmp_path):
        with pytest.raises(LookSchemaError, match="not found"):
            load_library_from_dir(tmp_path / "nope")

    def test_a_directory_with_no_assets_is_reported_explicitly(self, tmp_path):
        # An empty library must not load as a valid empty one — that is the
        # "silently serving a broken library" failure REQ-005 exists to stop.
        with pytest.raises(LookSchemaError, match="no look assets"):
            load_library_from_dir(tmp_path)

    def test_malformed_yaml_names_the_offending_file(self, tmp_path):
        (tmp_path / "rock.yaml").write_text("looks: [{unclosed", encoding="utf-8")
        with pytest.raises(LookSchemaError, match="rock.yaml"):
            load_library_from_dir(tmp_path)

    def test_an_empty_looks_list_is_rejected(self):
        with pytest.raises(LookSchemaError, match="looks"):
            load_library({"schema_version": SCHEMA_VERSION, "looks": []})


class TestNoPerShowBindingFieldsExist:
    """REQ-LOOKLIB-004 — the schema simply has no place to put a rig binding."""

    def test_the_look_dataclass_has_no_rig_binding_field(self):
        look = load_library(_library()).looks[0]
        for forbidden in ("group", "group_number", "slot", "preset", "fid", "executor"):
            assert not any(forbidden in field for field in vars(look)), forbidden
