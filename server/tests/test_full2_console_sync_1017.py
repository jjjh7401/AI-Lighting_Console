"""2차 전체 실행(1017) 리드 일괄 배차 2차 — 앱과 콘솔이 같이 재생·정지한다.

- G-19 콘솔 큐 시각은 음원 시각 + 콘솔→음원 지연(``console_audio_offset.yaml``)이다.
  근거: t520 실기 생성기 ``.moai/reports/t520/m2a_batch1.py:15``
  「타임코드 시각 = 음악 시각 + LEAD(3초)」. 앱 음원은 이미 ``Go`` 뒤 같은 지연만큼
  기다렸다 시작하므로(UI), 고칠 곳은 큐 시각 하나다.
- G-22·I-02·I-03 정지는 t506·t520 실기 해제 묶음과 같다 — ``Off Timecode N`` 다음에 그 곡
  트랙의 시퀀스마다 ``Off Sequence S``(``.moai/reports/t520/approval_m2a_play_b2.txt``).
  보낸 뒤 커서를 읽어 멈췄는지 확인하고, 못 읽거나 아직 움직이면 알린다.
- B-07 콘솔 이름이 ``LDBEAT Timecode 3`` 이고 트랙도 ``LDBEAT`` 시퀀스를 가리켜도, 이 앱의
  반영 기록이 그 번호를 적고 있지 않으면 남의 타임코드다(감독 손설계 TC3·4).
- J-09 「세션 첫 승인」은 연결이 아니라 서버 단위다 — 새로고침·재접속 뒤 재생도 다시 묻지 않는다.
- 「⇪ 반영N」 배지: 색 번호가 있는 칸에 화면용으로만 붙는 ``color_rgb`` 는 미반영 비교에서 뺀다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.design.beat_grid_console_audio_offset import CONSOLE_AUDIO_OFFSET_SECONDS
from server.design.beat_grid_send import (
    beat_grid_cell_snapshot,
    song_end_seconds_from_bar_map,
    unsent_beat_grid_cells,
)
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


# -- B-07 ---------------------------------------------------------------------


def test_timecode_input_refuses_an_app_named_timecode_no_record_owns(tmp_path) -> None:
    # 실제 콘솔의 TC3: 이름 「LDBEAT Timecode 3」, 트랙이 가리키는 시퀀스도 「LDBEAT …」 — 이름만
    # 보면 앱 것처럼 보이지만 이 앱의 반영 기록(TC 20)은 3번을 적고 있지 않다.
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    tree = _owned_state_tree()
    tree["DataPool/Timecodes"] = {
        "children": [
            {"i": TIMECODE_NUMBER, "name": f"LDBEAT Timecode {TIMECODE_NUMBER}"},
            {"i": 3, "name": "LDBEAT Timecode 3"},
        ],
        "node": {"childCount": 2},
    }
    tree["DataPool/Sequences"] = {"children": [{"i": 70, "name": "LDBEAT FOH"}]}
    session, console, _approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    session._beat_grid_timecode_track_targets = lambda wanted: [
        {"target": "Sequence 70", "track_name": "LDBEAT FOH"}
    ]

    event = session.beat_grid_timecode_set(3)

    assert event["ok"] is False
    assert "이 앱이 만든 타임코드가 아니라서 쓸 수 없어요" in event["reason"]
    assert store.latest["timecode_number"] == TIMECODE_NUMBER
    assert console.executed == []


def test_timecode_input_accepts_a_timecode_another_song_record_owns(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline()
    store.set_beat_grid_allocation(
        ("OTHER SONG", None),
        {"timecode_number": 7, "timecode_name": "LDBEAT Timecode 7", "tracks": {}},
    )
    tree = _empty_pool_state_tree()
    tree["DataPool/Timecodes"] = {
        "children": [{"i": 7, "name": "LDBEAT Timecode 7#2"}],
        "node": {"childCount": 1},
    }
    session, _console, _approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)

    event = session.beat_grid_timecode_set(7)

    assert event["ok"] is True
    assert store.latest["timecode_number"] == 7


# -- J-09 ---------------------------------------------------------------------


def test_the_first_play_approval_survives_a_reconnect(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    first, _console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree()
    )
    assert first.beat_grid_console_play()["ok"] is True
    assert len(approval.requests) == 1

    # 새로고침 = 같은 서버(같은 저장소)의 새 연결(새 ChatSession).
    second, console, approval_2, _audit_2 = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree()
    )
    event = second.beat_grid_console_play()

    assert event["ok"] is True
    assert approval_2.requests == []
    assert [c for c in console.executed if "Timecode" in c] == [
        f"Top Timecode {TIMECODE_NUMBER}",
        f"Go Timecode {TIMECODE_NUMBER}",
    ]


def test_a_declined_first_play_keeps_asking_on_the_next_connection(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    first, _console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree(), decisions=(False,)
    )
    assert first.beat_grid_console_play()["ok"] is False

    second, _console_2, approval_2, _audit_2 = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree()
    )
    assert second.beat_grid_console_play()["ok"] is True
    assert len(approval_2.requests) == 1


# -- 「⇪ 반영N」 배지 ------------------------------------------------------------


def _grid(cue: dict) -> dict:
    return {"tracks": [{"group_name": "FOH", "cues": [cue]}]}


def test_a_colour_resolved_only_for_display_is_not_an_unsent_change() -> None:
    # 2차 전체 실행 — 반영 두 번 뒤에도 「⇪ 반영64」. 미반영 64칸은 전부 색 번호가 있고 서빙이
    # 그 번호에서 푼 ``color_rgb`` 를 단 칸이었다(스냅샷은 저장 모양이라 그 키가 없다).
    stored = _grid({"bar": 0, "label": "FOH 켬", "color_preset_no": "4.124"})
    served = _grid(
        {"bar": 0, "label": "FOH 켬", "color_preset_no": "4.124", "color_rgb": [100.0, 75.0, 40.0]}
    )

    assert unsent_beat_grid_cells(served, beat_grid_cell_snapshot(stored)) == []


def test_a_changed_colour_number_is_still_unsent() -> None:
    stored = _grid({"bar": 0, "label": "FOH 켬", "color_preset_no": "4.124"})
    changed = _grid(
        {"bar": 0, "label": "FOH 켬", "color_preset_no": "4.125", "color_rgb": [1, 2, 3]}
    )

    assert unsent_beat_grid_cells(changed, beat_grid_cell_snapshot(stored)) == [
        {"group_name": "FOH", "bar": 0}
    ]


def test_a_raw_colour_without_a_number_is_still_compared() -> None:
    stored = _grid({"bar": 0, "color_preset_no": None, "color_rgb": [10, 20, 30]})
    changed = _grid({"bar": 0, "color_preset_no": None, "color_rgb": [10, 20, 99]})

    assert unsent_beat_grid_cells(changed, beat_grid_cell_snapshot(stored)) == [
        {"group_name": "FOH", "bar": 0}
    ]
