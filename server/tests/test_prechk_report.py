"""Pre-check report tests (M5 — AC-PRECHK-012).

The report is the only surface the user reads, so it carries three obligations
the judging layers do not: the aggregate must equal the per-fixture list, every
judgement code must come from a closed vocabulary, and every user-facing label
must come from a table rather than a literal spelled at the call site.

The label policy differs from ``server/looks/report.py`` on purpose. That module
passes an unknown code through, because its section-failure reasons arrive as
free strings from the console and an invented translation would stop the user
from searching for the original. A pre-check VERDICT has no such origin -- it is
always a member of one of the closed sets -- so an unknown code there is a bug,
and :func:`server.prechk.report.label` raises instead of passing it through
(AC-PRECHK-012 ⑤ d).
"""

from __future__ import annotations

import ast
import importlib
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType

import pytest

from server.prechk.inventory import FixtureRecord, Inventory, ReadFailure
from server.prechk.macro import (
    GroupPool,
    GroupTarget,
    MacroPolicy,
    build_response_check_macro,
)
from server.prechk.patch import SCOPE_QUALIFIER, FootprintPolicy, evaluate_patch
from server.prechk.report import VOCABULARY_LABELS, build_report, label
from server.prechk.verdicts import CLOSED_VOCABULARIES, UnknownVerdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRECHK_DIR = PROJECT_ROOT / "server" / "prechk"
REPORT_SOURCE = PRECHK_DIR / "report.py"

ROOT = "Patch/Stages/1/Fixtures"


def _record(slot: int, patch: str | None, *, type_ok: bool = True) -> FixtureRecord:
    return FixtureRecord(
        slot=slot,
        name=f"MMX {slot}",
        patch_raw=patch,
        fixture_type="FixtureType 1" if type_ok else None,
        mode="1 Mode 1" if type_ok else None,
    )


def _inventory(
    records: list[FixtureRecord],
    *,
    child_count: int | None = None,
    read_failures: tuple[ReadFailure, ...] = (),
    recovered_slots: tuple[int, ...] = (),
) -> Inventory:
    observed = tuple(records)
    total = child_count if child_count is not None else len(observed)
    missing = total - len(observed)
    short = bool(recovered_slots) or missing > 0
    return Inventory(
        path=ROOT,
        child_count=total,
        enumerated_count=len(observed) - len(recovered_slots),
        recovered_count=len(recovered_slots),
        observed_count=len(observed),
        missing_count=missing,
        completeness="incomplete" if short else "complete",
        recovery_boundary=total if short else None,
        index_domain_unknown=short,
        recovered_slots=recovered_slots,
        fixtures=observed,
        read_failures=read_failures,
        state_paths=(ROOT,),
        property_queries=tuple((f"{ROOT}/{r.slot}", "Patch") for r in observed),
    )


def _clean_rig() -> Inventory:
    # Synthetic, NOT a live mirror: binding an in-memory fixture to the site
    # showfile would break the suite every time the rig changes
    # (progress.md §E.2 M0, scout item 4).
    return _inventory([_record(slot, f"1.{slot:03d}") for slot in range(1, 19)])


def _duplicate_rig() -> Inventory:
    return _inventory([_record(1, "1.001"), _record(2, "1.001"), _record(3, "2.001")])


def _macro(groups: tuple[GroupTarget, ...] = (GroupTarget(no=11, name="Back"),)):
    return build_response_check_macro(GroupPool(targets=groups), MacroPolicy.available(91))


def _macro_no_groups():
    return build_response_check_macro(GroupPool(targets=()), MacroPolicy.available(91))


