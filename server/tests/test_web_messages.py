"""WebSocket protocol v1 message schema tests (M5 — REQ-MVP-020/021 surface).

The protocol is the contract between the FastAPI WebSocket server, the React
client, and the M6 measurement harness — versioned (``v: 1``) and documented in
``server/web/PROTOCOL.md``. Client messages are strictly validated (unknown or
malformed input never reaches the orchestrator); server events are plain dicts
built by one builder per event type.
"""

from __future__ import annotations

import json

import pytest

from server.safety.approval import ApprovalItem, ApprovalRequest
from server.web.messages import (
    PANEL_CLIENT_MESSAGE_TYPES,
    PROTOCOL_VERSION,
    ProtocolError,
    approval_request_event,
    approval_resolved_event,
    busy_event,
    chat_response_event,
    error_event,
    notice_event,
    panel_busy_event,
    panel_catalog_event,
    panel_item,
    panel_item_id,
    panel_item_state_event,
    panel_section,
    parse_client_message,
    proposal_event,
    status_event,
)


def _raw(**fields) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


class TestClientMessageParsing:
    def test_chat_message_parses(self):
        message = parse_client_message(_raw(type="chat", text="보컬 그룹 만들어줘"))
        assert message["type"] == "chat"
        assert message["text"] == "보컬 그룹 만들어줘"

    def test_approval_decision_parses(self):
        message = parse_client_message(
            _raw(type="approval_decision", request_id="req-1", approved=True)
        )
        assert message["type"] == "approval_decision"
        assert message["request_id"] == "req-1"
        assert message["approved"] is True

    def test_lock_toggle_parses(self):
        message = parse_client_message(_raw(type="lock", active=False))
        assert message["type"] == "lock"
        assert message["active"] is False

    def test_status_request_parses(self):
        assert parse_client_message(_raw(type="status_request"))["type"] == "status_request"

    @pytest.mark.parametrize(
        "raw",
        [
            "not json at all",
            json.dumps(["a", "list"]),
            json.dumps({"type": "chat", "text": "hi"}),  # missing v
            json.dumps({"v": 99, "type": "chat", "text": "hi"}),  # wrong version
            json.dumps({"v": 1, "type": "unknown_type"}),
            json.dumps({"v": 1, "type": "chat"}),  # missing text
            json.dumps({"v": 1, "type": "chat", "text": "   "}),  # blank text
            json.dumps({"v": 1, "type": "chat", "text": 42}),  # non-string text
            json.dumps({"v": 1, "type": "approval_decision", "approved": True}),  # no id
            json.dumps({"v": 1, "type": "approval_decision", "request_id": "r"}),  # no bool
            json.dumps({"v": 1, "type": "approval_decision", "request_id": "r", "approved": "yes"}),
            json.dumps({"v": 1, "type": "lock"}),  # missing active
            json.dumps({"v": 1, "type": "lock", "active": 1}),  # non-bool active
        ],
    )
    def test_malformed_client_messages_are_rejected(self, raw):
        with pytest.raises(ProtocolError):
            parse_client_message(raw)


def _request() -> ApprovalRequest:
    return ApprovalRequest(
        items=(
            ApprovalItem(
                command="Delete Sequence 5",
                risk_reasons=("blacklist: Delete",),
                warnings=("unspecified-target warning",),
            ),
        )
    )


