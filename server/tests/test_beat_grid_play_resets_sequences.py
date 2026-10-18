"""SPEC-LDRHYTHM-001 WT-back-side-dark ① — ▶ 는 곡의 트랙 시퀀스를 끈 뒤 타임코드를 되감고 재생한다.

새 곡 2차 점검(2026-10-18): 반영 뒤 ▶ 를 다시 누르자 FOH·BACK·SIDE 가 곡 내내 꺼져 있었다.
실기(응답기 판독 + 시트, 측정 창 02:33Z, 감사로그에 다른 재생 0건):
- 재생이 끝난 뒤 시퀀스들은 마지막 큐(DIM-0, 1.924)에 머문다(``Off Timecode 5`` 뒤에도).
- ``Goto Cue 1 Sequence 71`` 은 BACK 을 1.923·SKY 로 켠다 — 큐 내용은 정상이다.
- 타임코드 트랙 이벤트는 ``Go+`` 이고, 시퀀스는 ``WrapAround`` 꺼짐(#816). 마지막 큐에 선
  시퀀스에 ``Go+`` 는 큐 1 로 돌아가지 않는다. 그래서 두 번째 ▶ 부터는 곡 내내 마지막 큐다.
  예전 시퀀스(WRAPAROUND true)는 ``Go+`` 가 큐 1 로 감겼다.

고침: ▶ 묶음 맨 앞에 그 곡 트랙 시퀀스의 ``Off Sequence`` 를 넣는다(정지 묶음과 같은 번호).
꺼진 시퀀스에 ``Go+`` 는 큐 1 부터다(#816 실측도 ``Off Sequence`` 뒤 ``Top/Go`` 였다).
콘솔 접촉 0건.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)


def _played(tmp_path) -> tuple[dict, list[str], tuple[int, ...]]:
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    session, console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree()
    )
    owned = session._beat_grid_owned_sequence_numbers()
    event = session.beat_grid_console_play()
    return event, list(console.executed), owned


def test_play_turns_the_song_sequences_off_before_top_and_go(tmp_path) -> None:
    event, executed, owned = _played(tmp_path)

    assert event["ok"] is True
    assert owned, "시험 기록에 소유 시퀀스가 있어야 한다"
    top = executed.index(f"Top Timecode {TIMECODE_NUMBER}")
    offs = [executed.index(f"Off Sequence {number}") for number in owned]
    assert all(index < top for index in offs), executed
    assert executed[top + 1] == f"Go Timecode {TIMECODE_NUMBER}"


def test_play_sends_no_off_timecode(tmp_path) -> None:
    _event, executed, _owned = _played(tmp_path)

    assert not [line for line in executed if line.startswith("Off Timecode")]
