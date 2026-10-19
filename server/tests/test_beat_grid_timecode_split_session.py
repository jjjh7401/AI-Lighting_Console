"""세션 반영·재생·정지가 타임코드 여러 개를 함께 쓴다(카드 WT-track-model PR2).

16줄(잰 트랙 수)을 넘는 격자는 감독이 정한 타임코드(여기 20)에 16줄, 다음 빈 번호(21…)에 나머지를
담는다. 소유 기록이 추가 타임코드를 기억하고, ▶·정지는 그 타임코드들을 함께 Top/Go/Off 한다.
콘솔은 가짜다(쓰기 0 — 승인 카드에 실린 명령만 본다).
"""

from __future__ import annotations

from server.design.beat_grid_emit import MEASURED_MAX_TIMECODE_TRACKS
from server.design.timecode_split import transport_commands

from .test_new_color_preset_t594 import _apply_session


def _grid(count: int) -> dict:
    return {
        "tracks": [
            {
                "group_name": f"T{i}",
                "group_no": 10 + i,
                "group_no_confirmed": True,
                "cues": [{"bar": 1, "color_preset_no": "4.41", "evidence": None}],
            }
            for i in range(1, count + 1)
        ],
        "probe_results": {},
    }


def _commands(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


def test_thirty_rows_are_split_over_two_timecodes_on_the_approval_card(tmp_path) -> None:
    names = [f"T{i}" for i in range(1, 31)]
    status, store, approval, _console = _apply_session(
        tmp_path, _grid(30), pool4=[41], members={name: [101] for name in names}
    )
    assert status["ok"] is True, status
    sent = _commands(approval)
    assert "Store Timecode 20" in sent
    assert "Store Timecode 21" in sent
    assigns = [line for line in sent if line.startswith("Assign Sequence")]
    assert len(assigns) == 30
    cap = MEASURED_MAX_TIMECODE_TRACKS
    assert sum(" At Timecode 20.1." in line for line in assigns) == cap
    assert sum(" At Timecode 21.1." in line for line in assigns) == 30 - cap
    risk = " ".join(approval.requests[0].items[0].risk_reasons)
    assert "타임코드 2개(20, 21)에 나눠 담습니다" in risk
    record = next(iter(store._beat_grid_allocations.values()))
    assert record["timecode_number"] == 20
    assert record["extra_timecodes"] == [
        {"timecode_number": 21, "timecode_name": "LDBEAT Timecode 21"}
    ]


def test_an_occupied_number_is_skipped_for_the_extra_timecode(tmp_path, monkeypatch) -> None:
    from . import test_new_preset_dialog_t589 as base

    occupied = {"children": [{"i": 21, "name": "Someone Else"}], "node": {"childCount": 1}}
    monkeypatch.setattr(base, "_TIMECODE_POOL_CHILDREN_EMPTY", occupied, raising=False)
    names = [f"T{i}" for i in range(1, 18)]
    status, _store, approval, _console = _apply_session(
        tmp_path, _grid(17), pool4=[41], members={name: [101] for name in names}
    )
    assert status["ok"] is True, status
    sent = _commands(approval)
    assert "Store Timecode 21" not in sent
    assert "Store Timecode 22" in sent


def test_sixteen_rows_stay_on_one_timecode(tmp_path) -> None:
    names = [f"T{i}" for i in range(1, 17)]
    status, store, approval, _console = _apply_session(
        tmp_path, _grid(16), pool4=[41], members={name: [101] for name in names}
    )
    assert status["ok"] is True, status
    assert "Store Timecode 21" not in _commands(approval)
    record = next(iter(store._beat_grid_allocations.values()))
    assert record.get("extra_timecodes", []) == []


def _transport_session(tmp_path, monkeypatch, *, extra_name: str, extra_target: str = "LDBEAT T2"):
    """이 곡이 TC20 + TC21 로 나눠 반영돼 있는 상태 — 소유 기록과 콘솔 타임코드 이름."""
    from server.web.session import SongTimelineStore

    from . import test_new_preset_dialog_t589 as base

    pool = {
        "children": [
            {"i": 20, "name": "LDBEAT Timecode 20"},
            {"i": 21, "name": extra_name},
        ],
        "node": {"childCount": 2, "enumeration": "ok"},
    }
    monkeypatch.setattr(base, "_TIMECODE_POOL_CHILDREN_EMPTY", pool, raising=False)
    store = SongTimelineStore()
    store.latest = base._timeline_for_apply()
    session, console, approval, _audit = base._new_session(
        tmp_path, store=store, state_tree=base._state_tree()
    )
    # WT-play-stale-owner — 콘솔: T1(300)은 TC20, T2(301)은 TC21 에 있다.
    console.state_tree["DataPool/Sequences"] = {
        "children": [
            {"i": 300, "name": "LDBEAT T1"},
            {"i": 301, "name": "LDBEAT T2"},
            {"i": 302, "name": "LDBEAT T3"},  # 이 곡의 기록에 없는 시퀀스(다른 곡의 것)
        ]
    }
    for number, sequence_name in ((20, "LDBEAT T1"), (21, extra_target)):
        console.state_tree[f"DataPool/Timecodes/{number}/1"] = {
            "children": [{"i": 1, "class": "Track"}]
        }
        console.state_tree[f"DataPool/Timecodes/{number}/1/1"] = {
            "children": [],
            "props": {"TARGET": sequence_name, "NAME": "Track 1"},
        }
    store.set_beat_grid_allocation(
        session._beat_grid_song_key(store.latest),
        {
            "timecode_number": 20,
            "timecode_name": "LDBEAT Timecode 20",
            "extra_timecodes": [{"timecode_number": 21, "timecode_name": "LDBEAT Timecode 21"}],
            "tracks": {
                "T1": {"sequence_number": 300, "sequence_name": "LDBEAT T1", "cues": {}},
                "T2": {"sequence_number": 301, "sequence_name": "LDBEAT T2", "cues": {}},
            },
        },
    )
    sent: list[tuple[str, ...]] = []
    session._preview_approval.approve()
    monkeypatch.setattr(
        session,
        "_beat_grid_send_transport_preapproved",
        lambda commands, **_kw: sent.append(tuple(commands)) or True,
    )
    return session, sent


def test_play_and_stop_send_every_owned_timecode(tmp_path, monkeypatch) -> None:
    session, sent = _transport_session(tmp_path, monkeypatch, extra_name="LDBEAT Timecode 21")
    session._beat_grid_console_transport("console_play", ("Top", "Go"))
    # WT-back-side-dark — 되감기 전에 그 곡 트랙 시퀀스를 끈다.
    assert sent[-1][-4:] == (
        "Top Timecode 20",
        "Top Timecode 21",
        "Go Timecode 20",
        "Go Timecode 21",
    )
    assert all(line.startswith("Off Sequence ") for line in sent[-1][:-4])
    assert "Off Sequence 300" in sent[-1]
    session._beat_grid_console_transport("console_stop", ("Off",), stop=True)
    assert sent[-1][:2] == ("Off Timecode 20", "Off Timecode 21")
    assert "Off Sequence 300" in sent[-1]


def test_an_extra_timecode_pointing_at_another_songs_sequence_is_not_played(
    tmp_path, monkeypatch
) -> None:
    # WT-play-stale-owner — 이름이 맞아도 TC21 이 기록에 없는 시퀀스를 가리키면 건드리지 않는다.
    session, sent = _transport_session(
        tmp_path, monkeypatch, extra_name="LDBEAT Timecode 21", extra_target="LDBEAT T3"
    )
    session._beat_grid_console_transport("console_play", ("Top", "Go"))
    assert sent[-1][-2:] == ("Top Timecode 20", "Go Timecode 20")
    assert not [line for line in sent[-1] if "Timecode 21" in line]


def test_an_extra_timecode_renamed_on_the_console_is_not_played(tmp_path, monkeypatch) -> None:
    # 기록에 있어도 콘솔 이름이 다르면(남이 덮어씀) 그 번호는 건드리지 않는다.
    session, sent = _transport_session(tmp_path, monkeypatch, extra_name="Someone Else")
    session._beat_grid_console_transport("console_play", ("Top", "Go"))
    assert sent[-1][-2:] == ("Top Timecode 20", "Go Timecode 20")
    assert not [line for line in sent[-1] if "Timecode 21" in line]


def test_transport_commands_run_every_timecode_together() -> None:
    assert transport_commands((20, 21), ("Top", "Go")) == (
        "Top Timecode 20",
        "Top Timecode 21",
        "Go Timecode 20",
        "Go Timecode 21",
    )
    assert transport_commands((20,), ("Off",)) == ("Off Timecode 20",)
