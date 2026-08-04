"""Tests for the responder wire protocol codec (M2 — REQ-MVP-003/004 server twin).

The codec is the Python half of the console protocol defined in
``console/lua/PROTOCOL.md`` (v1): payloads are percent-encoded JSON so they
survive MA3's packed OSC-send string form (comma/quote-free on the wire).
"""

from __future__ import annotations

import json

import pytest

from server.bridge.protocol import (
    MAX_PLUGIN_CALL_BYTES,
    MAX_PROPS_NAMES,
    PLUGIN_NAME,
    PROTOCOL_VERSION,
    ProtocolError,
    build_exec_request,
    build_introspect_query,
    build_ping,
    build_prop_query,
    build_props_query,
    build_state_query,
    decode_payload,
    encode_payload,
)


class TestPayloadCodec:
    def test_encode_decode_roundtrip_preserves_structure(self):
        payload = {
            "v": 1,
            "kind": "state",
            "id": "42",
            "ok": True,
            "children": [{"i": 1, "name": "Sequence 1"}],
        }
        assert decode_payload(encode_payload(payload)) == payload

    def test_encoded_payload_contains_no_commas_or_quotes(self):
        # Comma/quote freedom is the load-bearing property: MA3's packed
        # OSC-send form ("/addr,s,<payload>") splits on commas.
        payload = {"name": 'A, "quoted" name', "list": [1, 2, 3]}
        encoded = encode_payload(payload)
        assert "," not in encoded
        assert '"' not in encoded
        assert " " not in encoded

    def test_roundtrip_preserves_korean_utf8(self):
        payload = {"name": "보컬 그룹", "error": "시퀀스 없음"}
        assert decode_payload(encode_payload(payload)) == payload

    def test_decode_accepts_raw_json_leniently(self):
        # A future clean transport may deliver unencoded JSON.
        assert decode_payload('{"v": 1, "ok": true}') == {"v": 1, "ok": True}

    def test_decode_rejects_garbage(self):
        with pytest.raises(ProtocolError):
            decode_payload("not-json-not-percent")

    def test_decode_rejects_non_object_json(self):
        with pytest.raises(ProtocolError):
            decode_payload("%5B1%2C2%5D")  # percent-encoded "[1,2]"

    def test_decode_rejects_empty_string(self):
        with pytest.raises(ProtocolError):
            decode_payload("")

    def test_raw_json_with_literal_percent_substring_is_not_percent_decoded(self):
        # M6c backlog: a percent-shaped substring ANYWHERE in a raw (not
        # actually percent-encoded) payload used to trip the old
        # "does %XX appear anywhere" sniff and get incorrectly
        # urllib.parse.unquote'd — silently corrupting the value.
        payload = {"note": "discount %20 code"}
        text = json.dumps(payload)
        assert decode_payload(text) == payload

    def test_raw_json_with_literal_percent_newline_token_is_not_smuggled(self):
        # Worst case of the same bug: a literal "%0A" substring inside an
        # untouched raw-JSON string value must NOT become a real newline
        # character ("newline smuggling").
        payload = {"note": "escape %0A sequence"}
        text = json.dumps(payload)
        decoded = decode_payload(text)
        assert decoded["note"] == "escape %0A sequence"
        assert "\n" not in decoded["note"]
        assert "\r" not in decoded["note"]

    def test_genuinely_percent_encoded_payload_still_roundtrips(self):
        # Regression guard: percent-encoded replies (the production wire
        # form) must still decode correctly once raw-JSON-first parsing
        # is the primary path.
        payload = {"v": 1, "kind": "feedback", "note": "50% off, plus tax"}
        assert decode_payload(encode_payload(payload)) == payload