class TestServerEventBuilders:
    def test_every_event_carries_version_and_type(self):
        events = [
            chat_response_event(status="ok", summary="완료", text="했어요", commands=[]),
            approval_request_event(request_id="r1", request=_request()),
            approval_resolved_event(request_id="r1", approved=True),
            status_event(health="online", live_lock=False, executions_blocked=False),
            proposal_event(commands=["Store Cue 1"], reasons=["live lock"]),
            error_event(message="오류", kind="rate_limit"),
            busy_event(message="처리 중"),
            notice_event(message="알림"),
        ]
        for event in events:
            assert event["v"] == PROTOCOL_VERSION
            assert isinstance(event["type"], str) and event["type"]
            json.dumps(event, ensure_ascii=False)  # must be JSON-serializable

    def test_approval_request_event_carries_commands_reasons_warnings_actions(self):
        event = approval_request_event(request_id="req-7", request=_request())
        assert event["type"] == "approval_request"
        assert event["request_id"] == "req-7"
        assert event["actions"] == ["approve", "reject"]
        (item,) = event["items"]
        assert item["command"] == "Delete Sequence 5"
        assert item["risk_reasons"] == ["blacklist: Delete"]
        assert item["warnings"] == ["unspecified-target warning"]

    def test_chat_response_event_shape(self):
        event = chat_response_event(
            status="ok",
            summary="실행 완료",
            text="그룹을 만들었습니다",
            commands=[{"command": "Store Group 3", "status": "executed_ok", "label": "실행 완료"}],
        )
        assert event["type"] == "chat_response"
        assert event["status"] == "ok"
        assert event["summary"] == "실행 완료"
        assert event["text"] == "그룹을 만들었습니다"
        assert event["commands"][0]["label"] == "실행 완료"

    def test_status_event_shape(self):
        event = status_event(health="console_offline", live_lock=True, executions_blocked=True)
        assert event["type"] == "status"
        assert event["health"] == "console_offline"
        assert event["live_lock"] is True
        assert event["executions_blocked"] is True

    def test_proposal_event_shape(self):
        event = proposal_event(commands=["Store Cue 1"], reasons=["live lock active"])
        assert event["type"] == "proposal"
        assert event["commands"] == ["Store Cue 1"]
        assert event["reasons"] == ["live lock active"]

    def test_error_event_shape(self):
        event = error_event(message="한도 초과", kind="rate_limit")
        assert event["type"] == "error"
        assert event["message"] == "한도 초과"
        assert event["kind"] == "rate_limit"


# -- SPEC-COPILOT-SHOWUI-001 M1 — show-control panel protocol contract ----------
#
# The panel's client messages and server events are an ADDITIVE v1 extension
# (the same call as the M7 ``review_decision`` extension): PROTOCOL_VERSION
# stays 1 and every new type is registered on BOTH allowlists (REQ-SHOWUI-014).
# The two sides' unknown-type contracts stay DELIBERATELY asymmetric — the TS
# client null-drops, the server rejects loudly — and both halves are pinned.


class TestPanelClientMessages:
    """AC-SHOWUI-001 (server half) + AC-SHOWUI-005 rejection half (REQ-022)."""

    def test_every_panel_type_is_on_the_client_allowlist(self):
        # AC-SHOWUI-001: the five new client types parse. A type missing from
        # the allowlist is the silent-feature-loss failure REQ-014 exists for.
        assert set(PANEL_CLIENT_MESSAGE_TYPES) == {
            "panel_execute",
            "panel_stop",
            "panel_pin",
            "panel_unpin",
            "panel_catalog_request",
        }

    def test_panel_execute_parses_with_a_real_object_number(self):
        message = parse_client_message(
            _raw(type="panel_execute", target_kind="executor", target=191)
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "panel_execute",
            "target_kind": "executor",
            "target": 191,
        }

    def test_panel_stop_parses_with_a_real_object_number(self):
        message = parse_client_message(_raw(type="panel_stop", target_kind="sequence", target=41))
        assert message["type"] == "panel_stop"
        assert message["target_kind"] == "sequence"
        assert message["target"] == 41

    def test_panel_unpin_parses_with_a_real_object_number(self):
        message = parse_client_message(_raw(type="panel_unpin", target_kind="executor", target=201))
        assert message["type"] == "panel_unpin"
        assert message["target"] == 201

    def test_payload_free_panel_messages_parse(self):
        # REQ-SHOWUI-004: the pin seed is the server's own ``_last_created``
        # cross-turn memory, so the client sends no target to be trusted with.
        assert parse_client_message(_raw(type="panel_pin"))["type"] == "panel_pin"
        assert (
            parse_client_message(_raw(type="panel_catalog_request"))["type"]
            == "panel_catalog_request"
        )

    def test_a_panel_typo_is_still_an_unknown_type(self):
        # AC-SHOWUI-001 negative half: widening the allowlist must not turn it
        # into a prefix match — the server rejects, loudly, as before.
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="panel_execute_all"))

    @pytest.mark.parametrize("message_type", ["panel_execute", "panel_stop", "panel_unpin"])
    @pytest.mark.parametrize(
        "target",
        [
            "191",  # a string that merely looks like a number
            19.1,  # a float
            None,  # explicit null
            True,  # bool is an int subclass in Python — must NOT slip through
            -3,  # negative
            0,  # console pools are 1-based; 0 addresses nothing
            [191],
            {"no": 191},
        ],
        ids=["string", "float", "null", "bool", "negative", "zero", "list", "object"],
    )
    def test_malformed_targets_are_rejected_at_parse_time(self, message_type, target):
        # REQ-SHOWUI-022 / AC-SHOWUI-005: rejection happens in
        # parse_client_message, so no command bundle is ever constructed and
        # gate.screen() is never reached with a client-controlled number.
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type=message_type, target_kind="executor", target=target))

    @pytest.mark.parametrize("message_type", ["panel_execute", "panel_stop", "panel_unpin"])
    def test_a_missing_target_is_rejected(self, message_type):
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type=message_type, target_kind="executor"))

    @pytest.mark.parametrize("message_type", ["panel_execute", "panel_stop", "panel_unpin"])
    @pytest.mark.parametrize("target_kind", ["fixtures", "fixture", "group", "", None, 1])
    def test_a_non_playback_target_kind_is_rejected(self, message_type, target_kind):
        # REQ-SHOWUI-003: a fixture's ``no`` is its patch slot, NOT its FID, so
        # fixtures can never be a playback target. The discriminator is closed.
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type=message_type, target_kind=target_kind, target=191),
            )

    @pytest.mark.parametrize("message_type", ["panel_execute", "panel_stop", "panel_unpin"])
    def test_a_missing_target_kind_is_rejected(self, message_type):
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type=message_type, target=191))

    def test_the_panel_extension_does_not_bump_the_protocol_version(self):
        # REQ-SHOWUI-014: additive extension, v stays 1 (M7 review_decision call).
        assert PROTOCOL_VERSION == 1
        with pytest.raises(ProtocolError):
            parse_client_message(
                json.dumps(
                    {"v": 2, "type": "panel_execute", "target_kind": "executor", "target": 1}
                )
            )


