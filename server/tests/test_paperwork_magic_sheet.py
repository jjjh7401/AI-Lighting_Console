"""Reduced magic sheet (P0-5).

The FULL magic sheet — a group tile listing the fixtures it holds — is not
buildable and never will be by fixing this code: group membership is not
readable on grandMA3 (SPEC-COPILOT-GROUPGEN-001 walked the whole ``prop``
ladder and the ``COUNT`` accessors, and the fabricated control group is what
proves the zeros are real reads). What IS buildable is the reduced form:
group/preset NAMES, a patch SUMMARY, and placement COORDINATES — the last of
which SPATIAL-001 opened after the reduced sheet was first proposed, so the
plan view is more possible now than the proposal assumed.

These tests hold that line in both directions. The sheet must carry the three
readable axes, and it must never let a reader infer the fourth.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset
from server.paperwork.data import GROUP_MEMBERSHIP_UNAVAILABLE, build_magic_sheet
from server.paperwork.render import render_magic_sheet
from server.prechk.inventory import FIXTURE_ROOT

_GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]
_PRESET_POOLS_PATH = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


class FakeConsolePort:
    """StateQueryPort + PropertyQueryPort on one object, dict-backed."""

    def __init__(self, states: dict[str, dict], properties: dict[tuple[str, str], dict]):
        self._states = states
        self._properties = properties

    def query_state(self, path: str) -> dict:
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        key = (path, property_name)
        if key not in self._properties:
            raise LookupError(f"unknown property: {key}")
        return self._properties[key]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _states(fixture_count: int = 2) -> dict[str, dict]:
    children = [{"i": slot, "name": f"Spot {slot}"} for slot in range(1, fixture_count + 1)]
    return {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": fixture_count},
            "children": children,
        },
        # Two REAL groups, each carrying children in the snapshot. The reduced
        # sheet must still refuse to say what is in them — see
        # test_group_children_in_the_snapshot_are_not_rendered_as_membership.
        _GROUPS_PATH: {
            "children": [
                {"i": 1, "name": "Front Truss"},
                {"i": 2, "name": "Back Truss"},
            ]
        },
        _PRESET_POOLS_PATH: {"children": [{"i": 1, "name": "Dimmer"}, {"i": 4, "name": "Color"}]},
    }


def _properties(fixture_count: int = 2, *, unreadable_slot: int | None = None) -> dict:
    out: dict[tuple[str, str], dict] = {}
    for slot in range(1, fixture_count + 1):
        base = f"{FIXTURE_ROOT}/{slot}"
        out[(base, "Patch")] = _prop(f"1.{slot:03d}")
        out[(base, "FixtureType")] = _prop("Robe MegaPointe")
        out[(base, "Mode")] = _prop("Standard")
        out[(base, "Name")] = _prop(f"Spot {slot}")
        if slot == unreadable_slot:
            out[(base, "fid")] = {"ok": False, "error": "no such property"}
            continue
        out[(base, "fid")] = _prop(str(slot + 100))
        out[(base, "posx")] = _prop(f"{slot}.5")
        out[(base, "posy")] = _prop("0.0")
        out[(base, "posz")] = _prop("-3.25")
    return out


def _sheet(fixture_count: int = 2, **kwargs):
    port = FakeConsolePort(_states(fixture_count), _properties(fixture_count, **kwargs))
    return build_magic_sheet(port)


class TestTheThreeReadableAxes:
    def test_group_and_preset_names_are_carried(self):
        sheet = _sheet()
        assert sheet.group_names == ("Front Truss", "Back Truss")
        assert sheet.preset_names == ("Dimmer", "Color")

    def test_the_patch_summary_is_a_summary_not_the_full_row_table(self):
        sheet = _sheet()
        assert sheet.patch is not None
        assert sheet.patch.observed_count == 2
        assert sheet.patch.child_count == 2
        # The patch sheet already prints the rows; the magic sheet renders only
        # the counts, so a reader has ONE place to check for the row detail.
        html = render_magic_sheet(sheet)
        assert "Robe MegaPointe" not in html

    def test_placements_carry_fid_and_all_three_axes(self):
        sheet = _sheet()
        assert [(p.fid, p.name, p.x, p.y, p.z) for p in sheet.placements] == [
            (101, "Spot 1", 1.5, 0.0, -3.25),
            (102, "Spot 2", 2.5, 0.0, -3.25),
        ]
        assert sheet.placements_complete is True

    def test_the_rendered_page_shows_every_placement_row(self):
        html = render_magic_sheet(_sheet())
        assert "Spot 1" in html
        assert "Spot 2" in html
        assert "1.5" in html and "-3.25" in html


class TestGroupMembershipIsNeverImplied:
    """W1 — the wall this sheet exists beside. Not a nicety: group names above
    a coordinate table is an invitation to read membership off adjacency."""

    def test_the_caveat_is_a_required_field_carrying_the_platform_reason(self):
        sheet = _sheet()
        assert sheet.group_membership_unavailable == GROUP_MEMBERSHIP_UNAVAILABLE
        assert "판독되지 않는다" in sheet.group_membership_unavailable

    def test_the_caveat_renders_before_the_group_tiles(self):
        html = render_magic_sheet(_sheet())
        caveat_at = html.index("판독되지 않는다")
        tile_at = html.index("Front Truss")
        assert caveat_at < tile_at

    def test_the_caveat_renders_even_when_there_are_no_groups(self):
        """Non-vacuity in the direction that matters: a build that found no
        groups and a build that could never look must read identically."""
        states = _states()
        states[_GROUPS_PATH] = {"children": []}
        sheet = build_magic_sheet(FakeConsolePort(states, _properties()))
        assert sheet.group_names == ()
        assert render_magic_sheet(sheet).count("판독되지 않는다") == 1

    def test_group_children_in_the_snapshot_are_not_rendered_as_membership(self):
        """The enumeration CAN carry children; drilling them is what is
        forbidden. A fixture name planted inside a group must not surface as
        that group's content — if it did, the sheet would be asserting a
        membership nobody read."""
        states = _states()
        states[f"{_GROUPS_PATH}/1"] = {"children": [{"i": 1, "name": "PLANTED MEMBER"}]}
        sheet = build_magic_sheet(FakeConsolePort(states, _properties()))
        assert "PLANTED MEMBER" not in render_magic_sheet(sheet)


class TestTruncateTwoShapeHandling:
    """SPEC-COPILOT-TRUNCATE-001: a partial spatial read arrives under a
    DIFFERENT key with no ``fixtures`` at all, so a consumer that ignored the
    branch would raise rather than silently shorten."""

    def test_an_unreadable_fixture_makes_the_read_partial_with_arithmetic(self):
        sheet = _sheet(2, unreadable_slot=2)
        assert sheet.placements_complete is False
        expected, received, unseen = sheet.placements_missing
        assert (expected, received, unseen) == (2, 1, 1)
        assert len(sheet.placements) == 1
        assert any("Spot 2" in line for line in sheet.placements_unreadable)

    def test_the_shortfall_prints_as_numbers_not_as_an_adjective(self):
        html = render_magic_sheet(_sheet(2, unreadable_slot=2))
        # REQ-TRUNCATE-004 survives the change of medium: how many, not "some".
        assert "expected 2" in html
        assert "received 1" in html
        assert "unseen 1" in html

    def test_a_complete_read_prints_no_shortfall_caveat(self):
        html = render_magic_sheet(_sheet())
        assert "expected" not in html
        assert "배치 좌표가 전량이 아니다" not in html


class TestPerSectionDegradation:
    """One dead section must not take the page down — the other sections were
    genuinely read and throwing them away reports less than was observed."""

    def test_a_dead_group_pool_still_yields_placements_and_says_why(self):
        states = _states()
        del states[_GROUPS_PATH]
        sheet = build_magic_sheet(FakeConsolePort(states, _properties()))
        assert sheet.group_names == ()
        assert sheet.groups_unavailable_reason is not None
        assert len(sheet.placements) == 2
        html = render_magic_sheet(sheet)
        assert "The group pool did not arrive" in html

    def test_a_dead_preset_pool_still_yields_groups(self):
        states = _states()
        del states[_PRESET_POOLS_PATH]
        sheet = build_magic_sheet(FakeConsolePort(states, _properties()))
        assert sheet.preset_names == ()
        assert sheet.presets_unavailable_reason is not None
        assert sheet.group_names == ("Front Truss", "Back Truss")

    def test_an_empty_pool_and_a_dead_pool_do_not_render_the_same(self):
        """Non-vacuity: "no presets" and "the console never answered" are
        different facts and the page must not collapse them."""
        empty_states = _states()
        empty_states[_PRESET_POOLS_PATH] = {"children": []}
        empty_html = render_magic_sheet(
            build_magic_sheet(FakeConsolePort(empty_states, _properties()))
        )
        dead_states = _states()
        del dead_states[_PRESET_POOLS_PATH]
        dead_html = render_magic_sheet(
            build_magic_sheet(FakeConsolePort(dead_states, _properties()))
        )
        assert "No preset pools in this showfile." in empty_html
        assert "No preset pools in this showfile." not in dead_html
        assert "The preset pools did not arrive" in dead_html


class TestToolRegistration:
    def _dispatch(self, port, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)
        registry = build_toolset(execution_port=_DummyExecutionPort(), state_port=port)
        return registry.dispatch(ToolCall(id="c1", name="build_magic_sheet", arguments={}))

    def test_dispatch_returns_a_path_and_a_summary_never_html(self, tmp_path, monkeypatch):
        port = FakeConsolePort(_states(), _properties())
        execution = self._dispatch(port, tmp_path, monkeypatch)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["group_count"] == 2
        assert payload["preset_pool_count"] == 2
        assert payload["placement_count"] == 2
        assert payload["placements_complete"] is True
        assert "<html" not in execution.result.content

    def test_the_result_itself_states_membership_is_unreadable(self, tmp_path, monkeypatch):
        """A model that reads only this JSON — never opening the HTML — must
        not conclude the sheet answers "what is in this group"."""
        port = FakeConsolePort(_states(), _properties())
        payload = json.loads(self._dispatch(port, tmp_path, monkeypatch).result.content)
        assert payload["group_membership_readable"] is False

    def test_an_unwired_property_port_is_an_error_not_an_empty_plan_view(self):
        registry = build_toolset(
            execution_port=_DummyExecutionPort(), state_port=_StateOnlyPort(_states())
        )
        execution = registry.dispatch(ToolCall(id="c1", name="build_magic_sheet", arguments={}))
        assert execution.result.is_error is True
        assert "property reads are not wired" in execution.result.content

    def test_dispatch_never_calls_the_execution_port(self, tmp_path, monkeypatch):
        port = FakeConsolePort(_states(), _properties())
        assert self._dispatch(port, tmp_path, monkeypatch).result.is_error is False


class _DummyExecutionPort:
    def execute(self, command: str):  # pragma: no cover - never called by this tool
        raise AssertionError("build_magic_sheet must never call execution_port")


class _StateOnlyPort:
    """A state port with NO ``query_property`` — the unwired-capability case."""

    def __init__(self, states: dict[str, dict]):
        self._states = states

    def query_state(self, path: str) -> dict:
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]
