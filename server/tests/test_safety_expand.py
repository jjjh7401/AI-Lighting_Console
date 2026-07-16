"""Expand-or-hold tests (M4 — REQ-MVP-026, AC-MVP-017 seed).

Reference-invoking commands have their target bodies fetched (production: the
M2 state path) and classified. HOLD on: unverifiable body, recursion depth > 3,
reference cycle, unparseable body line, or a nested unverifiable reference.
Pure logic with an injectable body fetcher — fully deterministic (no OSC).
"""

from __future__ import annotations

from server.safety.expand import BodyUnavailable, evaluate_reference
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset

RULESET = load_ruleset()


class DictBodyFetcher:
    """Deterministic in-memory body fetcher keyed by normalized reference."""

    def __init__(self, bodies: dict[str, tuple[str, ...]]):
        self.bodies = {k.lower(): tuple(v) for k, v in bodies.items()}
        self.fetched: list[str] = []

    def fetch_body(self, reference: str) -> tuple[str, ...]:
        self.fetched.append(reference)
        key = reference.lower()
        if key not in self.bodies:
            raise BodyUnavailable(f"no body available for {reference!r}")
        return self.bodies[key]


def _evaluate(reference, fetcher, **kwargs):
    return evaluate_reference(reference, ruleset=RULESET, fetcher=fetcher, **kwargs)


class TestExpansion:
    def test_clean_body_passes(self):
        fetcher = DictBodyFetcher({"Macro 9": ("Store Cue 1", "List")})
        outcome = _evaluate("Macro 9", fetcher)
        assert outcome.hold is False

    def test_body_with_blacklisted_command_holds_as_risky(self):
        fetcher = DictBodyFetcher({"Macro 9": ("Delete Sequence 5",)})
        outcome = _evaluate("Macro 9", fetcher)
        assert outcome.hold is True
        assert outcome.risky is True
        assert any("blacklist" in r for r in outcome.reasons)

    def test_unavailable_body_holds_as_unverifiable(self):
        fetcher = DictBodyFetcher({})
        outcome = _evaluate("Macro 9", fetcher)
        assert outcome.hold is True
        assert any("unverifiable" in r for r in outcome.reasons)

    def test_none_reference_holds(self):
        fetcher = DictBodyFetcher({})
        outcome = _evaluate(None, fetcher)
        assert outcome.hold is True
        assert fetcher.fetched == []  # nothing to fetch

    def test_unparseable_body_line_holds(self):
        fetcher = DictBodyFetcher({"Macro 9": ("'broken",)})
        outcome = _evaluate("Macro 9", fetcher)
        assert outcome.hold is True

    def test_nested_clean_chain_within_depth_limit_passes(self):
        fetcher = DictBodyFetcher(
            {
                "Macro 1": ("Go Macro 2",),
                "Macro 2": ("Go Macro 3",),
                "Macro 3": ("Store Cue 1",),
            }
        )
        outcome = _evaluate("Macro 1", fetcher)
        assert outcome.hold is False

    def test_depth_exceeding_three_holds(self):
        # AC-MVP-017 case 3: a 4-level chain exceeds the recursion cap of 3.
        fetcher = DictBodyFetcher(
            {
                "Macro 1": ("Go Macro 2",),
                "Macro 2": ("Go Macro 3",),
                "Macro 3": ("Go Macro 4",),
                "Macro 4": ("Store Cue 1",),
            }
        )
        outcome = _evaluate("Macro 1", fetcher)
        assert outcome.hold is True
        assert any("depth" in r for r in outcome.reasons)

    def test_reference_cycle_holds(self):
        # AC-MVP-017 case 4: a reference cycle is held, never looped.
        fetcher = DictBodyFetcher(
            {
                "Macro 1": ("Go Macro 2",),
                "Macro 2": ("Go Macro 1",),
            }
        )
        outcome = _evaluate("Macro 1", fetcher)
        assert outcome.hold is True
        assert any("cycle" in r for r in outcome.reasons)

    def test_nested_unrecognized_reference_holds(self):
        fetcher = DictBodyFetcher({"Macro 1": ("Goto Cue 3",)})
        outcome = _evaluate("Macro 1", fetcher)
        assert outcome.hold is True


class TestPluginRegistryIntegration:
    def test_destructive_flagged_plugin_holds_every_time(self):
        registry = PluginFlagRegistry()
        registry.register("Plugin 7", destructive=True)
        fetcher = DictBodyFetcher({})
        outcome = _evaluate("Plugin 7", fetcher, plugin_registry=registry)
        assert outcome.hold is True
        assert outcome.risky is True
        assert any("destructive" in r for r in outcome.reasons)
        assert fetcher.fetched == []  # registry verdict, no body fetch

    def test_registered_non_destructive_plugin_passes_without_fetch(self):
        registry = PluginFlagRegistry()
        registry.register("Plugin 7", destructive=False)
        fetcher = DictBodyFetcher({})
        outcome = _evaluate("Plugin 7", fetcher, plugin_registry=registry)
        assert outcome.hold is False
        assert fetcher.fetched == []

    def test_unregistered_plugin_falls_back_to_expand_or_hold(self):
        registry = PluginFlagRegistry()
        fetcher = DictBodyFetcher({})
        outcome = _evaluate("Plugin 8", fetcher, plugin_registry=registry)
        assert outcome.hold is True  # unverifiable
        assert fetcher.fetched == ["Plugin 8"]

    def test_registry_lookup_is_case_insensitive(self):
        registry = PluginFlagRegistry()
        registry.register("Plugin 7", destructive=True)
        assert registry.lookup("plugin 7") is not None
        assert registry.lookup("PLUGIN 7").destructive is True
        assert registry.lookup("Plugin 8") is None
