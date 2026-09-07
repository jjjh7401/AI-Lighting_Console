"""Expand-or-hold tests (M4 — REQ-MVP-026, AC-MVP-017 seed).

Reference-invoking commands have their target bodies fetched (production: the
M2 state path) and classified. HOLD on: unverifiable body, recursion depth > 3,
reference cycle, unparseable body line, or a nested unverifiable reference.
Pure logic with an injectable body fetcher — fully deterministic (no OSC).
"""

from __future__ import annotations

from server.safety.console import StateBodyFetcher
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


#: 「깨끗한 본문」 리터럴 — 확장이 blanket-hold 가 아니라 실제 분류 결과라는 것을
#: 보이는 대조군에 쓴다.
#:
#: 갱신 근거 (t299 Phase 3): 옛 리터럴은 `Store Cue 1` 이었고 v7
#: (SPEC-COPILOT-CLASSIFYGAP-001)이 `Store Cue` 를 폐집합에 넣어 더는 깨끗하지
#: 않다. Phase 1·2 가 세운 규율대로 **프로그래머 값**으로 옮긴다 — 폐집합은 쇼파일
#: 쓰기 오브젝트만 담으므로 어떤 리비전도 이 리터럴을 다시 잡지 않는다. 다른 `Store`
#: 오브젝트로 옮기면 Phase 1 이 겪은 대로 한 리비전 만에 다시 잃는다.
_CLEAN_BODY_LINE = "Fixture 1 At 50"


class TestExpansion:
    def test_clean_body_passes(self):
        fetcher = DictBodyFetcher({"Macro 9": (_CLEAN_BODY_LINE, "List")})
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
                # 갱신 근거 (t299 Phase 3): 재는 축은 **깊이**(3단 이내면 통과)이고
                # 사슬 끝의 본문 내용은 축과 무관하다. 옛 `Store Cue 1` 은 v7 이
                # 폐집합에 넣었으므로 `_CLEAN_BODY_LINE` 으로 옮긴다.
                "Macro 3": (_CLEAN_BODY_LINE,),
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


def _state_fetcher(tree: dict[str, dict]) -> StateBodyFetcher:
    """Real production fetcher (M2 wire shape), keyed by object-tree path --
    NOT DictBodyFetcher. M5 (REQ-EXECBODY-011): every fail-closed reason
    EXECREF-001 introduced holds identically when the top-level reference is
    resolved via the M4 Executor->assigned-sequence delegation, not just via
    a direct Macro/Plugin/Sequence lookup.
    """

    def query(path: str) -> dict:
        if path not in tree:
            raise KeyError(f"no reply for {path}")
        return tree[path]

    return StateBodyFetcher(query)


def _cues(*names: str) -> dict:
    return {"ok": True, "children": [{"name": name} for name in names]}


_EXECUTOR_201_ASSIGNED_71 = {
    "Executor 201": {"ok": True, "node": {"class": "Executor", "sequenceNo": 71}}
}


class TestExecutorMediatedFailClosed:
    """M5: EXECREF-001's fail-closed reasons, exercised end-to-end through the
    real StateBodyFetcher's Executor->Sequence delegation (not the abstract
    DictBodyFetcher above) -- each held individually, never merged
    (design.md §6.2 principle)."""

    def test_executor_unverifiable_body_holds(self):
        # Identity resolves, but the assigned sequence's own state query
        # never comes back -- genuinely unverifiable.
        fetcher = _state_fetcher(dict(_EXECUTOR_201_ASSIGNED_71))
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is True
        assert any("unverifiable" in r for r in outcome.reasons)

    def test_executor_body_with_blacklisted_command_holds_as_risky(self):
        fetcher = _state_fetcher(
            {**_EXECUTOR_201_ASSIGNED_71, "DataPool/Sequences/71": _cues("Delete Sequence 5")}
        )
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is True
        assert outcome.risky is True
        assert any("blacklist" in r for r in outcome.reasons)

    def test_executor_depth_exceeding_three_holds(self):
        # AC-MVP-017 case 3, entered via the executor delegation: Executor
        # 201 (depth 1) -> Macro 10 (2) -> Macro 11 (3) -> Macro 12 (4)
        # exceeds the cap of 3.
        fetcher = _state_fetcher(
            {
                **_EXECUTOR_201_ASSIGNED_71,
                "DataPool/Sequences/71": _cues("Go Macro 10"),
                "DataPool/Macros/10": _cues("Go Macro 11"),
                "DataPool/Macros/11": _cues("Go Macro 12"),
                "DataPool/Macros/12": _cues("Store Cue 1"),
            }
        )
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is True
        assert any("depth" in r for r in outcome.reasons)

    def test_executor_reference_cycle_holds(self):
        # AC-MVP-017 case 4: the assigned sequence's body loops back to the
        # SAME executor reference by way of a nested macro.
        fetcher = _state_fetcher(
            {
                **_EXECUTOR_201_ASSIGNED_71,
                "DataPool/Sequences/71": _cues("Go Macro 10"),
                "DataPool/Macros/10": _cues("Go Executor 201"),
            }
        )
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is True
        assert any("cycle" in r for r in outcome.reasons)

    def test_executor_unparseable_body_line_holds(self):
        fetcher = _state_fetcher(
            {**_EXECUTOR_201_ASSIGNED_71, "DataPool/Sequences/71": _cues("'broken")}
        )
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is True

    def test_executor_assigned_to_empty_sequence_passes(self):
        # acceptance.md §D "빈 시퀀스": zero cues is a verified-empty body, a
        # positive pass -- distinct from the unverifiable case above.
        fetcher = _state_fetcher(
            {
                **_EXECUTOR_201_ASSIGNED_71,
                "DataPool/Sequences/71": {"ok": True, "children": []},
            }
        )
        outcome = _evaluate("Executor 201", fetcher)
        assert outcome.hold is False
