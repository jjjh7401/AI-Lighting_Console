"""Preset-list builder + renderer (SPEC-COPILOT-PAPERWORK-001).

``build_preset_list`` rides the SAME ``collect_rig_sections`` drilldown
helper as ``build_cue_sheet``, over the preset-pools section
(``DataPool/PresetPools``): one level into each preset TYPE, listing what is
actually stored inside it.
"""

from __future__ import annotations

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
from server.paperwork.data import PoolListing, build_preset_list
from server.paperwork.render import render_preset_list

_PRESET_POOLS_PATH = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


class FakeStatePort:
    def __init__(self, tree: dict[str, dict]):
        self._tree = tree

    def query_state(self, path: str) -> dict:
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
        _PRESET_POOLS_PATH: _snapshot([(1, "Dimmer"), (2, "Color")]),
        f"{_PRESET_POOLS_PATH}/1": _snapshot([(5, "Warm 50%")]),
        f"{_PRESET_POOLS_PATH}/2": _snapshot([]),
    }


class TestBuildPresetList:
    def test_one_pool_per_preset_type(self):
        listing = build_preset_list(FakeStatePort(_tree()))
        assert isinstance(listing, PoolListing)
        assert [pool.name for pool in listing.pools] == ["Dimmer", "Color"]

    def test_stored_presets_carry_the_real_pool_slot(self):
        listing = build_preset_list(FakeStatePort(_tree()))
        dimmer = listing.pools[0]
        assert [item.no for item in dimmer.items] == [5]
        assert [item.name for item in dimmer.items] == ["Warm 50%"]

    def test_a_verified_empty_type_is_distinct_from_unavailable(self):
        listing = build_preset_list(FakeStatePort(_tree()))
        color = listing.pools[1]
        assert color.items == ()
        assert color.contents_unavailable is False

    def test_an_unreachable_drill_marks_contents_unavailable(self):
        tree = {_PRESET_POOLS_PATH: _snapshot([(1, "Dimmer")])}
        # No f"{_PRESET_POOLS_PATH}/1" entry -> drill_into's per-object query fails.
        listing = build_preset_list(FakeStatePort(tree))
        assert listing.pools[0].contents_unavailable is True

    def test_console_unreachable_is_reported_not_raised(self):
        listing = build_preset_list(FakeStatePort({}))
        assert listing.pools == ()
        assert listing.unavailable_reason == "console_unreachable"

    def test_a_path_override_is_honored(self):
        tree = {"Custom/Path": _snapshot([(1, "Dimmer")]), "Custom/Path/1": _snapshot([])}
        listing = build_preset_list(FakeStatePort(tree), preset_pools_path="Custom/Path")
        assert listing.path == "Custom/Path"
        assert listing.pools[0].name == "Dimmer"


class TestRenderPresetList:
    def test_renders_a_self_contained_html_document(self):
        listing = build_preset_list(FakeStatePort(_tree()))
        html = render_preset_list(listing)
        assert html.startswith("<!doctype html>")
        assert "<style>" in html
        assert "<link " not in html
        assert "Dimmer" in html
        assert "Warm 50%" in html

    def test_escapes_preset_names_against_html_injection(self):
        tree = {
            _PRESET_POOLS_PATH: _snapshot([(1, "Dimmer")]),
            f"{_PRESET_POOLS_PATH}/1": _snapshot([(1, "</table><script>x</script>")]),
        }
        html = render_preset_list(build_preset_list(FakeStatePort(tree)))
        assert "<script>x</script>" not in html
