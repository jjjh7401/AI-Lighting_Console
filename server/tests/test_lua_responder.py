"""Lua responder tests (M2 — REQ-MVP-003/004, AC-MVP-012 automated sub-evidence).

Runs the production ``console/lua/copilot_responder.lua`` inside an embedded
Lua 5.4 runtime (lupa) with the MA3 API surface mocked — see
``lua_mock_env.py``. Replies captured on the Lua side are decoded with the
PYTHON codec (:mod:`server.bridge.protocol`), so every test here is also a
cross-language contract test of the v1 wire format.
"""

from __future__ import annotations

import json

import pytest

from server.bridge.protocol import decode_payload
from server.orchestrator.tools import rig_object

from .lua_mock_env import (
    GAPPED_GROUP_NAMES,
    GAPPED_GROUP_SLOTS,
    RESPONDER_PATH,
    ResponderHarness,
    gapped_groups_env,
)

STATE_ADDRESS = "/copilot/state"
FEEDBACK_ADDRESS = "/copilot/feedback"


@pytest.fixture()
def harness() -> ResponderHarness:
    return ResponderHarness()


def _lua_string(value: str) -> str:
    return json.dumps(value)


def _lua_array(values: list[str]) -> str:
    return "{ " + ", ".join(_lua_string(value) for value in values) + " }"


def _lua_props(values: dict[str, str]) -> str:
    return (
        "{ "
        + ", ".join(
            f"[{_lua_string(name)}] = {_lua_string(value)}" for name, value in values.items()
        )
        + " }"
    )


def _sequence_props_env(
    values: dict[str, str], order: list[str] | None = None, extra: str = ""
) -> str:
    order = order or list(values)
    props, index = _lua_props(values), _lua_array(order)
    return (
        "local node = __NODE\n"
        f'local seq = node("Sequence 101", "Sequence", {{}}, {props}, {index})\n'
        f"{extra}\n"
        '__DATAPOOL = node("Default", "DataPool", {\n'
        '    node("Sequences", "Pool", { seq }),\n'
        "})\n"
        "function DataPool() return __DATAPOOL end\n"
    )


class TestLoading:
    def test_plugin_returns_callable_main(self, harness):
        assert callable(harness.main)

    def test_module_export_and_defaults(self, harness):
        config = harness.config
        assert config["state_address"] == STATE_ADDRESS
        assert config["feedback_address"] == FEEDBACK_ADDRESS
        assert config["send_variant"] == "packed"
        assert config["max_props_names"] == 16
        assert harness.module["PROTO"] == 1
        assert harness.module["VERSION"] == "1.6.3"


class TestParseRequest:
    def test_state_request(self, harness):
        req = harness.module["parse_request"]("state 42 DataPool/Sequences")
        assert req["kind"] == "state"
        assert req["id"] == "42"
        assert req["rest"] == "DataPool/Sequences"

    def test_rest_keeps_embedded_spaces(self, harness):
        req = harness.module["parse_request"]("exec 7 Store Cue 5")
        assert req["kind"] == "exec"
        assert req["rest"] == "Store Cue 5"

    def test_ping_has_empty_rest(self, harness):
        req = harness.module["parse_request"]("ping 1")
        assert req["kind"] == "ping"
        assert req["rest"] == ""

    def test_missing_id_is_error(self, harness):
        result = harness.module["parse_request"]("ping")
        assert result[0] is None and "id" in result[1]

    def test_empty_request_is_error(self, harness):
        result = harness.module["parse_request"]("   ")
        assert result[0] is None


class TestPercentEncoding:
    def test_reserved_characters_are_encoded(self, harness):
        encoded = harness.module["percent_encode"]('a,b "c" {d}')
        assert "," not in encoded
        assert '"' not in encoded
        assert " " not in encoded
        assert encoded == "a%2Cb%20%22c%22%20%7Bd%7D"

    def test_unreserved_characters_pass_through(self, harness):
        assert harness.module["percent_encode"]("Az09-._~") == "Az09-._~"

    def test_utf8_bytes_become_ascii(self, harness):
        encoded = harness.module["percent_encode"]("보컬")
        assert encoded.isascii()
        assert all(c.isalnum() or c in "%-._~" for c in encoded)


class TestPing:
    def test_pong_reply_on_feedback_address(self, harness):
        harness.main(None, "ping 11")
        sent = harness.sent()
        assert len(sent) == 1
        assert sent[0].address == FEEDBACK_ADDRESS
        payload = decode_payload(sent[0].payload)
        assert payload["kind"] == "pong"
        assert payload["id"] == "11"
        assert payload["v"] == 1
        assert payload["plugin"] == "CopilotResponder"