class TestSectionsArePresent:
    """AC-PRECHK-012 ① — five sections, all of them, always."""

    def test_every_designed_section_is_present(self):
        payload = build_report(evaluate_patch(_duplicate_rig()), macro=_macro()).to_dict()
        for key in (
            "inventory",
            "fixtures",
            "collisions",
            "read_failures",
            "skipped_checks",
            "macro",
            "summary_ko",
        ):
            assert key in payload, f"missing report section: {key}"

    def test_collisions_and_failures_are_present_even_when_empty(self):
        payload = build_report(evaluate_patch(_clean_rig())).to_dict()
        assert payload["collisions"] == {"address_duplicates": [], "range_overlaps": []}
        assert payload["read_failures"] == []

    def test_completeness_carries_three_numbers(self):
        payload = build_report(
            evaluate_patch(_inventory([_record(1, "1.001")], child_count=4))
        ).to_dict()
        inventory = payload["inventory"]
        assert inventory["child_count"] == 4
        assert inventory["observed_count"] == 1
        assert inventory["missing_count"] == 3
        assert inventory["completeness"] == "incomplete"

    def test_the_macro_key_is_absent_when_no_macro_was_requested(self):
        # design.md §5.1 marks `macro` as "매크로 요청 시" -- present on request,
        # not a permanent null every caller has to special-case.
        payload = build_report(evaluate_patch(_clean_rig())).to_dict()
        assert "macro" not in payload

    def test_skipped_checks_merges_both_producers(self):
        payload = build_report(evaluate_patch(_clean_rig()), macro=_macro_no_groups()).to_dict()
        kinds = [row["kind"] for row in payload["skipped_checks"]]
        assert "range_overlap_descope" in kinds
        assert "macro_no_groups" in kinds
        assert len(kinds) == len(set(kinds)) >= 2

    def test_a_created_macro_contributes_no_skipped_check(self):
        payload = build_report(evaluate_patch(_clean_rig()), macro=_macro()).to_dict()
        kinds = [row["kind"] for row in payload["skipped_checks"]]
        assert kinds == ["range_overlap_descope"]


class TestArithmeticCloses:
    """AC-PRECHK-012 ② — the aggregate IS the per-fixture list, counted once."""

    def test_verdict_counts_equal_the_per_fixture_rows(self):
        payload = build_report(evaluate_patch(_duplicate_rig())).to_dict()
        rows = payload["fixtures"]
        for verdict, count in payload["verdict_counts"].items():
            if verdict == "not_assessed":
                # The unobserved population has no rows — but "no rows" is not
                # "unverifiable". Skipping it left the ONE number that is not
                # derived from the rows unchecked: `not_assessed` is assigned
                # straight from `inventory.missing_count`, and the other two
                # tests here only read that assignment back. That is what let a
                # snapshot report `관측 3개 / 보고된 자식 수 2개` while calling itself
                # complete. Check it against the declared population instead.
                assert count == payload["inventory"]["child_count"] - len(rows)
                continue
            assert count == sum(1 for row in rows if row["verdict"] == verdict)
        # And the whole census closes: AC-PRECHK-003's identity, at report level.
        assert sum(payload["verdict_counts"].values()) == payload["inventory"]["child_count"]

    def test_every_observed_fixture_appears_exactly_once(self):
        inventory = _duplicate_rig()
        payload = build_report(evaluate_patch(inventory)).to_dict()
        slots = [row["slot"] for row in payload["fixtures"]]
        assert sorted(slots) == sorted(f.slot for f in inventory.fixtures)
        assert len(slots) == len(set(slots))

    def test_not_assessed_counts_the_unobserved_population(self):
        payload = build_report(
            evaluate_patch(_inventory([_record(1, "1.001")], child_count=5))
        ).to_dict()
        assert payload["verdict_counts"]["not_assessed"] == 4
        assert len(payload["fixtures"]) == 1

    def test_read_failure_counts_sum_to_the_read_failure_rows(self):
        failure = ReadFailure(
            slot=2,
            name="MMX 2",
            property="Patch",
            raw_value="function: 0xdeadbeef",
            kind="shape_invalid",
            detail="함수 참조가 값 자리에 왔다",
        )
        inventory = _inventory([_record(1, "1.001")], read_failures=(failure,))
        payload = build_report(evaluate_patch(inventory)).to_dict()
        assert sum(payload["read_failure_counts"].values()) == len(payload["read_failures"])
        assert len(payload["read_failures"]) == 1

    def test_collision_members_are_the_fixtures_that_collided(self):
        payload = build_report(evaluate_patch(_duplicate_rig())).to_dict()
        duplicates = payload["collisions"]["address_duplicates"]
        assert len(duplicates) == 1
        members = {member["slot"] for member in duplicates[0]["fixtures"]}
        assert members == {1, 2}


