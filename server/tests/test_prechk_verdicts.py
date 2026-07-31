"""Closed judgement vocabulary tests (shared contract — design.md slot C).

These sets are the cross-milestone contract: the inventory, the patch judge, the
macro builder and the report all draw from them. The tests below fix the two
properties every consumer relies on -- the sets are exactly the designed ones,
and an unknown code cannot pass silently.
"""

from __future__ import annotations

import ast
from pathlib import Path

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

from .test_prechk_macro import response_assertion_keys
from .test_prechk_patch import _VACUOUS_ASSERTION

_REPORT_SOURCE = Path(__file__).with_name("test_prechk_report.py")
_REPORT_SCAN_TEST = "test_no_report_field_asserts_that_a_fixture_answered"


def _report_forbidden_fields() -> tuple[str, ...]:
    """Scanner 3's field list, READ from its own source instead of copied.

    ``test_prechk_report`` spells the list as a tuple literal inside the test
    body, so there is no name to import. Re-typing it here would fork the rule:
    the copy would keep passing after the original grew a field. Lifting it out
    of the AST keeps one definition, and raising here means a refactor that
    removes the literal is reported rather than silently scanning nothing.
    """
    tree = ast.parse(_REPORT_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == _REPORT_SCAN_TEST):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.For) and isinstance(sub.iter, ast.Tuple):
                return tuple(
                    element.value
                    for element in sub.iter.elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                )
    raise AssertionError(f"{_REPORT_SCAN_TEST} no longer spells a tuple of field names")


REPORT_FORBIDDEN_FIELDS = _report_forbidden_fields()


def forbidden_token_hits(code: str) -> tuple[str, ...]:
    """Names of the shipped scanners that object to ``code``; empty is clean.

    All three rules come from where they already live -- the patch regex and the
    macro predicate are imported, the report field list is lifted from its AST.
    ``response_assertion_keys`` reads payload KEYS, so a one-entry mapping puts
    the code exactly where that scanner already looks; that is reuse, not a
    second definition of "forbidden".
    """
    hits: list[str] = []
    if _VACUOUS_ASSERTION.search(code):
        hits.append("patch:_VACUOUS_ASSERTION")
    if response_assertion_keys({code: None}):
        hits.append("macro:response_assertion_keys")
    hits.extend(f"report:{field}" for field in REPORT_FORBIDDEN_FIELDS if field in code)
    return tuple(hits)


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


class TestForbiddenTokensInVocabularyCodes:
    """AC-OVERLAP-014 ⑨ — the three shipped scanners, applied to code VALUES.

    ⑨ says the three forbidden-token scanners pass the whole new vocabulary.
    All three read payload KEYS (or a four-name field list), so until now
    nothing applied them to the code strings themselves: a value such as
    ``range_all_clear`` could ship and break no test. These apply the same three
    rules -- imported, not retyped -- to every code in every closed vocabulary.
    """

    def test_every_closed_vocabulary_code_passes_all_three_scanners(self):
        scanned = sorted(
            (name, code) for name, values in CLOSED_VOCABULARIES.items() for code in values
        )
        # Non-vacuity: an emptied or shrunken registry must not pass by scanning
        # nothing. 21 is MEASURED in this tree -- 2+4+2+4+5+4 with
        # ``overlap_basis`` landed -- and a later axis only grows it, so the
        # floor never moves down. The axis-relative line below is the part that
        # matters if someone ever renames or drops the new axis: the absolute
        # floor alone could still be met by the five older vocabularies.
        assert len(scanned) >= 21, scanned
        assert {name for name, _ in scanned} == set(CLOSED_VOCABULARIES)
        assert {code for _, code in scanned} >= OVERLAP_BASIS
        dirty = {f"{name}.{code}": forbidden_token_hits(code) for name, code in scanned}
        assert {key: hits for key, hits in dirty.items() if hits} == {}

    def test_the_new_axis_is_covered_code_by_code(self):
        assert {code: forbidden_token_hits(code) for code in sorted(OVERLAP_BASIS)} == {
            "bound_inconclusive": (),
            "bound_proves_clear": (),
            "exact_widths": (),
            "not_performed": (),
        }

    @pytest.mark.parametrize(
        "planted",
        ["range_all_clear", "proven_clear", "width_lit", "bound_verified", "responded_at_last"],
    )
    def test_a_planted_bad_code_is_rejected_by_the_same_rule(self, planted: str):
        """Positive control -- without it the scan above proves nothing."""
        assert forbidden_token_hits(planted), planted

    def test_the_shipped_grade_is_the_near_miss_the_rule_must_split(self):
        """``bound_proves_clear`` carries 'proves' and '_clear' and is CLEAN.

        A rule loosened to 'prove' or 'clear' fires on the real code and fails
        the first assertion; a rule tightened until it stops catching ``proven``
        or ``all_clear`` fails the other two. Only a rule that splits the pair
        passes both, which is what makes the scan above worth running.
        """
        assert "bound_proves_clear" in OVERLAP_BASIS
        assert forbidden_token_hits("bound_proves_clear") == ()
        assert forbidden_token_hits("proven_clear")
        assert forbidden_token_hits("range_all_clear")

    def test_each_of_the_three_scanners_is_actually_wired_in(self):
        """One sample per rule, so dropping a rule from the scan is observed."""
        assert forbidden_token_hits("patch_ok") == ("patch:_VACUOUS_ASSERTION",)
        assert forbidden_token_hits("width_lit") == ("macro:response_assertion_keys",)
        assert REPORT_FORBIDDEN_FIELDS == (
            "responded",
            "fixture_ok",
            "no_response",
            "fixtures_verified",
        )
