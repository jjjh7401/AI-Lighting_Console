"""Tests for server/spatial/fixture_type.py (TASK M1b, AC-008/009/013/014/030)."""

from __future__ import annotations

from pathlib import Path

import pytest

from server.spatial.fixture_type import (
    FixtureTypeAnalysisError,
    FixtureTypeRecord,
    analyze_fixture_type_records,
    analyze_fixture_types,
    fixture_type_analysis_to_dict,
    fixture_type_record_from_record,
    fixture_type_records_from_records,
)

MODULE_PATH = Path(__file__).resolve().parent.parent / "spatial" / "fixture_type.py"


# ---------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------


def test_parses_measured_2hop_record() -> None:
    # research.md §7.3.1 measured values — used verbatim, not re-measured.
    record = {
        "fid": 2,
        "manufacturer": "Robe",
        "type_name": "Robin MMX Spot",
        "short_name": "RMMXSm1",
    }
    fixture = fixture_type_record_from_record(record)
    assert fixture == FixtureTypeRecord(
        fid=2, manufacturer="Robe", type_name="Robin MMX Spot", short_name="RMMXSm1"
    )


def test_short_name_optional_defaults_empty() -> None:
    record = {"fid": 1, "manufacturer": "Robe", "type_name": "Robin MMX Spot"}
    fixture = fixture_type_record_from_record(record)
    assert fixture.short_name == ""


def test_missing_manufacturer_refused() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record({"fid": 1, "type_name": "Robin MMX Spot"})


def test_missing_type_name_refused() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record({"fid": 1, "manufacturer": "Robe"})


def test_empty_string_field_refused() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record({"fid": 1, "manufacturer": "", "type_name": "X"})


def test_non_string_manufacturer_refused() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record({"fid": 1, "manufacturer": 5, "type_name": "X"})


def test_non_mapping_record_refused() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_fid_must_be_int() -> None:
    with pytest.raises(FixtureTypeAnalysisError):
        fixture_type_record_from_record(
            {"fid": "2", "manufacturer": "Robe", "type_name": "Robin MMX Spot"}
        )


def test_unknown_keys_ignored() -> None:
    record = {
        "fid": 1,
        "manufacturer": "Robe",
        "type_name": "Robin MMX Spot",
        "console_object_index": 101,  # provenance field the read tool may add
    }
    fixture = fixture_type_record_from_record(record)
    assert fixture.fid == 1


# ---------------------------------------------------------------------------
# AC-030 — homogeneous rig -> explicit zero, never silent
# ---------------------------------------------------------------------------


def test_homogeneous_rig_yields_no_groups_with_explicit_reason() -> None:
    # The measured rig: 19 fixtures, one type, Patch/FixtureTypes childCount 1.
    fixtures = tuple(
        FixtureTypeRecord(fid=fid, manufacturer="Robe", type_name="Robin MMX Spot")
        for fid in range(2, 21)
    )
    analysis = analyze_fixture_types(fixtures)
    assert analysis.type_axis_groups == ()
    assert analysis.reason == "homogeneous_rig"
    assert analysis.fixture_count == 19


def test_no_fixtures_yields_explicit_reason_not_homogeneous() -> None:
    analysis = analyze_fixture_types(())
    assert analysis.type_axis_groups == ()
    assert analysis.reason == "no_fixtures"
    assert analysis.fixture_count == 0


def test_reason_is_none_exactly_when_groups_are_non_empty() -> None:
    fixtures = (
        FixtureTypeRecord(fid=1, manufacturer="Robe", type_name="Robin MMX Spot"),
        FixtureTypeRecord(fid=2, manufacturer="Chauvet", type_name="Rogue R2 Wash"),
    )
    analysis = analyze_fixture_types(fixtures)
    assert analysis.reason is None
    assert analysis.type_axis_groups != ()