class TestClosedVocabularies:
    """AC-PRECHK-012 ③ — no value from outside the designed sets appears."""

    def test_every_emitted_code_belongs_to_its_vocabulary(self):
        payload = build_report(evaluate_patch(_duplicate_rig()), macro=_macro()).to_dict()
        assert payload["inventory"]["completeness"] in CLOSED_VOCABULARIES["completeness"]
        for row in payload["fixtures"]:
            assert row["verdict"] in CLOSED_VOCABULARIES["fixture_verdict"]
        for group in payload["collisions"].values():
            for collision in group:
                assert collision["kind"] in CLOSED_VOCABULARIES["collision_kind"]
        for failure in payload["read_failures"]:
            assert failure["kind"] in CLOSED_VOCABULARIES["read_failure_kind"]
        for check in payload["skipped_checks"]:
            assert check["kind"] in CLOSED_VOCABULARIES["skipped_check_kind"]

    def test_the_verdict_count_keys_are_exactly_the_vocabulary(self):
        payload = build_report(evaluate_patch(_clean_rig())).to_dict()
        assert set(payload["verdict_counts"]) == set(CLOSED_VOCABULARIES["fixture_verdict"])

    def test_fixture_reason_codes_stay_inside_their_vocabularies(self):
        payload = build_report(evaluate_patch(_duplicate_rig())).to_dict()
        allowed = CLOSED_VOCABULARIES["collision_kind"] | CLOSED_VOCABULARIES["read_failure_kind"]
        seen = [code for row in payload["fixtures"] for code in row["reasons"]]
        assert seen, "no reason codes present — the check would be vacuous"
        assert set(seen) <= set(allowed)