class TestRequestBuilders:
    def test_build_ping(self):
        assert build_ping("7") == f'Plugin "{PLUGIN_NAME}" "ping 7"'

    def test_build_state_query(self):
        line = build_state_query("42", "DataPool/Sequences")
        assert line == f'Plugin "{PLUGIN_NAME}" "state 42 DataPool/Sequences"'

    def test_build_state_query_allows_spaces_in_path(self):
        # Path is rest-of-line on the Lua side, so embedded spaces are legal.
        line = build_state_query("1", "DataPool/Sequences/My Seq")
        assert line.endswith('"state 1 DataPool/Sequences/My Seq"')

    def test_build_introspect_query(self):
        line = build_introspect_query("i-1", "DataPool/Sequences/Sequence 101")
        assert line == f'Plugin "{PLUGIN_NAME}" "introspect i-1 DataPool/Sequences/Sequence 101"'
        assert "\n" not in line
        assert "\r" not in line

    def test_build_introspect_query_allows_spaces_in_path(self):
        line = build_introspect_query("i-2", "DataPool/Sequences/My Seq")
        assert line.endswith('"introspect i-2 DataPool/Sequences/My Seq"')

    def test_build_prop_query(self):
        line = build_prop_query("p-1", "DataPool/Sequences/Sequence 101/Cue 2", "TrigTime")
        assert line == (
            f'Plugin "{PLUGIN_NAME}" "prop p-1 DataPool/Sequences/Sequence 101/Cue 2 TrigTime"'
        )

    def test_build_prop_query_rejects_space_in_property_name(self):
        with pytest.raises(ProtocolError):
            build_prop_query("p-1", "DataPool/Sequences/1", "Trig Time")

    def test_build_props_query(self):
        line = build_props_query(
            "ps-1",
            "DataPool/Sequences/Sequence 101/Cue 2",
            ["INDEX", "CURRENTCUE"],
        )
        assert line == (
            f'Plugin "{PLUGIN_NAME}" '
            '"props ps-1 INDEX,CURRENTCUE DataPool/Sequences/Sequence 101/Cue 2"'
        )
        assert "\n" not in line
        assert "\r" not in line

    def test_build_props_query_accepts_name_count_at_limit(self):
        names = [f"P{i:02d}" for i in range(1, MAX_PROPS_NAMES + 1)]
        line = build_props_query("ps-limit", "DataPool/Sequences/1", names)
        assert f'"props ps-limit {",".join(names)} DataPool/Sequences/1"' in line

    def test_build_props_query_rejects_name_count_over_limit(self):
        names = [f"P{i:02d}" for i in range(1, MAX_PROPS_NAMES + 2)]
        with pytest.raises(ProtocolError):
            build_props_query("ps-over", "DataPool/Sequences/1", names)

    def test_build_props_query_rejects_empty_name_list(self):
        with pytest.raises(ProtocolError):
            build_props_query("ps-empty", "DataPool/Sequences/1", [])

    def test_build_props_query_rejects_string_name_list(self):
        with pytest.raises(ProtocolError):
            build_props_query("ps-string", "DataPool/Sequences/1", "INDEX")

    def test_build_props_query_rejects_space_in_property_name(self):
        with pytest.raises(ProtocolError):
            build_props_query("ps-space", "DataPool/Sequences/1", ["Trig Time"])

    def test_build_props_query_rejects_comma_in_property_name(self):
        with pytest.raises(ProtocolError):
            build_props_query("ps-comma", "DataPool/Sequences/1", ["TRIG,TIME"])

    def test_build_exec_request(self):
        line = build_exec_request("9", "List")
        assert line == f'Plugin "{PLUGIN_NAME}" "exec 9 List"'

    def test_double_quote_in_command_is_rejected(self):
        # A double quote would terminate MA3's quoted plugin argument.
        with pytest.raises(ProtocolError):
            build_exec_request("1", 'Store Cue 5 "name"')

    def test_double_quote_in_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_state_query("1", 'DataPool/"Sequences"')

    def test_double_quote_in_introspect_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_introspect_query("1", 'DataPool/"Sequences"')

    def test_double_quote_in_props_name_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_props_query("1", "DataPool/Sequences/1", ['"INDEX"'])

    def test_newline_in_introspect_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_introspect_query("1", "DataPool/Sequences\nList")

    def test_newline_in_props_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_props_query("1", "DataPool/Sequences\nList", ["INDEX"])

    def test_request_id_with_space_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_ping("4 2")

    def test_introspect_request_id_with_space_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_introspect_query("4 2", "DataPool/Sequences")

    def test_props_request_id_with_space_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_props_query("4 2", "DataPool/Sequences", ["INDEX"])

    def test_empty_request_id_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_state_query("", "DataPool/Sequences")

    def test_empty_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_state_query("1", "")

    def test_empty_props_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_props_query("1", "", ["INDEX"])

    def test_introspect_query_rejects_encoded_line_over_limit(self):
        with pytest.raises(ProtocolError):
            build_introspect_query("1", "DataPool/" + ("X" * MAX_PLUGIN_CALL_BYTES))

    def test_props_query_rejects_encoded_line_over_limit(self):
        with pytest.raises(ProtocolError):
            build_props_query(
                "1",
                "DataPool/" + ("X" * MAX_PLUGIN_CALL_BYTES),
                ["INDEX"],
            )

    def test_protocol_version_is_one(self):
        assert PROTOCOL_VERSION == 1
