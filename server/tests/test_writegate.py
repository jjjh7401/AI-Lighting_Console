"""Write-path integrity — SPEC-COPILOT-WRITEGATE-001 (AC-WRITEGATE-001~006).

A fixture's patch row is showfile state. Before the `blacklist.yaml` v1 -> v2
revision, `Set Fixture <fid> Pos* '<v>'` classified "safe", so the gate cleared
it with no approval card and no showfile snapshot — and the cost was OBSERVED,
not hypothesised: SPATIAL-001 progress.md §E.2.20 recorded 54 unrequested
coordinate writes reaching the console with no human in between, while the same
turn's `Go+ Page 1.202` correctly raised a card. The gate was healthy; only
writes slipped the net.

Three properties are load-bearing here, and each is asserted for a REASON that
a passing test alone would not explain:

* **Over-matching is the designed direction.** `classify.py`'s module docstring
  fixes the asymmetry: over-matching is resolved by human approval, while
  under-matching is a safety false negative. So the closed-set entry names the
  OBJECT (`Set Fixture`), not the property. Enumerating `Posx`/`Posy`/`Posz`/
  `Rotx`/... would be the open-ended list `blacklist.yaml`'s own header
  prohibits, and it would leave "what about the next property?" open forever.

* **The dangerous forms are not the pretty one.** Of five write forms probed
  live on onPC 2.4.2, THREE answered `ok:true` while storing the wrong value or
  nothing at all (`tools.py` ARRANGE_COMMAND_TEMPLATE comment). A rule that only
  caught the well-formed single-quoted line would miss exactly the forms a model
  is most likely to hand-write.

* **The category value is deliberately an EXISTING one.** `expand.py` and
  `server/deploy/scan.py` both branch on `category == "blacklisted"` / `"invoking"`
  and fall through everything else. A NEW category value would have failed OPEN
  in both — a macro body and a deployable Lua plugin could each still smuggle a
  patch write past the gate. Reusing "blacklisted" covers both paths with ZERO
  modification to either file, and `TestIndirectRoutes` pins that.
"""

from __future__ import annotations

import pytest

from server.deploy.scan import scan_lua_source
from server.safety.classify import classify_command
from server.safety.expand import evaluate_reference
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

RULESET = load_ruleset()

#: The entry this SPEC added. Named once so a rename shows up as one diff.
ENTRY = "Set Fixture"

#: Every write form that must be HELD. Each is a real shape, not a permutation
#: for its own sake — the comment says which live observation put it here.
HELD_FORMS = (
    ("Set Fixture 11 Posx '-3.5'", "the correct form the assembler emits"),
    ("Set Fixture 11 Posx -3.5", "live: answered OK and stored 3.5 — sign dropped"),
    ("Set Fixture 11 Posx - 3.5", "live: answered OK and stored nothing — silent no-op"),
    ("Set Fixture 11 Posx 0-3.5", "live: answered OK and stored 0.0 — wrong value"),
    ("Set Fixture 11 Pos -3.5", "3-char abbreviation; MA3 abbreviates keywords"),
    ("Set Fix 11 Posx '1.0'", "the VERB abbreviates too"),
    ("Set Fixture 1 Thru 18 Posz '5.0'", "range write — 18 fixtures in one line"),
    ("Set Fixture 11 Rotx '90.0'", "orientation: also a showfile mutation"),
    ("Set Fixture 11 Name 'Spot 11'", "non-coordinate patch write — over-match, on purpose"),
)

#: Every form whose classification must NOT move. The scope of this SPEC is the
#: whole point of this tuple: `Store` was descoped by user decision because it
#: collides with the measurement corpus in 13 of 21 scenarios, and with the
#: DEPLOY tests that use `Store Group 3` as their canonical SAFE fixture.
UNCHANGED_SAFE = (
    ("Store Group 3", "descoped: DEPLOY's canonical SAFE_SOURCE literal"),
    ("Store Preset 4.1", "descoped: measurement corpus representative"),
    ("Store Cue 12", "descoped: measurement corpus representative"),
    ("Store Page 3", "descoped: measurement corpus representative"),
    ("Store Macro 21", "descoped: measurement corpus representative"),
    ("Assign Sequence 4 Page 1.201", "descoped"),
    ("Copy Page 1 At Page 4", "descoped"),
    ("Label Group 3 'Vocals'", "labelling is not a patch write"),
    ("Fixture 1 Thru 12", "selection, not a write"),
    ("Group 4", "selection, not a write"),
    ("At 100", "programmer state, not a write"),
    ("Set Selection MAtricks 'PhaseFromX' 0", "programmer state: the property name is QUOTED"),
    ("Set Macro 1.1 Property 'Command' 'Group 11 At 0'", "macro authoring with a safe body"),
)


def _classify(command: str):
    grammar = validate(command)
    assert grammar.ok, f"fixture is not a valid command line: {command!r} — {grammar.reason}"
    return classify_command(grammar.parsed, RULESET)


