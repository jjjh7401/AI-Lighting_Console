"""문장 범위 편집이 칸 없는 마디를 건너뛰었다고 말한다.

「7~8마디 FOH 밝기를 50%로」는 FOH 의 7마디 칸만 고친다 — 8마디에는 칸이 없고,
범위 편집은 새 칸을 지어내지 않는다. 그런데 보고 문장이 7마디만 말하면 사용자는
두 마디가 다 바뀐 줄 안다. 그래서 건너뛴 마디를 보고에 적는다.
"""

from __future__ import annotations

from server.design.beat_grid import default_beat_grid
from server.design.beat_grid_edit import format_bar_runs, skipped_range_bars
from server.web.session import SongTimelineStore

from .test_session_beat_grid_edit_t551 import _new_session, _timeline


def test_skipped_range_bars_lists_bars_without_a_cue_for_the_target() -> None:
    grid = default_beat_grid("LOVE ATTACK")

    assert skipped_range_bars(grid, bar_start=7, bar_end=8, target="FOH") == [8]


def test_format_bar_runs_joins_consecutive_bars_into_one_run() -> None:
    assert format_bar_runs([8]) == "8마디"
    assert format_bar_runs([8, 9, 10, 12]) == "8~10마디, 12마디"
    assert format_bar_runs([]) == ""


def test_sentence_range_reply_names_the_skipped_bar(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline(beat_grid=default_beat_grid("LOVE ATTACK"))
    session, _console = _new_session(tmp_path, store=store)

    event = session.beat_grid_edit(
        bar=None, target=None, changes=None, sentence="7~8마디 FOH 밝기를 50%로"
    )

    assert event["type"] == "chat_response"
    assert event["status"] == "ok"
    assert "FOH 칸이 없어 건너뛴 마디: 8마디" in event["text"]
