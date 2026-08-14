"""Tests for server/design/rig.py (SPEC-COPILOT-SONGSTD-001, M1, R1b).

Scenarios per spec.md R1b §S: single-layer rigs never fire layer-conditioned
rules (RG1) but say so explicitly; a declared layer mapping activates those
rules; capable-fixture-count changes the RG6 budget factor; group-name
mapping (RG5) is deterministic and conservative — it never guesses.
"""

from __future__ import annotations

import pytest

from server.design.rig import (
    RIG_LAYER_ROLES,
    RIG_LAYER_SOURCE_DECLARED,
    RIG_LAYER_SOURCE_GROUP_HEURISTIC,
    RIG_LAYER_SOURCE_SINGLE_LAYER,
    RigProfileError,
    build_rig_profile,
    rig_fixture_record_from_record,
)
from server.spatial.schema import spatial_fixtures_from_records
from server.spatial.topology import classify


def _patch(*, count: int, capability: str | None = None) -> list[dict[str, object]]:
    """``count`` fixtures of one type; ``capability`` declared on all of them
    when given (never inferred — this helper mirrors how a real caller would
    declare capabilities explicitly)."""
    return [
        {
            "fid": fid,
            "type_name": "Sharpy",
            "capabilities": [capability] if capability else [],
        }
        for fid in range(1, count + 1)
    ]


def _coords(points: list[tuple[int, float, float, float]]) -> list[dict[str, object]]:
    return [{"fid": fid, "name": f"Fx{fid}", "x": x, "y": y, "z": z} for fid, x, y, z in points]


# ---------------------------------------------------------------------------
# Inventory (RG2/RG6)
# ---------------------------------------------------------------------------


def test_empty_patch_yields_empty_inventory() -> None:
    profile = build_rig_profile(patch=[], groups={}, coords=[])
    assert profile.inventory.fixture_count == 0
    assert profile.inventory.type_counts == {}
    assert profile.has_capability("strobe") is False
    assert profile.capable_fixture_count("strobe") == 0


def test_capability_is_declared_never_inferred_from_type_name() -> None:
    patch = _patch(count=2)  # type_name "Sharpy", no capability declared
    profile = build_rig_profile(patch=patch, groups={}, coords=[])
    # A real Sharpy has a strobe shutter, but nothing here DECLARED it —
    # RG2 must not guess from the type name.
    assert profile.has_capability("strobe") is False
    assert profile.inventory.type_counts == {"Sharpy": 2}


def test_rig_fixture_record_rejects_non_string_capability() -> None:
    with pytest.raises(RigProfileError):
        rig_fixture_record_from_record({"fid": 1, "type_name": "X", "capabilities": [1]})


def test_rig_fixture_record_rejects_missing_fid() -> None:
    with pytest.raises(RigProfileError):
        rig_fixture_record_from_record({"type_name": "X"})


# ---------------------------------------------------------------------------
# RG6 — budget scales with capable fixture count
# ---------------------------------------------------------------------------


def test_four_vs_forty_capable_fixtures_changes_budget_factor() -> None:
    small = build_rig_profile(patch=_patch(count=4, capability="blinder"), groups={}, coords=[])
    large = build_rig_profile(patch=_patch(count=40, capability="blinder"), groups={}, coords=[])

    small_factor = small.budget_scale_factor("blinder")
    large_factor = large.budget_scale_factor("blinder")

    assert small.capable_fixture_count("blinder") == 4
    assert large.capable_fixture_count("blinder") == 40
    assert small_factor < large_factor
    assert large_factor == 1.0  # saturates — RG6_FULL_BUDGET_FIXTURE_COUNT default is 8


def test_budget_factor_is_zero_when_rig_has_no_capable_fixtures() -> None:
    profile = build_rig_profile(patch=_patch(count=10), groups={}, coords=[])
    assert profile.budget_scale_factor("blinder") == 0.0


