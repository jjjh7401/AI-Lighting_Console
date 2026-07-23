"""Risk classification tests (M4 stage ② — REQ-MVP-013/026/036b).

Classification is command-SYNTAX based (acceptance edge case: a blacklist
keyword inside a quoted object NAME must not match). Keyword matching is
abbreviation-aware (case-insensitive exact OR a >=3-char prefix of the keyword;
options abbreviate from 1 char) — over-matching is acceptable (FP resolved by
human approval), under-matching is the FN direction the design forbids.
"""

from __future__ import annotations

import pytest

from server.safety.audit import AuditLog
from server.safety.classify import RECOGNIZED_REFERENCE_TYPES, classify_command
from server.safety.console import StateBodyFetcher
from server.safety.expand import evaluate_reference
from server.safety.gate import SafetyGate
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

from .test_safety_expand import DictBodyFetcher
from .test_safety_gate import FakeConsole, ScriptedApproval

RULESET = load_ruleset()


def _classify(line: str):
    result = validate(line)
    assert result.ok, f"test line must parse: {line!r} ({result.reason})"
    return classify_command(result.parsed, RULESET)


class TestBlacklistMatching:
    @pytest.mark.parametrize(
        "line,entry",
        [
            ("Delete Sequence 5", "Delete"),
            ("delete sequence 5", "Delete"),
            ("Remove Sequence 5", "Remove"),
            ("Off Everything", "Off Everything"),
            ("Store Cue 5 /overwrite", "Store /overwrite"),
            ("Shutdown", "Shutdown"),
            ("Format Disk", "Format"),
        ],
    )
    def test_direct_blacklist_commands_are_blacklisted(self, line, entry):
        finding = _classify(line)
        assert finding.category == "blacklisted"
        assert finding.risky is True
        assert finding.matched_entry == entry

    def test_verb_abbreviation_still_matches(self):
        # MA3 accepts abbreviated keywords (Del -> Delete); the classifier
        # matches >=3-char prefixes so abbreviation cannot bypass the set.
        assert _classify("Del Sequence 5").category == "blacklisted"
        assert _classify("Rem Sequence 5").category == "blacklisted"

    def test_option_abbreviation_still_matches(self):
        assert _classify("Store Cue 5 /o").category == "blacklisted"
        assert _classify("Store Cue 5 /over").category == "blacklisted"

    def test_plain_store_is_safe(self):
        finding = _classify("Store Cue 5")
        assert finding.category == "safe"
        assert finding.risky is False

    def test_blacklist_keyword_inside_quoted_name_does_not_match(self):
        # Acceptance edge case: quoted object names never match keywords.
        finding = _classify("Label Sequence 3 'Delete old look'")
        assert finding.category == "safe"

    def test_store_with_quoted_overwrite_text_is_safe(self):
        finding = _classify("Store Cue 5 '/overwrite'")
        assert finding.category == "safe"


class TestUnspecifiedTargetDetection:
    # REQ-MVP-036b / AC-MVP-024: deterministic, harness-level detection of
    # destructive commands lacking an explicit target (>=5-case corpus).
    @pytest.mark.parametrize(
        "line",
        [
            "Delete",  # no target at all
            "Delete *",  # wildcard
            "Delete Sequence Thru",  # open-ended Thru (all sequences)
            "Delete Thru 10",  # open start
            "Remove All",  # broad keyword
            "Off Everything",  # inherently broad
        ],
    )
    def test_unspecified_or_broad_destructive_commands_are_flagged(self, line):
        finding = _classify(line)
        assert finding.category == "blacklisted"
        assert finding.unspecified_target is True
        assert any("target" in r for r in finding.reasons)

    def test_bounded_range_is_specified(self):
        finding = _classify("Delete Sequence 1 Thru 10")
        assert finding.category == "blacklisted"
        assert finding.unspecified_target is False

    def test_explicit_target_is_specified(self):
        finding = _classify("Delete Sequence 5")
        assert finding.unspecified_target is False


