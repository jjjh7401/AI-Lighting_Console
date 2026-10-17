"""2차 전체 실행(1017) 리드 일괄 배차 2차 — 앱과 콘솔이 같이 재생·정지한다.

- G-19 콘솔 큐 시각은 음원 시각 + 콘솔→음원 지연(``console_audio_offset.yaml``)이다.
  근거: t520 실기 생성기 ``.moai/reports/t520/m2a_batch1.py:15``
  「타임코드 시각 = 음악 시각 + LEAD(3초)」. 앱 음원은 이미 ``Go`` 뒤 같은 지연만큼
  기다렸다 시작하므로(UI), 고칠 곳은 큐 시각 하나다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.design.beat_grid_console_audio_offset import CONSOLE_AUDIO_OFFSET_SECONDS
from server.design.beat_grid_send import song_end_seconds_from_bar_map
from server.looks.songcue import _format_seconds
from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _bar_map,
    _empty_pool_state_tree,
    _new_session,
    _timeline,
)

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
