"""Preset-pool browsing API (``server/web/presets_api.py``) — the on-demand
half of the dashboard preset design.

Four properties this file exists to hold:

* The pool number the client supplies is validated against the pool LISTING
  the console just returned — an unlisted number is a 404, never a guessed
  path read, and a TRUNCATED listing says so in the refusal.
* Contents are fetched fresh per call (two ``query_state`` reads, no shared
  drilldown budget) and carry the responder's own completeness signals.
* A name-only slot (no real ``no``) degrades honestly instead of being
  numbered by position — the shared ``rig_object`` rule.
* The module holds NO execution surface: a source scan pins that it never
  imports ``server.bridge`` or an execution-capable port.
"""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.web.presets_api import PresetsDeps, build_presets_router

POOLS_PATH = "DataPool/PresetPools"


class _StatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


def _payload(path: str, children: list[dict], *, truncated: bool = False) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": children,
        "node": {"childCount": len(children)},
        "truncated": truncated,
    }


def _client(tree: dict[str, dict]) -> tuple[TestClient, _StatePort]:
    port = _StatePort(tree)
    app = FastAPI()
    app.include_router(build_presets_router(PresetsDeps(state_port=port)))
    return TestClient(app), port


def _default_tree(*, pool_truncated: bool = False, pools_truncated: bool = False) -> dict:
    return {
        POOLS_PATH: _payload(
            POOLS_PATH,
            [{"i": 1, "name": "Dimmer"}, {"i": 21, "name": "All 1"}],
            truncated=pools_truncated,
        ),
        f"{POOLS_PATH}/21": _payload(
            f"{POOLS_PATH}/21",
            [{"i": 1, "name": "Breath FX"}, {"i": 2, "name": "Snap Pulse"}, {"name": "ghost"}],
            truncated=pool_truncated,
        ),
    }


class TestListPools:
    def test_the_pool_listing_rides_the_shared_rig_shape(self):
        client, _port = _client(_default_tree())
        body = client.get("/api/presets").json()
        assert body["pools"] == [
            {"no": 1, "name": "Dimmer"},
            {"no": 21, "name": "All 1"},
        ]
        assert body["truncated"] is False
        assert body["total"] == 2

    def test_an_unreachable_console_is_a_502_not_an_empty_list(self):
        client, _port = _client({})
        response = client.get("/api/presets")
        assert response.status_code == 502
        assert "읽지 못했습니다" in response.json()["detail"]


class TestReadPool:
    def test_one_pool_costs_exactly_two_reads_and_returns_fresh_contents(self):
        client, port = _client(_default_tree())
        body = client.get("/api/presets/21").json()
        assert port.queried == [POOLS_PATH, f"{POOLS_PATH}/21"]
        assert body["pool"] == {"no": 21, "name": "All 1"}
        # The name-only "ghost" child degrades to a name-only entry — never
        # numbered by its listing position.
        assert body["presets"] == [
            {"no": 1, "name": "Breath FX"},
            {"no": 2, "name": "Snap Pulse"},
            {"name": "ghost"},
        ]
        assert body["total"] == 3

    def test_an_unlisted_pool_is_a_404_before_any_pool_read(self):
        client, port = _client(_default_tree())
        response = client.get("/api/presets/99")
        assert response.status_code == 404
        assert port.queried == [POOLS_PATH]

    def test_a_truncated_pool_listing_names_the_uncertainty_in_the_404(self):
        client, _port = _client(_default_tree(pools_truncated=True))
        response = client.get("/api/presets/99")
        assert response.status_code == 404
        assert "잘려 있어" in response.json()["detail"]

    def test_the_pools_own_truncation_flag_rides_through(self):
        client, _port = _client(_default_tree(pool_truncated=True))
        assert client.get("/api/presets/21").json()["truncated"] is True

    def test_a_pool_read_failure_is_a_502(self):
        tree = _default_tree()
        del tree[f"{POOLS_PATH}/21"]
        client, _port = _client(tree)
        assert client.get("/api/presets/21").status_code == 502


class TestNoExecutionSurface:
    def test_the_module_never_imports_the_send_surface(self):
        source = Path("server/web/presets_api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
        forbidden = [m for m in modules if m.startswith("server.bridge")]
        assert forbidden == []
        assert "execute" not in source.replace("execution-capable", "")
