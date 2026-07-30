"""Upper-bound footprint walk tests (M2 — AC-OVERLAP-001..006).

The walk exists because the fixture-to-footprint join was refuted, so its output
is a WEAKER claim than the exact-width axis: it can prove that no overlap is
possible and it can never prove that one is. Two consequences shape this file.

**The dangerous failure is a false all-clear, not an exception.** Folding ``max``
over a partial mode set produces a number that looks like a bound and is smaller
than the real one, so it clears gaps it must not clear. Nothing raises, nothing
logs, and the report says the rig is fine. ``TestPartialEnumerationRefusesABound``
is that scenario, transcribed from the research note that found it.

**The unsettled branch is unreachable on the measured rig.** Its minimum gap is
larger than its widest mode, so every adjacent pair on that showfile clears the
bound and no live session can exercise the other branch. Synthetic in-memory rigs
are the only way to reach it, and the widths here are INJECTED for exactly the
reason ``RANGE_OVERLAP_WIDTHS`` is injected in the inventory tests.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from inspect import signature
from pathlib import Path

import pytest

from server.orchestrator.tools import REASON_UNREACHABLE, REASON_UNRESOLVED
from server.prechk.footprint import (
    REASON_UNREACHABLE as WALK_UNREACHABLE,
)
from server.prechk.footprint import (
    REASON_UNRESOLVED as WALK_UNRESOLVED,
)
from server.prechk.footprint import (
    ModeFootprint,
    WalkOutcome,
    address_gaps,
    bound_source,
    unsettled_gaps,
    upper_bound,
    walk_mode_widths,
)
from server.safety.console import StateQueryError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRECHK_DIR = PROJECT_ROOT / "server" / "prechk"
WALK_SOURCE = PRECHK_DIR / "footprint.py"

#: The fixture-type listing path. Passed in as an argument on every call — the
#: module holds no rig path of its own, which is what lets the ``rig_paths``
#: override seam reach this axis (D-2).
ROOT = "Patch/FixtureTypes"

#: Generous enough that no test hits it by accident. Budget behaviour gets its
#: own tests with explicit small numbers.
WIDE_BUDGET = 64

#: Widths are INJECTED, never derived. These two are deliberately NOT the
#: measured ones, so a bound that came from a hardcoded constant instead of the
#: rig would disagree with the assertion.
TWO_MODE_WIDTHS = (17, 23)

#: The research scenario: three narrow modes and one wide one. Enumerate only the
#: first three and the fold answers 29 -- smaller than the true 31 -- which
#: clears a gap of 30 that the true bound leaves unsettled.
TRAP_WIDTHS = (29, 29, 29, 31)


def _snapshot(
    path: str,
    *,
    child_count: int,
    children: list[dict] | None = None,
    truncated: bool = False,
) -> dict:
    """One ``state`` reply, shaped like the responder's (``PROTOCOL.md`` §4)."""
    return {
        "v": 1,
        "kind": "state",
        "id": "test",
        "path": path,
        "ok": True,
        "node": {"name": path.rsplit("/", 1)[-1], "class": "Pool", "childCount": child_count},
        "children": [] if children is None else children,
        "truncated": truncated,
    }