class TestStateSnapshot:
    def test_snapshot_of_datapool_sequences(self, harness):
        harness.main(None, "state 42 DataPool/Sequences")
        sent = harness.sent()
        assert len(sent) == 1
        assert sent[0].address == STATE_ADDRESS
        payload = decode_payload(sent[0].payload)
        assert payload["kind"] == "state"
        assert payload["id"] == "42"
        assert payload["ok"] is True
        assert payload["path"] == "DataPool/Sequences"
        assert payload["node"]["name"] == "Sequences"
        assert payload["node"]["childCount"] == 3
        names = [child["name"] for child in payload["children"]]
        assert names == ["Sequence 1", "Sequence 2", "Sequence 3"]
        assert payload["truncated"] is False

    def test_root_based_path(self, harness):
        harness.main(None, "state 1 Root/ShowData/DataPools")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["node"]["name"] == "DataPools"

    def test_leaf_node_has_empty_children_array(self, harness):
        harness.main(None, "state 2 DataPool/Sequences/Sequence 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["node"]["childCount"] == 0
        assert payload["children"] == []

    def test_numeric_segment_selects_child_by_index(self, harness):
        harness.main(None, "state 3 DataPool/Sequences/2")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["node"]["name"] == "Sequence 2"

    def test_unknown_path_reports_error(self, harness):
        harness.main(None, "state 4 DataPool/Nonexistent")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert "Nonexistent" in payload["error"]

    def test_missing_path_reports_error(self, harness):
        harness.main(None, "state 5")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False

    def test_child_cap_sets_truncated_flag(self, harness):
        harness.config["max_children"] = 2
        harness.main(None, "state 6 DataPool/Sequences")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["truncated"] is True
        assert len(payload["children"]) == 2
        assert payload["node"]["childCount"] == 3

    def test_payload_size_guard_drops_children_to_fit(self, harness):
        harness.config["max_payload"] = 300
        harness.main(None, "state 7 DataPool/Sequences")
        sent = harness.sent()[0]
        assert len(sent.payload) <= 300
        payload = decode_payload(sent.payload)
        assert payload["truncated"] is True
        assert payload["node"]["childCount"] == 3

    def test_failure_branch_payload_size_guard_truncates_long_path(self, harness):
        # Finding 2 (HIGH, M6c-4): build_snapshot()'s FAILURE branch echoed
        # the full, unbounded query path (twice — once directly, once inside
        # `error`) with no size guard, unlike the success branch above. A
        # long/malformed path must still respect CONFIG.max_payload.
        harness.config["max_payload"] = 300
        long_segment = "x" * 5000
        harness.main(None, f"state 20 DataPool/{long_segment}")
        sent = harness.sent()[0]
        assert len(sent.payload) <= 300
        payload = decode_payload(sent.payload)
        assert payload["ok"] is False


class TestCueNumberExposure:
    def test_cue_child_keeps_listing_i_and_adds_real_cue_no(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                "local function cue(name, cue_no, listed_index)\n"
                '    local c = node(name, "Cue")\n'
                "    function c:Index() return listed_index end\n"
                "    function c:Get(prop)\n"
                '        if prop == "No" then return cue_no end\n'
                '        if prop == "name" then return self.name end\n'
                "        return nil\n"
                "    end\n"
                "    return c\n"
                "end\n"
                'local seq = node("Sequence 101", "Sequence", {\n'
                '    cue("OffCue", "0", 1),\n'
                '    cue("CueZero", "0", 2),\n'
                '    cue("PROBEA1", "1000", 3),\n'
                '    cue("PROBEA2", "2000", 4),\n'
                '    cue("PROBEA7", "7000", 5),\n'
                "})\n"
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { seq }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "state 50 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        probe = next(child for child in payload["children"] if child["name"] == "PROBEA7")
        assert probe["i"] == 5
        assert probe["cueNo"] == 7

    def test_decimal_cue_no_is_scaled_from_live_no_property(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local cue = node("PROBEA1_5", "Cue")\n'
                "function cue:Index() return 3 end\n"
                "function cue:Get(prop)\n"
                '    if prop == "No" then return "1500" end\n'
                "    return nil\n"
                "end\n"
                'local seq = node("Sequence 101", "Sequence", { cue })\n'
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { seq }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "state 52 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["children"][0]["cueNo"] == 1.5

    def test_cue_no_is_omitted_when_the_number_is_not_numeric(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local cue = node("PROBEA7", "Cue")\n'
                "function cue:Index() return 5 end\n"
                "function cue:Get(prop)\n"
                '    if prop == "No" then return "Cue 7" end\n'
                "    return nil\n"
                "end\n"
                'local seq = node("Sequence 101", "Sequence", { cue })\n'
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { seq }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "state 51 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert "cueNo" not in payload["children"][0]


class TestPropRead:
    def test_prop_reads_property_value_on_state_address(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local cue = node("Cue 2", "Cue")\n'
                "function cue:Get(prop)\n"
                '    if prop == "TrigTime" then return "00:00:04.000" end\n'
                '    if prop == "name" then return self.name end\n'
                "    return nil\n"
                "end\n"
                'local seq = node("Sequence 101", "Sequence", { cue })\n'
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { seq }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "prop p1 DataPool/Sequences/Sequence 101/Cue 2 TrigTime")
        sent = harness.sent()[0]
        payload = decode_payload(sent.payload)
        assert sent.address == STATE_ADDRESS
        assert payload == {
            "v": 1,
            "kind": "prop",
            "id": "p1",
            "ok": True,
            "path": "DataPool/Sequences/Sequence 101/Cue 2",
            "property": "TrigTime",
            "value": "00:00:04.000",
        }

    def test_prop_reports_unknown_property_without_guessing(self, harness):
        harness.main(None, "prop p2 DataPool/Sequences/Sequence 1 ZzzBogus")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "prop"
        assert payload["ok"] is False
        assert payload["property"] == "ZzzBogus"
        assert "not readable" in payload["error"]

    def test_prop_requires_path_and_property(self, harness):
        harness.main(None, "prop p3 DataPool/Sequences")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "prop"
        assert payload["ok"] is False
        assert "malformed prop" in payload["error"]


class TestPropsRead:
    def test_props_mixed_reads_keep_top_level_ok_for_processed_request(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"CURRENTCUE": "Sequence 80.3", "CUENO": "", "FADER": "Master"},
                ["CURRENTCUE", "CUENO", "FADER"],
                extra=(
                    "function seq:Get(prop)\n"
                    '    if prop == "RAISES" then error("mock read failure") end\n'
                    "    return self._props[prop]\n"
                    "end\n"
                ),
            )
        )
        harness.main(
            None,
            "props bp1 CURRENTCUE,CUENO,MISSING,RAISES DataPool/Sequences/Sequence 101",
        )
        sent = harness.sent()[0]
        payload = decode_payload(sent.payload)
        assert sent.address == STATE_ADDRESS
        assert payload["kind"] == "props"
        assert payload["ok"] is True
        assert payload["path"] == "DataPool/Sequences/Sequence 101"
        assert payload["truncated"] is False
        assert payload["reads"] == [
            {"n": "CURRENTCUE", "ok": True, "t": "string", "v": "Sequence 80.3"},
            {"n": "CUENO", "ok": True, "t": "string", "v": ""},
            {"n": "MISSING", "ok": False, "e": "property not readable: MISSING"},
            {"n": "RAISES", "ok": False, "e": "property not readable: RAISES"},
        ]

    def test_props_all_failed_reads_are_still_a_processed_request(self, harness):
        harness.main(None, "props bp2 FOO,BAR DataPool/Sequences/Sequence 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "props"
        assert payload["ok"] is True
        assert [read["ok"] for read in payload["reads"]] == [False, False]

    def test_props_malformed_request_reports_props_failure(self, harness):
        harness.main(None, "props bp3 DataPool/Sequences")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "props"
        assert payload["ok"] is False
        assert payload["reads"] == []
        assert "malformed props" in payload["error"]

    def test_props_accepts_name_count_at_config_limit(self):
        names = [f"P{i:02d}" for i in range(1, 17)]
        harness = ResponderHarness(
            extra_env=_sequence_props_env({name: name for name in names}, names)
        )
        harness.main(None, f"props bp4 {','.join(names)} DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert len(payload["reads"]) == int(harness.config["max_props_names"])

    def test_props_rejects_name_count_over_config_limit(self, harness):
        names = [f"P{i:02d}" for i in range(1, 18)]
        harness.main(None, f"props bp5 {','.join(names)} DataPool/Sequences/Sequence 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "props"
        assert payload["ok"] is False
        assert "too many property names" in payload["error"]
        assert int(harness.config["max_props_names"]) == 16

    def test_props_value_truncation_is_marked_per_item(self):
        value = "A" * 80
        harness = ResponderHarness(extra_env=_sequence_props_env({"LONG": value}, ["LONG"]))
        harness.config["max_prop_value"] = 12
        harness.main(None, "props bp6 LONG DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        read = payload["reads"][0]
        assert payload["truncated"] is False
        assert read["ok"] is True
        assert read["t"] == "string"
        assert read["v"] == value[:12]
        assert read["truncated"] is True

    def test_props_payload_size_guard_drops_reads_and_signals_truncation(self):
        names = [f"P{i:02d}" for i in range(1, 17)]
        values = {name: "V" * 220 for name in names}
        assert sum(len(value) for value in values.values()) > 1900
        harness = ResponderHarness(extra_env=_sequence_props_env(values, names))
        harness.main(None, f"props bp7 {','.join(names)} DataPool/Sequences/Sequence 101")
        sent = harness.sent()[0]
        payload = decode_payload(sent.payload)
        assert len(sent.payload) <= int(harness.config["max_payload"])
        assert payload["truncated"] is True
        assert 0 < len(payload["reads"]) < len(names)

    def test_prop_and_props_dispatch_are_not_confused(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env({"CURRENTCUE": "Sequence 80.3"}, ["CURRENTCUE"])
        )
        harness.main(None, "prop d1 DataPool/Sequences/Sequence 101 CURRENTCUE")
        harness.main(None, "props d2 CURRENTCUE DataPool/Sequences/Sequence 101")
        prop_payload = decode_payload(harness.sent()[0].payload)
        props_payload = decode_payload(harness.sent()[1].payload)
        assert prop_payload["kind"] == "prop"
        assert prop_payload["property"] == "CURRENTCUE"
        assert props_payload["kind"] == "props"
        assert props_payload["reads"][0]["n"] == "CURRENTCUE"

    def test_props_duplicate_names_collapse_in_request_order(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"CURRENTCUE": "Sequence 80.3", "FADER": "Master"},
                ["CURRENTCUE", "FADER"],
            )
        )
        harness.main(None, "props bp8 CURRENTCUE,FADER,CURRENTCUE DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert [read["n"] for read in payload["reads"]] == ["CURRENTCUE", "FADER"]


class TestIntrospect:
    def test_introspect_returns_names_types_source_and_total(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"CURRENTCUE": "Sequence 80.3", "INDEX": "201", "FADER": "Master"},
                ["INDEX", "FADER", "CURRENTCUE"],
            )
        )
        harness.main(None, "introspect i1 DataPool/Sequences/Sequence 101")
        sent = harness.sent()[0]
        payload = decode_payload(sent.payload)
        assert sent.address == STATE_ADDRESS
        assert payload == {
            "v": 1,
            "kind": "introspect",
            "id": "i1",
            "ok": True,
            "path": "DataPool/Sequences/Sequence 101",
            "class": "Sequence",
            "source": "property_accessors",
            "fields": [
                {"n": "INDEX", "t": "string"},
                {"n": "FADER", "t": "string"},
                {"n": "CURRENTCUE", "t": "string"},
            ],
            "total": 3,
            "truncated": False,
            "offset": 0,
        }

    def test_introspect_unknown_path_reports_failure(self, harness):
        harness.main(None, "introspect i2 DataPool/NotThere")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "introspect"
        assert payload["ok"] is False
        assert "NotThere" in payload["error"]

    def test_introspect_unavailable_enumerator_is_explicit_failure(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"CURRENTCUE": "Sequence 80.3"},
                ["CURRENTCUE"],
                extra="seq.PropertyCount = nil\n",
            )
        )
        harness.main(None, "introspect i3 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "introspect"
        assert payload["ok"] is False
        assert "PropertyCount" in payload["error"]
        assert "fields" not in payload

    def test_introspect_rejects_nil_property_accessor_index(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"INDEX": "201", "FADER": "Master"},
                ["INDEX", "FADER"],
                extra=(
                    "function seq:PropertyName(i)\n"
                    "    if i == 1 then return nil end\n"
                    "    return self._property_order[i + 1]\n"
                    "end\n"
                ),
            )
        )
        harness.main(None, "introspect i4 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "introspect"
        assert payload["ok"] is False
        assert "incomplete" in payload["error"]
        assert "fields" not in payload

    def test_introspect_rejects_enumerator_missing_prop_readable_name(self):
        harness = ResponderHarness(
            extra_env=_sequence_props_env(
                {"INDEX": "201", "FADER": "Master", "CURRENTCUE": "Sequence 80.3"},
                ["INDEX", "FADER"],
            )
        )
        harness.main(None, "introspect i6 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "introspect"
        assert payload["ok"] is False
        assert "CURRENTCUE" in payload["error"]
        assert "Sequence 80.3" not in payload["error"]
        assert "fields" not in payload

    def test_introspect_contrast_gate_uses_pre_truncation_field_set(self):
        names = [f"FIELD{i:03d}_" + ("N" * 24) for i in range(1, 81)]
        names.append("CURRENTCUE")
        values = {name: "value" for name in names}
        values["CURRENTCUE"] = "Sequence 80.3"
        harness = ResponderHarness(extra_env=_sequence_props_env(values, names))
        harness.main(None, "introspect i7 DataPool/Sequences/Sequence 101")
        payload = decode_payload(harness.sent()[0].payload)
        returned_names = [field["n"] for field in payload["fields"]]
        assert payload["ok"] is True
        assert payload["truncated"] is True
        assert payload["total"] == len(names)
        assert "CURRENTCUE" not in returned_names

    def test_introspect_payload_truncation_preserves_total(self):
        names = [f"FIELD{i:03d}_" + ("N" * 24) for i in range(1, 81)]
        values = {name: "value" for name in names}
        assert sum(len(name) for name in names) > 1900
        harness = ResponderHarness(extra_env=_sequence_props_env(values, names))
        harness.main(None, "introspect i5 DataPool/Sequences/Sequence 101")
        sent = harness.sent()[0]
        payload = decode_payload(sent.payload)
        assert len(sent.payload) <= int(harness.config["max_payload"])
        assert payload["truncated"] is True
        assert payload["total"] == len(names)
        assert 0 < len(payload["fields"]) < payload["total"]

    def test_function_fields_are_reported_without_calling_them(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                "__FUNC_CALLS = 0\n"
                "local function spy()\n"
                "    __FUNC_CALLS = __FUNC_CALLS + 1\n"
                '    error("function field was called")\n'
                "end\n"
                'local seq = node("Sequence 101", "Sequence", {}, { INDEX = spy }, { "INDEX" })\n'
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { seq }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "props f1 INDEX DataPool/Sequences/Sequence 101")
        harness.main(None, "introspect f2 DataPool/Sequences/Sequence 101")
        props_payload = decode_payload(harness.sent()[0].payload)
        introspect_payload = decode_payload(harness.sent()[1].payload)
        assert harness.lua.globals()["__FUNC_CALLS"] == 0
        assert harness.cmd_log() == []
        assert props_payload["reads"][0]["t"] == "function"
        assert props_payload["reads"][0]["ok"] is True
        assert introspect_payload["fields"][0] == {"n": "INDEX", "t": "function"}

    # -- introspect paging (responder 1.6.2, t104) -------------------------
    #
    # 실측이 이 검사를 부른다: t95 가 DataPool/PresetPools/<pool>/<n> 에서
    # 프로퍼티 138개 중 27개만 받았다. 페이로드 예산 절단이고 introspect 에는
    # 페이징이 없어 나머지 111개 **이름이 이 채널로 도달 불가**였다. state 는
    # 1.6.0 부터 offset 을 갖는다 — 같은 방식을 여기로 옮긴다.
    #
    # 「목록에 있다」와 「읽힌다」는 여전히 따로다. 페이징은 전자만 연다.

    @staticmethod
    def _wide(count: int = 138):
        """이름이 138개인 핸들 — t95 가 실제로 만난 폭이다."""
        names = [f"PROP{i:03d}_" + ("N" * 24) for i in range(1, count + 1)]
        names.append("CURRENTCUE")  # 대조군 게이트가 요구하는 이름
        values = {name: "value" for name in names}
        values["CURRENTCUE"] = "Sequence 80.3"
        return ResponderHarness(extra_env=_sequence_props_env(values, names)), names

    def _reply(self, harness, request):
        harness.main(None, request)
        sent = harness.sent()[-1]
        assert sent.address == STATE_ADDRESS
        return decode_payload(sent.payload)

    def test_an_unpaged_request_echoes_offset_zero(self):
        harness, names = self._wide()
        payload = self._reply(harness, "introspect p1 DataPool/Sequences/Sequence 101")
        assert payload["ok"] is True
        assert payload["offset"] == 0
        assert payload["total"] == len(names)
        assert payload["truncated"] is True
        assert 0 < len(payload["fields"]) < payload["total"]

    def test_the_second_window_continues_where_the_first_stopped(self):
        """🔴 t95 가 막힌 자리다 — 첫 창 다음의 이름은 도달 수단이 없었다."""
        harness, names = self._wide()
        first = self._reply(harness, "introspect p2 DataPool/Sequences/Sequence 101")
        got = len(first["fields"])
        second = self._reply(harness, f"introspect p3 DataPool/Sequences/Sequence 101 offset={got}")
        assert second["ok"] is True
        assert second["offset"] == got
        assert second["total"] == len(names)
        assert second["fields"][0]["n"] == names[got]
        assert first["fields"][-1]["n"] == names[got - 1]

    def test_paging_to_exhaustion_reaches_every_name(self):
        """닫는 조건의 절반 — 138개가 **전부** 열거되는가. 창 수를 못박지 않는다
        (예산이 정하므로 개수를 세면 예산을 재는 검사가 된다)."""
        harness, names = self._wide()
        seen: list[str] = []
        offset = 0
        for _ in range(200):  # 진행이 멈추면 무한 루프 대신 여기서 끝난다
            payload = self._reply(
                harness, f"introspect p4 DataPool/Sequences/Sequence 101 offset={offset}"
            )
            assert payload["ok"] is True
            window = [field["n"] for field in payload["fields"]]
            if not window:
                break
            seen.extend(window)
            offset += len(window)
            if not payload["truncated"]:
                break
        assert seen == names, (len(seen), len(names))

    def test_truncated_means_names_remain_after_this_window(self):
        harness, names = self._wide()
        payload = self._reply(
            harness,
            f"introspect p5 DataPool/Sequences/Sequence 101 offset={len(names) - 1}",
        )
        assert payload["offset"] == len(names) - 1
        assert [field["n"] for field in payload["fields"]] == [names[-1]]
        assert payload["truncated"] is False

    def test_an_offset_at_or_past_the_total_is_an_empty_untruncated_window(self):
        harness, names = self._wide()
        for offset in (len(names), len(names) + 50):
            payload = self._reply(
                harness, f"introspect p6 DataPool/Sequences/Sequence 101 offset={offset}"
            )
            assert payload["ok"] is True
            assert payload["offset"] == offset
            assert payload["fields"] == []
            assert payload["truncated"] is False
            assert payload["total"] == len(names)

    @pytest.mark.parametrize("token", ["offset=-3", "offset=abc", "offset=1.5", "offset="])
    def test_an_invalid_offset_degrades_to_zero_rather_than_erroring(self, token):
        harness, names = self._wide()
        payload = self._reply(harness, f"introspect p7 DataPool/Sequences/Sequence 101 {token}")
        assert payload["ok"] is True
        assert payload["offset"] == 0
        assert payload["total"] == len(names)

    def test_a_spaced_path_survives_the_offset_token_split(self):
        """경로에 공백이 있다 — 맨 뒤 토큰만 떼어내야 'Sequence 101' 이 산다."""
        harness, _names = self._wide()
        payload = self._reply(harness, "introspect p8 DataPool/Sequences/Sequence 101 offset=0")
        assert payload["ok"] is True
        assert payload["path"] == "DataPool/Sequences/Sequence 101"

    def test_a_window_still_respects_the_payload_budget(self):
        """페이징이 예산 가드를 대체하지 않는다 — 창 안에서도 예산이 이긴다."""
        harness, _names = self._wide()
        harness.main(None, "introspect p9 DataPool/Sequences/Sequence 101 offset=5")
        sent = harness.sent()[-1]
        assert len(sent.payload) <= int(harness.config["max_payload"])

    def test_the_contrast_gate_still_sees_every_name_not_just_the_window(self):
        """게이트는 창 밖 이름에도 걸려야 한다 — 창으로 좁히면 게이트가 공허해진다.

        CURRENTCUE 를 열거 목록에서 뺀다. 그 이름은 창 밖에 있지만, 게이트는
        **전수**를 보므로 회신 전체가 실패해야 한다.
        """
        names = [f"PROP{i:03d}_" + ("N" * 24) for i in range(1, 139)]
        values = {name: "value" for name in names}
        values["CURRENTCUE"] = "Sequence 80.3"  # 읽히지만 열거되지 않는다
        harness = ResponderHarness(extra_env=_sequence_props_env(values, names))
        payload = self._reply(harness, "introspect p10 DataPool/Sequences/Sequence 101 offset=120")
        assert payload["ok"] is False
        assert "CURRENTCUE" in payload["error"]
        assert "fields" not in payload

    def test_new_read_paths_do_not_reference_cmd(self):
        source = RESPONDER_PATH.read_text(encoding="utf-8")
        builders = source.split("function M.build_props_result", 1)[1].split(
            "-- @MX:NOTE: [AUTO] Cmd() result classification", 1
        )[0]
        dispatch = source.split('elseif parsed.kind == "props"', 1)[1].split(
            'elseif parsed.kind == "exec"', 1
        )[0]
        assert "Cmd(" not in builders
        assert "Cmd(" not in dispatch


class TestExecutorSequenceIdentity:
    """The Executor-only additive field (M2, REQ-EXECBODY-003/AC-EXECBODY-004).

    Live-verified (SPEC-COPILOT-EXECBODY-001 design.md §5.9): ``exec.Object``
    returns a handle to the assigned sequence; ``GetClass()`` on that handle
    is ``"Sequence"`` and ``:Index()`` is its real pool number. The field is
    additive and omitted whenever the identity cannot be established —
    AC-EXECBODY-005 forbids deriving it from the executor's display name.
    """

    def _exec_env(self, object_snippet: str = "") -> str:
        return (
            "local node = __NODE\n"
            'local exec = node("Exec 1", "Executor")\n'
            f"{object_snippet}\n"
            '__DATAPOOL = node("Default", "DataPool", {\n'
            '    node("Execs", "Pool", { exec }),\n'
            "})\n"
            "function DataPool() return __DATAPOOL end\n"
        )

    def test_assigned_sequence_number_is_exposed(self):
        harness = ResponderHarness(
            extra_env=self._exec_env(
                'local seq = node("Sequence 71", "Sequence")\n'
                "function seq:Index() return 71 end\n"
                "exec.Object = seq\n"
            )
        )
        harness.main(None, "state 30 DataPool/Execs/Exec 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert payload["node"]["name"] == "Exec 1"
        assert payload["node"]["class"] == "Executor"
        assert payload["node"]["sequenceNo"] == 71

    def test_unassigned_executor_omits_the_field(self):
        harness = ResponderHarness(extra_env=self._exec_env())
        harness.main(None, "state 31 DataPool/Execs/Exec 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert "sequenceNo" not in payload["node"]

    def test_object_of_the_wrong_class_omits_the_field(self):
        harness = ResponderHarness(
            extra_env=self._exec_env('local other = node("Weird", "Preset")\nexec.Object = other\n')
        )
        harness.main(None, "state 32 DataPool/Execs/Exec 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert "sequenceNo" not in payload["node"]

    def test_non_executor_node_never_carries_the_field(self):
        harness = ResponderHarness()
        harness.main(None, "state 33 DataPool/Sequences/Sequence 1")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert "sequenceNo" not in payload["node"]


class TestExecutorAddressResolution:
    """resolve_path resolves the "Executor <n>" console-address form via the
    native ObjectList() API (M6, design.md §5.8, REQ-EXECBODY-004) instead of
    failing "path segment not found" -- executors are paged, so DataPool's
    tree-walk / pool-slot numbering does NOT correspond to the
    console-displayed number (the reverse-address problem M1 investigated).
    """

    def test_executor_address_resolves_via_object_list(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local exec = node("Exec 201", "Executor")\n'
                '__OBJECT_LIST = { ["Executor 201"] = { exec } }\n'
                "function ObjectList(addr) return __OBJECT_LIST[addr] end\n"
            )
        )
        harness.main(None, "state 40 Executor 201")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert payload["node"]["class"] == "Executor"

    def test_executor_address_exposes_assigned_sequence_end_to_end(self):
        # Composes with M2 (§4.2 node.sequenceNo) — the exact wire shape
        # server/safety/console.py's _fetch_executor_body (M4) consumes.
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local exec = node("Exec 201", "Executor")\n'
                'local seq = node("Sequence 71", "Sequence")\n'
                "function seq:Index() return 71 end\n"
                "exec.Object = seq\n"
                '__OBJECT_LIST = { ["Executor 201"] = { exec } }\n'
                "function ObjectList(addr) return __OBJECT_LIST[addr] end\n"
            )
        )
        harness.main(None, "state 41 Executor 201")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert payload["node"]["sequenceNo"] == 71

    def test_object_list_returning_nothing_holds_as_unavailable(self):
        harness = ResponderHarness(extra_env="function ObjectList(addr) return nil end\n")
        harness.main(None, "state 42 Executor 999")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert "Executor 999" in payload["error"]

    def test_object_list_wrong_class_holds_as_unavailable(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                'local wrong = node("Not An Exec", "Sequence")\n'
                '__OBJECT_LIST = { ["Executor 5"] = { wrong } }\n'
                "function ObjectList(addr) return __OBJECT_LIST[addr] end\n"
            )
        )
        harness.main(None, "state 43 Executor 5")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert "Executor 5" in payload["error"]

    def test_object_list_absent_entirely_holds_gracefully(self):
        # ObjectList() doesn't exist in the default mock env at all -- pcall
        # must catch the nil-call, not crash the responder.
        harness = ResponderHarness()
        harness.main(None, "state 44 Executor 7")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False

    def test_non_executor_paths_still_walk_the_tree(self):
        # Regression: the DataPool tree-walk resolution path is unaffected.
        harness = ResponderHarness()
        harness.main(None, "state 45 DataPool/Sequences")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["node"]["name"] == "Sequences"


class TestPoolSlotContract:
    """The snapshot child ``i`` is the REAL pool slot — or it is absent.

    Live-demo defect: on a gapped Groups pool the responder emitted the LOOP
    POSITION as ``i``, so the model was told groups 1, 2, 3 exist, confidently
    issued ``Group 2 + 3``, and the console rejected the object — after
    ``ChangeDestination Root`` and ``ClearAll`` had already run. A position is
    never an address: report the slot, or report no number at all.
    """

    def _children(self, harness, request="state 1 DataPool/Groups"):
        harness.main(None, request)
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        return payload["children"]

    def test_gapped_pool_reports_real_slots_not_listing_positions(self):
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form="Index"))
        children = self._children(harness)
        assert [c["name"] for c in children] == list(GAPPED_GROUP_NAMES)
        assert [c["i"] for c in children] == list(GAPPED_GROUP_SLOTS)

    def test_index_property_accessor_form_is_probed_too(self):
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form="index"))
        assert [c["i"] for c in self._children(harness)] == list(GAPPED_GROUP_SLOTS)

    def test_unestablished_slot_is_omitted_rather_than_faked(self):
        # No self-index accessor at all: only the child the parent hands back
        # for the slot we guessed (slot 1) is confirmable. The rest carry NO
        # number — silence beats a plausible-looking wrong one.
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form=None))
        children = self._children(harness)
        assert children[0]["i"] == 1
        assert [c["name"] for c in children] == list(GAPPED_GROUP_NAMES)
        assert "i" not in children[1]
        assert "i" not in children[2]

    def test_dense_pool_still_reports_contiguous_slots(self, harness):
        # Regression guard: on a dense pool position == slot, and Ptr() confirms
        # it, so the reported numbers must not become unknown.
        children = self._children(harness, "state 2 DataPool/Sequences")
        assert [c["i"] for c in children] == [1, 2, 3]

    def test_unknown_slot_reaches_the_llm_as_a_name_only_entry(self):
        # Cross-layer contract (the defect was the two layers disagreeing):
        # the rig-context tool must NOT invent a "no" for an unnumbered child.
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form=None))
        objects = [rig_object(c) for c in self._children(harness)]
        assert objects[0] == {"no": 1, "name": "Vocals"}
        assert objects[1] == {"name": "Drums"}
        assert objects[2] == {"name": "Keys"}

    def test_self_reported_slot_wins_over_a_positional_ptr(self):
        # If Ptr() is positional on 2.4.2 (unverified), it carries no slot
        # information — it must NOT be allowed to veto the object's own answer
        # and push the listing position back out as "confirmed".
        harness = ResponderHarness(
            extra_env=gapped_groups_env(index_form="Index", ptr_form="positional")
        )
        assert [c["i"] for c in self._children(harness)] == list(GAPPED_GROUP_SLOTS)

    def test_skewed_index_accessor_is_discarded_whole(self):
        # A 0-based accessor answers every child plausibly and every child
        # wrongly. Its first answer (0) is not a legal slot, so the whole set
        # is dropped rather than partially believed: slot 1 survives only
        # because Ptr() independently confirms it.
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form="Index0"))
        children = self._children(harness)
        assert children[0]["i"] == 1
        assert "i" not in children[1]
        assert "i" not in children[2]

    def test_known_blind_spot_no_accessor_plus_positional_ptr(self):
        # CHARACTERIZATION, not an endorsement. With no self-index accessor AND
        # a positional Ptr(), the console exposes NO slot information whatsoever
        # and every position "confirms" — so the old, wrong numbers come back.
        # Nothing in the responder can detect this from the inside; it is the
        # one combination that must be ruled out on real onPC hardware
        # (PROTOCOL.md ASSUMPTION-7). If this test ever starts failing, someone
        # found a third source of truth — update the assumption.
        harness = ResponderHarness(extra_env=gapped_groups_env(ptr_form="positional"))
        assert [c["i"] for c in self._children(harness)] == [1, 2, 3]

    def test_numeric_path_segment_addresses_the_pool_slot(self):
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form="Index"))
        harness.main(None, "state 3 DataPool/Groups/5")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["node"]["name"] == "Drums"

    def test_numeric_path_segment_does_not_resolve_a_gap(self):
        # Slot 2 is EMPTY. Resolving it to the 2nd listed object is the same
        # lie in a different surface.
        harness = ResponderHarness(extra_env=gapped_groups_env(index_form="Index"))
        harness.main(None, "state 4 DataPool/Groups/2")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert "not found" in payload["error"]


