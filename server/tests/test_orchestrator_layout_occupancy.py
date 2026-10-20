"""Occupancy fetch now lives in server.orchestrator (T-J) — see module docstring
in server/orchestrator/layout_occupancy.py for the layering rationale.

``server/tests/test_web_layout_occupancy.py`` exercises the same functions in
more detail; this file is a direct import-path smoke test.
"""

from __future__ import annotations

from server.looks.layout import OCCUPIED, plan_layout
from server.orchestrator.layout_occupancy import check_occupancy as orchestrator_check_occupancy
from server.tests.busking_fixtures import make_bundle, make_look


class _FakeStatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree

    def query_state(self, path: str) -> dict:
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


class TestDirectOrchestratorImport:
    def test_an_occupied_target_becomes_a_flagged_conflict(self):
        bundle = make_bundle((make_look("intro", "Intro Wash", dynamics=1),), genre="rock")
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        port = _FakeStatePort({f"Executor {target}": {"node": {"sequenceNo": 42}}})
        result = orchestrator_check_occupancy(port, plan)
        assert result.items[0].conflict is True
        assert result.items[0].conflict_reason == OCCUPIED