class Rig:
    """An in-memory ``state`` reader. Offers ``query_state`` and NOTHING else.

    Omitting ``query_property`` is the point: if the walk ever grew a property
    dependency, every test here would fail with ``AttributeError`` rather than
    quietly widen the safety-chokepoint surface the module claims not to need.
    """

    def __init__(
        self,
        *,
        widths: tuple[int, ...] = TWO_MODE_WIDTHS,
        types: int = 1,
        modes_listed: int | None = None,
        types_listed: int | None = None,
        channels_truncated: bool = True,
        dead_paths: tuple[str, ...] = (),
        dead_everything: bool = False,
        exception: type[BaseException] = StateQueryError,
    ) -> None:
        self.widths = widths
        self.types = types
        self.modes_listed = len(widths) if modes_listed is None else modes_listed
        self.types_listed = types if types_listed is None else types_listed
        self.channels_truncated = channels_truncated
        self.dead_paths = dead_paths
        self.dead_everything = dead_everything
        self.exception = exception
        self.calls: list[str] = []

    def query_state(self, path: str) -> dict:
        self.calls.append(path)
        if self.dead_everything or path in self.dead_paths:
            raise self.exception(f"no state reply for {path!r}")
        if path == ROOT:
            kids = [
                {"i": n, "name": f"Type {n}", "class": "FixtureType"}
                for n in range(1, self.types_listed + 1)
            ]
            return _snapshot(path, child_count=self.types, children=kids)
        parts = path.split("/")
        if parts[-1] == "DMXModes":
            kids = [
                {"i": n, "name": f"Mode {n}", "class": "DMXMode"}
                for n in range(1, self.modes_listed + 1)
            ]
            return _snapshot(path, child_count=len(self.widths), children=kids)
        if parts[-1] == "DMXChannels":
            width = self.widths[int(parts[-2]) - 1]
            kids = (
                None
                if self.channels_truncated
                else [
                    {"i": n, "name": f"Slot {n}", "class": "DMXChannel"}
                    for n in range(1, width + 1)
                ]
            )
            return _snapshot(
                path, child_count=width, children=kids, truncated=self.channels_truncated
            )
        raise self.exception(f"path segment not found: {path!r}")


def _walk(rig: Rig, budget: int = WIDE_BUDGET) -> WalkOutcome:
    return walk_mode_widths(rig, root=ROOT, budget=budget)


def _module_tree() -> ast.Module:
    return ast.parse(WALK_SOURCE.read_text(encoding="utf-8"))


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"no function named {name} in {WALK_SOURCE}")


def _string_constants(source: Path) -> list[str]:
    return [
        node.value
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


class TestBoundComesFromTheRig:
    """AC-OVERLAP-001 — nothing about the measured rig is written down."""

    def test_no_measured_width_or_gap_is_a_constant_in_the_package(self):
        forbidden = {29, 31, 42, 50}
        visited = 0
        collected = 0
        planted: list[tuple[str, int]] = []
        for source in sorted(PRECHK_DIR.rglob("*.py")):
            visited += 1
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Constant):
                    continue
                if isinstance(node.value, bool) or not isinstance(node.value, int):
                    continue
                collected += 1
                if node.value in forbidden:
                    planted.append((source.name, node.value))
        # Non-vacuity: a scan that reached no file, or found no integer at all,
        # reports zero for the wrong reason.
        assert visited >= 1, f"AST 스캔이 {PRECHK_DIR} 아래 파일을 방문하지 않았다"
        assert collected >= 1, "AST 스캔이 정수 상수를 하나도 모으지 않았다"
        assert planted == [], f"실측 폭·간격이 상수로 박혀 있다: {planted}"

    def test_the_bound_is_whatever_was_injected(self):
        outcome = _walk(Rig(widths=TWO_MODE_WIDTHS))
        assert outcome.complete
        assert outcome.mode_widths == TWO_MODE_WIDTHS
        assert upper_bound(outcome) == max(TWO_MODE_WIDTHS)

    def test_a_different_injection_gives_a_different_bound(self):
        # The pair above would also pass if the bound were pinned to 23. Two
        # injections with different maxima is what makes the claim non-vacuous.
        wider = _walk(Rig(widths=(11, 19, 47)))
        assert upper_bound(wider) == 47

    def test_the_three_tiers_are_queried_in_order(self):
        outcome = _walk(Rig(widths=(5, 7)))
        assert len(outcome.queried_paths) >= 3
        assert outcome.queried_paths[0] == ROOT
        assert outcome.queried_paths[1] == f"{ROOT}/1/DMXModes"
        assert outcome.queried_paths[2] == f"{ROOT}/1/DMXModes/1/DMXChannels"
        assert outcome.query_count == len(outcome.queried_paths)

    def test_the_channel_tier_never_reads_the_child_list(self):
        """AC-OVERLAP-001 ④ — the width is the declared count, full stop."""
        tier_three = _function(_module_tree(), "_declared_child_count")
        names = [node.value for node in ast.walk(tier_three) if isinstance(node, ast.Constant)]
        assert names, "3단 술어에서 상수를 하나도 모으지 못하면 이 단정이 공허하다"
        assert "children" not in names
        assert not any(
            isinstance(node, ast.Name) and node.id == "children" for node in ast.walk(tier_three)
        )

    def test_the_walk_addresses_children_by_pool_slot_not_by_position(self):
        """A sparse pool is where position and slot disagree.

        The listing reports slots 4 and 9; walking positions 1 and 2 would read
        two paths that do not exist, so the width pair proves the walk used ``i``.
        """

        class Sparse(Rig):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path.endswith("DMXModes"):
                    payload["children"] = [
                        {"i": 4, "name": "Mode 4", "class": "DMXMode"},
                        {"i": 9, "name": "Mode 9", "class": "DMXMode"},
                    ]
                    payload["node"]["childCount"] = 2
                return payload

        rig = Sparse(widths=(0, 0, 0, 13, 0, 0, 0, 0, 21))
        outcome = _walk(rig)
        assert f"{ROOT}/1/DMXModes/4/DMXChannels" in outcome.queried_paths
        assert f"{ROOT}/1/DMXModes/9/DMXChannels" in outcome.queried_paths
        assert outcome.mode_widths == (13, 21)


