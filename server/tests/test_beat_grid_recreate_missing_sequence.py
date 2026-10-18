"""옛 반영 기록의 시퀀스가 콘솔에서 빠졌거나 다른 것이 쓰고 있으면 「⇪ 반영」은 새로 만든다.

WT-play-stale-owner — 리드 지시(2026-10-18): 기록된 앱 소유 시퀀스가 ① 콘솔에 없거나
② 다른 곡이 같은 번호를 다른 이름으로 쓰고 있으면, 그 번호는 건드리지 않고 비어 있는
새 번호에 만들어 소유 기록을 바꿔 쓴다. 덮어쓰기는 이름이 기록과 같을 때만이다.

실측: 실제 LOVE ATTACK 기록(54~61)은 60·61 이 콘솔에 없고, 55 는 FRESH TEST 1018-3 이
「LDBEAT BACK#7」로 다시 썼다. 그래서 「⇪」이 「재적용을 거절합니다」로 막혔다.

콘솔 접촉 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

import re

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    _cue,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _song_key,
    _timeline,
)

#: 기록: BACK 은 콘솔의 1번(살아 있다), SIDE-ALL 은 60번(콘솔에서 사라졌다).
RECORDED_TRACKS = {
    "BACK": {"sequence_number": 1, "sequence_name": "LDBEAT BACK", "cues": {"1": 1}},
    "SIDE-ALL": {"sequence_number": 60, "sequence_name": "LDBEAT SIDE-ALL", "cues": {"1": 1}},
}

#: 실제 LOVE ATTACK 기록 꼴 — 54~61. 60·61 은 콘솔에 없고, 55 는 다른 곡이 다시 썼다.
LOVE_RECORD = {
    "BACK": {"sequence_number": 54, "sequence_name": "LDBEAT BACK", "cues": {"1": 1}},
    "WASH-ALL": {"sequence_number": 55, "sequence_name": "LDBEAT WASH-ALL", "cues": {"1": 1}},
    "SIDE-L": {"sequence_number": 56, "sequence_name": "LDBEAT SIDE-L", "cues": {"1": 1}},
    "SIDE-R": {"sequence_number": 57, "sequence_name": "LDBEAT SIDE-R", "cues": {"1": 1}},
    "MOVER-U": {"sequence_number": 58, "sequence_name": "LDBEAT MOVER-U", "cues": {"1": 1}},
    "MOVER-D": {"sequence_number": 59, "sequence_name": "LDBEAT MOVER-D", "cues": {"1": 1}},
    "FOH": {"sequence_number": 60, "sequence_name": "LDBEAT FOH", "cues": {"1": 1}},
    "KEY": {"sequence_number": 61, "sequence_name": "LDBEAT KEY", "cues": {"1": 1}},
}
#: 콘솔 시퀀스 풀 — 54~59 만 있고, 55 는 다른 곡의 「LDBEAT BACK#7」이다.
LOVE_CONSOLE_SEQUENCES = {
    54: "LDBEAT BACK",
    55: "LDBEAT BACK#7",
    56: "LDBEAT SIDE-L",
    57: "LDBEAT SIDE-R",
    58: "LDBEAT MOVER-U",
    59: "LDBEAT MOVER-D",
}
#: 줄 → (그룹 번호, 프리셋). 프리셋은 시험 콘솔 풀(1~4번 풀)에 있는 번호다.
LOVE_GRID = {
    "BACK": (7, "1.1"),
    "WASH-ALL": (10, "1.2"),
    "SIDE-L": (5, "2.1"),
    "SIDE-R": (6, "2.2"),
    "MOVER-U": (11, "3.1"),
    "MOVER-D": (12, "3.2"),
    "FOH": (3, "4.1"),
    "KEY": (2, "4.2"),
}
#: 이번 격자 — WASH-ALL·SIDE-ALL 은 격자에서 빠졌다(WT-owned-record-grid).
NOW_GRID = {name: LOVE_GRID[name] for name in ("BACK", "SIDE-L", "MOVER-U", "MOVER-D")}
#: 옛 기록 — 격자에 없는 WASH-ALL(55)·SIDE-ALL(57) 항목이 남아 있다.
STALE_RECORD = {
    "BACK": {"sequence_number": 54, "sequence_name": "LDBEAT BACK", "cues": {"1": 1}},
    "WASH-ALL": {"sequence_number": 55, "sequence_name": "LDBEAT WASH-ALL", "cues": {"1": 1}},
    "SIDE-L": {"sequence_number": 56, "sequence_name": "LDBEAT SIDE-L", "cues": {"1": 1}},
    "SIDE-ALL": {"sequence_number": 57, "sequence_name": "LDBEAT SIDE-ALL", "cues": {"1": 1}},
    "MOVER-U": {"sequence_number": 58, "sequence_name": "LDBEAT MOVER-U", "cues": {"1": 1}},
    "MOVER-D": {"sequence_number": 59, "sequence_name": "LDBEAT MOVER-D", "cues": {"1": 1}},
}
#: 지금 콘솔 — 55 는 다른 곡의 「LDBEAT BACK#7」, 57 은 「LDBEAT SIDE-R」이다. 60·61 없음.
NOW_CONSOLE_SEQUENCES = {
    54: "LDBEAT BACK",
    55: "LDBEAT BACK#7",
    56: "LDBEAT SIDE-L",
    57: "LDBEAT SIDE-R",
    58: "LDBEAT MOVER-U",
    59: "LDBEAT MOVER-D",
}


def _two_track_timeline():
    return _timeline(
        beat_grid={
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [_cue(1, "1.1")],
                },
                {
                    "group_name": "SIDE-ALL",
                    "group_no": 8,
                    "group_no_confirmed": True,
                    "cues": [_cue(1, "2.2")],
                },
            ],
            "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        }
    )


def _love_timeline(grid: dict = LOVE_GRID):
    tracks = [
        {
            "group_name": name,
            "group_no": number,
            "group_no_confirmed": True,
            "cues": [_cue(1, preset)],
        }
        for name, (number, preset) in grid.items()
    ]
    return _timeline(
        beat_grid={
            "tracks": tracks,
            "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        }
    )


def _love_console_tree(sequences: dict = LOVE_CONSOLE_SEQUENCES) -> dict:
    tree = _owned_state_tree()
    tree["DataPool/Sequences"] = {
        "children": [{"i": n, "name": name} for n, name in sequences.items()]
    }
    return tree


class TestRecreateMissingSequence:
    def test_a_recorded_sequence_gone_from_the_console_is_recreated_not_refused(
        self, tmp_path
    ) -> None:
        store = SongTimelineStore()
        store.latest = _two_track_timeline()
        _seed_record(store, tracks=RECORDED_TRACKS)
        session, console, _approval, _audit = _new_session(
            tmp_path,
            store=store,
            state_tree=_owned_state_tree(),  # 콘솔에는 1번(BACK)만 있다
            decisions=(True,) * 10,
        )

        event = session.beat_grid_apply()

        assert event["ok"] is True, event
        # 빈 번호(2번)에 새로 만든다. 사라진 60번은 쓰지 않는다.
        assert any("Store Sequence 2" in c for c in console.executed)
        assert not any("Store Sequence 60" in c for c in console.executed)
        # 살아 있는 BACK 은 그대로 재사용한다(새로 만들지 않는다).
        assert "Store Sequence 1" not in console.executed
        # 소유 기록을 새 번호로 고쳐 쓴다.
        record = store.beat_grid_allocation(_song_key())
        assert record["tracks"]["SIDE-ALL"]["sequence_number"] == 2
        assert record["tracks"]["BACK"]["sequence_number"] == 1

    def test_the_real_love_attack_record_gets_fresh_numbers_and_leaves_the_other_songs_55(
        self, tmp_path
    ) -> None:
        store = SongTimelineStore()
        store.latest = _love_timeline()
        _seed_record(store, tracks=LOVE_RECORD)
        session, console, _approval, _audit = _new_session(
            tmp_path,
            store=store,
            state_tree=_love_console_tree(),
            decisions=(True,) * 10,
        )

        event = session.beat_grid_apply()

        assert event["ok"] is True, event
        # 55번은 다른 곡의 시퀀스다 — 덮어쓰지도 지우지도 않는다.
        assert not any(re.search(r"Sequence 55\b", c) for c in console.executed)
        record = store.beat_grid_allocation(_song_key())
        # 이름이 같은 트랙은 그 번호 그대로 다시 쓴다.
        assert record["tracks"]["BACK"]["sequence_number"] == 54
        assert record["tracks"]["SIDE-L"]["sequence_number"] == 56
        # 이름이 다르거나 사라진 트랙(WASH-ALL·FOH·KEY)은 빈 번호에 새로 만들고 기록을 고쳐 쓴다.
        fresh = {record["tracks"][name]["sequence_number"] for name in ("WASH-ALL", "FOH", "KEY")}
        assert len(fresh) == 3
        # 새 번호는 콘솔에서 비어 있는 번호다 — 54~59(다른 곡과 이 곡의 살아 있는 것)를 쓰지 않는다.
        assert not (fresh & set(LOVE_CONSOLE_SEQUENCES))
        for number in fresh:
            assert any(c.startswith(f"Store Sequence {number} ") for c in console.executed), number

    def test_a_successful_apply_keeps_only_this_grids_tracks_in_the_record(self, tmp_path) -> None:
        # WT-owned-record-grid(리드 지시) — 「⇪」이 성공하면 소유 기록은
        # 이번 격자의 트랙만 담는다. 격자에서 빠진 옛 트랙을 남기면 그 번호를
        # 다른 곡이 쓰는 동안 「▶」가 이 곡을 콘솔에 없다고 막는다.
        # 콘솔 시퀀스(55·57)는 건드리지 않는다.
        store = SongTimelineStore()
        store.latest = _love_timeline(NOW_GRID)
        _seed_record(store, tracks=STALE_RECORD)
        session, console, _approval, _audit = _new_session(
            tmp_path,
            store=store,
            state_tree=_love_console_tree(NOW_CONSOLE_SEQUENCES),
            decisions=(True,) * 10,
        )

        event = session.beat_grid_apply()

        assert event["ok"] is True, event
        assert not any(re.search(r"Sequence (55|57)\b", c) for c in console.executed)
        record = store.beat_grid_allocation(_song_key())
        assert set(record["tracks"]) == set(NOW_GRID)
        assert record["tracks"]["SIDE-L"]["sequence_number"] == 56
