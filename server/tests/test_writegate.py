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
from server.measurement.corpus import Scenario, load_corpus
from server.safety.classify import classify_command
from server.safety.expand import BodyUnavailable, evaluate_reference
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
    # `Pos` is a PROPERTY token and the entry is `Set` + `Fixture`: nothing in
    # the entry matches `Pos`, so this walks the IDENTICAL `_match_blacklist`
    # path as the plain form above (same verb, same unquoted `Fixture` arg). It
    # varies the VALUE shape, not the matching — kept because it is a shape
    # observed live, not because it reaches a distinct branch.
    ("Set Fixture 11 Pos -3.5", "duplicate match path; a live-observed value shape"),
    # The OBJECT abbreviates, not the verb: the parse is verb='Set',
    # args=['Fix','11','Posx',"'1.0'"], and `Fix` reaches `Fixture` through the
    # >=3-char-prefix branch of `_keyword_match` (`classify.py:62-65`). This is
    # the ONLY one of the nine forms that exercises that branch. The verb cannot
    # abbreviate at all: `Set` is already 3 characters, so any shortening falls
    # under the length floor (measured: `Se Fixture 11 Posx '1.0'` -> safe).
    ("Set Fix 11 Posx '1.0'", "the OBJECT abbreviates: `Fix` -> `Fixture`"),
    ("Set Fixture 1 Thru 18 Posz '5.0'", "range write — 18 fixtures in one line"),
    ("Set Fixture 11 Rotx '90.0'", "orientation: also a showfile mutation"),
    ("Set Fixture 11 Name 'Spot 11'", "non-coordinate patch write — over-match, on purpose"),
)

#: Every form whose classification must NOT move. The scope of this SPEC is the
#: whole point of this tuple: `Store` was descoped by user decision because it
#: collides with the measurement corpus, and with the DEPLOY tests that use
#: `Store Group 3` as their canonical SAFE fixture.
#:
#: The collision was re-measured with `_would_be_held` over `load_corpus()`. An
#: earlier "13 of 21 scenarios (7 of 10 representative task types)" was WRONG:
#: the 13 came from a broad `Store|Set|Assign|Copy` write-verb regex counting 13
#: COMMANDS, which was then restated as `Store`'s scenario count. Measured:
#:
#:   * entry `Store`       -> 10 of 21 scenarios, 5 of 10 task types
#:     (cue-store-1/2, group-create-1/2/3, macro-create-1/2, page-setup-1,
#:     preset-store-1/2)
#:   * entry `Store Group` ->  3 of 21 scenarios, 1 of 10 task types
#:     (group-create-1/2/3) — and `Store Group` is the literal actually named
#:
#: The "3 DEPLOY tests" half of that sentence is exactly right, but for
#: `Store Group`, not `Store`: `test_deploy_gate_e2e::
#: test_registered_non_destructive_plugin_passes_audited`, `test_deploy_pipeline::
#: test_non_destructive_plugin_registers_unflagged`, and `test_deploy_scan::
#: test_safe_commands_yield_no_findings`. The two halves were computed against
#: DIFFERENT entries — that is the mechanism by which the mismatch survived.
#:
#: The descope DECISION stands; only the magnitude was inflated. `group_create`
#: is 1 of the AC-MVP-001 10 representatives, so even 3/21 costs a whole task
#: type, and the DEPLOY fixture collision is independent of corpus size.
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
    # NOT because the property name is quoted. `_match_blacklist` needs the verb
    # to match `Set` AND some UNQUOTED arg to match `Fixture`; the args here are
    # `Selection`, `MAtricks`, `'PhaseFromX'`, `0`, and none of them spells
    # `Fixture`. Measured: dropping the quotes leaves it safe
    # (`Set Selection MAtricks PhaseFromX 0`), while `Set Selection MAtricks
    # Fixture 0` is risky with matched_entry='Set Fixture'. Quoting is not what
    # protects programmer-state commands from this widening.
    ("Set Selection MAtricks 'PhaseFromX' 0", "programmer state: no arg spells `Fixture`"),
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
        offenders = _corpus_offenders(load_corpus())
        assert offenders == [], (
            "a baseline corpus command is now risky — the corpus header's "
            f"'non-risky verbs only' invariant is broken by: {offenders}"
        )

    def test_the_corpus_collision_check_can_actually_fail(self):
        # Non-vacuity: the predicate must be able to say True, or the test above
        # would pass over an empty check.
        assert _would_be_held("Set Fixture 11 Posx '-3.5'") is True
        assert _would_be_held("Store Group 3") is False
        # The invoking branch counts too: `Go Macro 9` is not risky on its own
        # line, but the gate holds it because the body is unverifiable.
        assert _would_be_held("Go Macro 9") is True

    def test_the_corpus_plugin_collision_check_can_actually_fail(self):
        """Non-vacuity for the plugin half, which folds ZERO findings today.

        Both shipped corpus plugin bodies are inert (`return true` / `return
        {}`), so the scan half cannot demonstrate itself against the real
        corpus. Run the same fold over synthetic scenarios of each kind: a
        mis-wired comprehension — wrong `mock` field, wrong kind filter — comes
        back empty here instead of silently guarding nothing.
        """
        from server.measurement.corpus import MockScript

        write = "Set Fixture 11 Posx '5.0'"
        scenarios = (
            Scenario(
                id="probe-commands",
                task_type="group_create",
                instruction="probe",
                mock=MockScript(kind="commands", commands=(write,)),
            ),
            Scenario(
                id="probe-plugin",
                task_type="plugin_deploy",
                instruction="probe",
                mock=MockScript(
                    kind="plugin",
                    plugin_name="Probe",
                    plugin_source=f'local function main()\n    Cmd("{write}")\nend\nreturn main\n',
                ),
            ),
        )
        assert _corpus_offenders(scenarios) == [
            ("probe-commands", write),
            ("probe-plugin", write),
        ]


