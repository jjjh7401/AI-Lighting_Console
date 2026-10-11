"""WebSocket protocol v1 — 박자 격자 편집 세 길의 전용 메시지 타입 (카드
t551, SPEC-LDBEAT-001 M3). 채팅(`"chat"`) 타입과 분리된 별도 채널 —
``"beat_grid_edit"``/``"beat_grid_suggest"``/``"beat_grid_suggestion_apply"``.
"""

from __future__ import annotations

import json

import pytest

from server.web.messages import (
    PROTOCOL_VERSION,
    ProtocolError,
    beat_grid_suggestion_consumed_event,
    beat_grid_suggestion_event,
    parse_client_message,
)


def _raw(**fields) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


class TestBeatGridEditMessage:
    def test_changes_path_parses(self) -> None:
        message = parse_client_message(
            _raw(
                type="beat_grid_edit",
                bar=11,
                target="MOVER-U",
                changes={"entry": {"fade_bars": 1, "mib_mode": None}},
            )
        )
        assert message["type"] == "beat_grid_edit"
        assert message["bar"] == 11
        assert message["target"] == "MOVER-U"
        assert message["changes"] == {"entry": {"fade_bars": 1, "mib_mode": None}}
        assert "sentence" not in message

    def test_sentence_path_parses(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_edit", sentence="11마디 MOVER-U 밝기를 70%로")
        )
        assert message["type"] == "beat_grid_edit"
        assert message["sentence"] == "11마디 MOVER-U 밝기를 70%로"
        assert "bar" not in message
        assert "changes" not in message

    def test_both_changes_and_sentence_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(
                    type="beat_grid_edit",
                    bar=11,
                    target="MOVER-U",
                    changes={"entry": {"fade_bars": 1}},
                    sentence="11마디 MOVER-U 밝기를 70%로",
                )
            )

    def test_neither_changes_nor_sentence_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", bar=11, target="MOVER-U"))

    def test_missing_target_with_changes_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_edit", bar=11, changes={"entry": {"fade_bars": 1}})
            )

    def test_empty_changes_dict_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", bar=11, target="MOVER-U", changes={}))

    def test_bool_bar_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(
                    type="beat_grid_edit",
                    bar=True,
                    target="MOVER-U",
                    changes={"entry": {"fade_bars": 1}},
                )
            )


class TestBeatGridSuggestMessage:
    def test_valid_message_parses(self) -> None:
        message = parse_client_message(_raw(type="beat_grid_suggest", bar=7, target="BACK"))
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_suggest",
            "bar": 7,
            "target": "BACK",
        }

    def test_missing_target_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_suggest", bar=7))


class TestBeatGridSuggestionApplyMessage:
    def test_valid_message_parses(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_suggestion_apply", suggestion_id="abc-123")
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_suggestion_apply",
            "suggestion_id": "abc-123",
        }

    def test_missing_suggestion_id_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_suggestion_apply"))


class TestBeatGridSuggestionEvent:
    def test_builder_shape(self) -> None:
        event = beat_grid_suggestion_event(
            suggestion_id="abc-123",
            bar=7,
            target="BACK",
            changes={"entry": {"fade_bars": 1}},
            rationale="테스트 근거",
        )
        assert event == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_suggestion",
            "suggestion_id": "abc-123",
            "bar": 7,
            "target": "BACK",
            "changes": {"entry": {"fade_bars": 1}},
            "rationale": "테스트 근거",
        }


class TestBeatGridSuggestionConsumedEvent:
    def test_builder_shape(self) -> None:
        event = beat_grid_suggestion_consumed_event(suggestion_id="abc-123")
        assert event == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_suggestion_consumed",
            "suggestion_id": "abc-123",
        }
