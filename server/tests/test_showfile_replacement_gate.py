"""Showfile-replacement approval gate (blacklist v3).

The hole this closes, stated as the observation that found it: the six v1
blacklist entries are object/system scoped and v2's is a patch write, so a
command that discards the console's ENTIRE live show classified ``safe`` and
would have executed with no approval card.

It is strictly worse than the v2 false negative it mirrors. A wrongly-loaded
show is **unrecoverable by this application**: ``server/safety/backup.py``
retains snapshots but there is no restore SEND path (``gate.py`` @MX:NOTE), and
``BACKUP_COMMAND`` is a bare ``SaveShow``, so N snapshots address exactly one
file. Approval is the only barrier that exists.

SCOPE — read this before trusting the gate: MA3's real show-reload keyword is
UNVERIFIED. These literals mirror ``SaveShow``, the one member of the family
this repository has actually executed. If the console's spelling differs, these
tests still pass and the hole is still open. They pin that the ENTRIES WORK,
never that the vocabulary is complete — that needs a live calibration.
"""

from __future__ import annotations

import pytest

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

RULESET = load_ruleset()


def _verdict(command: str):
    grammar = validate(command)
    assert grammar.ok, f"grammar rejected the probe itself: {command!r}"
    return classify_command(grammar.parsed, RULESET)


#: Spellings a model could plausibly emit for "replace the show". The bare
#: verbs are reached through ``_keyword_match``'s abbreviation branch
#: (command-token is a >=3-char prefix of the entry keyword), which is why one
#: entry covers its own family.
HELD = (
    ("LoadShow", "the single-token form, mirroring the verified SaveShow"),
    ("LoadShow 'Concert 2026'", "with a target name"),
    ("Load", "bare verb — abbreviation branch of the same entry"),
    ("Load 'Concert 2026'", "bare verb with a target"),
    ("NewShow", "discarding the show without loading another"),
    ("NewShow 'Untitled'", "with a name"),
    ("New", "bare verb"),
    ("loadshow", "case-insensitive"),
)

#: Classification that must NOT move to ``blacklisted``. Recorded because
#: over-matching is the designed direction here and an unbounded widening would
#: be paid for on every benign command instead.
#:
#: The property is "did not become blacklisted", NOT "is safe": ``Go`` is an
#: invoking verb and classifies ``invoking`` on its own merits (a stricter
#: category than safe, and nothing to do with v3). Asserting ``== "safe"`` here
#: would pin an unrelated contract and fail for the wrong reason.
UNCHANGED = (
    ("Store Group 3", "DEPLOY's canonical SAFE literal"),
    ("Store Cue 12", "measurement corpus representative"),
    ("Go Sequence 4 Cue 2", "playback, not replacement — invoking, never blacklisted"),
    ("Label Group 3 'Vocals'", "labelling"),
    ("SaveShow", "the BACKUP command itself must stay executable"),
)


class TestShowfileReplacementIsHeld:
    @pytest.mark.parametrize(("command", "why"), HELD, ids=[c for c, _ in HELD])
    def test_it_is_blacklisted_and_risky(self, command: str, why: str):
        verdict = _verdict(command)
        assert verdict.category == "blacklisted", why
        assert verdict.risky is True, why

    def test_the_matched_entry_is_named_so_the_card_can_say_why(self):
        # A card that cannot name the rule teaches the operator to click through.
        assert _verdict("LoadShow 'X'").matched_entry == "LoadShow"
        assert _verdict("NewShow").matched_entry == "NewShow"


class TestTheBackupPathStaysOpen:
    def test_saveshow_is_not_caught_by_the_new_entries(self):
        """The one command in this family production sends on a timer.

        ``_keyword_match`` runs command-token -> entry-keyword, so ``SaveShow``
        cannot match ``LoadShow``/``NewShow`` — but this is asserted rather than
        reasoned, because catching it would silently break the 10-minute
        periodic backup and the pre-risky backup, and a blocked backup FAILS the
        execution it was protecting (``backup.py`` fail-safe).
        """
        from server.safety.gate import BACKUP_COMMAND

        verdict = _verdict(BACKUP_COMMAND)
        assert verdict.category == "safe"
        assert verdict.risky is False


class TestNoCollateralWidening:
    @pytest.mark.parametrize(("command", "why"), UNCHANGED, ids=[c for c, _ in UNCHANGED])
    def test_classification_did_not_move(self, command: str, why: str):
        assert _verdict(command).category != "blacklisted", why


class TestNonVacuity:
    def test_the_probe_can_report_safe(self):
        """Without this, a broken ``_verdict`` returning 'blacklisted' for
        everything would make every assertion above pass."""
        assert _verdict("Store Group 3").category == "safe"

    def test_the_probe_can_report_blacklisted_from_a_pre_existing_entry(self):
        """And a v1 entry, so the check is not measuring only what v3 added."""
        assert _verdict("Delete Group 3").category == "blacklisted"

    def test_removing_the_entries_would_reopen_the_hole(self):
        """The assertion that gives the suite its meaning: these commands are
        held BECAUSE of the v3 entries, not by some other rule that happened to
        catch them. Without it, a future revision could delete both entries and
        this file would keep passing for the wrong reason."""
        import dataclasses

        without_v3 = dataclasses.replace(
            RULESET,
            blacklist=tuple(e for e in RULESET.blacklist if e not in ("LoadShow", "NewShow")),
        )
        for command in ("LoadShow", "Load", "NewShow", "New"):
            grammar = validate(command)
            assert grammar.ok
            assert classify_command(grammar.parsed, without_v3).category == "safe", (
                f"{command!r} is held by something other than the v3 entries — "
                "this suite is not measuring what it claims to"
            )