class TestExecResult:
    def test_success_result(self, harness):
        harness.main(None, "exec 9 List")
        assert harness.cmd_log() == ["List"]
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "result"
        assert payload["id"] == "9"
        assert payload["ok"] is True
        assert payload["result"] == "OK"

    def test_command_is_rest_of_line_with_spaces(self, harness):
        harness.main(None, "exec 10 Store Cue 5")
        assert harness.cmd_log() == ["Store Cue 5"]

    def test_error_result_string_classified_as_failure(self, harness):
        harness.lua.execute('__CMD_RESULT = "Illegal command"')
        harness.main(None, "exec 11 Bogus")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert payload["error"] == "Illegal command"
        assert payload["result"] == "Illegal command"

    def test_lua_error_in_cmd_is_captured(self, harness):
        harness.lua.execute("__CMD_RAISE = true")
        harness.main(None, "exec 12 List")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False
        assert "mock cmd failure" in payload["error"]

    def test_missing_command_reports_error(self, harness):
        harness.main(None, "exec 13")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False


class TestDispatchAndFallbacks:
    def test_unknown_kind_reports_error(self, harness):
        harness.main(None, "frobnicate 1 x")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "error"
        assert "frobnicate" in payload["error"]

    def test_nil_argument_falls_back_to_uservar(self, harness):
        harness.lua.execute('__USER_VARS["COPILOT_REQ"] = "ping 77"')
        harness.main(None, None)
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["kind"] == "pong"
        assert payload["id"] == "77"

    def test_no_request_at_all_sends_nothing(self, harness):
        harness.main(None, None)
        assert harness.sent() == []

    def test_args_send_variant(self, harness):
        harness.config["send_variant"] = "args"
        harness.main(None, "ping 1")
        sent = harness.sent()
        assert len(sent) == 1
        payload = decode_payload(sent[0].payload)
        assert payload["kind"] == "pong"

    def test_a_sendoscmessage_wanting_separate_args_is_actually_tried(self, harness):
        # Live 2026-07-22. On a console whose SendOSCMessage takes
        # (slot, address, payload), the configured "packed" variant raises —
        # and the fallback jumped STRAIGHT to cmd_keyword, so "args" was never
        # attempted. The reply then left via `Cmd('SendOSC ...')`, which that
        # console rejected with "Illegal property"; Cmd() does not raise on a
        # rejected command, so pcall reported success and the reply silently
        # died. Every variant must be tried before giving up, and cmd_keyword
        # must stay LAST precisely because its failures are invisible.
        harness.lua.execute(
            """
            __SENT = {}
            function SendOSCMessage(slot, a, b)
                if b == nil then error("this console wants (slot, address, payload)") end
                table.insert(__SENT, { slot = slot, a = a, b = b })
            end
            """
        )
        harness.main(None, "ping 5")
        sent = harness.sent()
        assert len(sent) == 1, "the args variant must be tried before falling back to Cmd"
        assert harness.cmd_log() == [], "cmd_keyword must not be reached while a real send works"
        assert decode_payload(sent[0].payload)["kind"] == "pong"

    def test_missing_sendoscmessage_falls_back_to_cmd_keyword(self, harness):
        harness.lua.execute("SendOSCMessage = nil")
        harness.main(None, "ping 2")
        cmd_lines = harness.cmd_log()
        assert len(cmd_lines) == 1
        # Read the slot from the LOADED CONFIG rather than repeating a literal:
        # osc_slot moved 1 -> 2 (row 1 is receive-only; replies need a Send=Yes
        # row) and this assertion kept expecting 1, failing for a shipped value
        # that was correct. A literal here only ever rots.
        expected = f'SendOSC {int(harness.config["osc_slot"])} "{FEEDBACK_ADDRESS},s,'
        assert cmd_lines[0].startswith(expected)
        assert cmd_lines[0].endswith('"')