class TestLabelReuseBoundary:
    """AC-PRECHK-012 ④ — reuse rides the public accessor, never a private name."""

    def _import_nodes(self) -> list[ast.ImportFrom]:
        nodes: list[ast.ImportFrom] = []
        for source in sorted(PRECHK_DIR.rglob("*.py")):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            nodes.extend(n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
        return nodes

    def test_no_underscore_identifier_is_imported_from_the_looks_report(self):
        nodes = self._import_nodes()
        # Non-vacuity: an empty scan makes the 0-count free.
        assert len(nodes) >= 1, "scan collected no ImportFrom nodes"
        private = [
            f"{node.module}.{alias.name}"
            for node in nodes
            if (node.module or "").startswith("server.looks")
            for alias in node.names
            if alias.name.startswith("_")
        ]
        assert private == [], f"private label identifiers imported: {private}"

    def test_the_scanner_catches_a_planted_private_import(self):
        planted = ast.parse("from server.looks.report import _REASON_LABELS")
        private = [
            alias.name
            for node in ast.walk(planted)
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("server.looks")
            for alias in node.names
            if alias.name.startswith("_")
        ]
        assert private == ["_REASON_LABELS"]


class TestKoreanLabels:
    """AC-PRECHK-012 ⑤ — labels are structural, not decorative."""

    def test_label_tables_match_the_vocabularies_exactly(self):
        assert set(VOCABULARY_LABELS) == set(CLOSED_VOCABULARIES)
        for vocabulary, codes in CLOSED_VOCABULARIES.items():
            assert set(VOCABULARY_LABELS[vocabulary]) == set(codes), (
                f"label table for {vocabulary} does not match its vocabulary"
            )

    def test_every_label_is_a_non_empty_korean_string(self):
        for table in VOCABULARY_LABELS.values():
            for code, text in table.items():
                assert text.strip(), f"empty label for {code}"
                assert any("\uac00" <= character <= "\ud7a3" for character in text), (
                    f"label for {code} carries no Korean: {text!r}"
                )

    def test_the_incomplete_label_does_not_claim_unread_fixtures(self):
        """M8 live finding: recovery can observe everything and stay incomplete.

        The rig read end-to-end on 2026-07-30 recovered all 19 declared fixtures
        (``missing_count`` 0) while ``completeness`` stayed ``incomplete``,
        because the index domain's upper bound is unknown. The label said unread
        fixtures existed, which was false in the first string the user reads.
        """
        recovered = _inventory(
            [_record(slot, f"1.{slot:03d}") for slot in range(1, 4)],
            recovered_slots=(3,),
        )
        assert recovered.completeness == "incomplete"
        assert recovered.missing_count == 0
        summary = build_report(evaluate_patch(recovered)).to_dict()["summary_ko"]
        assert label("completeness", "incomplete") in summary
        for false_claim in ("못 읽은 픽스처가 있다", "미관측"):
            assert false_claim not in summary, (
                f"summary claims unread fixtures while missing_count is 0: {false_claim}"
            )

    def test_summary_ko_is_not_empty(self):
        payload = build_report(evaluate_patch(_duplicate_rig()), macro=_macro()).to_dict()
        assert payload["summary_ko"].strip()

    def test_summary_ko_states_the_counts_it_claims(self):
        evaluation = evaluate_patch(_duplicate_rig())
        summary = build_report(evaluation).to_dict()["summary_ko"]
        assert str(evaluation.inventory.observed_count) in summary
        assert str(evaluation.collision_total) in summary

    def test_summary_ko_carries_the_incompleteness_label(self):
        evaluation = evaluate_patch(_inventory([_record(1, "1.001")], child_count=9))
        summary = build_report(evaluation).to_dict()["summary_ko"]
        # An incomplete read must not read as a clean bill of health.
        assert label("completeness", "incomplete") in summary

    def test_an_incomplete_read_qualifies_the_collision_count(self):
        # `scope_qualified`/`scope_note` exist for exactly this claim and the
        # paragraph was dropping them: a bare `충돌 N건` reads as a number covering
        # the whole rig even when part of it was never observed — the reading
        # REQ-PRECHK-010 exists to prevent, and the one a log grep performs.
        evaluation = evaluate_patch(_inventory([_record(1, "1.001")], child_count=9))
        assert evaluation.scope_qualified is True
        summary = build_report(evaluation).to_dict()["summary_ko"]
        assert f"{SCOPE_QUALIFIER} 충돌" in summary, summary

    def test_a_complete_read_does_not_qualify_the_collision_count(self):
        # Non-vacuity: the qualifier must not become unconditional decoration —
        # a rig read in full IS a rig-wide statement.
        evaluation = evaluate_patch(_clean_rig())
        assert evaluation.scope_qualified is False
        summary = build_report(evaluation).to_dict()["summary_ko"]
        assert SCOPE_QUALIFIER not in summary, summary
        assert "충돌 0건" in summary

    def test_a_complete_read_says_so_with_the_other_label(self):
        summary = build_report(evaluate_patch(_clean_rig())).to_dict()["summary_ko"]
        assert label("completeness", "complete") in summary

    def test_an_unknown_code_raises_and_is_not_returned(self):
        with pytest.raises(UnknownVerdict) as raised:
            label("fixture_verdict", "probably_fine")
        # The code may appear in the developer-facing exception; what must never
        # happen is RETURNING it as though it were a label.
        assert "probably_fine" in str(raised.value)

    def test_an_unknown_vocabulary_raises(self):
        with pytest.raises(UnknownVerdict):
            label("verdict", "complete")

    def test_a_code_from_the_wrong_vocabulary_raises(self):
        with pytest.raises(UnknownVerdict):
            label("collision_kind", "read_failed")

    def test_no_vocabulary_code_is_spelled_as_a_literal_outside_the_tables(self):
        """AC-PRECHK-012 ⑤ c — codes are referenced, not retyped."""
        tree = ast.parse(REPORT_SOURCE.read_text(encoding="utf-8"))
        every_code = {code for codes in CLOSED_VOCABULARIES.values() for code in codes}
        table_constants: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id.endswith("_LABELS")
                for target in node.targets
            ):
                table_constants.update(
                    id(child) for child in ast.walk(node.value) if isinstance(child, ast.Constant)
                )
        stray: list[str] = []
        in_tables = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node.value not in every_code:
                continue
            if id(node) in table_constants:
                in_tables += 1
            else:
                stray.append(node.value)
        # Non-vacuity: the scan must actually have reached the tables.
        assert in_tables >= len(every_code), (
            f"scan found only {in_tables} table codes; expected at least {len(every_code)}"
        )
        assert stray == [], f"vocabulary codes retyped outside the label tables: {stray}"