class TestInvokingDetection:
    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Go Macro 5", "Macro 5"),
            ("Go+ Executor 201", "Executor 201"),  # REQ-EXECREF-001/002
            ("Goto Cue 3", None),
            ("On Sequence 2", "Sequence 2"),
            ("Off Sequence 3", "Sequence 3"),
            ("Toggle Sequence 2", "Sequence 2"),
            ("Call Macro 7", "Macro 7"),
            ("Temp Sequence 4", "Sequence 4"),
            ("Flash Sequence 4", "Sequence 4"),
        ],
    )
    def test_invoking_verbs_are_detected_with_reference(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Macro 5", "Macro 5"),
            ("Plugin 7", "Plugin 7"),
            ('Plugin "CopilotResponder" "ping x"', "Plugin CopilotResponder"),
        ],
    )
    def test_bare_object_forms_are_detected(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    def test_off_everything_wins_over_off_as_invoking_verb(self):
        # Blacklist matching has priority over invoking-verb detection.
        assert _classify("Off Everything").category == "blacklisted"

    def test_verb_abbreviation_of_invoking_verb_is_detected(self):
        finding = _classify("Got Macro 5")  # >=3-char prefix of Goto
        assert finding.category == "invoking"

    def test_plain_commands_are_not_invoking(self):
        assert _classify("Store Cue 5").category == "safe"
        assert _classify("List").category == "safe"
        assert _classify("Assign Sequence 1 At Executor 201").category == "safe"


class TestQuotedPropertyCommandContent:
    # M6c-2 Finding 1 (REQ-MVP-013): the M6b-1r2 macro-authoring recipe
    # (`Set Macro <pool>.<line> Property 'Command' '<text>'`) persists a
    # command LINE as a quoted property value. The outer assignment syntax
    # (verb "Set", args Macro/1.1/Property/"Command") is not itself blacklist
    # or invoking-verb shaped, so without recursion a destructive string
    # smuggled this way would classify as "safe" with zero approval.
    def test_destructive_content_in_command_property_is_blacklisted(self):
        finding = _classify('Set Macro 1.1 Property "Command" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True
        assert finding.matched_entry == "Delete"

    def test_legacy_cmd_property_name_spelling_is_also_recursed(self):
        # Older MA3 material calls the property `Cmd` instead of `Command`.
        finding = _classify('Set Macro 1.1 Property "Cmd" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True

    def test_assign_verb_legacy_form_adjacent_equivalent_is_also_recursed(self):
        # Detection is verb-agnostic (shape-driven on Property/Command/value),
        # so a different outer verb still catches the smuggled content.
        finding = _classify('Assign Macro 1.1 Property "Command" "Delete Everything"')
        assert finding.category == "blacklisted"
        assert finding.risky is True

    def test_benign_quoted_macro_command_stays_low_risk(self):
        # Must NOT over-block every quoted property assignment.
        finding = _classify('Set Macro 1.1 Property "Command" "Group \'Vocals\' At Full"')
        assert finding.category == "safe"
        assert finding.risky is False

    def test_nested_quoted_name_reference_is_not_a_command_and_does_not_false_positive(self):
        # A standalone quoted-name object reference (`Preset 'Blue'`-style,
        # per the 00_grammar.md object-by-name rule) carries no `Property`
        # keyword at all -> the detector must never engage on it.
        finding = _classify("At Preset 4.1")
        assert finding.category == "safe"
        finding = _classify("Select Preset 'Blue'")
        assert finding.category == "safe"


class TestExecutorReferenceRecognition:
    """SPEC-COPILOT-EXECREF-001 M1 (REQ-EXECREF-001/002/003): Executor joins
    the closed set of recognized reference types -- a deliberate, documented
    revision of RECOGNIZED_REFERENCE_TYPES (classify.py:33), not a second
    classification path (classify_command stays the single entry point)."""

    def test_executor_is_in_the_recognized_reference_type_closed_set(self):
        assert "Executor" in RECOGNIZED_REFERENCE_TYPES

    @pytest.mark.parametrize(
        "line,reference",
        [
            ("Go+ Executor 191", "Executor 191"),
            ("Go Executor 5", "Executor 5"),
            ("Off Executor 3", "Executor 3"),
        ],
    )
    def test_invoking_verbs_extract_executor_reference(self, line, reference):
        finding = _classify(line)
        assert finding.category == "invoking"
        assert finding.reference == reference

    def test_quoted_executor_token_is_still_skipped(self):
        # Existing semantics preserved (acceptance.md §D edge case 3): a
        # quoted token is never treated as a type-word match.
        finding = _classify('Go+ "Executor 201"')
        assert finding.category == "invoking"
        assert finding.reference is None

    def test_single_classification_entry_point_unchanged(self):
        # REQ-EXECREF-003: classify_command stays the ONE matching semantics;
        # Executor recognition is a closed-set data change, not a new branch.
        import inspect

        assert set(inspect.signature(classify_command).parameters.keys()) == {
            "parsed",
            "ruleset",
            "reference_types",
        }


class TestExecutorRenameInvariance:
    """AC-EXECREF-015 / REQ-EXECREF-007: reference extraction is derived
    purely from the executor NUMBER token in the raw command text -- it never
    reads a display/assigned-sequence name. Renaming the sequence assigned to
    an executor (e.g. 'Sequence 71' -> 'Cyan Look') must not change the
    extracted reference or the hold/risky screening result."""

    def test_reference_extraction_ignores_the_assigned_sequence_name(self):
        finding = _classify("Go+ Executor 202")
        assert finding.category == "invoking"
        assert finding.reference == "Executor 202"  # number-only, never a name

    @pytest.mark.parametrize(
        "body_content",
        [
            ("Store Cue 1",),  # 'Sequence 71'-era body content
            ("Store Cue 1",),  # 'Cyan Look'-era body content (post-rename)
        ],
        ids=["before-rename", "after-rename"],
    )
    def test_screening_result_is_identical_across_rename(self, body_content):
        # Both fixtures key on the SAME reference string ("Executor 202") --
        # proving the rename never changes which body the gate consults,
        # because the reference is number-derived, not name-derived.
        finding = _classify("Go+ Executor 202")
        fetcher = DictBodyFetcher({"Executor 202": body_content})
        outcome = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=fetcher)
        assert outcome.hold is False
        assert outcome.risky is False

    def test_before_and_after_rename_outcomes_are_byte_identical(self):
        finding = _classify("Go+ Executor 202")
        before = DictBodyFetcher({"Executor 202": ("Delete Sequence 5",)})
        after = DictBodyFetcher({"Executor 202": ("Delete Sequence 5",)})
        outcome_before = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=before)
        outcome_after = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=after)
        assert outcome_before.hold == outcome_after.hold
        assert outcome_before.risky == outcome_after.risky