class TestStateOnlySurface:
    """AC-OVERLAP-002 ① — one port method, and it is not the property read."""

    def test_the_module_uses_query_state_and_never_query_property(self):
        tree = _module_tree()
        attributes = [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        assert len(calls) >= 1, "호출 노드를 하나도 방문하지 않으면 0건 판정이 공허하다"
        assert "query_state" in attributes
        assert "query_property" not in attributes

    def test_a_reader_without_a_property_method_is_enough(self):
        # Structural, not stylistic: ``Rig`` has no ``query_property`` at all, so
        # a property dependency would raise here instead of passing silently.
        rig = Rig()
        assert not hasattr(rig, "query_property")
        assert upper_bound(_walk(rig)) == max(TWO_MODE_WIDTHS)


class TestPartialEnumerationRefusesABound:
    """AC-OVERLAP-003 — an incomplete mode set has NO bound, not a small one."""

    def test_a_short_type_listing_yields_no_bound(self):
        outcome = _walk(Rig(types=5, types_listed=3))
        assert outcome.complete is False
        assert upper_bound(outcome) is None
        assert outcome.notes

    def test_a_short_mode_listing_yields_no_bound(self):
        outcome = _walk(Rig(widths=(5, 7, 11), modes_listed=2))
        assert outcome.complete is False
        assert upper_bound(outcome) is None

    def test_an_exhausted_budget_yields_no_bound(self):
        outcome = _walk(Rig(widths=(5, 7, 11)), budget=2)
        assert outcome.complete is False
        assert upper_bound(outcome) is None
        assert any("예산" in note for note in outcome.notes)

    def test_a_raising_query_yields_no_bound(self):
        outcome = _walk(Rig(dead_paths=(f"{ROOT}/1/DMXModes",)))
        assert outcome.complete is False
        assert upper_bound(outcome) is None

    def test_the_fold_lives_inside_the_completeness_branch(self):
        """AC-OVERLAP-003 ⑤ — control flow, not a comment.

        A fold that runs unconditionally and gets annulled afterwards is the
        defect: the annotation decorates the walk while the verdict decorates an
        address pair and travels onward by itself.
        """
        tree = _module_tree()
        folds = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "max"
        ]
        assert len(folds) >= 1, "max 노드를 찾지 못하면 이 판정이 공허하다"
        guarded = 0
        for branch in (node for node in ast.walk(tree) if isinstance(node, ast.If)):
            mentions_completeness = any(
                isinstance(inner, ast.Attribute) and inner.attr == "complete"
                for inner in ast.walk(branch.test)
            )
            if not mentions_completeness:
                continue
            inside = {id(node) for node in ast.walk(branch) if node is not branch}
            guarded += sum(1 for fold in folds if id(fold) in inside)
        assert guarded == len(folds), (
            "max 연산이 완전성 판정 분기 밖에 있다 — 부분 결과가 상계처럼 보이게 된다"
        )

    def test_the_subset_bound_trap_does_not_clear_a_gap_of_thirty(self):
        """AC-OVERLAP-003 ⑥ — the research scenario, transcribed.

        Enumerating three of four modes folds to 29. The true bound is 31, and
        the gap under test is 30: ``30 >= 29`` would clear the rig while
        ``30 < 31`` leaves it unsettled. The walk must therefore hand back NO
        bound, so the caller has nothing to compare 30 against.
        """
        gap = 30
        rig = Rig(widths=TRAP_WIDTHS, modes_listed=3)
        outcome = _walk(rig)
        subset_fold = max(outcome.mode_widths)
        true_bound = max(TRAP_WIDTHS)
        # The trap is real: the partial fold and the true bound disagree ACROSS
        # the gap, so the two answers differ. Without this the test could pass on
        # a rig where the distinction does not matter.
        assert subset_fold < true_bound
        assert gap >= subset_fold
        assert gap < true_bound
        assert outcome.complete is False
        assert upper_bound(outcome) is None


