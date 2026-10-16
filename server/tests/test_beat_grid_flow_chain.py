"""``beat_grid_send_status`` 의 선택 필드 ``completed`` · ``timecode_suggestion`` (흐름 사슬).

UI 는 기존 ``beat_grid_send_status`` 이벤트 하나로 「방금 어느 단계가 성공으로 끝났는지」를
읽는다. 새 메시지 타입은 없다. 계약:

- ``completed``: ``draft_applied`` | ``preset_saved`` | ``reflected`` — 그 단계의 **성공**에만
  실린다.
- ``timecode_suggestion``: 1 이상의 정수 — ``preset_saved`` 성공 때, 곡 초안에 타임코드 번호가
  없고 콘솔이 비어 있다고 확인한 슬롯이 있을 때만 실린다.
- 둘 다 없으면 **키 자체가 없다**(``null`` 이 아니다). 기능이 없을 때의 이벤트는 예전과
  바이트가 같다.

세 층: ① 이벤트 빌더(순수) ② ``ChatSession._beat_grid_timecode_suggestion``(점유 판독을 가짜로
바꿔 끼운다) ③ 프리셋 저장 세션 경로(가짜 콘솔). 콘솔 접촉 0건 — ``FakeConsole`` 과 가짜 점유
판독만 쓰고 실기 포트로는 한 바이트도 나가지 않는다.
"""

from __future__ import annotations

import json

import pytest

from server.web.messages import BEAT_GRID_COMPLETED_STEPS, beat_grid_send_status_event
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _new_session, _timeline
from .test_preset_plan import _EXPECTED_SAVE, _love_attack_session

#: 선택 필드가 없을 때 이벤트가 가진 키와 그 순서 — 예전 바이트와 같아야 한다.
_BASE_KEYS = [
    "v",
    "type",
    "pending_apply_count",
    "last_action",
    "ok",
    "reason",
    "blocked_cells",
    "approval_vs_sent",
    "stale_tracks",
    "notices",
]


def _status(**overrides: object) -> dict:
    fields: dict[str, object] = {
        "pending_apply_count": 0,
        "last_action": "apply",
        "ok": True,
        "blocked_cells": [],
    }
    fields.update(overrides)
    return beat_grid_send_status_event(**fields)


# == ① 이벤트 빌더 ===================================================================


class TestEventBuilder:
    def test_neither_key_is_present_when_unset(self) -> None:
        event = _status()
        assert list(event) == _BASE_KEYS
        assert "completed" not in event
        assert "timecode_suggestion" not in event

    def test_the_completed_steps_are_the_three_chain_stages_in_order(self) -> None:
        assert BEAT_GRID_COMPLETED_STEPS == ("draft_applied", "preset_saved", "reflected")

    @pytest.mark.parametrize("step", BEAT_GRID_COMPLETED_STEPS)
    def test_completed_is_present_when_set_and_nothing_else_changes(self, step: str) -> None:
        event = _status(completed=step)
        assert event["completed"] == step
        assert "timecode_suggestion" not in event
        assert {key: value for key, value in event.items() if key != "completed"} == _status()

    def test_timecode_suggestion_is_present_when_set(self) -> None:
        event = _status(completed="preset_saved", timecode_suggestion=4)
        assert event["completed"] == "preset_saved"
        assert event["timecode_suggestion"] == 4
        assert list(event)[: len(_BASE_KEYS)] == _BASE_KEYS  # 기존 키 순서는 그대로, 새 키는 뒤에

    def test_a_suggestion_alone_does_not_invent_a_completed_key(self) -> None:
        event = _status(timecode_suggestion=1)
        assert event["timecode_suggestion"] == 1
        assert "completed" not in event

    @pytest.mark.parametrize("bad", ["", "draft_apply", "Reflected", " reflected", "done"])
    def test_an_unknown_completed_value_raises_value_error(self, bad: str) -> None:
        with pytest.raises(ValueError, match="completed"):
            _status(completed=bad)

    def test_the_event_stays_json_serialisable(self) -> None:
        frame = json.dumps(_status(completed="preset_saved", timecode_suggestion=2))
        assert json.loads(frame)["timecode_suggestion"] == 2