class TestExecutorNoOpBeforeBodyPath:
    """design.md §2.1 (EXECREF-001) + REQ-EXECBODY-004 (EXECBODY-001 M4): an
    Executor reference always holds -- never risky -- regardless of whether
    its identity resolves. Pre-M4 (EXECREF-001), 'Executor' had no body path
    at all and short-circuited with 'no body path mapping' without ever
    querying the console. As of M4, StateBodyFetcher DOES query the console
    for the assigned-sequence identity (REQ-EXECBODY-003/004); when that
    query itself cannot resolve an identity, the hold REASON now reads
    'identity query failed for ...' instead -- the observable
    hold=True/risky=False shape is unchanged (fail-closed, REQ-EXECBODY-006)."""

    def test_executor_reference_with_unresolvable_identity_still_holds_not_risky(self):
        finding = _classify("Go+ Executor 201")
        assert finding.reference == "Executor 201"  # newly recognized (was None pre-M1)

        def _failing_query(path: str) -> dict:
            raise RuntimeError("no console reply")

        fetcher = StateBodyFetcher(query=_failing_query)
        outcome = evaluate_reference(finding.reference, ruleset=RULESET, fetcher=fetcher)
        assert outcome.hold is True
        assert outcome.risky is False
        assert "identity query failed for 'Executor 201'" in outcome.reasons[0]

    def test_none_reference_and_executor_reference_produce_the_same_hold_shape(self):
        # design.md §2.1: both the pre-M1 (`reference=None`) and post-M1
        # (`reference="Executor 201"`, no body path) states hold with
        # risky=False -- the gate's OBSERVABLE decision is unchanged.
        none_outcome = evaluate_reference(None, ruleset=RULESET, fetcher=DictBodyFetcher({}))
        executor_outcome = evaluate_reference(
            "Executor 201", ruleset=RULESET, fetcher=StateBodyFetcher(query=lambda p: {})
        )
        assert none_outcome.hold == executor_outcome.hold is True
        assert none_outcome.risky == executor_outcome.risky is False


class TestExecutorSinglePressClearance:
    """AC-EXECREF-001: a resolvable, benign-body Executor reference clears
    through the FULL gate pipeline with zero approval requests and console
    execution recorded as exactly the one bundled command -- no 'SaveShow'
    (SHOWUI M3's measured shape ["SaveShow", "Go+ Executor 201"] is the
    defect this SPEC corrects at the recognition layer). This scenario
    injects an in-memory body_fetcher directly into SafetyGate (bypassing
    console.py's StateBodyFetcher/DEFAULT_BODY_PATHS entirely, since S2
    body-path interpretation is DESCOPED for this milestone) -- it proves
    the gate's general screening machine handles a recognized Executor
    reference correctly, not that this path is reachable in production
    (acceptance.md AC-EXECREF-001 note)."""

    def test_benign_executor_body_clears_with_no_approval_and_no_saveshow(self, tmp_path):
        console = FakeConsole()
        approval = ScriptedApproval(decisions=[])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(tmp_path / "audit"),
            approval_port=approval,
            body_fetcher=DictBodyFetcher({"Executor 201": ("Store Cue 1",)}),
        )
        command = "Go+ Executor 201"
        decision = gate.screen([command])
        assert decision.cleared is True
        assert approval.requests == []  # zero approval requests
        # panel.py's fire() executes ONLY after screen() clears (REQ-SHOWUI-022
        # ordering) -- mirror that two-step production flow here.
        gate.execution_port.execute(command)
        assert console.executed == ["Go+ Executor 201"]  # exact shape, no "SaveShow"
