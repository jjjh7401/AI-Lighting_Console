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
        # 칸마다 마디·라벨과 그 칸의 방향 값(`direction`)을 싣는다. 옛 구조화 필드는 싣지 않는다.
        assert set(back["cells"][0]) == {"bar", "label", "direction"}

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
        # 있었다). 구간 시작 31 에 칸이 서고, 구간 안쪽 30 에는 새 칸이 없다. 31 의 창에서는 보조
        # 자리가 체이스 차례라 BACK 이 쉰다(카드 WT-side-allocation) — 킥 칸은 다른 창에 선다.
        back_bars = {cue["bar"]: cue["label"] for cue in back["cues"]}
        assert 31 in back_bars
        assert 30 not in back_bars
        assert any(label not in (None, "—") for label in back_bars.values())
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


class TestNewSongRowsFromConsole:
    """카드 WT-all-fixtures — 등록 안 된 곡도 콘솔 그룹으로 줄이 생긴다(감독 2026-10-18).

    예전에는 기본 격자 파일이 없는 곡의 줄이 0개라 「자동 배치 초안이 비어 있습니다」로
    거절됐다. 지금은 콘솔에서 그룹·소속 장비를 **읽기만** 해서 줄을 정한다.
    """

    @staticmethod
    def _session(tmp_path, *, title: str = "NEW SONG"):
        from .test_beat_grid_stage import FIXTURES, GROUPS
        from .test_beat_grid_stage import FakeConsole as StageConsole

        fixtures = [
            {"slot": 1, "fid": 101, "name": "Key 1", "x": 0.0, "y": 0.0, "z": 0.0, "sf": 1},
            {"slot": 2, "fid": 111, "name": "Foh 1", "x": 1.0, "y": 0.0, "z": 0.0, "sf": 2},
            {"slot": 3, "fid": 201, "name": "Back 1", "x": 0.0, "y": 5.0, "z": 3.0, "sf": 3},
            {"slot": 4, "fid": 202, "name": "Back 2", "x": 2.0, "y": 5.0, "z": 3.0, "sf": 4},
        ]
        groups = {
            1: ("ALL", [1, 2, 3, 4]),
            2: ("KEY", [1]),
            3: ("FOH", [2]),
            4: ("BACK", [3, 4]),
        }
        store = SongTimelineStore()
        store.latest = {"song_title": title, "sequence_number": 7, "bar_map": _bar_map()}
        sent: list[dict] = []
        session, console = _new_session(tmp_path, store=store, sent=sent)
        session._stage_port = StageConsole(fixtures=fixtures, groups=groups)
        session._rig_paths = {**session._rig_paths, "fixtures": FIXTURES, "groups": GROUPS}
        return session, console, store, sent

    def test_a_new_song_gets_rows_from_console_groups_and_the_draft_is_not_refused(
        self, tmp_path
    ) -> None:
        session, console, store, sent = self._session(tmp_path)
        event = session.beat_grid_draft_propose()
        assert event["type"] == "beat_grid_draft", event.get("text")
        assert [track["group_name"] for track in event["tracks"]] == ["KEY", "FOH", "BACK"]
        assert event["console_coverage"]["uncovered"] == []
        assert console.executed == []

    def test_applying_it_creates_the_rows_and_keeps_the_coverage_on_the_grid(
        self, tmp_path
    ) -> None:
        session, console, store, sent = self._session(tmp_path)
        draft_id = session.beat_grid_draft_propose()["draft_id"]
        result = session.beat_grid_draft_apply(draft_id)
        assert result["status"] == "ok", result.get("text")
        grid = store.latest["beat_grid"]
        assert [track["group_name"] for track in grid["tracks"]] == ["KEY", "FOH", "BACK"]
        assert grid["console_coverage"]["uncovered"] == []
        assert console.executed == []

    def test_love_attack_rows_stay_and_the_missing_key_row_is_added(self, tmp_path) -> None:
        session, console, store, sent = self._session(tmp_path, title=LOVE_ATTACK_TITLE)
        event = session.beat_grid_draft_propose()
        names = [track["group_name"] for track in event["tracks"]]
        default_names = [
            track["group_name"] for track in default_beat_grid(LOVE_ATTACK_TITLE)["tracks"]
        ]
        # 기본 격자의 줄은 그대로 앞에 있고, 콘솔에만 있는 KEY 가 뒤에 붙는다.
        assert names[: len(default_names)] == default_names
        assert names[len(default_names) :] == ["KEY"]

    def test_a_smoke_machine_is_left_out_on_purpose_and_shown_as_such(self, tmp_path) -> None:
        # 감독 2026-10-18 — HAZE 는 연기 장비라 무시. 판단은 채널 속성(Haze1·Blower1)으로 한다.
        from types import SimpleNamespace

        from .test_beat_grid_stage import FakeConsole as StageConsole

        session, console, store, sent = self._session(tmp_path)
        stage = session._stage_port
        session._stage_port = StageConsole(
            fixtures=[
                *stage.fixtures,
                {"slot": 5, "fid": 621, "name": "Haze 1", "x": 0.0, "y": 6.0, "z": 0.0, "sf": 5},
            ],
            groups={**stage.groups, 1: ("ALL", [1, 2, 3, 4, 5]), 16: ("HAZE", [5])},
        )

        def cap(*attributes: str) -> SimpleNamespace:
            return SimpleNamespace(
                whole=True,
                attributes=attributes,
                has_attribute=lambda name, a=attributes: name in a,
            )

        fixtures = {101: cap("Dimmer"), 111: cap("Dimmer"), 201: cap("Dimmer"), 202: cap("Dimmer")}
        fixtures[621] = cap("Haze1", "Blower1")
        session._try_rig_capabilities = lambda: SimpleNamespace(  # type: ignore[method-assign]
            capabilities=SimpleNamespace(fixtures=fixtures)
        )
        event = session.beat_grid_draft_propose()
        assert [track["group_name"] for track in event["tracks"]] == ["KEY", "FOH", "BACK"]
        [missing] = event["console_coverage"]["uncovered"]
        assert missing["fid"] == 621
        assert missing["group_names"] == ["HAZE"]
        assert missing["reason"] == "일부러 뺌: 연기 장비(연출 대상 아님)"
        assert missing["intentional"] is True
        assert console.executed == []

    def test_without_console_paths_a_new_song_is_refused_with_the_reason(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = {"song_title": "NEW SONG", "sequence_number": 7, "bar_map": _bar_map()}
        session, console = _new_session(tmp_path, store=store, sent=[])
        session._rig_paths = {**session._rig_paths, "fixtures": None, "groups": None}
        event = session.beat_grid_draft_propose()
        assert event["type"] == "chat_response"
        # 「비어 있습니다」가 아니라 왜 줄이 없는지(콘솔 그룹을 못 읽음)를 말한다.
        assert "콘솔 그룹" in event["text"]
