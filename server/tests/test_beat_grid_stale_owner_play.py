"""「콘솔 같이」 재생·정지 전 소유 기록 확인 — 카드 WT-play-stale-owner.

감독 실측(2026-10-18): 라이브러리에서 LOVE ATTACK 을 불러와 「콘솔 같이」를 켜고 ▶ 를 누르면
위험 명령 승인 카드만 반복해서 떴다(명령 11개: 쇼 백업 + Off Sequence 54~61 + Top/Go TC5). 옛
반영 기록은 시퀀스 54~61 을 가리키는데, 콘솔에는 마지막 반영(FRESH TEST 1018-3)이 만든 54~59 만
있고 60·61 은 없었다. 타임코드 이름(「LDBEAT Timecode 5」)은 곡마다 같아서, 이름만 보는 판정
(t578)은 남의 TC5 를 이 곡의 것으로 받았다 — t578 보고서가 「점유자 이름은 맞지만 다른 쇼로 바뀐
경우」를 안 잰 것으로 적어 둔 바로 그 틈이다.

안내는 갈래별이다(``_beat_grid_record_is_stale``):
- 기록의 시퀀스가 콘솔에서 사라짐 → 「⇪」이 빈 번호에 새로 만든다(리드 지시) → 「⇪」 안내.
- 같은 번호를 다른 이름의 시퀀스가 쓰고 있음 → 「⇪」이 그 트랙을 빈 번호에 새로 만든다(리드 지시).
- 타임코드가 이 곡 기록 밖의 이 앱 시퀀스를 가리킴 → 「⇪」이 타임코드를 다시 짠다 → 「⇪」 안내.
- 타임코드가 이 앱이 만들지 않은 시퀀스를 가리킴 → 리드에게 넘긴다(「⇪」 확인 안 됨).
- 타임코드 트랙을 콘솔에서 못 읽음 → 맞다고 하지 않는다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    _EXISTING_PRESET_POOLS,
    OWNED_TIMECODE_NAME,
    TIMECODE_NUMBER,
    _new_session,
    _seed_record,
    _timeline,
)

#: 사라진 시퀀스 — 「⇪」이 빈 번호에 새로 만든다.
MISSING_SEQUENCE_GUIDANCE = (
    "이 곡은 지금 콘솔에 반영돼 있지 않아요 — ⇪ 콘솔에 반영을 먼저 누르세요."
)
#: 타임코드가 이 앱이 만들지 않은 시퀀스를 가리킨다 — 리드에게 넘긴다.
FOREIGN_GUIDANCE = "이 앱이 만들지 않은 시퀀스를 가리켜"
#: 타임코드 트랙을 콘솔에서 확인하지 못했다.
UNCONFIRMED_GUIDANCE = "타임코드 트랙을 확인하지 못해"

#: 옛 반영 기록 — 시퀀스 1·2 를 가리킨다.
RECORD_TRACKS = {
    "BACK": {"sequence_number": 1, "sequence_name": "LDBEAT BACK", "cues": {"1": 1}},
    "SIDE-ALL": {"sequence_number": 2, "sequence_name": "LDBEAT SIDE-ALL", "cues": {"1": 1}},
}


def _console(*, sequences: dict[int, str], timecode_targets: list[str]) -> dict:
    """콘솔 나무 — 타임코드 TC 의 트랙이 ``timecode_targets`` 시퀀스를 가리킨다(TARGET)."""
    tree: dict = {
        **_EXISTING_PRESET_POOLS,
        "DataPool/Sequences": {
            "children": [{"i": number, "name": name} for number, name in sequences.items()]
        },
        "DataPool/Timecodes": {
            "children": [{"i": TIMECODE_NUMBER, "name": OWNED_TIMECODE_NAME}],
            "node": {"childCount": 1},
        },
        f"DataPool/Timecodes/{TIMECODE_NUMBER}/1": {
            "children": [{"i": i, "class": "Track"} for i in range(1, len(timecode_targets) + 1)]
        },
    }
    for index, target in enumerate(timecode_targets, start=1):
        tree[f"DataPool/Timecodes/{TIMECODE_NUMBER}/1/{index}"] = {
            "children": [],
            "props": {"TARGET": target, "NAME": f"Track {index}"},
        }
    return tree


def _timecode_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if "Timecode" in c]


def _session_with(tmp_path, *, sequences, timecode_targets):
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store, tracks=RECORD_TRACKS)
    return _new_session(
        tmp_path,
        store=store,
        state_tree=_console(sequences=sequences, timecode_targets=timecode_targets),
    )


#: 시퀀스 2 가 사라졌고, 타임코드는 남은 시퀀스 1 만 가리킨다.
_RECORD_SEQUENCE_GONE = {"sequences": {1: "LDBEAT BACK"}, "timecode_targets": ["LDBEAT BACK"]}
#: 시퀀스 2 번호를 다른 이름(「Someone Else」)의 시퀀스가 차지했다 — 남의 것.
_RECORD_NUMBER_TAKEN_BY_OTHER = {
    "sequences": {1: "LDBEAT BACK", 2: "Someone Else"},
    "timecode_targets": ["LDBEAT BACK"],
}
#: 기록의 시퀀스 1·2 는 있지만, 타임코드가 이 곡 기록에 없는 LDBEAT 시퀀스 3 도 가리킨다.
_TIMECODE_POINTS_AT_OTHER_APP_SEQUENCE = {
    "sequences": {1: "LDBEAT BACK", 2: "LDBEAT SIDE-ALL", 3: "LDBEAT MOVER-U"},
    "timecode_targets": ["LDBEAT BACK", "LDBEAT SIDE-ALL", "LDBEAT MOVER-U"],
}
#: 타임코드가 이 앱이 만들지 않은 시퀀스(「Someone Else」)를 가리킨다.
_TIMECODE_POINTS_AT_FOREIGN_SEQUENCE = {
    "sequences": {1: "LDBEAT BACK", 2: "LDBEAT SIDE-ALL", 4: "Someone Else"},
    "timecode_targets": ["LDBEAT BACK", "LDBEAT SIDE-ALL", "Someone Else"],
}
#: 타임코드 트랙이 하나도 없다(읽을 것이 없다).
_TIMECODE_HAS_NO_TRACKS = {
    "sequences": {1: "LDBEAT BACK", 2: "LDBEAT SIDE-ALL"},
    "timecode_targets": [],
}
#: 기록과 콘솔이 맞는다 — 대조군.
_RECORD_MATCHES = {
    "sequences": {1: "LDBEAT BACK", 2: "LDBEAT SIDE-ALL"},
    "timecode_targets": ["LDBEAT BACK", "LDBEAT SIDE-ALL"],
}


class TestStaleOwnerPlay:
    def test_a_record_sequence_gone_from_the_console_asks_no_card_and_sends_nothing(
        self, tmp_path
    ) -> None:
        session, console, approval, _audit = _session_with(tmp_path, **_RECORD_SEQUENCE_GONE)

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert MISSING_SEQUENCE_GUIDANCE in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_number_taken_by_another_name_asks_to_press_apply_which_recreates_it(
        self, tmp_path
    ) -> None:
        # WT-play-stale-owner(리드 지시) — 같은 번호를 다른 이름이 쓰면 「⇪」이 새로 만든다.
        session, console, approval, _audit = _session_with(
            tmp_path, **_RECORD_NUMBER_TAKEN_BY_OTHER
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert MISSING_SEQUENCE_GUIDANCE in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_timecode_pointing_at_another_app_sequence_asks_to_press_apply(
        self, tmp_path
    ) -> None:
        # 브라우저 확인(outside 상태): 「⇪」 승인 카드가 타임코드를 기록대로 다시 짠다.
        session, console, approval, _audit = _session_with(
            tmp_path, **_TIMECODE_POINTS_AT_OTHER_APP_SEQUENCE
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert MISSING_SEQUENCE_GUIDANCE in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_timecode_pointing_at_a_foreign_sequence_goes_to_the_lead(self, tmp_path) -> None:
        session, console, approval, _audit = _session_with(
            tmp_path, **_TIMECODE_POINTS_AT_FOREIGN_SEQUENCE
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert FOREIGN_GUIDANCE in event["reason"]
        assert "⇪" not in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_timecode_with_no_readable_tracks_is_not_called_in_sync(self, tmp_path) -> None:
        session, console, approval, _audit = _session_with(tmp_path, **_TIMECODE_HAS_NO_TRACKS)

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert UNCONFIRMED_GUIDANCE in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_stop_with_a_missing_record_sequence_does_not_switch_off_the_other_songs_timecode(
        self, tmp_path
    ) -> None:
        session, console, approval, _audit = _session_with(tmp_path, **_RECORD_SEQUENCE_GONE)

        event = session.beat_grid_console_stop()

        assert event["ok"] is False
        assert MISSING_SEQUENCE_GUIDANCE in event["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_record_that_matches_the_console_still_plays_top_then_go(self, tmp_path) -> None:
        # 대조군: 판정이 맞는 기록을 막지 않는다.
        session, console, _approval, _audit = _session_with(tmp_path, **_RECORD_MATCHES)

        event = session.beat_grid_console_play()

        assert event["ok"] is True
        assert _timecode_lines(console.executed) == [
            f"Top Timecode {TIMECODE_NUMBER}",
            f"Go Timecode {TIMECODE_NUMBER}",
        ]