class TestWireSafety:
    def test_packed_form_has_exactly_two_commas(self, harness):
        harness.main(None, "state 1 DataPool/Sequences")
        for packed in harness.raw_packed():
            assert packed.count(",") == 2

    def test_payload_is_ascii_and_quote_free_despite_utf8_names(self):
        harness = ResponderHarness(
            extra_env=(
                "local node = __NODE\n"
                '__DATAPOOL = node("Default", "DataPool", {\n'
                '    node("Sequences", "Pool", { node("보컬 그룹", "Sequence") }),\n'
                "})\n"
                "function DataPool() return __DATAPOOL end\n"
            )
        )
        harness.main(None, "state 8 DataPool/Sequences")
        sent = harness.sent()[0]
        assert sent.payload.isascii()
        assert '"' not in sent.payload
        assert "," not in sent.payload
        payload = decode_payload(sent.payload)
        assert payload["children"][0]["name"] == "보컬 그룹"


#: 30-child dense pool — wider than CONFIG.max_children (24), so the default
#: cap actually windows it (the default 3-sequence tree never fills a page).
WIDE_POOL_LUA = r"""
local node = __NODE
local kids = {}
for i = 1, 30 do kids[i] = node(string.format("Seq %02d", i), "Sequence") end
__DATAPOOL = node("Default", "DataPool", { node("Sequences", "Pool", kids) })
function DataPool() return __DATAPOOL end
"""


