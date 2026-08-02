"""Occupancy fetch now lives in server.orchestrator (T-J) — see module docstring
in server/orchestrator/layout_occupancy.py for the layering rationale.

``server/tests/test_web_layout_occupancy.py`` keeps exercising the same
behavior through the backward-compatible ``server.web.layout_occupancy``
re-export; this file pins that the two import paths are the SAME objects
(not two independent copies that could drift), plus a direct import-path
smoke test.
"""

from __future__ import annotations

from server.looks.layout import OCCUPIED, plan_layout
from server.orchestrator.layout_occupancy import check_occupancy as orchestrator_check_occupancy
from server.orchestrator.layout_occupancy import (
    fetch_executor_states as orchestrator_fetch_executor_states,
)
from server.tests.busking_fixtures import make_bundle, make_look
from server.web.layout_occupancy import check_occupancy as web_check_occupancy
from server.web.layout_occupancy import fetch_executor_states as web_fetch_executor_states


class _FakeStatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree

    def query_state(self, path: str) -> dict:
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


class TestWebReExportIsTheSameObject:
    def test_check_occupancy_is_identical_across_both_import_paths(self):
        assert web_check_occupancy is orchestrator_check_occupancy

    def test_fetch_executor_states_is_identical_across_both_import_paths(self):
        assert web_fetch_executor_states is orchestrator_fetch_executor_states


class TestDirectOrchestratorImport:
    def test_an_occupied_target_becomes_a_flagged_conflict(self):
        bundle = make_bundle((make_look("intro", "Intro Wash", dynamics=1),), genre="rock")
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        port = _FakeStatePort({f"Executor {target}": {"node": {"sequenceNo": 42}}})
        result = orchestrator_check_occupancy(port, plan)
        assert result.items[0].conflict is True
        assert result.items[0].conflict_reason == OCCUPIED