@contextmanager
def _registry_patched_to(registry: dict):
    """Swap the closed-vocabulary registry, then put it back and re-import.

    The guard under test runs at MODULE IMPORT, so the only way to observe it is
    to re-import with a registry that disagrees with the label tables. The
    ``finally`` reload matters: a failed reload leaves the module half-built, and
    every later test in the suite imports from it.
    """
    import server.prechk.report as report_module
    import server.prechk.verdicts as verdicts_module

    original = verdicts_module.CLOSED_VOCABULARIES
    verdicts_module.CLOSED_VOCABULARIES = MappingProxyType(dict(registry))
    try:
        yield report_module
    finally:
        verdicts_module.CLOSED_VOCABULARIES = original
        importlib.reload(report_module)


class TestImportTimeLabelGuard:
    """SPEC-COPILOT-OVERLAP-001 D-6 — the guard walks the registry.

    NOT a regression test: nothing here failed before this class existed. The
    hand-kept ``(name, set)`` tuple this guard replaced skipped any vocabulary
    nobody added to it, import still succeeded, and the label-drift test walks
    the registry so it saw nothing either. These tests exist because that step
    was symptom-free, and they are the symptom.
    """

    def test_the_unpatched_module_reimports_cleanly(self):
        # Positive control: the two negative cases below mean nothing if a
        # plain reload already raised.
        import server.prechk.report as report_module

        importlib.reload(report_module)
        assert set(report_module.VOCABULARY_LABELS) == set(CLOSED_VOCABULARIES)

    def test_a_vocabulary_with_no_label_table_fails_at_import(self):
        extended = {**CLOSED_VOCABULARIES, "unlabelled_axis": frozenset({"a", "b"})}
        with (
            _registry_patched_to(extended) as report_module,
            pytest.raises(UnknownVerdict, match="unlabelled_axis"),
        ):
            importlib.reload(report_module)

    def test_a_label_table_short_one_code_fails_at_import(self):
        # The realistic shape: the axis IS registered and IS labelled, but one
        # value was added to the vocabulary and forgotten in the table.
        short = dict(CLOSED_VOCABULARIES)
        short["skipped_check_kind"] = frozenset(
            {*short["skipped_check_kind"], "an_unlabelled_kind"}
        )
        with (
            _registry_patched_to(short) as report_module,
            pytest.raises(UnknownVerdict, match="skipped_check_kind"),
        ):
            importlib.reload(report_module)

    def test_the_guard_iterates_the_registry_rather_than_a_literal_tuple(self):
        """AC-OVERLAP-014 ⑦ — the form is the deliverable, not just the effect.

        Satisfying the two negative tests above by re-adding a hardcoded tuple
        and remembering to append to it is exactly the trap D-6 removes, so the
        source shape is asserted too: the guard's iterable is a call on
        ``CLOSED_VOCABULARIES``, and no loop enumerates the vocabularies from a
        literal sequence. (Vocabulary NAMES stay legal as literals elsewhere --
        ``label("fixture_verdict", code)`` has to spell one. It is the CODES the
        sibling scan forbids outside the tables.)
        """
        tree = ast.parse(REPORT_SOURCE.read_text(encoding="utf-8"))
        loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
        registry_walks = [
            node
            for node in loops
            if isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Attribute)
            and isinstance(node.iter.func.value, ast.Name)
            and node.iter.func.value.id == "CLOSED_VOCABULARIES"
        ]
        assert len(registry_walks) == 1, "the import-time guard must walk CLOSED_VOCABULARIES once"
        names = set(CLOSED_VOCABULARIES)
        relapsed = [
            ast.unparse(node.iter)
            for node in loops
            if isinstance(node.iter, ast.Tuple | ast.List)
            and any(
                isinstance(constant, ast.Constant) and constant.value in names
                for constant in ast.walk(node.iter)
            )
        ]
        assert relapsed == [], f"a literal vocabulary sequence came back: {relapsed}"


