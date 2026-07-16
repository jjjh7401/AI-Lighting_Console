"""Risk classification tests (M4 stage ② — REQ-MVP-013/026/036b).

Classification is command-SYNTAX based (acceptance edge case: a blacklist
keyword inside a quoted object NAME must not match). Keyword matching is
abbreviation-aware (case-insensitive exact OR a >=3-char prefix of the keyword;
options abbreviate from 1 char) — over-matching is acceptable (FP resolved by
human approval), under-matching is the FN direction the design forbids.
"""

from __future__ import annotations

import pytest

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

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
            ("Go+ Executor 201", None),  # no recognized reference type -> unverifiable
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