def test_budget_factor_rejects_nonpositive_threshold() -> None:
    profile = build_rig_profile(patch=_patch(count=4, capability="blinder"), groups={}, coords=[])
    with pytest.raises(RigProfileError):
        profile.budget_scale_factor("blinder", full_scale_at=0)


# ---------------------------------------------------------------------------
# RG1/RG5 — layer source priority: declared > group-name heuristic > single
# ---------------------------------------------------------------------------


def test_single_layer_degradation_deactivates_layer_rules_with_explicit_note() -> None:
    profile = build_rig_profile(patch=_patch(count=40), groups={}, coords=[])

    assert profile.layers.source == RIG_LAYER_SOURCE_SINGLE_LAYER
    assert profile.layer_rules_active() is False
    assert profile.has_layer("key") is False
    assert profile.has_layer("back") is False
    assert len(profile.notes) == 1
    assert "RG1" in profile.notes[0]
    assert "L6" in profile.notes[0] and "L7" in profile.notes[0]


def test_unrelated_group_names_do_not_map_and_still_degrade() -> None:
    """RG5 conservative: a group name outside the closed alias set must not
    be guessed into a role."""
    groups = {"Truss 1": [1, 2, 3], "Random Batten": [4, 5]}
    profile = build_rig_profile(patch=_patch(count=5), groups=groups, coords=[])

    assert profile.layers.source == RIG_LAYER_SOURCE_SINGLE_LAYER
    assert profile.layer_rules_active() is False


def test_group_name_heuristic_maps_recognised_role_aliases() -> None:
    groups = {"Front": [1, 2], "Back": [3, 4], "FX": [5]}
    profile = build_rig_profile(patch=_patch(count=5), groups=groups, coords=[])

    assert profile.layers.source == RIG_LAYER_SOURCE_GROUP_HEURISTIC
    assert profile.layer_rules_active() is True
    assert profile.has_layer("key") is True  # "Front" is a key alias
    assert profile.layers.fids_for("key") == (1, 2)
    assert profile.layers.fids_for("back") == (3, 4)
    assert profile.layers.fids_for("effect") == (5,)
    assert profile.has_layer("audience") is False
    assert profile.notes == ()


def test_group_name_heuristic_matches_case_insensitively_and_strips_whitespace() -> None:
    groups = {"  KEY  ": [7]}
    profile = build_rig_profile(patch=_patch(count=1), groups=groups, coords=[])
    assert profile.layers.fids_for("key") == (7,)


def test_group_name_heuristic_does_not_substring_match() -> None:
    """ "Front of House" must not spuriously hit both "key" (via "front")
    and "audience" (via "house") — RG5 requires an EXACT alias match."""
    groups = {"Front of House": [1, 2]}
    profile = build_rig_profile(patch=_patch(count=2), groups=groups, coords=[])
    assert profile.layers.source == RIG_LAYER_SOURCE_SINGLE_LAYER


def test_group_name_heuristic_is_deterministic() -> None:
    groups_a = {"Front": [1, 2], "Back": [3, 4]}
    groups_b = {"Back": [4, 3], "Front": [2, 1]}  # same content, different order
    profile_a = build_rig_profile(patch=_patch(count=4), groups=groups_a, coords=[])
    profile_b = build_rig_profile(patch=_patch(count=4), groups=groups_b, coords=[])
    assert profile_a.layers.mapping == profile_b.layers.mapping


def test_declared_layers_activate_layer_rules() -> None:
    declared = {"key": [1, 2], "back": [3, 4]}
    # A group-name heuristic hit is present too, but declaration outranks it.
    groups = {"FX": [5, 6]}
    profile = build_rig_profile(
        patch=_patch(count=6), groups=groups, coords=[], declared_layers=declared
    )

    assert profile.layers.source == RIG_LAYER_SOURCE_DECLARED
    assert profile.layer_rules_active() is True
    assert profile.has_layer("key") is True
    assert profile.has_layer("back") is True
    assert profile.has_layer("effect") is False  # the heuristic hit was overridden
    assert profile.notes == ()