# == ② 타임코드 권유 =================================================================


def _suggestion_session(tmp_path, *, timecode_number: object = "absent"):
    """``timecode_number`` 가 ``"absent"`` 면 키 자체가 없는 곡 초안, 그 밖의 값은 그대로 적는다."""
    timeline = _timeline()
    if timecode_number == "absent":
        del timeline["timecode_number"]
    else:
        timeline["timecode_number"] = timecode_number
    store = SongTimelineStore()
    store.latest = timeline
    session, console, _approval, _audit = _new_session(tmp_path, store=store)
    return session, console, store


def _fake_occupancy(session, monkeypatch, occupied: set[int]) -> list[int]:
    """콘솔 타임코드 슬롯 판독을 ``occupied`` 집합으로 바꿔 끼우고, 읽은 번호를 순서대로 모은다."""
    probed: list[int] = []

    def fake(timecode_no: int) -> bool:
        probed.append(timecode_no)
        return timecode_no in occupied

    monkeypatch.setattr(session, "_timecode_occupied", fake)
    return probed


class TestTimecodeSuggestion:
    def test_none_without_reading_the_console_when_the_timeline_has_a_number(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _store = _suggestion_session(tmp_path, timecode_number=20)
        probed = _fake_occupancy(session, monkeypatch, occupied=set())

        assert session._beat_grid_timecode_suggestion() is None
        assert probed == []  # 이미 번호가 있으면 콘솔을 읽지도 않는다
        assert console.executed == []

    @pytest.mark.parametrize(
        ("occupied", "expected"),
        [(set(), 1), ({1}, 2), ({1, 2, 3}, 4), ({2}, 1)],
    )
    def test_the_first_empty_slot_is_suggested_when_the_timecode_is_empty(
        self, tmp_path, monkeypatch, occupied: set[int], expected: int
    ) -> None:
        session, console, _store = _suggestion_session(tmp_path)
        probed = _fake_occupancy(session, monkeypatch, occupied=occupied)

        assert session._beat_grid_timecode_suggestion() == expected
        assert probed == list(range(1, expected + 1))  # 1번부터 읽고 첫 빈 자리에서 멈춘다
        assert console.executed == []  # 읽기만 한다

    def test_a_timecode_number_of_none_counts_as_empty(self, tmp_path, monkeypatch) -> None:
        session, _console, _store = _suggestion_session(tmp_path, timecode_number=None)
        _fake_occupancy(session, monkeypatch, occupied={1})

        assert session._beat_grid_timecode_suggestion() == 2

    def test_none_when_no_slot_is_free(self, tmp_path, monkeypatch) -> None:
        session, _console, _store = _suggestion_session(tmp_path)
        probed = _fake_occupancy(session, monkeypatch, occupied=set(range(1, 1000)))

        assert session._beat_grid_timecode_suggestion() is None
        assert probed[0] == 1

    def test_none_without_raising_when_the_slot_probe_raises(self, tmp_path, monkeypatch) -> None:
        session, _console, _store = _suggestion_session(tmp_path)

        def broken(timecode_no: int) -> bool:
            raise RuntimeError("console unreachable")

        monkeypatch.setattr(session, "_timecode_occupied", broken)

        assert session._beat_grid_timecode_suggestion() is None

    def test_none_without_raising_when_the_slot_search_raises(self, tmp_path, monkeypatch) -> None:
        session, _console, _store = _suggestion_session(tmp_path)

        def broken(start: int, *, count: int = 2, probes: int = 10) -> list[int]:
            raise RuntimeError("console unreachable")

        monkeypatch.setattr(session, "_free_timecode_slots", broken)

        assert session._beat_grid_timecode_suggestion() is None

    def test_none_without_a_timeline_or_a_store(self, tmp_path, monkeypatch) -> None:
        session, _console, store = _suggestion_session(tmp_path)
        probed = _fake_occupancy(session, monkeypatch, occupied=set())

        store.latest = None
        assert session._beat_grid_timecode_suggestion() is None

        monkeypatch.setattr(session, "_timeline_store", None)
        assert session._beat_grid_timecode_suggestion() is None
        assert probed == []


# == ③ 프리셋 저장 세션 경로 ===========================================================


class TestPresetSavedEvent:
    """``beat_grid_preset_plan`` 의 성공 이벤트. 가짜 콘솔의 타임코드 풀 슬롯을 실제 판독 경로
    (``_timecode_occupied`` → ``query_state``)로 읽는다 — 점유 판독 자체는 바꿔 끼우지 않는다."""

    def test_success_carries_preset_saved_and_the_first_console_verified_empty_slot(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, store = _love_attack_session(
            tmp_path, decisions=(True,), monkeypatch=monkeypatch
        )
        del store.latest["timecode_number"]
        # 1번은 남이 쓰고 있고, 2번은 응답기가 빈 자리에 주는 모양(``{}``)이다.
        console.state_tree["DataPool/Timecodes/1"] = {"ok": True, "node": {"name": "SOMEONE ELSE"}}
        console.state_tree["DataPool/Timecodes/2"] = {}

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert event["last_action"] == "apply"
        assert event["completed"] == "preset_saved"
        assert event["timecode_suggestion"] == 2
        # 권유는 읽기뿐이다 — 저장 줄 말고는 콘솔에 나간 것이 없다.
        assert console.executed == list(_EXPECTED_SAVE)
        assert "timecode_number" not in store.latest  # 권유를 초안에 적지 않는다

    def test_a_timeline_that_already_has_a_timecode_number_gets_no_suggestion(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, _approval, store = _love_attack_session(
            tmp_path, decisions=(True,), monkeypatch=monkeypatch
        )
        assert store.latest["timecode_number"] == 20
        probed = _fake_occupancy(session, monkeypatch, occupied=set())

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert event["completed"] == "preset_saved"
        assert "timecode_suggestion" not in event
        assert probed == []

    def test_an_unreadable_timecode_pool_leaves_the_key_out_and_the_save_still_succeeds(
        self, tmp_path, monkeypatch
    ) -> None:
        # 가짜 콘솔은 모르는 경로를 오류로 답한다 → 못 읽은 슬롯은 점유로 본다(fail-closed) →
        # 확인된 빈 자리가 없으니 권유가 없다. 저장 성공은 그대로다.
        session, _console, _approval, store = _love_attack_session(
            tmp_path, decisions=(True,), monkeypatch=monkeypatch
        )
        del store.latest["timecode_number"]

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert event["completed"] == "preset_saved"
        assert "timecode_suggestion" not in event

    def test_a_probe_that_raises_does_not_turn_the_success_into_an_error(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, _approval, store = _love_attack_session(
            tmp_path, decisions=(True,), monkeypatch=monkeypatch
        )
        del store.latest["timecode_number"]

        def broken(timecode_no: int) -> bool:
            raise RuntimeError("console unreachable")

        monkeypatch.setattr(session, "_timecode_occupied", broken)

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert event["completed"] == "preset_saved"
        assert "timecode_suggestion" not in event

    def test_a_rejected_card_carries_neither_key_even_when_a_slot_is_free(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, _approval, store = _love_attack_session(
            tmp_path, decisions=(False,), monkeypatch=monkeypatch
        )
        del store.latest["timecode_number"]
        console.state_tree["DataPool/Timecodes/1"] = {}

        event = session.beat_grid_preset_plan()

        assert event["ok"] is False
        assert "completed" not in event
        assert "timecode_suggestion" not in event
