"""SPEC-LDBEAT-001 「콘솔 같이」 마디 이동 — 정지 중 옮긴 마디의 시각으로 타임코드 커서를 세운다.

``Set Timecode N Property 'Cursor' <초>`` 한 줄(소유 타임코드마다)만 보낸다. 재생은 켜지 않는다
(정지 중 실측). 보낸 뒤 커서를 되읽어 목표에 섰는지 알린다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓰고, 커서 되읽기는 테스트가 값을 정해 준다.
"""

from __future__ import annotations

import json

import pytest

from server.web.messages import PROTOCOL_VERSION, ProtocolError, parse_client_message
from server.web.session import SongTimelineStore, _cursor_seconds_text

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _empty_pool_state_tree,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)


def _owned_session(tmp_path):
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    return _new_session(tmp_path, store=store, state_tree=_owned_state_tree())


def _cursor_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if "'Cursor'" in c]


def _quiet_reads(monkeypatch, session, cursor):
    monkeypatch.setattr(session, "_beat_grid_stop_check_interval_seconds", 0.0)
    monkeypatch.setattr(session, "_beat_grid_timecode_cursor", lambda path: cursor)


class TestConsoleSeek:
    def test_seek_sends_one_cursor_line_per_owned_timecode_and_never_starts_playback(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, 82.4)

        event = session.beat_grid_console_seek(82.4)

        assert event["ok"] is True
        assert _cursor_lines(console.executed) == [
            f"Set Timecode {TIMECODE_NUMBER} Property 'Cursor' 82.4"
        ]
        # 재생을 켜는 줄(Top·Go)과 멈춤 줄(Off)은 보내지 않는다.
        forbidden = ("Top Timecode", "Go Timecode", "Off Timecode")
        assert not any(c.startswith(forbidden) for c in console.executed)

    def test_seek_says_so_when_the_cursor_did_not_land_on_the_target(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, 83.7)

        event = session.beat_grid_console_seek(82.4)

        assert event["ok"] is True
        assert "83.70초에 있어요" in json.dumps(event, ensure_ascii=False)

    def test_seek_says_it_could_not_verify_when_the_cursor_cannot_be_read(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, None)

        event = session.beat_grid_console_seek(82.4)

        assert "확인하지 못했어요" in json.dumps(event, ensure_ascii=False)

    def test_seek_refuses_without_an_owned_timecode_and_sends_nothing(self, tmp_path) -> None:
        session, console, _approval, _audit = _new_session(
            tmp_path, store=SongTimelineStore(), state_tree=_empty_pool_state_tree()
        )

        event = session.beat_grid_console_seek(82.4)

        assert event["ok"] is False
        assert _cursor_lines(console.executed) == []

    @pytest.mark.parametrize(
        ("seconds", "text"),
        [
            (82.4, "82.4"),
            (83.0, "83"),
            (0.5, "0.5"),
            (82.35, "82.35"),
            (0.0, "0"),
            (82.3456, "82.346"),
        ],
    )
    def test_cursor_text_keeps_three_decimals_at_most_and_drops_trailing_zeros(
        self, seconds, text
    ) -> None:
        assert _cursor_seconds_text(seconds) == text


class TestSeekMessage:
    def test_the_parser_takes_a_finite_number_of_seconds(self) -> None:
        raw = json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_console_seek", "seconds": 82.4})

        message = parse_client_message(raw)

        assert message == {"v": PROTOCOL_VERSION, "type": "beat_grid_console_seek", "seconds": 82.4}

    @pytest.mark.parametrize("seconds", [True, -1, "82.4", None, 86401, float("nan")])
    def test_the_parser_refuses_bad_seconds(self, seconds) -> None:
        raw = json.dumps(
            {"v": PROTOCOL_VERSION, "type": "beat_grid_console_seek", "seconds": seconds},
            allow_nan=True,
        )

        with pytest.raises(ProtocolError):
            parse_client_message(raw)

    def test_the_parser_accepts_the_playing_and_resync_flags_and_refuses_non_booleans(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_console_seek",
                "seconds": 60,
                "playing": True,
                "resync": True,
            }
        )

        assert parse_client_message(raw) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_console_seek",
            "seconds": 60.0,
            "playing": True,
            "resync": True,
        }
        bad = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_console_seek",
                "seconds": 60,
                "resync": "yes",
            }
        )
        with pytest.raises(ProtocolError):
            parse_client_message(bad)


class TestLiveAndResync:
    def test_a_seek_while_playing_says_nothing_about_landing(self, tmp_path, monkeypatch) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, 83.7)

        event = session.beat_grid_console_seek(82.4, playing=True)

        assert event["ok"] is True
        assert _cursor_lines(console.executed) == [
            f"Set Timecode {TIMECODE_NUMBER} Property 'Cursor' 82.4"
        ]
        assert "83.70초에 있어요" not in json.dumps(event, ensure_ascii=False)

    def test_resync_sends_nothing_when_the_cursor_is_within_tolerance(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, 60.1)

        event = session.beat_grid_console_seek(60.0, resync=True)

        assert event["ok"] is True
        assert _cursor_lines(console.executed) == []

    def test_resync_corrects_a_cursor_that_drifted_past_the_tolerance(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, 61.0)

        event = session.beat_grid_console_seek(60.0, resync=True)

        assert event["ok"] is True
        assert _cursor_lines(console.executed) == [
            f"Set Timecode {TIMECODE_NUMBER} Property 'Cursor' 60"
        ]

    def test_resync_does_not_write_blind_when_the_cursor_cannot_be_read(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)
        _quiet_reads(monkeypatch, session, None)

        event = session.beat_grid_console_seek(60.0, resync=True)

        assert event["ok"] is False
        assert _cursor_lines(console.executed) == []
