"""Closed judgement vocabulary tests (shared contract — design.md slot C).

These sets are the cross-milestone contract: the inventory, the patch judge, the
macro builder and the report all draw from them. The tests below fix the two
properties every consumer relies on -- the sets are exactly the designed ones,
and an unknown code cannot pass silently.
"""

from __future__ import annotations

import pytest

from server.prechk.verdicts import (
    CLOSED_VOCABULARIES,
    COLLISION_KIND,
    COMPLETENESS,
    FIXTURE_VERDICT,
    OVERLAP_BASIS,
    READ_FAILURE_KIND,
    SKIPPED_CHECK_KIND,
    UnknownVerdict,
    validate,
)


class TestVocabularies:
    def test_sets_are_exactly_the_designed_ones(self):
        designed = {
            "completeness": {"complete", "incomplete"},
            "fixture_verdict": {"observed_clear", "collision", "read_failed", "not_assessed"},
            "collision_kind": {"address_duplicate", "range_overlap"},
            "read_failure_kind": {
                "property_unreadable",
                "shape_invalid",
                "address_parse_failed",
                "type_mode_unresolved",
            },
            "skipped_check_kind": {
                "range_overlap_descope",
                "range_overlap_bound_inconclusive",
                "macro_descope",
                "macro_no_groups",
                "gate_unapproved",
            },
            "overlap_basis": {
                "exact_widths",
                "bound_proves_clear",
                "bound_inconclusive",
                "not_performed",
            },
        }
        actual = {name: set(values) for name, values in CLOSED_VOCABULARIES.items()}
        assert actual == designed

    def test_registry_covers_every_vocabulary_and_nothing_else(self):
        assert set(CLOSED_VOCABULARIES) == {
            "completeness",
            "fixture_verdict",
            "collision_kind",
            "read_failure_kind",
            "skipped_check_kind",
            "overlap_basis",
        }
        # Ordered, not just set-equal: ``overlap_basis`` was appended LAST so the
        # five existing rows stayed byte-identical, and a reader can confirm the
        # registry edit and this edit agree by eye. Weakening this to a set
        # comparison would let the order drift unobserved.
        assert list(CLOSED_VOCABULARIES.values()) == [
            COMPLETENESS,
            FIXTURE_VERDICT,
            COLLISION_KIND,
            READ_FAILURE_KIND,
            SKIPPED_CHECK_KIND,
            OVERLAP_BASIS,
        ]

    def test_the_registry_is_not_mutable(self):
        # A consumer that could add a code would defeat the closed set.
        with pytest.raises(TypeError):
            CLOSED_VOCABULARIES["fixture_verdict"] = frozenset({"anything"})


class TestValidate:
    def test_a_member_round_trips(self):
        for vocabulary, allowed in CLOSED_VOCABULARIES.items():
            for value in allowed:
                assert validate(vocabulary, value) == value

    def test_an_unknown_value_raises_and_names_the_allowed_set(self):
        with pytest.raises(UnknownVerdict, match="not a fixture_verdict"):
            validate("fixture_verdict", "probably_fine")

    def test_a_value_from_the_wrong_vocabulary_raises(self):
        # Cross-vocabulary leakage is the realistic bug: 'collision' is a
        # fixture verdict, never a collision KIND.
        with pytest.raises(UnknownVerdict):
            validate("collision_kind", "collision")

    def test_an_unknown_vocabulary_raises(self):
        with pytest.raises(UnknownVerdict, match="no such vocabulary"):
            validate("verdict", "complete")

    def test_case_and_whitespace_variants_are_not_accepted(self):
        for bad in ("Complete", "complete ", " complete", "COMPLETE"):
            with pytest.raises(UnknownVerdict):
                validate("completeness", bad)