@pytest.fixture()
def wide_harness() -> ResponderHarness:
    h = ResponderHarness(extra_env=WIDE_POOL_LUA)
    # Window-shape tests need the FULL 24-cap window; the default 1900-byte
    # payload budget shrinks a 24-child percent-encoded reply, which is the
    # budget guard's job, not these tests' subject (the budget interaction
    # has its own test below, which re-lowers this).
    h.config["max_payload"] = 100000
    return h


class TestStatePaging:
    """Snapshot paging (responder 1.6.0, PROTOCOL.md §2/§4.2).

    A state request may end in one trailing ``offset=<n>`` token — the 0-based
    children window start. The reply always echoes the offset actually used
    (0 for an old-style request), and ``truncated`` means "children remain
    AFTER this window" — on the first window, exactly the pre-paging meaning.
    """

    def _reply(self, h, request):
        h.main(None, request)
        sent = h.sent()
        assert sent[-1].address == STATE_ADDRESS
        return decode_payload(sent[-1].payload)

    def test_unpaged_request_echoes_offset_zero_and_is_otherwise_unchanged(self, harness):
        payload = self._reply(harness, "state 1 DataPool/Sequences")
        assert payload["offset"] == 0
        assert payload["ok"] is True
        assert [c["name"] for c in payload["children"]] == [
            "Sequence 1",
            "Sequence 2",
            "Sequence 3",
        ]
        assert payload["truncated"] is False
        assert payload["node"]["childCount"] == 3

    def test_explicit_offset_zero_matches_unpaged_reply(self, harness):
        paged = self._reply(harness, "state a DataPool/Sequences offset=0")
        assert paged["offset"] == 0
        assert paged["path"] == "DataPool/Sequences"
        assert [c["name"] for c in paged["children"]] == [
            "Sequence 1",
            "Sequence 2",
            "Sequence 3",
        ]
        assert paged["truncated"] is False

    def test_first_window_caps_at_max_children_and_truncates(self, wide_harness):
        payload = self._reply(wide_harness, "state 2 DataPool/Sequences")
        assert payload["offset"] == 0
        assert len(payload["children"]) == 24
        assert payload["children"][0]["name"] == "Seq 01"
        assert payload["children"][-1]["name"] == "Seq 24"
        assert payload["truncated"] is True
        assert payload["node"]["childCount"] == 30

    def test_offset_window_continues_where_first_stopped(self, wide_harness):
        payload = self._reply(wide_harness, "state 3 DataPool/Sequences offset=24")
        assert payload["offset"] == 24
        assert [c["name"] for c in payload["children"]] == [f"Seq {n:02d}" for n in range(25, 31)]
        assert payload["truncated"] is False
        assert payload["node"]["childCount"] == 30

    def test_mid_pool_offset_window_is_still_truncated(self, wide_harness):
        payload = self._reply(wide_harness, "state 4 DataPool/Sequences offset=3")
        assert payload["offset"] == 3
        assert payload["children"][0]["name"] == "Seq 04"
        assert payload["children"][-1]["name"] == "Seq 27"
        assert payload["truncated"] is True

    def test_offset_at_or_past_child_count_yields_empty_untruncated_window(self, wide_harness):
        for offset in (30, 99):
            payload = self._reply(wide_harness, f"state 5 DataPool/Sequences offset={offset}")
            assert payload["offset"] == offset
            assert payload["children"] == []
            assert payload["truncated"] is False
            assert payload["node"]["childCount"] == 30

    @pytest.mark.parametrize("token", ["offset=-3", "offset=abc", "offset=1.5", "offset="])
    def test_invalid_offset_values_degrade_to_zero(self, harness, token):
        payload = self._reply(harness, f"state 6 DataPool/Sequences {token}")
        assert payload["offset"] == 0
        assert payload["ok"] is True
        assert payload["path"] == "DataPool/Sequences"
        assert len(payload["children"]) == 3

    def test_spaced_path_survives_offset_token_split(self, harness):
        # Paths are rest-of-line (spaces legal); only the TRAILING token is
        # peeled off, so "Sequence 1" must still resolve.
        payload = self._reply(harness, "state 7 DataPool/Sequences/Sequence 1 offset=0")
        assert payload["ok"] is True
        assert payload["node"]["name"] == "Sequence 1"
        assert payload["offset"] == 0

    def test_failure_branch_echoes_offset(self, harness):
        payload = self._reply(harness, "state 8 DataPool/Nonexistent offset=3")
        assert payload["ok"] is False
        assert payload["offset"] == 3
        assert "Nonexistent" in payload["error"]

    def test_budget_shrunk_window_keeps_offset_and_reports_truncated(self, wide_harness):
        # The final window (offset 24 -> 6 children) would be truncated:false,
        # but a tight payload budget drops trailing children — the reply must
        # then say truncated:true (children remain after the window) and keep
        # the offset echo so the caller can advance by len(children).
        wide_harness.config["max_payload"] = 450
        payload = self._reply(wide_harness, "state 9 DataPool/Sequences offset=24")
        assert len(wide_harness.sent()[-1].payload) <= 450
        assert payload["offset"] == 24
        assert 0 < len(payload["children"]) < 6
        assert payload["truncated"] is True
        assert payload["node"]["childCount"] == 30