# ---------------------------------------------------------------------------
# Synthetic heterogeneous golden — manufacturer / type-name axis non-vacuity
# (ASSUMPTION-67 SKIP: CONDITION_NOT_MET on the real rig, so this is
# necessarily a synthetic golden per the TASK brief, rule 4.)
# ---------------------------------------------------------------------------


def _synthetic_heterogeneous_rig() -> tuple[FixtureTypeRecord, ...]:
    return (
        FixtureTypeRecord(fid=1, manufacturer="Robe", type_name="Robin MMX Spot"),
        FixtureTypeRecord(fid=2, manufacturer="Robe", type_name="Robin MMX Spot"),
        FixtureTypeRecord(fid=3, manufacturer="Robe", type_name="Robin T1 Profile"),
        FixtureTypeRecord(fid=4, manufacturer="Chauvet", type_name="Rogue R2 Wash"),
        FixtureTypeRecord(fid=5, manufacturer="Chauvet", type_name="Rogue R2 Wash"),
    )


def test_synthetic_heterogeneous_rig_splits_by_type_name() -> None:
    analysis = analyze_fixture_types(_synthetic_heterogeneous_rig())
    type_name_groups = [g for g in analysis.type_axis_groups if g.axis == "type_name"]
    values = {g.value: g.fids for g in type_name_groups}
    assert values == {
        "Robin MMX Spot": (1, 2),
        "Robin T1 Profile": (3,),
        "Rogue R2 Wash": (4, 5),
    }


def test_synthetic_heterogeneous_rig_splits_by_manufacturer() -> None:
    analysis = analyze_fixture_types(_synthetic_heterogeneous_rig())
    manufacturer_groups = [g for g in analysis.type_axis_groups if g.axis == "manufacturer"]
    values = {g.value: g.fids for g in manufacturer_groups}
    assert values == {
        "Robe": (1, 2, 3),
        "Chauvet": (4, 5),
    }


def test_single_axis_variance_still_produces_that_axis_groups() -> None:
    # Same manufacturer throughout, but two type names: manufacturer axis
    # alone is homogeneous, yet the overall verdict must not be
    # "homogeneous_rig" and the type_name axis must still divide.
    fixtures = (
        FixtureTypeRecord(fid=1, manufacturer="Robe", type_name="Robin MMX Spot"),
        FixtureTypeRecord(fid=2, manufacturer="Robe", type_name="Robin T1 Profile"),
    )
    analysis = analyze_fixture_types(fixtures)
    assert analysis.reason is None
    axes_present = {g.axis for g in analysis.type_axis_groups}
    assert axes_present == {"type_name"}


def test_groups_carry_no_string_transformation_of_source_fields() -> None:
    # REQ-009: structured fields used as-is — no casing/whitespace/strip work.
    fixtures = (
        FixtureTypeRecord(fid=1, manufacturer=" Robe ", type_name="Robin MMX Spot"),
        FixtureTypeRecord(fid=2, manufacturer="Chauvet", type_name="robin mmx spot"),
    )
    analysis = analyze_fixture_types(fixtures)
    values = {g.value for g in analysis.type_axis_groups}
    # Both original strings pass through untouched (no strip, no casefold) —
    # proving equality is used verbatim, not derived.
    assert " Robe " in values
    assert "robin mmx spot" in values


# ---------------------------------------------------------------------------
# End-to-end record path
# ---------------------------------------------------------------------------


def test_analyze_fixture_type_records_end_to_end() -> None:
    records = [
        {"fid": 1, "manufacturer": "Robe", "type_name": "Robin MMX Spot"},
        {"fid": 2, "manufacturer": "Chauvet", "type_name": "Rogue R2 Wash"},
    ]
    analysis = analyze_fixture_type_records(records)
    assert analysis.fixture_count == 2
    assert analysis.reason is None
    assert len(analysis.type_axis_groups) > 0


