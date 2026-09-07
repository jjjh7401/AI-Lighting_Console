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
    # `Store Group 3` WAS here, ratified "descoped: DEPLOY's canonical SAFE_SOURCE
    # literal". SPEC-COPILOT-CLASSIFYGAP-001 (card t299, Phase 1) removed that one
    # line when ruleset v5 took `Store Group`. The argument for THAT line
    # specifically, not for the tuple: its ratification reason was never a safety
    # claim — it recorded that three DEPLOY tests happened to use the command as
    # their "safe example" fixture. A fixture-convenience reason cannot outweigh a
    # measured false negative, and the 2026-09-07 browser observation is exactly
    # that: 28 commands out to the desk, 25 executed, `approved` entries in the
    # audit log = 0, with `Store Group <n>` among them. The three DEPLOY tests were
    # moved to a non-`Store` literal (`Group 4`, selection) rather than re-pointed
    # at another `Store` object, so the same collision cannot recur on the next
    # revision.
    #
    # `Store Preset 4.1` WAS here, ratified "descoped: measurement corpus
    # representative". SPEC-COPILOT-UNREQ-001 (card t86) removed that one line
    # when ruleset v4 took `Store Preset`, on a measured false-negative
    # observation (the LXSEQ-003 M4 accident) — see blacklist.yaml's v4 header.
    #
    # [READ THIS BEFORE REMOVING ANOTHER LINE] Every entry that remains below is
    # STILL RATIFIED. Taking one line out does not release the rest, and the
    # reasons are not interchangeable: the `Store *` / `Assign` / `Copy` entries
    # are descoped on COST (2026-08-05 user decision, re-measured and reinforced
    # by t86 — entry `Store` breaks 67 of 10183 and puts an approval card on one
    # ordinary conversational turn), while `Label Group` is descoped on a
    # SEMANTIC judgement ("labelling is not a patch write"). A cost measurement
    # can update the first group; it cannot update the second. Removing a line
    # here without its own argument reopens a hole that someone closed on purpose.
    #
    # `Store Timecode` never appeared in this tuple, so v5 removed nothing for it.
    # `Store Sequence` never appeared here either, so v6 removed nothing for it.
    #
    # `Store Cue 12` WAS here, ratified "descoped: measurement corpus
    # representative". SPEC-COPILOT-CLASSIFYGAP-001 (card t299, Phase 3) removed
    # that one line when ruleset v7 took `Store Cue`. The argument for THAT line
    # specifically, not for the tuple: its ratification reason was never a safety
    # claim either — it recorded that the measurement corpus happens to use the
    # command as a `cue_store` representative. Two independent observations
    # outweigh that convenience, and BOTH were measured rather than argued:
    #   ① `write_reason.py::_STORE_CUE` (card t323) already reads this exact line
    #      as a showfile write when a caller declares a bundle, so the seal layer
    #      and the classification layer disagreed about the same command;
    #   ② the model's `run_commands` path emits this short form directly, and
    #      `Store Sequence` (v6) does not reach it — measured in
    #      `reports/classifygap-t299-p3/08_entry_order.txt`.
    # The corpus scenarios it collides with are ratified below rather than
    # re-pointed at another `Store` object, so this collision cannot recur.
    #
    # `Assign Sequence 4 Page 1.201` WAS here, ratified bare "descoped".
    # SPEC-COPILOT-CLASSIFYGAP-001 (card t325, Phase 4) removed that one line when
    # ruleset v8 took `Assign Sequence`. The argument for THAT line specifically:
    # its ratification reason was the thinnest in this tuple — a bare "descoped"
    # with no property named, inherited from the 2026-08-05 cost decision that was
    # about the `Store` VERB, not about this object. Two measured observations
    # replace it:
    #   ① `write_reason.py::_ASSIGN_EXECUTOR` (card t323) already reads
    #      `Assign Sequence <n> At Executor <m>` as a showfile write when a caller
    #      declares a bundle, so the seal layer and the classification layer
    #      disagreed about the same command;
    #   ② `test_writegate_session_sites.py::SEAL_DEFENCE` measured this object as
    #      the ONLY thing standing between `_offer_fx_executor_assignment` /
    #      `_setlist_mode` and an unapproved console write — seal-only 2 of 11
    #      (`reports/classifygap-t299-p3/07_seal_defence_p3.txt`).
    #
    # `Copy Page 1 At Page 4` STAYS. v8 takes `Copy Sequence`, an OBJECT, so the
    # `Page` form is untouched — measured, not assumed:
    # `reports/classifygap-t325-p4/05_probe_after.txt` [A-4] shows it still
    # `matched_entry=None`. That is the whole point of scoping to the object.
    ("Store Page 3", "descoped: measurement corpus representative"),
    ("Store Macro 21", "descoped: measurement corpus representative"),
    ("Copy Page 1 At Page 4", "descoped: v8 took `Copy Sequence`, not the `Copy` verb"),
    ("Assign Preset 4.1 At Executor 101", "descoped: v8 took `Assign Sequence`, not `Assign`"),
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

