"""배치 초안 연결 시험 — 메시지 모양과 세션 흐름 (SPEC-LDARRANGE-001 두 번째 묶음).

제안(보류)은 격자와 콘솔을 바꾸지 않는다. 「적용」은 격자를 한 번에 바꾸고 되돌리기 기록을 남긴다.
「거절」은 아무것도 쓰지 않는다. 세 메시지 모두 콘솔에 닿지 않는다(``FakeConsole.executed``).
"""

from __future__ import annotations

import copy
import json

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_generator import generate_arrangement_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.web.messages import (
    PROTOCOL_VERSION,
    ProtocolError,
    beat_grid_draft_consumed_event,
    beat_grid_draft_event,
    parse_client_message,
)
from server.web.session import SongTimelineStore

from .test_session_beat_grid_edit_t551 import _new_session

EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]


def _bar_map() -> dict:
    beats = [index * 500 for index in range(40 * 4)]
    return build_bar_map_payload(beats, 0, bpm=120.0, events=EVENTS)


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = {"song_title": LOVE_ATTACK_TITLE, "sequence_number": 210, "bar_map": _bar_map()}
    sent: list[dict] = []
    session, console = _new_session(tmp_path, store=store, sent=sent)
    return session, console, store, sent


def _sent_of_type(sent: list[dict], event_type: str) -> list[dict]:
    return [event for event in sent if event.get("type") == event_type]


def _completed_statuses(sent: list[dict]) -> list[dict]:
    """``beat_grid_send_status`` 중 단계 완료(``completed``)를 실은 것만."""
    return [e for e in _sent_of_type(sent, "beat_grid_send_status") if "completed" in e]


class TestClientMessages:
    def test_propose_is_payload_free_and_is_not_turned_into_a_status_request(self) -> None:
        parsed = parse_client_message(
            json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_draft_propose"})
        )
        assert parsed["type"] == "beat_grid_draft_propose"

    def test_apply_and_reject_carry_the_draft_id(self) -> None:
        for kind in ("beat_grid_draft_apply", "beat_grid_draft_reject"):
            parsed = parse_client_message(
                json.dumps({"v": PROTOCOL_VERSION, "type": kind, "draft_id": "d-1"})
            )
            assert parsed == {"v": PROTOCOL_VERSION, "type": kind, "draft_id": "d-1"}

    def test_a_missing_or_blank_draft_id_is_a_protocol_error(self) -> None:
        for kind in ("beat_grid_draft_apply", "beat_grid_draft_reject"):
            with pytest.raises(ProtocolError):
                parse_client_message(json.dumps({"v": PROTOCOL_VERSION, "type": kind}))
            with pytest.raises(ProtocolError):
                parse_client_message(
                    json.dumps({"v": PROTOCOL_VERSION, "type": kind, "draft_id": " "})
                )


class TestServerEvents:
    def test_the_draft_event_is_json_and_lists_each_cell(self) -> None:
        bar_map = build_bar_map_payload([index * 500 for index in range(8 * 4)], 0, bpm=120.0)
        draft = generate_arrangement_draft(
            bar_map, list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])
        )
        event = beat_grid_draft_event(draft_id="d-1", draft=draft)
        assert event["v"] == PROTOCOL_VERSION
        assert event["type"] == "beat_grid_draft"
        assert event["draft_id"] == "d-1"
        assert event["bar_range"] == {"start": 1, "end": 8}
        json.dumps(event, ensure_ascii=False)
        back = next(track for track in event["tracks"] if track["group_name"] == "BACK")
        assert len(back["cells"]) == 8
        assert set(back["cells"][0]) == {"bar", "label"}

    def test_the_consumed_event_names_the_draft(self) -> None:
        assert beat_grid_draft_consumed_event(draft_id="d-1") == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_draft_consumed",
            "draft_id": "d-1",
        }


class TestPropose:
    def test_without_a_bar_map_the_proposal_is_refused(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = {"song_title": LOVE_ATTACK_TITLE, "sequence_number": 210}
        session, console = _new_session(tmp_path, store=store, sent=[])
        event = session.beat_grid_draft_propose()
        assert event["type"] == "chat_response"
        assert "마디 지도" in event["text"]
        assert "beat_grid" not in store.latest
        assert console.executed == []

    def test_propose_holds_a_draft_and_changes_nothing(self, harness) -> None:
        session, console, store, sent = harness
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_draft_propose()
        assert event["type"] == "beat_grid_draft"
        assert event["bar_range"] == {"start": 1, "end": 40}
        assert store.latest == before
        assert console.executed == []
        assert _sent_of_type(sent, "beat_grid_draft")[-1]["draft_id"] == event["draft_id"]


class TestApply:
    def test_apply_writes_the_grid_once_and_announces_it(self, harness) -> None:
        session, console, store, sent = harness
        draft_id = session.beat_grid_draft_propose()["draft_id"]
        result = session.beat_grid_draft_apply(draft_id)
        assert result["type"] == "chat_response"
        assert result["status"] == "ok"
        back = next(
            track for track in store.latest["beat_grid"]["tracks"] if track["group_name"] == "BACK"
        )
        # 운영 경로는 구간 생성기다: 구간 시작에만 칸이 선다(옛 생성기는 마디마다 하나라 30 이
        # 있었다). 구간 시작 31 에 킥 칸이 서고, 구간 안쪽 30 에는 새 칸이 없다.
        back_bars = {cue["bar"]: cue["label"] for cue in back["cues"]}
        assert back_bars.get(31) not in (None, "—")
        assert 30 not in back_bars
        assert len(back["cues"]) < 40
        assert _sent_of_type(sent, "beat_grid_draft_consumed")[-1]["draft_id"] == draft_id
        assert _sent_of_type(sent, "song_timeline")
        # 적용 성공은 기존 beat_grid_send_status 한 건으로 「초안 적용 단계 완료」를 알린다.
        statuses = _sent_of_type(sent, "beat_grid_send_status")
        assert statuses[-1]["last_action"] == "edit"
        assert statuses[-1]["ok"] is True
        assert statuses[-1]["completed"] == "draft_applied"
        assert "timecode_suggestion" not in statuses[-1]
        assert console.executed == []

    def test_a_second_apply_of_the_same_draft_is_refused(self, harness) -> None:
        session, console, store, sent = harness
        draft_id = session.beat_grid_draft_propose()["draft_id"]
        session.beat_grid_draft_apply(draft_id)
        completed_once = _completed_statuses(sent)
        again = session.beat_grid_draft_apply(draft_id)
        assert "찾을 수 없습니다" in again["text"]
        # 거절된 재적용은 단계 완료를 한 번 더 알리지 않는다.
        assert len(completed_once) == 1
        assert _completed_statuses(sent) == completed_once


class TestReject:
    def test_reject_consumes_the_draft_and_writes_nothing(self, harness) -> None:
        session, console, store, sent = harness
        draft_id = session.beat_grid_draft_propose()["draft_id"]
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_draft_reject(draft_id)
        assert event["status"] == "ok"
        assert store.latest == before
        assert console.executed == []
        assert _sent_of_type(sent, "beat_grid_draft_consumed")[-1]["draft_id"] == draft_id
        assert "찾을 수 없습니다" in session.beat_grid_draft_apply(draft_id)["text"]
        # 거절·그 뒤의 실패한 적용 어느 쪽도 「초안 적용」 단계 완료를 알리지 않는다.
        assert _completed_statuses(sent) == []
