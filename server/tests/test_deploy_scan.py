"""Destructive-content scan tests (M7 — REQ-MVP-027, AC-MVP-010 ③ / AC-MVP-018 ①).

The scan extracts ``Cmd()`` string-literal arguments from submitted Lua source
and classifies each through the SAME closed-set semantics the gate uses
(grammar.validate + classify.classify_command — one matching semantics,
abbreviation-aware). It is a BEST-EFFORT reviewer-assist signal: dynamic
string assembly evades it, so the human review gate stays authoritative
(REQ-MVP-027 residual-risk framing). False positives are acceptable; the
destructive flag only ever errs in the safe direction.
"""

from __future__ import annotations

import pytest

from server.deploy.scan import BEST_EFFORT_CAVEAT, scan_lua_source
from server.safety.ruleset import load_ruleset


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()  # the real SSOT file — corpus follows revisions


def _scan(source, ruleset):
    return scan_lua_source(source, ruleset)


class TestBlacklistedFindings:
    def test_delete_cmd_is_destructive_with_line_number(self, ruleset):
        source = 'local function main()\n    Cmd("Delete Sequence 5")\nend\n'
        report = _scan(source, ruleset)
        assert report.destructive is True
        (finding,) = report.findings
        assert finding.kind == "blacklisted"
        assert finding.line == 2
        assert finding.command == "Delete Sequence 5"
        assert finding.matched_entry == "Delete"

    def test_abbreviated_keyword_matches(self, ruleset):
        # classify.py abbreviation-aware matching must be reused verbatim:
        # MA3 accepts `Del` for `Delete`.
        report = _scan('Cmd("Del 1")', ruleset)
        assert report.destructive is True
        assert report.findings[0].matched_entry == "Delete"

    def test_single_quoted_lua_literal(self, ruleset):
        report = _scan("Cmd('Off Everything')", ruleset)
        assert report.destructive is True
        assert report.findings[0].matched_entry == "Off Everything"

    def test_call_sugar_without_parentheses(self, ruleset):
        # Lua allows `Cmd"..."` and `Cmd[[...]]` (single-string call sugar).
        assert _scan('Cmd"Delete Group 2"', ruleset).destructive is True
        assert _scan("Cmd[[Delete Group 2]]", ruleset).destructive is True

    def test_every_ssot_entry_is_detected(self, ruleset):
        # Closed-set completeness: the scan must detect ALL current entries.
        for entry in ruleset.blacklist:
            report = _scan(f'Cmd("{entry} 1")', ruleset)
            assert report.destructive is True, entry

    def test_multiple_findings_report_each_line(self, ruleset):
        source = 'Cmd("Store Cue 1")\nCmd("Delete 1")\nCmd("Remove 2")\n'
        report = _scan(source, ruleset)
        assert report.destructive is True
        assert [(f.line, f.matched_entry) for f in report.findings] == [
            (2, "Delete"),
            (3, "Remove"),
        ]


class TestSafeAndNonDestructive:
    def test_safe_commands_yield_no_findings(self, ruleset):
        report = _scan('Cmd("Store Group 3")\nCmd("List")', ruleset)
        assert report.destructive is False
        assert report.findings == ()
        assert report.dynamic_calls == ()

    def test_quoted_object_name_never_matches(self, ruleset):
        # Same acceptance edge case as the gate: a blacklist keyword inside a
        # quoted object name is NOT a destructive command.
        report = _scan("Cmd(\"Store Cue 5 'Delete'\")", ruleset)
        assert report.destructive is False

    def test_source_without_cmd_calls(self, ruleset):
        report = _scan("local x = 1\nreturn x", ruleset)
        assert report.destructive is False
        assert report.findings == ()

    def test_identifier_suffix_cmd_is_not_matched(self, ruleset):
        # `MyCmd(...)` is a different function — not the MA3 global.
        report = _scan('MyCmd("Delete 1")\nlocal SendCmd = f\nSendCmd("Delete 2")', ruleset)
        assert report.findings == ()


class TestInvokingFindings:
    def test_indirect_invocation_is_a_reviewer_signal_not_a_flag(self, ruleset):
        # `Cmd("Go Macro 5")` cannot be verified at deploy time. It is
        # surfaced to the reviewer but does NOT drive the destructive flag
        # (the invocation-time expand-or-hold gate covers execution).
        report = _scan('Cmd("Go Macro 5")', ruleset)
        assert report.destructive is False
        (finding,) = report.findings
        assert finding.kind == "invoking"


class TestDynamicAssembly:
    def test_non_literal_argument_is_recorded_as_dynamic(self, ruleset):
        report = _scan("local c = build()\nCmd(c)", ruleset)
        assert report.destructive is False
        (call,) = report.dynamic_calls
        assert call.line == 2

    def test_concatenated_literal_prefix_is_still_classified(self, ruleset):
        # Best-effort hardening: `Cmd("Delete " .. target)` — the literal
        # prefix classifies as blacklisted AND the call is marked dynamic.
        report = _scan('Cmd("Delete " .. target)', ruleset)
        assert report.destructive is True
        assert report.findings[0].kind == "blacklisted"
        assert len(report.dynamic_calls) == 1

    def test_string_format_call_is_dynamic(self, ruleset):
        report = _scan('Cmd(string.format("Delete %d", n))', ruleset)
        assert report.destructive is False
        assert len(report.dynamic_calls) == 1


class TestUnparseableLiterals:
    def test_unparseable_literal_is_surfaced_not_flagged(self, ruleset):
        # A literal the gate grammar cannot parse is a reviewer-assist
        # warning; the human review stays the authoritative control.
        report = _scan('Cmd("\'unbalanced")', ruleset)
        assert report.destructive is False
        (finding,) = report.findings
        assert finding.kind == "unparseable"


class TestReportShape:
    def test_report_carries_the_best_effort_caveat(self, ruleset):
        report = _scan('Cmd("Delete 1")', ruleset)
        assert report.caveat == BEST_EFFORT_CAVEAT
        assert "best-effort" in report.caveat