class TestPanelItemSchema:
    """The frozen panel-item shape every later milestone builds on."""

    def test_panel_item_carries_the_full_tile_contract(self):
        item = panel_item(
            kind="sequence",
            target_kind="executor",
            target=191,
            name="Summer Rock",
            appearance="#00c8ff",
            source="auto",
        )
        assert item == {
            "id": "executor:191",
            "kind": "sequence",
            "target_kind": "executor",
            "target": 191,
            "name": "Summer Rock",
            "appearance": "#00c8ff",
            "source": "auto",
        }

    def test_the_item_id_is_keyed_on_the_real_object_number(self):
        # REQ-SHOWUI-003: never an array index. Pool numbers are
        # non-contiguous, so "the Nth tile" and "object N" are different things.
        catalog = [
            panel_item(
                kind="sequence", target_kind="sequence", target=no, name=f"seq {no}", source="auto"
            )
            for no in (2, 7, 41)
        ]
        assert [item["id"] for item in catalog] == ["sequence:2", "sequence:7", "sequence:41"]
        assert panel_item_id("executor", 191) == "executor:191"

    def test_appearance_is_optional_and_defaults_to_null(self):
        item = panel_item(
            kind="look", target_kind="executor", target=5, name="Cyan Look", source="pin"
        )
        assert item["appearance"] is None

    @pytest.mark.parametrize("kind", ["look", "effect", "sequence"])
    def test_the_three_tile_kinds_are_accepted(self, kind):
        # design.md §4 — the LOOK / FX / SEQ badge set.
        assert (
            panel_item(kind=kind, target_kind="executor", target=1, name="x", source="auto")["kind"]
            == kind
        )

    @pytest.mark.parametrize("kind", ["fixture", "group", "cue", "", None])
    def test_an_unknown_tile_kind_is_refused(self, kind):
        with pytest.raises(ValueError):
            panel_item(kind=kind, target_kind="executor", target=1, name="x", source="auto")

    @pytest.mark.parametrize("target_kind", ["fixtures", "fixture", "group", "", None])
    def test_a_fixture_can_never_become_an_execution_tile(self, target_kind):
        # REQ-SHOWUI-003, second clause.
        with pytest.raises(ValueError):
            panel_item(kind="look", target_kind=target_kind, target=1, name="x", source="auto")

    @pytest.mark.parametrize("target", ["1", 1.5, None, True, 0, -1])
    def test_a_non_object_number_target_is_refused(self, target):
        with pytest.raises(ValueError):
            panel_item(kind="look", target_kind="executor", target=target, name="x", source="auto")

    @pytest.mark.parametrize("source", ["pin", "auto"])
    def test_both_item_sources_are_accepted(self, source):
        # REQ-SHOWUI-001 (rig enumeration) + REQ-SHOWUI-004 (chat pin).
        assert (
            panel_item(kind="look", target_kind="executor", target=1, name="x", source=source)[
                "source"
            ]
            == source
        )

    @pytest.mark.parametrize("source", ["chat", "", None, "AUTO"])
    def test_an_unknown_item_source_is_refused(self, source):
        with pytest.raises(ValueError):
            panel_item(kind="look", target_kind="executor", target=1, name="x", source=source)


