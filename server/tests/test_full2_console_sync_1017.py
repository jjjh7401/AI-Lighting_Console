"""2차 전체 실행(1017) 리드 일괄 배차 2차 — 앱과 콘솔이 같이 재생·정지한다.

- G-19 콘솔 큐 시각은 음원 시각 + 콘솔→음원 지연(``console_audio_offset.yaml``)이다.
  근거: t520 실기 생성기 ``.moai/reports/t520/m2a_batch1.py:15``
  「타임코드 시각 = 음악 시각 + LEAD(3초)」. 앱 음원은 이미 ``Go`` 뒤 같은 지연만큼
  기다렸다 시작하므로(UI), 고칠 곳은 큐 시각 하나다.
- G-22·I-02·I-03 정지는 t506·t520 실기 해제 묶음과 같다 — ``Off Timecode N`` 다음에 그 곡
  트랙의 시퀀스마다 ``Off Sequence S``(``.moai/reports/t520/approval_m2a_play_b2.txt``).
  보낸 뒤 커서를 읽어 멈췄는지 확인하고, 못 읽거나 아직 움직이면 알린다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.design.beat_grid_console_audio_offset import CONSOLE_AUDIO_OFFSET_SECONDS
from server.design.beat_grid_send import song_end_seconds_from_bar_map
from server.looks.songcue import _format_seconds
from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    FIRST_SEQUENCE_NUMBER,
    TIMECODE_NUMBER,
    _bar_map,
    _empty_pool_state_tree,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)


class _CursorPort:
    """세션 상태 포트 대역 — 상태 나무는 콘솔 대역에 넘기고, 커서 읽기만 대본대로 답한다."""

    def __init__(self, inner, cursors: list[object]) -> None:
        self._inner = inner
        self._cursors = list(cursors)

    def query_state(self, path: str, **kwargs) -> dict:
        return self._inner.query_state(path, **kwargs)

    def query_properties(self, path: str, names, **_kwargs) -> dict:
        if not self._cursors:
            raise RuntimeError("no reply")
        value = self._cursors.pop(0)
        return {"ok": True, "reads": [{"n": "CURSOR", "ok": True, "t": "string", "v": value}]}


def _played_session(tmp_path, cursors: list[object]):
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree()
    )
    session._rig_capability_port = _CursorPort(session._rig_capability_port, cursors)
    session._beat_grid_stop_check_interval_seconds = 0.0
    return session, console, approval


# -- G-19 ---------------------------------------------------------------------


def test_cue_trigger_times_carry_the_console_to_audio_lead(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline()
    session, console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_empty_pool_state_tree()
    )

    assert session.beat_grid_apply()["ok"] is True

    # 픽스처 마디 지도의 1마디 시작은 1.000 s(음원 시각) — 콘솔 큐는 지연만큼 늦은 시각에 선다.
    expected_ms = round((1.0 + CONSOLE_AUDIO_OFFSET_SECONDS) * 1000)
    trig = [c for c in console.executed if "Property 'TrigTime'" in c]
    assert trig == [f"Set Cue 1 Sequence 1 Property 'TrigTime' {_format_seconds(expected_ms)}"]
    events = [c for c in console.executed if "'Token' 'Go+'" in c]
    assert events and all(f"'Time' {_format_seconds(expected_ms)}" in c for c in events)
    song_end = song_end_seconds_from_bar_map(_bar_map())
    duration_ms = round((song_end + CONSOLE_AUDIO_OFFSET_SECONDS) * 1000)
    assert (
        f"Set Timecode {TIMECODE_NUMBER} Property 'Duration' {_format_seconds(duration_ms)} "
        "'AutoStop' 0"
    ) in console.executed


# -- G-22 · I-02 · I-03 -------------------------------------------------------


def test_stop_switches_off_the_timecode_and_every_owned_sequence(tmp_path) -> None:
    session, console, _approval = _played_session(tmp_path, cursors=["12.40", "12.40"])

    event = session.beat_grid_console_stop()

    assert event["ok"] is True
    assert [c for c in console.executed if c.startswith("Off ")] == [
        f"Off Timecode {TIMECODE_NUMBER}",
        f"Off Sequence {FIRST_SEQUENCE_NUMBER}",
    ]
    assert event["notices"] == []


def test_stop_warns_when_the_timecode_cursor_still_moves(tmp_path) -> None:
    session, _console, _approval = _played_session(tmp_path, cursors=["2m57.30", "2m57.80"])

    event = session.beat_grid_console_stop()

    assert event["ok"] is True
    assert any(f"Timecode {TIMECODE_NUMBER}" in n and "돌고" in n for n in event["notices"])


def test_stop_warns_when_it_cannot_read_whether_the_console_stopped(tmp_path) -> None:
    session, _console, _approval = _played_session(tmp_path, cursors=[])

    event = session.beat_grid_console_stop()

    assert event["ok"] is True
    assert any("확인하지 못" in n for n in event["notices"])


def test_the_stop_card_names_what_it_switches_off(tmp_path) -> None:
    session, _console, approval = _played_session(tmp_path, cursors=["1", "1"])

    assert session.beat_grid_console_stop()["ok"] is True

    reasons = approval.requests[0].items[0].risk_reasons
    assert any("박자 격자 정지" in r and f"Timecode {TIMECODE_NUMBER}" in r for r in reasons)


def test_a_declined_stop_warns_that_the_console_may_still_run(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    session, console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree(), decisions=(False,)
    )

    event = session.beat_grid_console_stop()

    assert event["ok"] is False
    assert "돌고 있을 수 있어요" in event["reason"]
    assert [c for c in console.executed if c.startswith("Off ")] == []
