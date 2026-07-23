"""Safety FN corpora (M4 — AC-MVP-004 / AC-MVP-017 / AC-MVP-024).

Safety asymmetry: false positives (over-holding) are acceptable and resolved
by human approval; false negatives — a blacklisted command reaching the
console without approval — must be ZERO across every corpus case.

The corpora iterate the SSOT config file's CLOSED SETS dynamically
(never hardcoded lists), so a version-bumped config revision auto-extends the
corpus. Deterministic: commands are injected into the gate directly (no model),
bodies come from an in-memory fetcher (no OSC anywhere in screening), and the
console is a recording fake — "zero OSC sends pre-approval" is asserted as
``console.executed == []`` under a deny-all approval port.
"""

from __future__ import annotations

import pytest

from server.safety.audit import AuditLog
from server.safety.classify import RECOGNIZED_REFERENCE_TYPES
from server.safety.gate import SafetyGate
from server.safety.ruleset import load_ruleset

from .test_safety_expand import DictBodyFetcher
from .test_safety_gate import FakeConsole, ScriptedApproval

RULESET = load_ruleset()


def _blacklist_variants(entry: str) -> list[tuple[str, list[str], dict]]:
    """Build >=3 expression variants for one SSOT blacklist entry.

    Variants per AC-MVP-004: ① direct command ② inside a bundle of safe
    commands ③ indirect macro invocation whose body contains the command.
    """
    direct = f"{entry} Sequence 5"
    return [
        ("direct", [direct], {}),
        ("bundle", ["Store Cue 1", direct, "Store Cue 2"], {}),
        ("indirect-macro", ["Go Macro 9"], {"Macro 9": (direct,)}),
    ]


def _gate(tmp_path, bodies: dict, approval) -> tuple[SafetyGate, FakeConsole]:
    console = FakeConsole()
    gate = SafetyGate(
        console=console,
        audit=AuditLog(tmp_path / "audit"),
        approval_port=approval,
        body_fetcher=DictBodyFetcher(bodies),
    )
    return gate, console


class TestBlacklistFnCorpus:
    """AC-MVP-004: every SSOT blacklist entry x >=3 variants -> zero unapproved sends."""

    @pytest.mark.parametrize("entry", load_ruleset().blacklist)
    @pytest.mark.parametrize("variant_index", [0, 1, 2])
    def test_no_send_without_approval(self, tmp_path, entry, variant_index):
        name, bundle, bodies = _blacklist_variants(entry)[variant_index]
        approval = ScriptedApproval(decisions=[False])
        gate, console = _gate(tmp_path, bodies, approval)
        decision = gate.screen(bundle)
        assert decision.cleared is False, f"{entry} [{name}] must not clear unapproved"
        assert console.executed == [], f"{entry} [{name}] sent without approval (FN!)"
        # the risky command actually reached the approval stage (held, not lost)
        assert len(approval.requests) == 1, f"{entry} [{name}] was not held for approval"

    def test_corpus_size_meets_the_minimum(self):
        # >=6 entries x 3 variants = >=18 cases (AC-MVP-004 floor).
        total = sum(len(_blacklist_variants(e)) for e in RULESET.blacklist)
        assert total >= 18

    @pytest.mark.parametrize("entry", load_ruleset().blacklist)
    def test_execution_port_also_refuses_unapproved_blacklisted_commands(self, tmp_path, entry):
        # Defense in depth: even a direct port call cannot bypass screening.
        gate, console = _gate(tmp_path, {}, ScriptedApproval(decisions=[False]))
        command = f"{entry} Sequence 5"
        gate.screen([command])
        result = gate.execution_port.execute(command)
        assert result.ok is False
        assert console.executed == []


def _invoking_commands() -> list[str]:
    """One gate-level command per SSOT invoking-verb entry, crossed with the
    RECOGNIZED_REFERENCE_TYPES closed set (REQ-EXECREF-011) -- the reference-
    type axis is dynamic (imported from classify.py), so a future revision of
    that closed set auto-extends this corpus with zero edits here. The bare
    object forms (Macro <n> / Plugin <n>) stay a separate, type-fixed axis:
    they are matched by ``_bare_form_reference`` against ``bare_object_forms``
    in blacklist.yaml, not against RECOGNIZED_REFERENCE_TYPES.
    """
    commands = [
        f"{verb} {type_word} 9"
        for verb in RULESET.invoking_verbs
        for type_word in RECOGNIZED_REFERENCE_TYPES
    ]
    for form in RULESET.bare_object_forms:
        commands.append(form.replace("<n>", "9"))
    return commands