class TestTruncationPredicatesStaySeparate:
    """AC-OVERLAP-004 — the channel count survives truncation; a listing does not."""

    def test_a_truncated_channel_listing_still_yields_its_width(self):
        rig = Rig(widths=(23,), channels_truncated=True)
        outcome = _walk(rig)
        assert outcome.mode_widths == (23,)
        assert outcome.complete is True

    def test_the_two_predicates_disagree_on_the_same_flag(self):
        """AC-OVERLAP-004 ④ — run both in one test; merging them breaks this."""

        class TruncatedRoot(Rig):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path == ROOT:
                    payload["truncated"] = True
                return payload

        truncated_channels = _walk(Rig(widths=(23,), channels_truncated=True))
        truncated_root = _walk(TruncatedRoot(widths=(23,), channels_truncated=True))
        assert truncated_channels.complete is True
        assert truncated_root.complete is False
        assert upper_bound(truncated_channels) == 23
        assert upper_bound(truncated_root) is None

    def test_the_channel_predicate_makes_no_count_comparison(self):
        """AC-OVERLAP-004 ③ — ``childCount > len(children)`` here kills the axis.

        On the measured rig the channel listing is always truncated, so a count
        comparison at this tier would mean the bound is never available.
        """
        tier_three = _function(_module_tree(), "_declared_child_count")
        comparisons = [node for node in ast.walk(tier_three) if isinstance(node, ast.Compare)]
        lens = [
            node
            for node in ast.walk(tier_three)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "len"
        ]
        assert lens == []
        # A count comparison would need `len(...)`; the remaining comparisons are
        # the type and lower-bound checks, which are not list-length tests.
        assert all(
            not any(isinstance(inner, ast.Call) for inner in ast.walk(node)) for node in comparisons
        )

    def test_the_listing_predicate_does_compare_counts(self):
        # Positive control for the test above: the separation only means
        # something if the OTHER predicate really does the comparison.
        tier_one_two = _function(_module_tree(), "_listing_is_whole")
        lens = [
            node
            for node in ast.walk(tier_one_two)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "len"
        ]
        assert lens, "1·2단 술어가 목록 길이를 보지 않으면 술어 분리가 무의미하다"


