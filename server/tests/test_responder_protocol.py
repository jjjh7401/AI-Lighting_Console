"""Tests for the responder wire protocol codec (M2 — REQ-MVP-003/004 server twin).

The codec is the Python half of the console protocol defined in
``console/lua/PROTOCOL.md`` (v1): payloads are percent-encoded JSON so they
survive MA3's packed OSC-send string form (comma/quote-free on the wire).
"""

from __future__ import annotations

import json

import pytest

from server.bridge.protocol import (
    PLUGIN_NAME,
    PROTOCOL_VERSION,
    ProtocolError,
    build_exec_request,
    build_ping,
    build_prop_query,
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

    def test_build_prop_query(self):
        line = build_prop_query("p-1", "DataPool/Sequences/Sequence 101/Cue 2", "TrigTime")
        assert line == (
            f'Plugin "{PLUGIN_NAME}" "prop p-1 DataPool/Sequences/Sequence 101/Cue 2 TrigTime"'
        )

    def test_build_prop_query_rejects_space_in_property_name(self):
        with pytest.raises(ProtocolError):
            build_prop_query("p-1", "DataPool/Sequences/1", "Trig Time")

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

    def test_request_id_with_space_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_ping("4 2")

    def test_empty_request_id_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_state_query("", "DataPool/Sequences")

    def test_empty_path_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_state_query("1", "")

    def test_protocol_version_is_one(self):
        assert PROTOCOL_VERSION == 1
