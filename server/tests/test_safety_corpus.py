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
    """One gate-level command per SSOT invoking entry (verbs + bare forms)."""
    commands = [f"{verb} Macro 9" for verb in RULESET.invoking_verbs]
    for form in RULESET.bare_object_forms:
        commands.append(form.replace("<n>", "9"))
    return commands


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


class TestInvokingVerbFnCorpus:
    """AC-MVP-017: ALL invoking_verbs entries x 4 hold scenarios -> zero sends."""

    @pytest.mark.parametrize("command", _invoking_commands())
    @pytest.mark.parametrize("scenario", sorted(_SCENARIOS))
    def test_no_send_pre_approval_in_every_scenario(self, tmp_path, command, scenario):
        approval = ScriptedApproval(decisions=[False])
        gate, console = _gate(tmp_path, _SCENARIOS[scenario], approval)
        decision = gate.screen([command])
        assert decision.cleared is False, f"{command} [{scenario}] must hold"
        assert console.executed == [], f"{command} [{scenario}] sent pre-approval (FN!)"
        assert len(approval.requests) == 1, f"{command} [{scenario}] not held for approval"

    def test_corpus_iterates_the_full_closed_set(self):
        # 10 verbs + 2 bare forms, read from the SSOT file.
        assert len(_invoking_commands()) == len(RULESET.invoking_verbs) + len(
            RULESET.bare_object_forms
        )
        assert len(_invoking_commands()) >= 12

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