def test_declared_layers_reject_unknown_role() -> None:
    with pytest.raises(RigProfileError):
        build_rig_profile(
            patch=_patch(count=1), groups={}, coords=[], declared_layers={"weird": [1]}
        )


def test_declared_layers_role_vocabulary_is_the_standard_four() -> None:
    assert RIG_LAYER_ROLES == ("key", "back", "effect", "audience")


def test_empty_declared_layers_falls_through_to_heuristic() -> None:
    """An explicitly empty declaration is not a declaration (RG5: a
    role declared with zero fids carries no signal)."""
    groups = {"Back": [3, 4]}
    profile = build_rig_profile(
        patch=_patch(count=4), groups=groups, coords=[], declared_layers={"key": []}
    )
    assert profile.layers.source == RIG_LAYER_SOURCE_GROUP_HEURISTIC


# ---------------------------------------------------------------------------
# Geometry — centroid + dominant axis + arrangement (reuses topology.classify)
# ---------------------------------------------------------------------------


def test_geometry_is_low_confidence_when_no_coordinates_given() -> None:
    profile = build_rig_profile(patch=[], groups={}, coords=[])
    assert profile.geometry.arrangement is None
    assert profile.geometry.arrangement_low_confidence is True
    assert profile.geometry.centroid is None
    assert profile.geometry.dominant_axis is None


def test_geometry_centroid_and_dominant_axis_along_x() -> None:
    points = [(1, 0.0, 0.0, 0.0), (2, 1.0, 0.0, 0.0), (3, 2.0, 0.0, 0.0), (4, 3.0, 0.0, 0.0)]
    profile = build_rig_profile(patch=[], groups={}, coords=_coords(points))
    assert profile.geometry.centroid == (1.5, 0.0, 0.0)
    assert profile.geometry.dominant_axis == "x"


def test_geometry_dominant_axis_along_y() -> None:
    points = [(1, 0.0, 0.0, 0.0), (2, 0.0, 2.0, 0.0), (3, 0.0, 4.0, 0.0)]
    profile = build_rig_profile(patch=[], groups={}, coords=_coords(points))
    assert profile.geometry.dominant_axis == "y"


def test_geometry_dominant_axis_ties_break_toward_x() -> None:
    points = [(1, 0.0, 0.0, 0.0), (2, 2.0, 2.0, 0.0)]  # x span == y span == 2.0
    profile = build_rig_profile(patch=[], groups={}, coords=_coords(points))
    assert profile.geometry.dominant_axis == "x"


def test_geometry_arrangement_matches_topology_classify_directly() -> None:
    """Boundary check: rig.py must not reimplement or diverge from the
    existing arrangement classifier — it proxies the same verdict."""
    points = [(fid, float(fid), 0.0, 0.0) for fid in range(1, 11)]
    coords = _coords(points)
    profile = build_rig_profile(patch=[], groups={}, coords=coords)

    expected = classify(spatial_fixtures_from_records(coords)).selected
    assert profile.geometry.arrangement == expected.kind
    assert profile.geometry.arrangement_low_confidence == expected.low_confidence


# ---------------------------------------------------------------------------
# Scale (RG4)
# ---------------------------------------------------------------------------


def test_scale_defaults_to_undeclared_unit_factor() -> None:
    profile = build_rig_profile(patch=[], groups={}, coords=[])
    assert profile.scale.declared is False
    assert profile.scale.factor == 1.0


def test_scale_factor_is_declared_when_given() -> None:
    profile = build_rig_profile(patch=[], groups={}, coords=[], scale_factor=2.5)
    assert profile.scale.declared is True
    assert profile.scale.factor == 2.5


def test_scale_factor_rejects_nonpositive_values() -> None:
    with pytest.raises(RigProfileError):
        build_rig_profile(patch=[], groups={}, coords=[], scale_factor=0.0)
    with pytest.raises(RigProfileError):
        build_rig_profile(patch=[], groups={}, coords=[], scale_factor=-1.0)