class TestMacroSection:
    """The macro axis reaches the report without acquiring a response claim."""

    def test_the_macro_section_keeps_its_six_designed_keys(self):
        payload = build_report(evaluate_patch(_clean_rig()), macro=_macro()).to_dict()
        assert set(payload["macro"]) == {
            "created",
            "target_kind",
            "targets",
            "commands",
            "requires_human_visual_confirmation",
            "reason",
        }

    def test_the_visual_confirmation_notice_reaches_the_korean_summary(self):
        summary = build_report(evaluate_patch(_clean_rig()), macro=_macro()).to_dict()["summary_ko"]
        assert "눈으로" in summary

    def test_no_report_field_asserts_that_a_fixture_answered(self):
        payload = build_report(evaluate_patch(_clean_rig()), macro=_macro()).to_dict()
        flat = repr(payload)
        for field in ("responded", "fixture_ok", "no_response", "fixtures_verified"):
            assert field not in flat

    def test_a_descoped_macro_reports_zero_commands_and_a_reason(self):
        macro = build_response_check_macro(
            GroupPool(targets=(GroupTarget(no=11, name="Back"),)),
            MacroPolicy.descoped("ASSUMPTION-26 부정 — 저작 문법 없음"),
        )
        payload = build_report(evaluate_patch(_clean_rig()), macro=macro).to_dict()
        assert payload["macro"]["commands"] == []
        assert payload["macro"]["created"] is False
        assert payload["macro"]["reason"].strip()
        assert "macro_descope" in [row["kind"] for row in payload["skipped_checks"]]


class TestRangeOverlapBranchReachesTheReport:
    """AC-PRECHK-012 ① (e) — the descoped axis is named, not silently missing."""

    def test_descope_is_reported_with_its_assumption(self):
        payload = build_report(evaluate_patch(_clean_rig())).to_dict()
        rows = [r for r in payload["skipped_checks"] if r["kind"] == "range_overlap_descope"]
        assert len(rows) == 1
        assert rows[0]["assumption"] == "ASSUMPTION-27"
        assert rows[0]["reason"].strip()

    def test_a_go_footprint_produces_range_overlaps_and_no_descope(self):
        inventory = _inventory([_record(1, "1.001"), _record(2, "1.015")])
        evaluation = evaluate_patch(
            inventory,
            FootprintPolicy(enabled=True, widths={1: 29, 2: 29}, source="DMXChannels childCount"),
        )
        payload = build_report(evaluation).to_dict()
        assert payload["collisions"]["range_overlaps"]
        assert "range_overlap_descope" not in [r["kind"] for r in payload["skipped_checks"]]