class TestPanelSectionSchema:
    """REQ-SHOWUI-001/002 — the completeness + failure-cause carriers."""

    def test_a_resolved_section_reports_its_own_completeness_flags(self):
        section = panel_section(
            name="sequences",
            status="ok",
            truncated=True,
            drilldown_capped=True,
            contents_unavailable=True,
        )
        assert section == {
            "name": "sequences",
            "status": "ok",
            "truncated": True,
            "drilldown_capped": True,
            "contents_unavailable": True,
        }

    def test_completeness_flags_default_to_false(self):
        section = panel_section(name="pages", status="ok")
        assert section["truncated"] is False
        assert section["drilldown_capped"] is False
        assert section["contents_unavailable"] is False

    def test_the_two_failure_causes_stay_distinct(self):
        # REQ-SHOWUI-002: merging these is exactly how two dead default rig
        # paths survived unnoticed for a whole stage — "the path is wrong" and
        # "the console did not answer" demand different operator actions.
        unresolved = panel_section(name="pages", status="path_not_resolved")
        unreachable = panel_section(name="sequences", status="console_unreachable")
        assert unresolved["status"] != unreachable["status"]
        assert {unresolved["status"], unreachable["status"]} == {
            "path_not_resolved",
            "console_unreachable",
        }

    @pytest.mark.parametrize("status", ["unavailable", "error", "", None, "OK"])
    def test_an_unknown_section_status_is_refused(self, status):
        with pytest.raises(ValueError):
            panel_section(name="sequences", status=status)


class TestPanelServerEvents:
    """AC-SHOWUI-001 (server-event half) — builders + JSON-serializability."""

    def _catalog(self) -> dict:
        return panel_catalog_event(
            items=[
                panel_item(
                    kind="sequence",
                    target_kind="executor",
                    target=191,
                    name="Summer Rock",
                    appearance="#ff3fa4",
                    source="auto",
                ),
                panel_item(
                    kind="look", target_kind="executor", target=201, name="Cyan", source="pin"
                ),
            ],
            sections=[
                panel_section(name="sequences", status="ok", truncated=True),
                panel_section(name="pages", status="path_not_resolved"),
            ],
        )

    def test_every_panel_event_carries_version_and_type(self):
        events = [
            self._catalog(),
            panel_item_state_event(target_kind="executor", target=191, running=True, cue="3"),
            panel_busy_event(target_kind="executor", target=191, message="실행 처리 중입니다"),
        ]
        for event in events:
            assert event["v"] == PROTOCOL_VERSION
            assert isinstance(event["type"], str) and event["type"]
            json.dumps(event, ensure_ascii=False)  # must be JSON-serializable

    def test_catalog_event_preserves_item_order(self):
        # REQ-SHOWUI-005/017: append-only. The wire order IS the grid order —
        # nothing sorts it, so a tile never moves under the operator's finger.
        event = self._catalog()
        assert event["type"] == "panel_catalog"
        assert [item["id"] for item in event["items"]] == ["executor:191", "executor:201"]

    def test_catalog_event_carries_the_section_flags_through(self):
        event = self._catalog()
        sequences, pages = event["sections"]
        assert sequences["truncated"] is True
        assert pages["status"] == "path_not_resolved"

    def test_catalog_event_accepts_an_empty_rig(self):
        event = panel_catalog_event(items=[], sections=[])
        assert event["items"] == []
        assert event["sections"] == []

    def test_item_state_event_shape(self):
        event = panel_item_state_event(target_kind="executor", target=191, running=True, cue="3")
        assert event["type"] == "panel_item_state"
        assert event["id"] == "executor:191"
        assert event["target_kind"] == "executor"
        assert event["target"] == 191
        assert event["running"] is True
        assert event["cue"] == "3"

    def test_item_state_cue_is_optional(self):
        event = panel_item_state_event(target_kind="sequence", target=41, running=False)
        assert event["running"] is False
        assert event["cue"] is None

    def test_busy_event_names_the_tile_it_refused(self):
        # REQ-SHOWUI-011: the UI must unlock the RIGHT tile — a bare busy
        # message would leave the pressed tile latched forever.
        event = panel_busy_event(target_kind="executor", target=191, message="실행 처리 중입니다")
        assert event["type"] == "panel_busy"
        assert event["id"] == "executor:191"
        assert event["message"] == "실행 처리 중입니다"
