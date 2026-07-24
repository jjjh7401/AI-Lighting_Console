"""Console-info dashboard catalog builder (SPEC-COPILOT-DASHUI-001 M2).

The dash catalog's server half: groups / preset pools (drilled) / macros /
plugins / a fixture-count summary / an executor-resolution report — all
info-only by shape (REQ-DASHUI-007), all sourced through the SAME
gate-audited ``state_port`` seam the rig-context tool and the playback
catalog use.

Every test drives the builder through an in-memory ``StateQueryPort`` fake —
the same shape ``gate.state_port`` presents — so nothing here can reach the
console or the OSC send surface (REQ-DASHUI-016/019).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.dash import (
    DASH_EXECUTOR_VERIFY_QUERY_CAP,
    DASH_PRESET_POOL_QUERY_CAP,
    build_dash_catalog,
    dash_catalog_snapshot,
)
from server.web.messages import PROTOCOL_VERSION

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

DASH_MODULE = Path(__file__).resolve().parents[1] / "web" / "dash.py"


# -- fixtures -------------------------------------------------------------------


class FakeStatePort:
    """Fake StateQueryPort backed by path -> decoded snapshot payload.

    Mirrors ``server/tests/test_web_panel.py::FakeStatePort`` — the dashboard
    reads the console through the SAME gate-audited seam the playback
    catalog and the rig-context tool use.
    """

    def __init__(self, tree: dict):
        self.tree = tree
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        if path not in self.tree:
            raise LookupError(f"unknown object path: {path}")
        return self.tree[path]


class DeadStatePort:
    """Every query fails — the console did not answer at all."""

    def query_state(self, path: str) -> dict:
        raise TimeoutError("no reply")


def _snapshot(path: str, entries: list[tuple[int | None, str]], **extra) -> dict:
    children = []
    for number, name in entries:
        child: dict[str, object] = {"name": name}
        if number is not None:
            child["i"] = number
        children.append(child)
    payload: dict[str, object] = {"v": 1, "kind": "state", "path": path, "children": children}
    payload.update(extra)
    return payload


def _identity(name: str) -> dict:
    """One "Executor <n>" resolve reply — the shape EXECBODY-001's
    ObjectList-backed resolve_path address form returns (node.name)."""
    return {"v": 1, "kind": "state", "ok": True, "node": {"name": name, "class": "Executor"}}


def _rig_tree() -> dict:
    return {
        "DataPool/Groups": _snapshot("DataPool/Groups", [(3, "Vocals"), (11, "Drums")]),
        "DataPool/PresetPools": _snapshot("DataPool/PresetPools", [(1, "Dimmer"), (2, "Color")]),
        "DataPool/PresetPools/1": _snapshot("DataPool/PresetPools/1", [(5, "Warm 50%")]),
        "DataPool/PresetPools/2": _snapshot("DataPool/PresetPools/2", []),
        "DataPool/Macros": _snapshot("DataPool/Macros", [(3, "Blackout FX"), (9, "Danger Macro")]),
        "DataPool/Plugins": _snapshot("DataPool/Plugins", [(1, "AutoFocus")]),
        "Patch/Stages/1/Fixtures": _snapshot(
            "Patch/Stages/1/Fixtures",
            [(1, "Spot 1"), (2, "Wash 1"), (3, "Wash 2")],
            node={"name": "Fixtures", "class": "Container", "childCount": 3},
        ),
        "DataPool/Pages": _snapshot("DataPool/Pages", [(1, "Main")]),
        # 101 resolves (name matches its "Executor 101" identity); 102's
        # identity query fails outright; 103 resolves to a DIFFERENT name —
        # both 102 and 103 must land as unresolved, for different reasons.
        "DataPool/Pages/1": _snapshot(
            "DataPool/Pages/1", [(101, "Cyan Look"), (102, "Chase"), (103, "Storm")]
        ),
        "Executor 101": _identity("Cyan Look"),
        "Executor 103": _identity("Some Other Object"),
    }


def _section(sections: list[dict], name: str) -> dict:
    for section in sections:
        if section["name"] == name:
            return section
    raise AssertionError(f"no section named {name!r}: {[s['name'] for s in sections]}")


def _ids(items: list[dict]) -> list[int]:
    return [item["no"] for item in items]


# -- accuracy (AC-DASHUI-002) ---------------------------------------------------


class TestDashCatalogAccuracy:
    def test_every_section_the_ia_names_is_present_in_priority_order(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        assert [s["name"] for s in sections] == [
            "groups",
            "preset_pools",
            "macros",
            "plugins",
            "fixtures",
            "executors",
        ]

    def test_group_items_carry_the_real_pool_number_never_a_list_position(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        groups = _section(sections, "groups")
        assert _ids(groups["items"]) == [3, 11]

    def test_macro_items_are_present_and_non_contiguous(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        macros = _section(sections, "macros")
        assert _ids(macros["items"]) == [3, 9]

    def test_plugin_items_are_present(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        plugins = _section(sections, "plugins")
        assert _ids(plugins["items"]) == [1]

    def test_a_child_without_a_slot_number_is_not_an_item(self):
        tree = _rig_tree()
        tree["DataPool/Groups"] = _snapshot(
            "DataPool/Groups", [(3, "Vocals"), (None, "Unnumbered")]
        )
        sections = build_dash_catalog(FakeStatePort(tree))
        groups = _section(sections, "groups")
        assert "Unnumbered" not in [i["name"] for i in groups["items"]]
        assert _ids(groups["items"]) == [3]

    def test_no_dash_item_ever_carries_a_fire_address(self):
        # Structural half of REQ-DASHUI-007 / AC-DASHUI-003: dash_section's
        # own construction-time refusal already proves this per-item
        # (test_web_messages.py), so this is the integration-level echo —
        # every section this builder actually produces stays info-only.
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        for section in sections:
            for item in section["items"]:
                assert "target_kind" not in item
                assert "target" not in item
                assert "id" not in item


# -- completeness (AC-DASHUI-002) ------------------------------------------------


class TestDashCatalogCompleteness:
    def test_truncated_is_propagated_not_dropped(self):
        tree = _rig_tree()
        tree["DataPool/Groups"] = _snapshot("DataPool/Groups", [(3, "Vocals")], truncated=True)
        sections = build_dash_catalog(FakeStatePort(tree))
        assert _section(sections, "groups")["truncated"] is True
        assert _section(sections, "macros")["truncated"] is False

    def test_every_resolved_section_reports_ok(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        # executors' own status is folded into "ok" whenever its own pages
        # path resolves — see TestExecutorResolution for its item-level
        # resolved/unresolved reporting.
        assert {s["status"] for s in sections} == {"ok"}


class TestDashCatalogFailureReasons:
    def test_a_sibling_answering_makes_the_failure_a_path_defect(self):
        tree = _rig_tree()
        del tree["DataPool/Macros"]
        sections = build_dash_catalog(FakeStatePort(tree))
        assert _section(sections, "groups")["status"] == "ok"
        assert _section(sections, "macros")["status"] == "path_not_resolved"

    def test_nothing_answering_is_an_unreachable_console(self):
        sections = build_dash_catalog(DeadStatePort())
        assert {s["status"] for s in sections} == {"console_unreachable"}
        assert all(s["items"] == [] for s in sections)

    def test_the_two_failure_reasons_are_never_merged(self):
        tree = _rig_tree()
        del tree["DataPool/Macros"]
        partial = build_dash_catalog(FakeStatePort(tree))
        dead = build_dash_catalog(DeadStatePort())
        assert _section(partial, "macros")["status"] != _section(dead, "macros")["status"]

    def test_a_failed_section_contributes_no_items(self):
        sections = build_dash_catalog(DeadStatePort())
        assert all(s["items"] == [] for s in sections)


# -- preset pools drilldown (REQ-DASHUI-005/008, acceptance.md §D edge 3) -------


class TestPresetPoolsDrilldown:
    def test_a_stored_pool_reports_its_stored_count(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        presets = _section(sections, "preset_pools")
        dimmer = next(i for i in presets["items"] if i["no"] == 1)
        assert dimmer["meta"] == {"stored_count": 1}

    def test_a_verified_empty_pool_is_distinct_from_contents_unavailable(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        presets = _section(sections, "preset_pools")
        color = next(i for i in presets["items"] if i["no"] == 2)
        # "the pool exists" AND "verified empty" — never confused with a pool
        # that could not be opened at all.
        assert color["meta"] == {"stored_count": 0}

    def test_a_pool_that_cannot_be_opened_is_contents_unavailable(self):
        tree = _rig_tree()
        tree["DataPool/PresetPools"] = _snapshot(
            "DataPool/PresetPools", [(1, "Dimmer"), (2, "Color"), (3, "Gobo")]
        )
        # Gobo (3) has no "DataPool/PresetPools/3" entry -> drill fails.
        sections = build_dash_catalog(FakeStatePort(tree))
        presets = _section(sections, "preset_pools")
        assert presets["contents_unavailable"] is True
        gobo = next(i for i in presets["items"] if i["no"] == 3)
        assert gobo["meta"] == {"contents_unavailable": True}

    def test_the_drilldown_budget_is_separate_from_the_executor_budget(self):
        # design.md §5 / plan.md §B M2 item 2 — a single shared 16-cap would
        # always cap out with ~8-10 preset TYPES sharing it with the
        # executor page-walk+verify queries; each concern's cap is bounded
        # independently instead.
        tree = _rig_tree()
        many_pools = [(n, f"Pool {n}") for n in range(1, 15)]
        tree["DataPool/PresetPools"] = _snapshot("DataPool/PresetPools", many_pools)
        for number, _ in many_pools:
            tree[f"DataPool/PresetPools/{number}"] = _snapshot(
                f"DataPool/PresetPools/{number}", [(1, "Stored")]
            )
        sections = build_dash_catalog(
            FakeStatePort(tree), preset_pool_query_cap=DASH_PRESET_POOL_QUERY_CAP
        )
        presets = _section(sections, "preset_pools")
        assert presets["drilldown_capped"] is True
        # A capped walk still yields the pools it DID open.
        assert len(presets["items"]) == len(many_pools)  # every pool listed
        # Pools past the budget never got a "contents" key at all — their
        # dash_item carries no meta rather than a guessed stored_count.
        opened = [i for i in presets["items"] if i.get("meta", {}).get("stored_count") == 1]
        assert len(opened) == DASH_PRESET_POOL_QUERY_CAP


# -- fixtures count summary (REQ-DASHUI-009) -------------------------------------


class TestFixturesSummary:
    def test_the_section_carries_a_count_not_a_listing(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        fixtures = _section(sections, "fixtures")
        assert len(fixtures["items"]) == 1
        assert fixtures["items"][0]["meta"] == {"count": 3}

    def test_no_fixture_slot_number_is_ever_presented(self):
        # design.md §2 point 4 — "슬롯≠FID 함정도 목록 미제시로 구조적으로
        # 회피" — the fixtures section item carries the synthetic no=1
        # placeholder, never a real patch slot.
        tree = _rig_tree()
        tree["Patch/Stages/1/Fixtures"] = _snapshot(
            "Patch/Stages/1/Fixtures",
            [(7, "Spot 7"), (12, "Wash 12")],
            node={"name": "Fixtures", "class": "Container", "childCount": 2},
        )
        sections = build_dash_catalog(FakeStatePort(tree))
        fixtures = _section(sections, "fixtures")
        assert "Spot 7" not in json.dumps(fixtures)
        assert 7 not in _ids(fixtures["items"])
        assert 12 not in _ids(fixtures["items"])

    def test_the_count_falls_back_to_the_visible_length_without_a_childcount_hint(self):
        tree = _rig_tree()
        tree["Patch/Stages/1/Fixtures"] = _snapshot(
            "Patch/Stages/1/Fixtures", [(1, "Spot 1"), (2, "Wash 1")]
        )
        sections = build_dash_catalog(FakeStatePort(tree))
        fixtures = _section(sections, "fixtures")
        assert fixtures["items"][0]["meta"] == {"count": 2}


# -- executor resolution transparency (REQ-DASHUI-011) ---------------------------


class TestExecutorResolution:
    def test_a_verified_candidate_is_reported_resolved(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        executors = _section(sections, "executors")
        resolved = next(i for i in executors["items"] if i["no"] == 101)
        assert resolved["meta"] == {"resolved": True}

    def test_an_unqueryable_candidate_is_reported_unresolved(self):
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        executors = _section(sections, "executors")
        unresolved = next(i for i in executors["items"] if i["no"] == 102)
        assert unresolved["meta"] == {"resolved": False}

    def test_a_name_mismatched_candidate_is_reported_unresolved(self):
        # The console DID answer "Executor 103" — with a DIFFERENT object.
        # Confirming a query succeeded is not enough; the identity must match
        # (EXECBODY AC-016 inherited principle: no offset/position guessing).
        sections = build_dash_catalog(FakeStatePort(_rig_tree()))
        executors = _section(sections, "executors")
        mismatched = next(i for i in executors["items"] if i["no"] == 103)
        assert mismatched["meta"] == {"resolved": False}

    def test_no_child_index_or_offset_math_is_used(self):
        # The FakeStatePort ONLY resolves the exact page-drilled candidate
        # number ("Executor 101") — never a +100 offset or any other guess.
        # If offset math were used, "Executor 201" would have been queried
        # and this port would raise LookupError for it — never a silent
        # wrong-answer. This test pins that no such query happens.
        port = FakeStatePort(_rig_tree())
        build_dash_catalog(port)
        assert "Executor 201" not in port.queries
        assert "Executor 202" not in port.queries
        assert "Executor 203" not in port.queries

    def test_panel_catalogs_own_executor_generation_is_unaffected(self):
        # This module's resolution report is read-only and additive; the
        # SHOWUI-owned playback catalog builder is a completely separate
        # (and unmodified) code path — see server/tests/test_web_panel.py.
        from server.web.panel import build_catalog

        playback = build_catalog(FakeStatePort(_rig_tree()))
        executor_ids = [i["id"] for i in playback.items if i["id"].startswith("executor:")]
        # All three page-drilled candidates ride the (unchanged) playback
        # catalog — resolution status does not filter it at M2.
        assert executor_ids == ["executor:101", "executor:102", "executor:103"]

    def test_the_verify_budget_is_separate_from_the_page_walk_budget(self):
        tree = _rig_tree()
        many = [(100 + n, f"Exec {100 + n}") for n in range(1, 20)]
        tree["DataPool/Pages/1"] = _snapshot("DataPool/Pages/1", many)
        for number, name in many:
            tree[f"Executor {number}"] = _identity(name)
        sections = build_dash_catalog(
            FakeStatePort(tree), executor_verify_query_cap=DASH_EXECUTOR_VERIFY_QUERY_CAP
        )
        executors = _section(sections, "executors")
        assert executors["drilldown_capped"] is True
        assert len(executors["items"]) == DASH_EXECUTOR_VERIFY_QUERY_CAP

    def test_a_page_that_cannot_be_opened_is_contents_unavailable(self):
        tree = _rig_tree()
        tree["DataPool/Pages"] = _snapshot("DataPool/Pages", [(1, "Main"), (2, "Spare")])
        # No "DataPool/Pages/2" entry -> that page cannot be opened.
        sections = build_dash_catalog(FakeStatePort(tree))
        executors = _section(sections, "executors")
        assert executors["contents_unavailable"] is True

    def test_no_page_answering_makes_executors_console_unreachable(self):
        tree = _rig_tree()
        del tree["DataPool/Pages"]
        del tree["DataPool/Groups"]
        del tree["DataPool/PresetPools"]
        del tree["DataPool/PresetPools/1"]
        del tree["DataPool/PresetPools/2"]
        del tree["DataPool/Macros"]
        del tree["DataPool/Plugins"]
        del tree["Patch/Stages/1/Fixtures"]
        sections = build_dash_catalog(FakeStatePort(tree))
        assert {s["status"] for s in sections} == {"console_unreachable"}


# -- event builder (AC-DASHUI-001/002) -------------------------------------------


class TestDashCatalogSnapshot:
    def test_the_snapshot_is_a_valid_dash_catalog_event(self):
        event = dash_catalog_snapshot(FakeStatePort(_rig_tree()))
        assert event["v"] == PROTOCOL_VERSION
        assert event["type"] == "dash_catalog"
        json.dumps(event, ensure_ascii=False)  # must be JSON-serializable

    def test_paths_are_overridable_so_a_site_can_move_them(self):
        tree = {"Elsewhere/Groups": _snapshot("Elsewhere/Groups", [(5, "Site Group")])}
        port = FakeStatePort(tree)
        sections = build_dash_catalog(port, paths={"groups": "Elsewhere/Groups"})
        assert "Elsewhere/Groups" in port.queries
        assert _ids(_section(sections, "groups")["items"]) == [5]


# -- architecture boundary (REQ-DASHUI-016/019) ----------------------------------


class TestDashModuleBoundary:
    def test_the_dash_module_never_reaches_the_osc_send_surface(self):
        source = DASH_MODULE.read_text(encoding="utf-8")
        for forbidden in ("server.bridge", "pythonosc"):
            assert forbidden not in source, f"dash.py must not reference {forbidden}"

    def test_the_dash_module_declares_no_execution_surface(self):
        from server.web import dash as dash_module

        assert not hasattr(dash_module, "execute")
        assert not hasattr(dash_module, "screen")


# -- /ws dispatch (M1 handoff gap: dash_catalog_request fell through to
# status_request before M2 wired the else-branch dispatch fix) ------------------


def _deps(tmp_path, provider):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    return WebDeps(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
    )


def _send(ws, **fields) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


class TestDashCatalogRequestDispatch:
    def test_dash_catalog_request_answers_with_a_dash_catalog_event(self, tmp_path):
        deps = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="dash_catalog_request")
            event = ws.receive_json()
        assert event["type"] == "dash_catalog"
        assert isinstance(event["sections"], list)

    def test_dash_catalog_request_no_longer_falls_through_to_status(self, tmp_path):
        # The M1 handoff gap this milestone closes: dash_catalog_request used
        # to land on the `else: # status_request` fallback (app.py:409) and
        # answer with a status frame instead.
        deps = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="dash_catalog_request")
            event = ws.receive_json()
        assert event["type"] != "status"