class _NoBodyAvailable:
    """The gate's own default fetcher (`gate.py:97-101`): nothing is verifiable."""

    def fetch_body(self, reference: str):
        raise BodyUnavailable("no body fetcher configured — reference bodies unverifiable")


def _would_be_held(command: str) -> bool:
    """True when the gate would HOLD this command line for human approval.

    Mirrors `gate.py::_stage_classify` (`:461-489`) instead of stopping at
    `classify_command(...).risky`, because the gate's hold is a strict SUPERSET
    of riskiness: an `invoking` verdict also holds when the referenced body
    cannot be verified. Stopping at `.risky` made `_would_be_held("Go Macro 9")`
    return False even though the gate raises a card for it — the very card shape
    SPATIAL-001 progress.md §E.2.20 records as having correctly fired — while
    the invariant this feeds is "clears the gate WITHOUT APPROVAL", not "is not
    risky". Inert against today's corpus (all 35 parseable lines are safe and
    none uses an invoking verb), which is exactly why the mismatch was invisible.

    The unavailable-body fetcher is not a pessimistic modelling choice: it is
    the gate's OWN default (`gate.py:152`), i.e. what an offline M6a run gets.
    The one hold branch NOT modelled is `self._unconfirmed` (`gate.py:484`) —
    per-session state rather than a property of a command line, so it is beyond
    the reach of a source-level check by construction.
    """
    grammar = validate(command)
    if not grammar.ok:
        return False
    verdict = classify_command(grammar.parsed, RULESET)
    if verdict.risky:
        return True
    if verdict.category == "invoking":
        return evaluate_reference(
            verdict.reference,
            ruleset=RULESET,
            fetcher=_NoBodyAvailable(),
            plugin_registry=None,
        ).hold
    return False


def _corpus_offenders(scenarios: tuple[Scenario, ...]) -> list[tuple[str, str]]:
    """Every corpus line that would NOT clear the gate without approval.

    Two halves, because a scenario's mock action has three kinds and only one of
    them is a command list (`Counter(s.mock.kind for s in load_corpus())` =
    `{'commands': 17, 'query': 2, 'plugin': 2}`):

    * `commands` — every line through `_would_be_held`;
    * `plugin` — the Lua body through the deploy-time scan, the SAME route
      `test_a_deployable_lua_source_carrying_a_patch_write_is_refused` proves a
      patch write now travels. EVERY finding counts, not just `blacklisted`:
      `scan.py::_classify_literal` also emits `invoking` and `unparseable`, and
      neither of those clears without a human either. Iterating only
      `mock.commands` skipped `plugin-deploy-1/2` outright, so a future revision
      that tripped a corpus plugin body would have left this guard green while
      M6a broke at runtime.

    `query` scenarios (`state-query-1/2`) carry neither commands nor a source —
    a read path gives the gate nothing to hold — so they contribute nothing.
    """
    offenders = [
        (scenario.id, command)
        for scenario in scenarios
        for command in scenario.mock.commands
        if _would_be_held(command)
    ]
    offenders += [
        (scenario.id, finding.command)
        for scenario in scenarios
        if scenario.mock.kind == "plugin"
        for finding in scan_lua_source(scenario.mock.plugin_source, RULESET).findings
    ]
    return offenders


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