class TestPatchWritesAreRisky:
    """AC-WRITEGATE-001 — every patch-write form is held."""

    @pytest.mark.parametrize(("command", "why"), HELD_FORMS)
    def test_the_form_is_classified_risky(self, command, why):
        finding = _classify(command)
        assert finding.risky is True, why
        assert finding.matched_entry == ENTRY

    def test_the_range_form_is_not_flagged_unspecified_target(self):
        """`Thru` between two numbers is a BOUNDED range, not an open one.

        REQ-MVP-036b's unspecified-target warning is for `Delete` with no
        target. A bounded `1 Thru 18` must not borrow that warning, or the
        operator learns to ignore it.
        """
        finding = _classify("Set Fixture 1 Thru 18 Posz '5.0'")
        assert finding.risky is True
        assert finding.unspecified_target is False

    def test_the_card_states_a_reason(self):
        finding = _classify("Set Fixture 11 Posx '-3.5'")
        assert finding.reasons, "a risk verdict with no reason is a blank approval prompt"
        assert ENTRY in " ".join(finding.reasons)


class TestScopeIsHeldExactly:
    """AC-WRITEGATE-005 / 006 — the widening reaches nothing else."""

    @pytest.mark.parametrize(("command", "why"), UNCHANGED_SAFE)
    def test_the_form_stays_non_risky(self, command, why):
        finding = _classify(command)
        assert finding.risky is False, why

    def test_the_measurement_corpus_cannot_collide_with_this_entry(self):
        """AC-WRITEGATE-006, checked at the SOURCE rather than by running M6a.

        `corpus.yaml`'s header declares its 21 baseline scenarios "clear the
        safety gate without approval (non-risky verbs only)". This preserves that
        invariant by SCOPE, not by luck — and asserts it over the PARSED corpus
        rather than the YAML text, so it keeps holding as scenarios are added. If
        a future revision adds a `Store` entry, THIS is the test that stops it,
        naming the exact scenarios it would break.
        """
        from server.measurement.corpus import load_corpus

        offenders = [
            (scenario.id, command)
            for scenario in load_corpus()
            for command in scenario.mock.commands
            if _would_be_held(command)
        ]
        assert offenders == [], (
            "a baseline corpus command is now risky — the corpus header's "
            f"'non-risky verbs only' invariant is broken by: {offenders}"
        )

    def test_the_corpus_collision_check_can_actually_fail(self):
        # Non-vacuity: the predicate must be able to say True, or the test above
        # would pass over an empty check.
        assert _would_be_held("Set Fixture 11 Posx '-3.5'") is True
        assert _would_be_held("Store Group 3") is False


def _would_be_held(command: str) -> bool:
    """True when a corpus mock command line would be held by the gate."""
    grammar = validate(command)
    if not grammar.ok:
        return False
    return classify_command(grammar.parsed, RULESET).risky


class TestIndirectRoutes:
    """AC-WRITEGATE-004 — the two routes that would have failed OPEN.

    Both consumers below branch on `category == "blacklisted"`. Neither file was
    touched by this SPEC; these tests assert that reusing the existing category
    value is what buys that, so a later "let's give it its own category" change
    turns them RED instead of quietly reopening two bypasses.
    """

    def test_a_macro_body_carrying_a_patch_write_is_held(self):
        class Fetcher:
            def fetch_body(self, reference):
                return ("Set Fixture 11 Posx '5.0'",)

        result = evaluate_reference(
            "Macro 9", ruleset=RULESET, fetcher=Fetcher(), plugin_registry=None
        )
        assert result.hold is True
        assert any("blacklisted" in reason for reason in result.reasons)

    def test_a_deployable_lua_source_carrying_a_patch_write_is_refused(self):
        source = "local function main()\n    Cmd(\"Set Fixture 11 Posx '5.0'\")\nend\nreturn main\n"
        report = scan_lua_source(source, RULESET)
        assert report.destructive is True
        assert [f.kind for f in report.findings] == ["blacklisted"]
        assert report.findings[0].matched_entry == ENTRY

    def test_the_deploy_scan_still_passes_a_genuinely_safe_source(self):
        # Non-vacuity: DEPLOY's canonical SAFE_SOURCE literal. If this went
        # destructive, the entry would have been scoped too widely.
        source = 'local function main()\n    Cmd("Store Group 3")\nend\nreturn main\n'
        report = scan_lua_source(source, RULESET)
        assert report.destructive is False
        assert list(report.findings) == []

    def test_a_patch_write_smuggled_in_a_quoted_property_value_is_held(self):
        """The M6c-2 Finding 1 bypass shape, re-checked for this entry.

        `classify_command` recurses into a `Property 'Command' '<value>'`
        assignment, so a patch write persisted as macro TEXT is classified as if
        it had been sent bare. The outer verb never has to look dangerous.
        """
        finding = _classify("Set Macro 1.1 Property 'Command' \"Set Fixture 11 Posx '5.0'\"")
        assert finding.risky is True
        assert finding.matched_entry == ENTRY


class TestClassificationVocabularyIsUnchanged:
    """The design constraint behind AC-WRITEGATE-004, stated as an invariant."""

    def test_no_new_category_value_was_introduced(self):
        categories = {_classify(command).category for command, _why in HELD_FORMS + UNCHANGED_SAFE}
        assert categories <= {"safe", "blacklisted", "invoking"}, (
            "a new RiskFinding.category value fails OPEN in expand.py and "
            "server/deploy/scan.py — both branch only on 'blacklisted'/'invoking'"
        )

    def test_a_patch_write_reports_the_existing_blacklisted_category(self):
        assert _classify("Set Fixture 11 Posx '-3.5'").category == "blacklisted"
