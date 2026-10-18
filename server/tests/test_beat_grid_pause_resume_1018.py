"""SPEC-LDBEAT-001 PR 1 — 일시정지·이어 가기 (❚❚ = Off Timecode만, ▶ = Go만).

❚❚ 는 ``Off Timecode N`` 만 보낸다 — 시퀀스는 끄지 않는다. ▶ 는 처음으로 되감지 않고
``Go Timecode N`` 만 보내 타임코드 커서부터 잇는다. 정지 묶음(■ 끄기)과 처음부터
재생(``Top`` + ``Go``)은 그대로다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

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


def _sequence_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if "Sequence" in c]


def _timecode_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if "Timecode" in c]


class TestPauseAndResume:
    def test_pause_sends_only_off_timecode_and_keeps_the_sequences(self, tmp_path) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)

        event = session.beat_grid_console_pause()

        assert event["ok"] is True
        assert event["last_action"] == "console_stop"
        assert _timecode_lines(console.executed) == [f"Off Timecode {TIMECODE_NUMBER}"]
        assert _sequence_lines(console.executed) == []

    def test_resume_sends_only_go_timecode_and_never_tops(self, tmp_path) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)

        event = session.beat_grid_console_resume()

        assert event["ok"] is True
        assert event["last_action"] == "console_play"
        assert _timecode_lines(console.executed) == [f"Go Timecode {TIMECODE_NUMBER}"]
        assert _sequence_lines(console.executed) == []

    def test_full_stop_still_turns_the_sequences_off(self, tmp_path) -> None:
        session, console, _approval, _audit = _owned_session(tmp_path)

        session.beat_grid_console_stop()

        assert _timecode_lines(console.executed) == [f"Off Timecode {TIMECODE_NUMBER}"]
        assert any(c.startswith("Off Sequence ") for c in _sequence_lines(console.executed))

    def test_pause_without_a_record_refuses_and_sends_nothing(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_empty_pool_state_tree()
        )

        event = session.beat_grid_console_pause()

        assert event["ok"] is False
        assert console.executed == []
        assert approval.requests == []