# Base scenario bodies, keyed by the legacy "Macro 9" / "Plugin 9" entry
# points. ``_expand_scenario_bodies`` broadcasts each scenario's entry-point
# content onto EVERY recognized reference type's "<Type> 9" key below, so a
# verb-invoking command targeting any recognized type -- including one added
# to classify.py after this corpus was written -- hits equivalent scenario
# content. Deeper chain steps (Macro 10/11/12) are internal continuations
# reached via nested "Go Macro N" body lines and are left untouched; they are
# type-independent because expand.py recurses on whatever reference the body
# line itself carries, not on the entry command's reference type.
_SCENARIOS = {
    "risky-body": {"Macro 9": ("Delete Sequence 5",), "Plugin 9": ("Delete Sequence 5",)},
    "unverifiable-body": {},
    "depth-exceeded": {
        "Macro 9": ("Go Macro 10",),
        "Plugin 9": ("Go Macro 10",),
        "Macro 10": ("Go Macro 11",),
        "Macro 11": ("Go Macro 12",),
        "Macro 12": ("Store Cue 1",),
    },
    "cycle": {
        "Macro 9": ("Go Macro 10",),
        "Plugin 9": ("Go Macro 10",),
        "Macro 10": ("Go Macro 9",),
    },
}


def _expand_scenario_bodies() -> dict[str, dict[str, tuple[str, ...]]]:
    """Broadcast each scenario's "Macro 9" entry-point content across every
    RECOGNIZED_REFERENCE_TYPES "<Type> 9" key, so the scenario's hold/risky
    semantics apply no matter which recognized type an under-test command
    targets. A scenario with NO entry-point key (e.g. "unverifiable-body")
    stays untouched for every type -- broadcasting an empty-tuple placeholder
    would silently turn "body unavailable" into "body present but empty",
    which is NOT the same hold path.
    """
    expanded: dict[str, dict[str, tuple[str, ...]]] = {}
    for scenario, bodies in _SCENARIOS.items():
        if "Macro 9" not in bodies:
            expanded[scenario] = dict(bodies)
            continue
        entry_content = bodies["Macro 9"]
        broadcast = {f"{type_word} 9": entry_content for type_word in RECOGNIZED_REFERENCE_TYPES}
        expanded[scenario] = {**bodies, **broadcast}
    return expanded


_EXPANDED_SCENARIOS = _expand_scenario_bodies()


class TestInvokingVerbFnCorpus:
    """AC-MVP-017 / AC-EXECREF-006: ALL invoking_verbs entries x ALL recognized
    reference types x 4 hold scenarios -> zero sends. The reference-type axis
    dynamically tracks classify.RECOGNIZED_REFERENCE_TYPES (REQ-EXECREF-011)."""

    @pytest.mark.parametrize("command", _invoking_commands())
    @pytest.mark.parametrize("scenario", sorted(_SCENARIOS))
    def test_no_send_pre_approval_in_every_scenario(self, tmp_path, command, scenario):
        approval = ScriptedApproval(decisions=[False])
        gate, console = _gate(tmp_path, _EXPANDED_SCENARIOS[scenario], approval)
        decision = gate.screen([command])
        assert decision.cleared is False, f"{command} [{scenario}] must hold"
        assert console.executed == [], f"{command} [{scenario}] sent pre-approval (FN!)"
        assert len(approval.requests) == 1, f"{command} [{scenario}] not held for approval"

    def test_corpus_iterates_the_full_closed_set(self):
        # verbs x recognized reference types, plus bare forms -- both closed
        # sets read from their respective SSOT sources.
        assert len(_invoking_commands()) == (
            len(RULESET.invoking_verbs) * len(RECOGNIZED_REFERENCE_TYPES)
            + len(RULESET.bare_object_forms)
        )
        assert len(_invoking_commands()) >= 12

    def test_reference_type_axis_matches_the_recognized_closed_set(self):
        # AC-EXECREF-006 binary evidence: the corpus's reference-type axis IS
        # classify.RECOGNIZED_REFERENCE_TYPES, not a hardcoded literal set --
        # every recognized type appears in at least one generated command.
        commands = _invoking_commands()
        for type_word in RECOGNIZED_REFERENCE_TYPES:
            assert any(f" {type_word} 9" in cmd for cmd in commands), (
                f"{type_word} missing from the dynamically-generated corpus"
            )

    def test_clean_expandable_body_is_not_held(self, tmp_path):
        # Counter-case: expansion CLEARS a verified-clean body (expand, not
        # blanket-hold) — proving the corpus holds are classification results.
        gate, console = _gate(
            tmp_path, {"Macro 9": ("Store Cue 1",)}, ScriptedApproval(decisions=[])
        )
        decision = gate.screen(["Go Macro 9"])
        assert decision.cleared is True


class TestUnspecifiedTargetCorpus:
    """AC-MVP-024: deterministic gate-level hold + warning, >=5 cases (no model)."""

    CORPUS = [
        "Delete",
        "Delete *",
        "Delete Sequence Thru",
        "Delete Thru 10",
        "Remove All",
        "Off Everything",
    ]

    @pytest.mark.parametrize("command", CORPUS)
    def test_held_with_unspecified_target_warning_and_zero_sends(self, tmp_path, command):
        approval = ScriptedApproval(decisions=[False])
        gate, console = _gate(tmp_path, {}, approval)
        decision = gate.screen([command])
        assert decision.cleared is False
        assert console.executed == []
        (request,) = approval.requests
        assert any("target" in w for w in request.items[0].warnings), (
            f"{command}: unspecified-target warning missing"
        )

    def test_corpus_size_meets_the_minimum(self):
        assert len(self.CORPUS) >= 5
