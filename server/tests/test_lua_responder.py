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
from server.orchestrator.tools import rig_object

from .lua_mock_env import (
    GAPPED_GROUP_NAMES,
    GAPPED_GROUP_SLOTS,
    ResponderHarness,
    gapped_groups_env,
)

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