#: Corpus baseline commands the gate HOLDS at ruleset v4, ratified by
#: SPEC-COPILOT-UNREQ-001. The corpus header's "non-risky verbs only" invariant
#: is TRUE for every scenario except these two, and that narrowing is deliberate:
#: v4 blacklists `Store Preset` because the LXSEQ-003 M4 accident sent exactly
#: that command with no approval card.
#:
#: CONSEQUENCE, stated because it is easy to miss: a live M6a run over the corpus
#: now raises an approval card on these two scenarios. They are no longer
#: unattended-runnable. Order matches `_corpus_offenders` iteration (scenario
#: order in corpus.yaml, command order within a scenario).
#: NARROWED AGAIN at ruleset v5 (SPEC-COPILOT-CLASSIFYGAP-001, card t299, Phase 1):
#: the three `group_create` scenarios join, because v5 blacklists `Store Group` on
#: the 2026-09-07 browser observation (28 commands out, 25 executed, 0 `approved`
#: audit entries, `Store Group <n>` among them). Same shape as the v4 narrowing,
#: same consequence: those three scenarios now raise a card, so a live M6a run over
#: them is no longer unattended-runnable. That cost is accepted rather than avoided —
#: `group_create` is 1 of the AC-MVP-001 ten representative task types, and losing
#: unattended operation on it is the price of closing a measured false negative.
#:
#: `Store Timecode` adds nothing here: the corpus carries no timecode line at all
#: (`grep -c 'Store Timecode' server/measurement/corpus.yaml` = 0).
#: `Store Sequence` (v6) added nothing either — the corpus carries no
#: `Store Sequence` line (`grep -c 'Store Sequence' server/measurement/corpus.yaml` = 0).
#:
#: NARROWED A THIRD TIME at ruleset v7 (same SPEC, card t299, Phase 3): the two
#: `cue_store` scenarios join, because v7 blacklists `Store Cue`. Same shape, same
#: consequence — `cue_store` is another of the AC-MVP-001 ten representative task
#: types, so a live M6a run over those two scenarios is no longer
#: unattended-runnable either. Running total: 3 of the 10 representative task
#: types (`group_create`, `preset_store`, `cue_store`) now raise a card. That is
#: the accumulating price of closing the four measured false negatives, and it is
#: recorded here rather than left for someone to rediscover mid-run.
#:
#: NARROWED A FOURTH TIME at ruleset v8 (same SPEC, card t325, Phase 4): the two
#: `sequence_assign` scenarios join, because v8 blacklists `Assign Sequence`. Same
#: shape, same consequence, and the running total is now **4 of the 10**
#: representative task types (`group_create`, `preset_store`, `cue_store`,
#: `sequence_assign`).
#:
#: 이 회차의 차이 하나는 기록해 둘 값이 있다. v5·v7 이 합류시킨 시나리오들은 봉합
#: 층(`write_reason.py`)이 이미 「쇼파일 쓰기」로 읽던 줄이라 `_DECLARED_WRITE_SCENARIOS`
#: 에도 들어 있었다. 이 둘은 다르다 — `Assign Sequence <n> Page <p>` 는
#: `_ASSIGN_EXECUTOR`(`At Executor` 형태만 읽는다)에 안 닿아서 봉합 층이 못 봤고,
#: 그래서 v8 이전에는 **어느 층도** 이 두 줄을 잡지 않았다. 실측:
#: `reports/classifygap-t325-p4/09_seal_layer_vs_classify.txt`.
#:
#: `Copy Sequence` 는 여기에 아무것도 더하지 않는다. 그 이유가 「`Copy` 줄이 없어서」가
#: **아니라는** 점이 이 리비전의 논거를 그대로 보여 준다 — 코퍼스에는 `Copy` 줄이 하나
#: 있고(`page-setup-2` 의 `Copy Page 1 At Page 4`, corpus.yaml:140), 그것이 v8 뒤에도
#: 안 걸린다. 실측: `matched_entry=None`
#: (`reports/classifygap-t325-p4/05_probe_after.txt` [A-4]).
#: 동사(`Copy`)를 넣었다면 이 시나리오도 무인 운전 밖으로 나갔을 것이다. 오브젝트로
#: 좁힌 대가가 여기서 정확히 한 시나리오만큼 회수된다.
#:
#: Order matches `_corpus_offenders` iteration (scenario order in corpus.yaml,
#: command order within a scenario) — group_create precedes preset_store, which
#: precedes cue_store, which precedes sequence_assign there.
RATIFIED_CORPUS_COLLISIONS = (
    ("group-create-1", "Store Group 3"),
    ("group-create-2", "Store Group 8"),
    ("group-create-3", "Store Group 11"),
    ("preset-store-1", "Store Preset 4.1"),
    ("preset-store-2", "Store Preset 4.7"),
    ("cue-store-1", "Store Cue 12"),
    ("cue-store-2", "Store Cue 5 Fade 3"),
    # 갱신 근거 (t325 Phase 4, ruleset v8): `Assign Sequence` 가 폐집합에 들어오면서
    # `sequence_assign` 시나리오 둘이 합류한다. v5·v7 의 narrowing 과 같은 모양이고
    # 같은 대가다 — 이 둘도 무인 운전 밖으로 나간다. 누적 4 / 10 대표 과제 유형
    # (`group_create` · `preset_store` · `cue_store` · `sequence_assign`).
    #
    # **이 두 줄에는 봉합이 없다 — 분류 층이 유일한 방어다.** 실측:
    # `showfile_write_risk(["Assign Sequence 4 Page 1.201"], kind="model_run_commands")`
    # -> `None` (`reports/classifygap-t325-p4/09_seal_layer_vs_classify.txt`).
    # `write_reason.py::_ASSIGN_EXECUTOR` 는 `At Executor` 형태만 읽고 `Page` 형태는
    # 못 읽기 때문이다. 그래서 이 두 시나리오는 `_DECLARED_WRITE_SCENARIOS` 에
    # 없었고, v8 이 넣기 전에는 아무 층도 잡지 않았다 — 카드가 새로 뜨는 것이 아니라
    # **처음 뜨는** 자리다.
    ("sequence-assign-1", "Assign Sequence 4 Page 1.201"),
    ("sequence-assign-2", "Assign Sequence 7 Page 2.203"),
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

        The v4 revision (SPEC-COPILOT-UNREQ-001) DID add a Store entry, and this
        test caught it — working exactly as the paragraph above promised. The two
        scenarios it names are recorded below as a RATIFIED exception rather than
        asserted away, so the tripwire still bites on any collision that was not
        argued for. The corpus header's own invariant is now narrower than it
        reads: see the note this revision added to corpus.yaml.
        """
        offenders = _corpus_offenders(load_corpus())
        assert offenders == list(RATIFIED_CORPUS_COLLISIONS), (
            "the set of corpus commands held by the gate is not the ratified one "
            f"— expected {list(RATIFIED_CORPUS_COLLISIONS)}, got {offenders}. A "
            "NEW collision means a ruleset revision broke a baseline scenario "
            "without arguing for it; a MISSING one means a ratified collision "
            "silently disappeared."
        )

    def test_the_corpus_collision_check_can_actually_fail(self):
        # Non-vacuity: the predicate must be able to say True, or the test above
        # would pass over an empty check.
        assert _would_be_held("Set Fixture 11 Posx '-3.5'") is True
        # t299 (v5): the False arm was `Store Group 3` until v5 blacklisted it.
        # Re-pointed at `Store Page 3`, which `UNCHANGED_SAFE` above still ratifies
        # as descoped — the arm needs a command the ruleset genuinely lets through,
        # and asserting False on a now-blacklisted literal would have inverted the
        # non-vacuity check into a false claim.
        assert _would_be_held("Store Page 3") is False
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
        #
        # t299 (v5): the literal was `Store Group 3` until v5 blacklisted it —
        # it must be a command the ruleset genuinely passes, or this non-vacuity
        # arm asserts something false. Re-pointed at `Group 4` (selection, not a
        # write) rather than another `Store` object, so a later Store revision
        # cannot collide with this fixture again. Same change in
        # `test_deploy_pipeline.SAFE_SOURCE`, which the two DEPLOY suites import.
        source = 'local function main()\n    Cmd("Group 4")\nend\nreturn main\n'
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
