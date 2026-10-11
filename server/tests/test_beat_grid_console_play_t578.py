"""SPEC-LDBEAT-001 REQ-LDBEAT-024(a) — 플레이 묶음 「콘솔 같이」 (카드 t578).

「콘솔 같이」를 켜고 ▶ 를 누르면 게이트를 거쳐 ``Top Timecode N`` → ``Go Timecode N``
을, ❚❚ 를 누르면 ``Off Timecode N`` 을 보낸다. 세 문면은 저장소 실측 선례다
(``.moai/reports/t520/verdict.md`` — Top 은 커서를 0.00 으로 되감고, Off 는 되감지
않는다). 송신은 t563 미리보기 길(``_beat_grid_dispatch_preview`` — 세션 시작 1회
승인)을 그대로 쓴다. 새 생쓰기 경로는 없다.

타임코드 번호는 t572 소유 기록(``SongTimelineStore.beat_grid_allocation``)에서만
온다. 기록이 없거나 콘솔의 그 타임코드 이름이 기록과 다르면 보내지 않고 이유를 돌려준다.

콘솔 접촉: 0건 — ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    OWNED_TIMECODE_NAME,
    TIMECODE_NUMBER,
    _empty_pool_state_tree,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)


def _timecode_lines(executed: list[str]) -> list[str]:
    return [c for c in executed if "Timecode" in c]


class TestConsolePlay:
    def test_no_apply_record_refuses_and_sends_nothing(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_empty_pool_state_tree()
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert event["last_action"] == "console_play"
        assert "반영" in event["reason"]
        assert console.executed == []
        assert approval.requests == []

    def test_play_sends_top_then_go_for_the_owned_timecode(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_owned_state_tree()
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is True
        assert event["last_action"] == "console_play"
        assert _timecode_lines(console.executed) == [
            f"Top Timecode {TIMECODE_NUMBER}",
            f"Go Timecode {TIMECODE_NUMBER}",
        ]

    def test_a_foreign_timecode_name_refuses_and_sends_nothing(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        session, console, approval, _audit = _new_session(
            tmp_path,
            store=store,
            state_tree=_owned_state_tree(timecode_name="Someone Else TC"),
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert OWNED_TIMECODE_NAME in event["reason"]
        assert console.executed == []
        assert approval.requests == []

    def test_a_declined_approval_sends_nothing(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_owned_state_tree(), decisions=(False,)
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert _timecode_lines(console.executed) == []


class TestConsoleStop:
    def test_stop_sends_off_timecode(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_owned_state_tree()
        )

        event = session.beat_grid_console_stop()

        assert event["ok"] is True
        assert event["last_action"] == "console_stop"
        assert _timecode_lines(console.executed) == [f"Off Timecode {TIMECODE_NUMBER}"]

    def test_stop_without_a_record_refuses(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)

        event = session.beat_grid_console_stop()

        assert event["ok"] is False
        assert console.executed == []