class TestModuleBoundaries:
    """AC-OVERLAP-005 — a pure function, importable on its own."""

    def test_the_walk_takes_the_path_and_the_budget_as_parameters(self):
        parameters = signature(walk_mode_widths).parameters
        assert "root" in parameters
        assert "budget" in parameters

    def test_the_module_does_not_import_the_toolset(self):
        tree = _module_tree()
        imports = [node for node in ast.walk(tree) if isinstance(node, ast.Import | ast.ImportFrom)]
        assert len(imports) >= 1, "import 노드를 방문하지 않으면 0건 판정이 공허하다"
        modules = [
            alias.name if isinstance(node, ast.Import) else (node.module or "")
            for node in imports
            for alias in node.names
        ]
        assert [m for m in modules if m.startswith("server.orchestrator.tools")] == []

    def test_the_module_imports_standalone(self):
        """AC-OVERLAP-005 ③ — the machine test that rules out a handler closure."""
        finished = subprocess.run(  # noqa: S603
            [sys.executable, "-c", "import server.prechk.footprint"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stderr

    def test_the_walk_is_callable_without_a_toolset(self):
        # The unsettled branch is reachable only through synthetic rigs, so unit
        # access to the walk is not a convenience -- it is the only coverage.
        assert upper_bound(_walk(Rig(widths=(3, 9)))) == 9

    def test_the_package_names_no_forbidden_property(self):
        collected = _string_constants(WALK_SOURCE)
        assert collected, "문자열 상수를 모으지 못하면 이 단정이 공허하다"
        forbidden = {"Address", "Universe", "Channels", "ChannelCount", "Footprint", "No", "Break"}
        assert set(collected) & forbidden == set()


class TestFailureClassification:
    """AC-OVERLAP-006 — a configuration defect and a dead console differ."""

    def test_the_reason_codes_are_the_existing_two(self):
        # Retyped in the module to avoid a cycle; pinned here so a drift fails
        # instead of forking the classification into a third vocabulary.
        assert WALK_UNRESOLVED == REASON_UNRESOLVED
        assert WALK_UNREACHABLE == REASON_UNREACHABLE

    def test_a_missing_path_and_a_dead_console_get_different_codes(self):
        missing = _walk(Rig(dead_paths=(f"{ROOT}/1/DMXModes",)))
        dead = _walk(Rig(dead_everything=True))
        assert missing.failure == REASON_UNRESOLVED
        assert dead.failure == REASON_UNREACHABLE
        assert missing.failure != dead.failure

    def test_the_same_exception_type_still_splits(self):
        """AC-OVERLAP-006 ③ — the discriminator is not the exception.

        ``ConsoleLink.query_state`` raises ``StateQueryError`` for a refused path
        AND for a timeout, so a classifier keyed on the exception type cannot
        tell them apart. This walk keys on whether a sibling already answered.
        """
        missing = _walk(Rig(dead_paths=(f"{ROOT}/1/DMXModes",), exception=StateQueryError))
        dead = _walk(Rig(dead_everything=True, exception=StateQueryError))
        assert missing.failure == REASON_UNRESOLVED
        assert dead.failure == REASON_UNREACHABLE

    def test_an_ok_false_payload_is_treated_as_a_failed_read(self):
        class Refusing(Rig):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path.endswith("DMXModes"):
                    return {"ok": False, "path": path, "error": "path segment not found"}
                return payload

        outcome = _walk(Refusing())
        assert outcome.failure == REASON_UNRESOLVED
        assert upper_bound(outcome) is None

    def test_neither_message_claims_an_absence_of_overlap_or_of_modes(self):
        missing = _walk(Rig(dead_paths=(f"{ROOT}/1/DMXModes",)))
        dead = _walk(Rig(dead_everything=True))
        for outcome in (missing, dead):
            detail = outcome.failure_detail
            assert detail.strip(), "사용자가 읽는 문자열이 비어 있다"
            assert any("\uac00" <= character <= "\ud7a3" for character in detail)
            assert "겹침이 없다" not in detail
            assert "모드가 없다" not in detail
        assert missing.failure_detail != dead.failure_detail

    def test_a_failed_walk_leaves_no_bound_behind(self):
        for outcome in (
            _walk(Rig(dead_paths=(f"{ROOT}/1/DMXModes",))),
            _walk(Rig(dead_everything=True)),
        ):
            assert outcome.complete is False
            assert upper_bound(outcome) is None

    def test_an_empty_type_pool_is_not_a_bound(self):
        # A rig with no fixture types is a valid rig, and it establishes nothing.
        outcome = _walk(Rig(types=0, types_listed=0))
        assert outcome.complete is False
        assert upper_bound(outcome) is None
        assert outcome.failure is None, "빈 풀은 판독 실패가 아니다"


class TestBudgetAccounting:
    """Slot C — exhaustion invalidates globally, not per branch."""

    def test_the_budget_caps_the_query_count(self):
        rig = Rig(widths=(5, 7, 11))
        _walk(rig, budget=3)
        assert len(rig.calls) == 3

    def test_a_sufficient_budget_costs_one_plus_types_plus_modes(self):
        rig = Rig(widths=(5, 7, 11))
        outcome = _walk(rig)
        assert outcome.query_count == 1 + rig.types + len(rig.widths)

    def test_exhaustion_is_not_reported_as_a_read_failure(self):
        outcome = _walk(Rig(widths=(5, 7, 11)), budget=2)
        assert outcome.failure is None
        assert any("예산" in note for note in outcome.notes)

    def test_exhaustion_after_some_widths_were_read_still_kills_the_bound(self):
        """The mutation that survived the first battery.

        Budget 4 on a three-mode type reads two channel counts and dies on the
        third. Downgrading that to a per-branch note leaves ``complete`` true
        over a two-of-three mode set, and the fold then answers 7 while the true
        bound is 11 -- a smaller bound, which is the false all-clear. The earlier
        budget tests missed it because both of their budgets died before ANY
        width was collected, so the empty-width guard covered for them.
        """
        rig = Rig(widths=(5, 7, 11))
        outcome = _walk(rig, budget=4)
        assert outcome.query_count == 4
        # Non-vacuity: two channel counts really were read before the budget
        # died, so the empty-width guard is not what makes this pass.
        channel_reads = [path for path in outcome.queried_paths if path.endswith("DMXChannels")]
        assert len(channel_reads) == 2
        # And the walk hands none of them back: a partial width tuple is a bound
        # waiting to be folded by a consumer that forgot to read ``complete``.
        assert outcome.mode_widths == ()
        assert outcome.complete is False
        assert upper_bound(outcome) is None


def test_the_outcome_carries_no_bound_attribute():
    """Slot A-ii, as a shape rather than a promise.

    If ``WalkOutcome`` grew a ``bound`` field, a consumer could read it without
    consulting ``complete`` -- which is the exact path a false all-clear takes.
    """
    assert not hasattr(
        WalkOutcome(complete=True, footprints=(ModeFootprint(path="p", width=3),)), "bound"
    )
    with pytest.raises(TypeError):
        WalkOutcome(complete=True, bound=3)  # type: ignore[call-arg]


class TestGapArithmetic:
    """AC-OVERLAP-009 · AC-OVERLAP-010 — distances live inside one universe."""

    def test_a_universe_boundary_is_not_a_gap(self):
        # 1.500 and 2.001 look adjacent as numbers and share no address space.
        gaps = address_gaps({(1, 500), (2, 1)})
        assert gaps == ()

    def test_adjacent_universes_never_contribute_a_difference(self):
        gaps = address_gaps({(1, 100), (1, 500), (2, 1), (2, 40)})
        sizes = sorted(gap.size for gap in gaps)
        assert sizes == [39, 400]
        # The cross-universe differences (500-1=499, 40-100=-60) must be absent.
        assert 499 not in sizes
        assert all(gap.size > 0 for gap in gaps)

    def test_the_gap_count_is_the_sum_of_members_minus_one(self):
        starts = {(1, address) for address in (1, 101, 143, 185)} | {
            (2, address) for address in (1, 51, 101)
        }
        per_universe: dict[int, int] = {}
        for universe, _ in starts:
            per_universe[universe] = per_universe.get(universe, 0) + 1
        expected = sum(count - 1 for count in per_universe.values())
        assert expected >= 1, "리그 형상에서 간격이 0개면 이 단정이 공허하다"
        assert len(address_gaps(starts)) == expected

    def test_a_shared_start_point_appears_once_and_makes_no_zero_gap(self):
        # The key set already folds duplicates, so a zero distance cannot arise
        # here -- it belongs to the duplicate axis.
        gaps = address_gaps({(1, 10), (1, 40)})
        assert [gap.size for gap in gaps] == [30]
        assert 0 not in [gap.size for gap in gaps]

    def test_one_address_per_universe_yields_no_gap(self):
        assert address_gaps({(1, 5), (2, 5), (3, 5)}) == ()


class TestBoundPredicate:
    """AC-OVERLAP-008 — the predicate is ``gap < bound``, not ``gap <= bound``."""

    def _at(self, gap: int) -> tuple:
        # Same rig shape every time; only the distance moves.
        return address_gaps({(1, 100), (1, 100 + gap)})

    def test_a_gap_one_below_the_bound_is_unsettled(self):
        bound = 23
        assert len(unsettled_gaps(self._at(bound - 1), bound)) == 1

    def test_a_gap_exactly_at_the_bound_is_settled(self):
        """The off-by-one test.

        A fixture at ``a`` occupying at most ``bound`` channels ends at
        ``a + bound - 1``; the next start is ``a + bound``. The intervals touch
        and share nothing. Spelling the predicate ``<=`` fails right here, and on
        the measured rig -- gap far wider than the bound -- both spellings agree,
        so nothing else would catch it.
        """
        bound = 23
        assert unsettled_gaps(self._at(bound), bound) == ()

    def test_a_gap_one_above_the_bound_is_settled(self):
        bound = 23
        assert unsettled_gaps(self._at(bound + 1), bound) == ()

    def test_the_three_answers_differ_only_where_they_should(self):
        bound = 23
        below = unsettled_gaps(self._at(bound - 1), bound)
        at = unsettled_gaps(self._at(bound), bound)
        above = unsettled_gaps(self._at(bound + 1), bound)
        assert below != at
        assert at == above
        assert len(below) == 1


class TestBoundOrigin:
    """AC-OVERLAP-016 ①② — the bound carries the path it was read from."""

    def test_the_origin_points_at_the_widest_mode(self):
        rig = Rig(widths=(5, 31, 7))
        outcome = _walk(rig)
        assert upper_bound(outcome) == 31
        assert bound_source(outcome) == f"{ROOT}/1/DMXModes/2/DMXChannels childCount"

    def test_the_origin_moves_with_the_widest_mode(self):
        # A single rig would also pass if the path were pinned to mode 2.
        assert bound_source(_walk(Rig(widths=(31, 5, 7)))).endswith(
            "/DMXModes/1/DMXChannels childCount"
        )

    def test_a_walk_with_no_bound_offers_no_origin(self):
        incomplete = WalkOutcome(
            complete=False, footprints=(ModeFootprint(path="어딘가", width=9),)
        )
        assert upper_bound(incomplete) is None
        assert bound_source(incomplete) == ""

    def test_the_origin_names_the_field_and_not_just_the_path(self):
        origin = bound_source(_walk(Rig(widths=(5, 31))))
        assert origin.endswith("childCount")
        assert "DMXChannels" in origin
