"""`presetdata` verb — read-only `GetPresetData` window (responder 1.7.0).

The mock `GetPresetData` below returns a PLAUSIBLE nested table. The REAL shape
on grandMA3 onPC 2.4.2 is unobserved — it must be confirmed on the console (see
the PR's 실기 확인 절차). These tests pin the transport contract only: read-only,
windowed by whole top-level entries, same offset/total/truncated convention as
`props` (PROTOCOL.md §4.9), and honest failures.
"""

from __future__ import annotations

import json

from server.bridge.protocol import build_presetdata_query, decode_payload

from .lua_mock_env import TABLE_PROBE_PATH, ResponderHarness, table_props_env

_ENV = table_props_env("{}")


def _harness(get_preset_data_lua: str | None) -> ResponderHarness:
    extra = _ENV + "\n__GPD_CALLS = {}\n"
    if get_preset_data_lua is not None:
        extra += "GetPresetData = " + get_preset_data_lua + "\n"
    return ResponderHarness(extra_env=extra)


def _read(harness: ResponderHarness, request: str) -> dict:
    harness.main(None, request)
    return decode_payload(harness.sent()[-1].payload)


_TWO_GROUP_COLORS = """function(handle, phasers_only, by_fixtures)
  table.insert(__GPD_CALLS, { handle = handle, p = phasers_only, f = by_fixtures })
  return {
    { fixtures = "Group 1", ColorRGB_R = 100, ColorRGB_G = 0, ColorRGB_B = 0 },
    { fixtures = "Group 2", ColorRGB_R = 0, ColorRGB_G = 0, ColorRGB_B = 100 },
  }
end"""

_MANY_ENTRIES = """function()
  local t = {}
  for i = 1, 120 do
    t[i] = { fixtures = "Fixture " .. i .. " member", ColorRGB_R = i }
  end
  return t
end"""


class TestPresetDataVerb:
    def test_replies_json_window_on_state_address(self):
        h = _harness(_TWO_GROUP_COLORS)
        payload = _read(h, f"presetdata p1 {TABLE_PROBE_PATH}")
        assert h.sent()[-1].address == h.config["state_address"]
        assert payload["kind"] == "presetdata" and payload["id"] == "p1"
        assert payload["ok"] is True and payload["offset"] == 0
        assert payload["total"] == 2 and payload["truncated"] is False
        data = json.loads(payload["data"])
        assert [row["ColorRGB_R"] for row in data] == [100, 0]

    def test_calls_get_preset_data_with_false_false_and_never_cmd(self):
        h = _harness(_TWO_GROUP_COLORS)
        _read(h, f"presetdata p2 {TABLE_PROBE_PATH}")
        assert h.lua.eval("#__GPD_CALLS") == 1
        call = h.lua.globals()["__GPD_CALLS"][1]
        assert call["p"] is False and call["f"] is False
        assert h.cmd_log() == []  # read-only: no console command

    def test_hash_table_windows_by_sorted_key_pairs(self):
        h = _harness("function() return { Dimmer = 50, Pan = 10, Tilt = -20 } end")
        payload = _read(h, f"presetdata p3 {TABLE_PROBE_PATH}")
        assert json.loads(payload["data"]) == {"Dimmer": 50, "Pan": 10, "Tilt": -20}
        assert payload["total"] == 3

    def test_large_table_pages_and_reassembles(self):
        h = _harness(_MANY_ENTRIES)
        collected: list[dict] = []
        offset = 0
        for _ in range(100):
            suffix = f" offset={offset}" if offset else ""
            h.main(None, f"presetdata pg{offset} {TABLE_PROBE_PATH}{suffix}")
            sent = h.sent()[-1]
            assert len(sent.payload) <= int(h.config["max_payload"])
            payload = decode_payload(sent.payload)
            assert payload["ok"] is True and payload["offset"] == offset
            assert payload["total"] == 120
            window = json.loads(payload["data"])
            collected.extend(window)
            if not payload["truncated"]:
                break
            assert window, "a truncated window must make progress"
            offset += len(window)
        else:
            raise AssertionError("never reached truncated=false")
        assert [row["ColorRGB_R"] for row in collected] == list(range(1, 121))

    def test_offset_past_end_is_empty_not_truncated(self):
        h = _harness(_TWO_GROUP_COLORS)
        payload = _read(h, f"presetdata p4 {TABLE_PROBE_PATH} offset=9")
        assert payload["ok"] is True and payload["data"] == "[]"
        assert payload["truncated"] is False and payload["offset"] == 9

    def test_empty_table_is_ok_and_empty(self):
        h = _harness("function() return {} end")
        payload = _read(h, f"presetdata p5 {TABLE_PROBE_PATH}")
        assert payload["ok"] is True and payload["total"] == 0
        assert payload["truncated"] is False

    def test_single_oversize_entry_fails_instead_of_spinning(self):
        h = _harness('function() return { { blob = string.rep("x", 4000) } } end')
        payload = _read(h, f"presetdata p6 {TABLE_PROBE_PATH}")
        assert payload["ok"] is False and "budget" in payload["error"]


class TestPresetDataFailures:
    def test_missing_function_is_a_clear_failure(self):
        payload = _read(_harness(None), f"presetdata f1 {TABLE_PROBE_PATH}")
        assert payload["ok"] is False and "GetPresetData" in payload["error"]

    def test_unresolved_path(self):
        payload = _read(_harness(_TWO_GROUP_COLORS), "presetdata f2 DataPool/Nope/9")
        assert payload["ok"] is False and "not found" in payload["error"]

    def test_non_table_result(self):
        payload = _read(_harness("function() return nil end"), f"presetdata f3 {TABLE_PROBE_PATH}")
        assert payload["ok"] is False and "nil" in payload["error"]

    def test_raising_function(self):
        payload = _read(
            _harness('function() error("boom") end'), f"presetdata f4 {TABLE_PROBE_PATH}"
        )
        assert payload["ok"] is False and "boom" in payload["error"]

    def test_bare_id_without_path_is_rejected(self):
        h = _harness(_TWO_GROUP_COLORS)
        payload = _read(h, "presetdata f5")
        assert payload["ok"] is False


class TestVersionAndWire:
    def test_version_bumped(self):
        assert _harness(None).module["VERSION"] == "1.7.0"

    def test_ping_reports_new_version(self):
        payload = _read(_harness(None), "ping v1")
        assert payload["kind"] == "pong" and payload["version"] == "1.7.0"

    def test_python_builder_matches_the_responder_grammar(self):
        path = "DataPool/PresetPools/4/22"
        assert build_presetdata_query("r1", path).endswith(f'presetdata r1 {path}"')
        assert "offset=40" in build_presetdata_query("r1", path, 40)
        assert "offset" not in build_presetdata_query("r1", path, 0)
