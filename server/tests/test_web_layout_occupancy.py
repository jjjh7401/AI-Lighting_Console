"""Live occupancy fetch for the executor layout planner (T-F, task item 4)."""

from __future__ import annotations

from server.looks.layout import OCCUPIED, UNCONFIRMED, plan_layout
from server.tests.busking_fixtures import make_bundle, make_look
from server.web.layout_occupancy import check_occupancy, fetch_executor_states


class _FakeStatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


def _bundle():
    return make_bundle(
        (make_look("intro", "Intro Wash", dynamics=1), make_look("verse", "Verse", dynamics=2)),
        genre="rock",
    )


class TestFetchExecutorStates:
    def test_queries_the_exact_executor_reference_form(self):
        port = _FakeStatePort({"Executor 101": {"node": {}}})
        fetch_executor_states(port, [101])
        assert port.queried == ["Executor 101"]

    def test_a_failed_query_is_dropped_not_substituted(self):
        port = _FakeStatePort({})
        states = fetch_executor_states(port, [101, 102])
        assert states == {}

    def test_returns_one_entry_per_confirmed_number(self):
        port = _FakeStatePort(
            {"Executor 101": {"node": {"sequenceNo": 5}}, "Executor 102": {"node": {}}}
        )
        states = fetch_executor_states(port, [101, 102])
        assert states[101]["node"]["sequenceNo"] == 5
        assert states[102]["node"] == {}


class TestCheckOccupancy:
    def test_queries_only_the_plans_own_targets(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12})
        targets = [item.executor_no for item in plan.items]
        port = _FakeStatePort({f"Executor {no}": {"node": {}} for no in targets})
        check_occupancy(port, plan)
        assert sorted(port.queried) == sorted(f"Executor {no}" for no in targets)

    def test_an_occupied_target_becomes_a_flagged_conflict(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        port = _FakeStatePort({f"Executor {target}": {"node": {"sequenceNo": 42}}})
        result = check_occupancy(port, plan)
        assert result.items[0].conflict is True
        assert result.items[0].conflict_reason == OCCUPIED

    def test_a_console_that_never_answers_marks_unconfirmed_not_free(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        port = _FakeStatePort({})  # every query raises LookupError
        result = check_occupancy(port, plan)
        assert result.items[0].conflict is True
        assert result.items[0].conflict_reason == UNCONFIRMED

    def test_a_free_target_stays_unconflicted(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        port = _FakeStatePort({f"Executor {target}": {"node": {}}})
        result = check_occupancy(port, plan)
        assert result.items[0].conflict is False
