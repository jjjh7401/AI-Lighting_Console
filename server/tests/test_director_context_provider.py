"""SPEC-LDWIRE-001 M3 -- REQ-LDWIRE-004/005.

RealContextProvider: identity/expiry/policy observed for real, the other six axes
filled with context.py honest-unobserved states (design.md section "la", confirmed
2026-09-19). RED first: server.director.provision does not exist yet.
"""

from __future__ import annotations

from server.director.context import missing_axes
from server.director.provision import RealContextProvider
from server.safety.ruleset import SafetyRuleset

PROJECT = "proj-wire-ctx"


def _ruleset(version: int = 1) -> SafetyRuleset:
    return SafetyRuleset(
        version=version,
        blacklist=("Blackout",),
        invoking_verbs=("At", "Off"),
        bare_object_forms=("Fixture",),
    )


class TestNineAxesAllPresent:
    def test_missing_axes_is_empty(self) -> None:
        provider = RealContextProvider(
            ruleset=_ruleset(), console_host="127.0.0.1", console_port=8000
        )
        snapshot = provider.current(PROJECT)
        assert missing_axes(snapshot) == ()

    def test_unobserved_six_axes_use_honest_states(self) -> None:
        provider = RealContextProvider(
            ruleset=_ruleset(), console_host="127.0.0.1", console_port=8000
        )
        snapshot = provider.current(PROJECT)
        assert snapshot["beat_map"]["status"] == "absent"
        assert snapshot["groups"] == []
        assert snapshot["presets"] == []
        assert snapshot["capabilities"] == []
        assert snapshot["audio"]["status"] == "unreadable"

    def test_identity_expiry_policy_are_really_observed(self) -> None:
        provider = RealContextProvider(
            ruleset=_ruleset(version=7), console_host="127.0.0.1", console_port=8000
        )
        snapshot = provider.current(PROJECT)
        assert snapshot["target"]["identity_status"] == "observed"
        assert len(snapshot["target"]["identity_evidence_refs"]) > 0
        assert snapshot["target"]["console_id"] == "127.0.0.1:8000"
        assert snapshot["safety_policy_revision"] == 7
        assert snapshot["expires_at"] > snapshot["created_at"]


class TestReissueSuppression:
    def test_repeated_call_without_change_keeps_the_same_context_id(self) -> None:
        provider = RealContextProvider(
            ruleset=_ruleset(), console_host="127.0.0.1", console_port=8000
        )
        first = provider.current(PROJECT)
        second = provider.current(PROJECT)
        assert second["context_id"] == first["context_id"]
        assert second["context_digest"] == first["context_digest"]

    def test_a_policy_version_change_reissues_a_new_context_id(self) -> None:
        ruleset_holder = {"ruleset": _ruleset(version=1)}

        class _MutableRulesetView:
            @property
            def version(self):
                return ruleset_holder["ruleset"].version

            @property
            def blacklist(self):
                return ruleset_holder["ruleset"].blacklist

            @property
            def invoking_verbs(self):
                return ruleset_holder["ruleset"].invoking_verbs

            @property
            def bare_object_forms(self):
                return ruleset_holder["ruleset"].bare_object_forms

        provider = RealContextProvider(
            ruleset=_MutableRulesetView(), console_host="127.0.0.1", console_port=8000
        )
        first = provider.current(PROJECT)
        ruleset_holder["ruleset"] = _ruleset(version=2)
        second = provider.current(PROJECT)
        assert second["context_id"] != first["context_id"]
        assert second["safety_policy_revision"] == 2
