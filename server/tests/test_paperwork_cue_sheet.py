"""Cue-sheet builder + renderer (SPEC-COPILOT-PAPERWORK-001).

``build_cue_sheet`` rides ``collect_rig_sections`` — the SAME drilldown
helper ``get_rig_context``/``dash_catalog`` use — over the sequences pool
(``DataPool/Sequences``), one level into each sequence's stored cues.
"""

from __future__ import annotations

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
from server.paperwork.data import PoolListing, build_cue_sheet
from server.paperwork.render import render_cue_sheet

_SEQUENCES_PATH = DEFAULT_RIG_CONTEXT_PATHS["sequences"]


class FakeStatePort:
    def __init__(self, tree: dict[str, dict]):
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


def _snapshot(entries: list[tuple[int | None, str]], **extra) -> dict:
    children = []
    for number, name in entries:
        child: dict[str, object] = {"name": name}
        if number is not None:
            child["i"] = number
        children.append(child)
    payload: dict[str, object] = {"children": children}
    payload.update(extra)
    return payload


def _tree() -> dict[str, dict]:
    return {
        _SEQUENCES_PATH: _snapshot([(1, "Main Show"), (2, "Encore")]),
        f"{_SEQUENCES_PATH}/1": _snapshot([(1, "Cyan Wash"), (2, "Chase")]),
        f"{_SEQUENCES_PATH}/2": _snapshot([]),
    }


class TestBuildCueSheet:
    def test_one_pool_per_sequence(self):
        listing = build_cue_sheet(FakeStatePort(_tree()))
        assert isinstance(listing, PoolListing)
        assert [pool.name for pool in listing.pools] == ["Main Show", "Encore"]
        assert [pool.no for pool in listing.pools] == [1, 2]

    def test_cues_carry_the_real_cue_number_never_a_list_position(self):
        listing = build_cue_sheet(FakeStatePort(_tree()))
        main_show = listing.pools[0]
        assert [item.no for item in main_show.items] == [1, 2]
        assert [item.name for item in main_show.items] == ["Cyan Wash", "Chase"]

    def test_a_verified_empty_sequence_reports_zero_items_not_unavailable(self):
        listing = build_cue_sheet(FakeStatePort(_tree()))
        encore = listing.pools[1]
        assert encore.items == ()
        assert encore.contents_unavailable is False

    def test_a_cue_without_a_slot_index_degrades_to_name_only(self):
        tree = {
            _SEQUENCES_PATH: _snapshot([(71, "Delete Sequence")]),
            f"{_SEQUENCES_PATH}/71": {"children": [{"name": "Store Cue 1"}]},
        }
        listing = build_cue_sheet(FakeStatePort(tree))
        cue = listing.pools[0].items[0]
        assert cue.no is None
        assert cue.name == "Store Cue 1"

    def test_console_unreachable_is_reported_not_raised(self):
        listing = build_cue_sheet(FakeStatePort({}))
        assert listing.pools == ()
        assert listing.unavailable_reason == "console_unreachable"

    def test_drilldown_budget_is_respected(self):
        tree = _tree()
        listing = build_cue_sheet(FakeStatePort(tree), query_cap=0)
        # No cue-level query spent: every sequence must report as un-drilled
        # (no ``items`` observed) or capped, never silently walked anyway.
        assert listing.drilldown_capped is True


class TestRenderCueSheet:
    def test_renders_a_self_contained_html_document(self):
        listing = build_cue_sheet(FakeStatePort(_tree()))
        html = render_cue_sheet(listing)
        assert html.startswith("<!doctype html>")
        assert "<style>" in html
        assert "<link " not in html
        assert "Main Show" in html
        assert "Cyan Wash" in html

    def test_unavailable_listing_still_renders_a_valid_document(self):
        listing = build_cue_sheet(FakeStatePort({}))
        html = render_cue_sheet(listing)
        assert "<!doctype html>" in html
        assert "console_unreachable" in html

    def test_escapes_cue_names_against_html_injection(self):
        tree = {
            _SEQUENCES_PATH: _snapshot([(1, "Main")]),
            f"{_SEQUENCES_PATH}/1": _snapshot([(1, "<img src=x onerror=alert(1)>")]),
        }
        html = render_cue_sheet(build_cue_sheet(FakeStatePort(tree)))
        assert "<img src=x onerror=alert(1)>" not in html
