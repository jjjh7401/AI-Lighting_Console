"""Patch-sheet builder + renderer (SPEC-COPILOT-PAPERWORK-001).

``build_patch_sheet`` rides ``server.prechk.inventory.read_inventory`` — the
SAME chokepoint the pre-check tool uses — so this suite fakes an
``InventoryPort`` (query_state + query_property) the same shape those tests
use, never a real console.
"""

from __future__ import annotations

import pytest

from server.paperwork.data import PatchSheet, build_patch_sheet
from server.paperwork.render import render_patch_sheet
from server.prechk.inventory import FIXTURE_ROOT, InventoryReadError


class FakeInventoryPort:
    """Fake StateQueryPort + PropertyQueryPort backed by dicts."""

    def __init__(self, states: dict[str, dict], properties: dict[tuple[str, str], dict]):
        self._states = states
        self._properties = properties
        self.state_queries: list[str] = []
        self.property_queries: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_queries.append(path)
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_queries.append((path, property_name))
        key = (path, property_name)
        if key not in self._properties:
            raise LookupError(f"unknown property: {key}")
        return self._properties[key]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _two_fixture_port() -> FakeInventoryPort:
    states = {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 2},
            "children": [{"i": 1, "name": "Spot 1"}, {"i": 2, "name": "Wash 1"}],
        }
    }
    properties = {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
        # slot 2: address does not parse — must degrade to raw text, not 0/1.
        (f"{FIXTURE_ROOT}/2", "Patch"): _prop("not-an-address"),
        (f"{FIXTURE_ROOT}/2", "FixtureType"): _prop("Wash Fixture"),
        (f"{FIXTURE_ROOT}/2", "Mode"): _prop("16bit"),
        (f"{FIXTURE_ROOT}/2", "Name"): _prop("Wash 1"),
    }
    return FakeInventoryPort(states, properties)


class TestBuildPatchSheet:
    def test_builds_one_row_per_observed_fixture(self):
        sheet = build_patch_sheet(_two_fixture_port())
        assert isinstance(sheet, PatchSheet)
        assert [row.slot for row in sheet.rows] == [1, 2]
        assert [row.name for row in sheet.rows] == ["Spot 1", "Wash 1"]

    def test_parses_the_universe_and_address_out_of_patch(self):
        sheet = build_patch_sheet(_two_fixture_port())
        row = sheet.rows[0]
        assert row.universe == 1
        assert row.address == 1
        assert row.fixture_type == "Robe MegaPointe"
        assert row.mode == "Standard"

    def test_a_malformed_address_degrades_to_raw_text_never_a_fabricated_number(self):
        sheet = build_patch_sheet(_two_fixture_port())
        row = sheet.rows[1]
        assert row.universe is None
        assert row.address is None
        assert row.patch_raw == "not-an-address"

    def test_reports_completeness_from_the_inventory_read(self):
        sheet = build_patch_sheet(_two_fixture_port())
        assert sheet.completeness == "complete"
        assert sheet.observed_count == 2
        assert sheet.child_count == 2
        assert sheet.root == FIXTURE_ROOT

    def test_unreadable_root_raises_instead_of_an_empty_sheet(self):
        states = {FIXTURE_ROOT: {"ok": False, "error": "path segment not found"}}
        port = FakeInventoryPort(states, {})
        with pytest.raises(InventoryReadError):
            build_patch_sheet(port)

    def test_a_short_root_snapshot_reports_incomplete(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 3},
                "children": [{"i": 1, "name": "Spot 1"}],
            }
        }
        properties = {
            (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
            (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
            (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
            (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
        }
        port = FakeInventoryPort(states, properties)
        sheet = build_patch_sheet(port)
        assert sheet.completeness == "incomplete"
        assert sheet.observed_count == 1
        assert sheet.child_count == 3


class TestRenderPatchSheet:
    def test_renders_a_self_contained_html_document(self):
        sheet = build_patch_sheet(_two_fixture_port())
        html = render_patch_sheet(sheet)
        assert html.startswith("<!doctype html>")
        assert "<style>" in html
        assert "<link " not in html  # no external stylesheet
        assert "<script" not in html  # no external/inline script needed either
        assert "Spot 1" in html
        assert "Robe MegaPointe" in html

    def test_escapes_fixture_names_against_html_injection(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 1},
                "children": [{"i": 1, "name": "<script>alert(1)</script>"}],
            }
        }
        properties = {
            (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
            (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Spot"),
            (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
            (f"{FIXTURE_ROOT}/1", "Name"): _prop("<script>alert(1)</script>"),
        }
        sheet = build_patch_sheet(FakeInventoryPort(states, properties))
        html = render_patch_sheet(sheet)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_empty_sheet_still_renders_a_valid_document(self):
        states = {
            FIXTURE_ROOT: {
                "ok": True,
                "node": {"name": "Fixtures", "class": "Container", "childCount": 0},
                "children": [],
            }
        }
        sheet = build_patch_sheet(FakeInventoryPort(states, {}))
        html = render_patch_sheet(sheet)
        assert "No fixtures observed." in html
