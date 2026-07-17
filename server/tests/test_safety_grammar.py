"""Grammar validator tests (M4 stage ① — REQ-MVP-011/012, AC-MVP-015 seed).

Validator depth (plan.md §A-6 decision, finalized in M4): STRUCTURAL parser —
single-line tokenization with quote balancing plus a verb-shape check on the
leading token. Deep enough to reject unparseable lines deterministically and to
hand verb/args tokens to the risk classifier; deliberately NOT a full MA3
grammar (grammar QUALITY is judged by the M6 error-rate measurement, while gate
SAFETY rides stage ② classification over these tokens). Over-blocking is
acceptable (safety asymmetry): a rejected line feeds the self-correction loop.
"""

from __future__ import annotations

from server.safety.grammar import ParsedCommand, validate


class TestAcceptedCommands:
    def test_simple_command_parses(self):
        result = validate("Store Cue 5")
        assert result.ok
        assert isinstance(result.parsed, ParsedCommand)
        assert result.parsed.verb == "Store"
        assert [t.text for t in result.parsed.args] == ["Cue", "5"]

    def test_quoted_name_is_a_single_quoted_token(self):
        result = validate("Store Cue 5 'My Look'")
        assert result.ok
        last = result.parsed.args[-1]
        assert last.text == "My Look"
        assert last.quoted is True

    def test_double_quoted_plugin_call_parses(self):
        result = validate('Plugin "CopilotResponder" "ping abc"')
        assert result.ok
        assert result.parsed.verb == "Plugin"
        assert [t.quoted for t in result.parsed.args] == [True, True]

    def test_option_token_parses(self):
        result = validate("Store Cue 5 /overwrite")
        assert result.ok
        assert result.parsed.args[-1].text == "/overwrite"

    def test_plus_minus_verbs_parse(self):
        assert validate("Go+ Executor 201").ok
        assert validate("Go- Executor 201").ok

    def test_range_command_parses(self):
        result = validate("Delete Sequence 1 Thru 10")
        assert result.ok
        assert [t.text for t in result.parsed.args] == ["Sequence", "1", "Thru", "10"]

    def test_leading_and_trailing_whitespace_tolerated(self):
        assert validate("  List  ").ok

    def test_korean_text_inside_quotes_is_allowed(self):
        result = validate("Label Group 3 '보컬'")
        assert result.ok
        assert result.parsed.args[-1].text == "보컬"


class TestRejectedCommands:
    def test_empty_line_rejected(self):
        result = validate("")
        assert not result.ok
        assert "empty" in result.reason

    def test_whitespace_only_rejected(self):
        assert not validate("   ").ok

    def test_multi_line_rejected(self):
        result = validate("Store Cue 5\nDelete Sequence 1")
        assert not result.ok
        assert "single line" in result.reason

    def test_carriage_return_rejected(self):
        assert not validate("Store Cue 5\rDelete").ok

    def test_control_character_rejected(self):
        result = validate("Store\x07 Cue 5")
        assert not result.ok
        assert "control" in result.reason

    def test_unbalanced_single_quote_rejected(self):
        result = validate("Store Cue 5 'unterminated")
        assert not result.ok
        assert "quote" in result.reason

    def test_unbalanced_double_quote_rejected(self):
        assert not validate('Plugin "Copilot').ok

    def test_quote_inside_unquoted_token_rejected(self):
        result = validate("Store Cue5'name'")
        assert not result.ok
        assert "quote" in result.reason

    def test_leading_option_token_rejected(self):
        # A command line must begin with a keyword verb.
        result = validate("/overwrite Store Cue 5")
        assert not result.ok
        assert "verb" in result.reason

    def test_leading_quoted_token_rejected(self):
        result = validate("'Delete' Sequence 5")
        assert not result.ok
        assert "verb" in result.reason

    def test_leading_number_rejected(self):
        # Bare numeric selection shorthand is rejected at this depth; the
        # model regenerates the keyword form via self-correction (FP-tolerant).
        result = validate("1 Thru 10 At 50")
        assert not result.ok
        assert "verb" in result.reason

    def test_rejection_reason_is_always_non_empty(self):
        for bad in ("", "  ", "'x", "5 At 50", "a\nb"):
            result = validate(bad)
            assert not result.ok
            assert result.reason


class TestMa2AssignmentRepairHint:
    """M6b-1r2 — the misplaced-quote rejection is CORRECT (MA2 `/Cmd='...'`
    assignment is invalid on MA3), but the bare reason gave the self-correction
    loop no way to repair (r1: 11 loop_limit turns). A rewrite hint is appended
    to the reason for MA2-assignment-shaped tokens. Rejection is UNCHANGED."""

    def test_ma2_slash_cmd_assignment_still_rejected(self):
        result = validate("Assign Macro 21.1 /Cmd='ClearAll'")
        assert not result.ok  # rejection behavior UNCHANGED
        assert "quote" in result.reason

    def test_ma2_slash_cmd_assignment_carries_a_rewrite_hint(self):
        result = validate("Assign Macro 21.1 /Cmd='ClearAll'")
        assert "MA2" in result.reason
        assert "Set" in result.reason and "Property" in result.reason

    def test_double_quoted_option_assignment_hinted(self):
        result = validate('Assign Macro 10.2 /Command="Group 3 At Full"')
        assert not result.ok
        assert "MA2" in result.reason

    def test_bare_property_equals_assignment_hinted(self):
        # X='...' shape without a leading slash (e.g. `Cmd='...'`).
        result = validate("Store Macro 21.1 Cmd='ClearAll'")
        assert not result.ok
        assert "MA2" in result.reason

    def test_plain_misplaced_quote_gets_no_ma2_hint(self):
        # A misplaced quote that is NOT assignment-shaped stays hint-free —
        # the hint must not fire on every misplaced-quote rejection.
        result = validate("Store Cue5'name'")
        assert not result.ok
        assert "quote" in result.reason
        assert "MA2" not in result.reason

    def test_valid_set_property_form_is_accepted(self):
        # The form the hint recommends must itself pass the validator.
        assert validate("Set Macro 21.1 Property 'Command' 'ClearAll'").ok
