"""3차 전체 실행(1017) I-02·I-03 — 「■ 끄기」도 곡 끝·❚❚ 와 같은 정지 묶음을 보낸다.

- 첫 세션: ■ 가 ``Off Sequence`` 만 보내고 ``Off Timecode 5`` 를 빠뜨려 TC5 가 계속 돌았다.
- 서버 재시작 세션: ■ 가 메모리의 마지막 반영만 보고 「반영된 적이 없어」로 아무것도 안 보냈다
  (CURSOR 51.57→55.70 계속). 둘 다 경고 없음.

고친 뒤: 대상 타임코드는 이 곡의 소유 기록(디스크)·타임코드 번호에서 찾고, ``Off Timecode N``
+ 소유 시퀀스 ``Off Sequence`` 를 보낸 뒤 커서로 멈췄는지 확인한다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    FIRST_SEQUENCE_NUMBER,
    TIMECODE_NUMBER,
    _empty_pool_state_tree,
    _new_session,
    _timeline,
)
from .test_full2_console_sync_1017 import _played_session


def test_preview_off_after_restart_switches_off_the_owned_timecode(tmp_path) -> None:
    # 재시작 세션: 메모리의 마지막 반영(beat_grid_applied)은 없고 디스크 소유 기록만 있다.
    session, console, _approval = _played_session(tmp_path, cursors=["51.57", "51.57"])
    assert session._timeline_store.beat_grid_applied is None

    event = session.beat_grid_preview_off()

    assert event["ok"] is True
    assert event["last_action"] == "preview_off"
    assert [c for c in console.executed if c.startswith("Off ")] == [
        f"Off Timecode {TIMECODE_NUMBER}",
        f"Off Sequence {FIRST_SEQUENCE_NUMBER}",
    ]
    assert event["notices"] == []


def test_preview_off_warns_when_the_timecode_keeps_running(tmp_path) -> None:
    session, _console, _approval = _played_session(tmp_path, cursors=["51.57", "53.63"])

    event = session.beat_grid_preview_off()

    assert event["ok"] is True
    assert any(f"Timecode {TIMECODE_NUMBER}" in n and "돌고" in n for n in event["notices"])


def test_preview_off_without_any_owned_timecode_says_to_stop_on_the_console(tmp_path) -> None:
    store = SongTimelineStore()
    timeline = _timeline()
    timeline.pop("timecode_number", None)
    store.latest = timeline
    session, console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_empty_pool_state_tree()
    )

    event = session.beat_grid_preview_off()

    assert event["ok"] is False
    assert "콘솔에서 직접" in event["reason"]
    assert console.executed == []