def test_fixture_type_records_from_records_preserves_order() -> None:
    records = [
        {"fid": 3, "manufacturer": "Robe", "type_name": "Robin MMX Spot"},
        {"fid": 1, "manufacturer": "Robe", "type_name": "Robin MMX Spot"},
    ]
    fixtures = fixture_type_records_from_records(records)
    assert [f.fid for f in fixtures] == [3, 1]


def test_analysis_to_dict_shape() -> None:
    analysis = analyze_fixture_types(_synthetic_heterogeneous_rig())
    payload = fixture_type_analysis_to_dict(analysis)
    assert payload["fixture_count"] == 5
    assert payload["reason"] is None
    assert isinstance(payload["type_axis_groups"], list)
    first = payload["type_axis_groups"][0]
    assert set(first) == {"axis", "value", "fids"}
    assert isinstance(first["fids"], list)


def test_analysis_to_dict_homogeneous_shape() -> None:
    fixtures = (FixtureTypeRecord(fid=1, manufacturer="Robe", type_name="Robin MMX Spot"),)
    analysis = analyze_fixture_types(fixtures)
    payload = fixture_type_analysis_to_dict(analysis)
    assert payload == {
        "fixture_count": 1,
        "reason": "homogeneous_rig",
        "type_axis_groups": [],
    }


# ---------------------------------------------------------------------------
# REQ-013 — no name-axis auto-grouping path exists
# ---------------------------------------------------------------------------


def test_no_public_symbol_groups_by_free_text_name() -> None:
    """Static check: nothing in this module's public surface groups on a
    free-text fixture *name* (as opposed to the structured type_name /
    manufacturer fields). Fixture *name* is not even a field this module's
    record shape carries."""
    import server.spatial.fixture_type as module

    assert not hasattr(FixtureTypeRecord, "name")
    public = {name for name in dir(module) if not name.startswith("_")}
    assert not any("name_group" in symbol.lower() for symbol in public)
    assert not any("naming" in symbol.lower() for symbol in public)


def test_three_naming_patterns_do_not_split_a_homogeneous_type_rig() -> None:
    # Measured: 19 fixtures, one type, three distinct free-text naming
    # patterns ('RMMXSm1 1', 'Copilot MMX n', 'MMX n'). None of those names
    # are inputs to this module — only manufacturer/type_name are — so the
    # verdict must still be homogeneous_rig regardless of naming variety.
    fixtures = tuple(
        FixtureTypeRecord(fid=fid, manufacturer="Robe", type_name="Robin MMX Spot")
        for fid in range(2, 21)
    )
    analysis = analyze_fixture_types(fixtures)
    assert analysis.reason == "homogeneous_rig"
    assert analysis.type_axis_groups == ()


# ---------------------------------------------------------------------------
# Static source checks (acceptance criteria run as unit tests)
# ---------------------------------------------------------------------------


def test_no_category_classification_constant_in_source() -> None:
    """No CATEGORY-shaped constant or literal set/dict is defined for category
    token matching. The acceptance criterion's authoritative grep (run by the
    harness, not here) checks the full file including the docstring's
    exclusion-rationale prose, which legitimately names the excluded category
    words while explaining why no code implements them; this test instead
    asserts no module-level constant is a category vocabulary."""
    import server.spatial.fixture_type as module

    category_words = {"spot", "wash", "beam", "fresnel", "blinder", "strobe", "par", "profile"}
    for name in dir(module):
        if name.startswith("_") or name in {"FIXTURE_TYPE_AXES"}:
            continue
        value = getattr(module, name)
        if isinstance(value, (frozenset, set, tuple, list)):
            for item in value:
                if isinstance(item, str) and item.lower() in category_words:
                    pytest.fail(f"{name} carries a category-token literal: {item!r}")


def test_no_import_of_transport_or_safety_modules() -> None:
    import ast

    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("bridge" in name or "pythonosc" in name for name in imported)
    assert not any(name.startswith("server.safety") for name in imported)
