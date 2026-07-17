"""Lua responder tests (M2 — REQ-MVP-003/004, AC-MVP-012 automated sub-evidence).

Runs the production ``console/lua/copilot_responder.lua`` inside an embedded
Lua 5.4 runtime (lupa) with the MA3 API surface mocked — see
``lua_mock_env.py``. Replies captured on the Lua side are decoded with the
PYTHON codec (:mod:`server.bridge.protocol`), so every test here is also a
cross-language contract test of the v1 wire format.
"""

from __future__ import annotations

import pytest

from server.bridge.protocol import decode_payload

from .lua_mock_env import ResponderHarness

STATE_ADDRESS = "/copilot/state"
FEEDBACK_ADDRESS = "/copilot/feedback"


@pytest.fixture()
def harness() -> ResponderHarness:
    return ResponderHarness()


class TestLoading:
    def test_plugin_returns_callable_main(self, harness):
        assert callable(harness.main)

    def test_module_export_and_defaults(self, harness):
        config = harness.config
        assert config["state_address"] == STATE_ADDRESS
        assert config["feedback_address"] == FEEDBACK_ADDRESS
        assert config["send_variant"] == "packed"
        assert harness.module["PROTO"] == 1


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

    def test_missing_sendoscmessage_falls_back_to_cmd_keyword(self, harness):
        harness.lua.execute("SendOSCMessage = nil")
        harness.main(None, "ping 2")
        cmd_lines = harness.cmd_log()
        assert len(cmd_lines) == 1
        assert cmd_lines[0].startswith('SendOSC 1 "/copilot/feedback,s,')
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