PROGRAMMER_ENV = r"""
local node = __NODE
__PROGRAMMER = node("Programmer", "Programmer", {
    node("Fixture 101", "Fixture"),
    node("Fixture 102", "Fixture"),
})
__SELECTION = node("Selection", "Selection", {
    node("Fixture 101", "Fixture"),
})
function Programmer() return __PROGRAMMER end
function Selection() return __SELECTION end
"""


class TestProgrammerAliases:
    """t235 — 세 레인이 「구조적 한계」로 읽은 것은 별칭의 부재였다.

    `path segment not found: 'Programmer'` 는 `resolve_path` 가 1번 세그먼트를
    별칭 표에서 못 찾아 `Root()` 자식 이름 대조로 떨어진 결과다. 별칭은
    **전역 호출**이므로, 전역이 있으면 열리고 없으면 오늘과 똑같이 실패한다.

    두 팔을 다 잰다 — 열리는 팔과, **없을 때 안 깨지는 팔**. 뒤엣것이 이
    변경의 안전 근거다.
    """

    def test_the_alias_opens_when_the_console_exposes_the_global(self):
        harness = ResponderHarness(PROGRAMMER_ENV)
        harness.main(None, "state 1 Programmer")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert payload["node"]["name"] == "Programmer"
        assert [child["name"] for child in payload["children"]] == [
            "Fixture 101",
            "Fixture 102",
        ]

    def test_the_selection_alias_opens_the_same_way(self):
        harness = ResponderHarness(PROGRAMMER_ENV)
        harness.main(None, "state 2 Selection")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload
        assert payload["node"]["name"] == "Selection"

    def test_the_alias_is_case_insensitive_like_the_others(self):
        harness = ResponderHarness(PROGRAMMER_ENV)
        harness.main(None, "state 3 programmer")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is True, payload

    def test_a_console_without_the_global_fails_exactly_as_before(self, harness):
        """🔴 이 팔이 안전 근거다 — 전역이 없으면 별칭이 nil 로 접히고
        `Root()` 자식 대조로 떨어져 **오늘과 같은 사유**로 실패한다.

        기본 목 환경에는 `Programmer` 전역이 없다. 즉 이것은 별칭을 넣기 전
        상태를 그대로 재는 팔이고, 통과한다는 것은 별칭 추가가 그 콘솔에서
        아무것도 바꾸지 않는다는 뜻이다.
        """
        harness.main(None, "state 4 Programmer")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False, payload
        assert "Programmer" in str(payload.get("error") or ""), payload

    def test_the_original_aliases_are_untouched(self, harness):
        """합치기가 아니라 덧붙이기라는 것 — 기존 별칭이 그대로 선다."""
        for index, path in enumerate(("DataPool", "Root", "ShowData")):
            harness.main(None, "state " + str(index) + " " + path)
        payloads = [decode_payload(item.payload) for item in harness.sent()]
        assert [item["ok"] for item in payloads] == [True, True, True], payloads

    def test_patch_shows_the_same_nil_fallback_and_predates_this_change(self, harness):
        """🔴 이 팔이 **기존 상태의 대조군**이다.

        기본 목 환경에는 `Patch` 전역이 **없다** — 별칭 표에는 1.6.2 때부터
        있었는데도. 그래서 `state Patch` 는 `Programmer` 와 **같은 모양**으로
        실패한다. 즉 「전역 없는 별칭」은 이 변경이 새로 만든 상태가 아니라
        저장소가 이미 갖고 돌던 상태다.

        이게 없으면 위 팔의 통과가 「내 별칭만 안전하다」로 읽히고, 그 안전이
        어디서 오는지(별칭이 아니라 `pcall` + nil 폴백) 안 보인다.
        """
        harness.main(None, "state 9 Patch")
        payload = decode_payload(harness.sent()[0].payload)
        assert payload["ok"] is False, payload
        assert "Patch" in str(payload.get("error") or ""), payload
