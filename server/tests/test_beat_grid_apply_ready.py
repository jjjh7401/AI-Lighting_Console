"""반영 준비 — 타임코드 번호 입력과 디머 판독 없는 칸 안내 (박자 격자 반영 경로).

- 타임코드 번호가 비어 있으면 「콘솔에 반영」 전체를 「타임코드 번호를 넣어 주세요」로 막는다.
- 타임코드 번호는 양의 정수만 받아 곡 초안과 보관함에 적는다. 번호를 지어내지 않는다.
- 디머 속성 판독이 없어 막힌 칸은 빼고 나머지 칸은 그대로 보낸다. 미리보기 안내에는
  「이 장비는 밝기 정보를 아직 읽지 않았어요 — N칸 제외」 한 줄이 붙는다.

콘솔 접촉: ``FakeConsole`` 만, 실기 쓰기 0건.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_send import dimmer_unread_notices
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import (
    _APPROVED_EVIDENCE,
    _new_session,
    _timeline,
    _timeline_events,
)


def _cue(bar: int, **fields: object) -> dict:
    return {"bar": bar, "evidence": _APPROVED_EVIDENCE, **fields}


def _store_with(timeline: dict) -> SongTimelineStore:
    store = SongTimelineStore()
    store.latest = timeline
    return store


def test_apply_without_a_timecode_number_is_refused_before_any_console_contact(tmp_path):
    timeline = _timeline()
    del timeline["timecode_number"]
    session, console, approval, _audit = _new_session(tmp_path, store=_store_with(timeline))

    event = session.beat_grid_apply()

    assert event["ok"] is False
    assert event["reason"] == "타임코드 번호를 넣어 주세요"
    assert console.executed == []
    assert approval.requests == []


@pytest.mark.parametrize("bad", [0, -3, "3", 2.0, True, None])
def test_timecode_setter_refuses_anything_but_a_positive_integer(tmp_path, bad):
    store = _store_with(_timeline())  # 타임코드 번호 20
    sent: list[dict] = []
    session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)

    event = session.beat_grid_timecode_set(bad)

    assert event["ok"] is False
    assert store.latest["timecode_number"] == 20
    assert _timeline_events(sent) == []


def test_timecode_setter_saves_on_the_draft_and_a_library_snapshot(tmp_path):
    timeline = _timeline()
    del timeline["timecode_number"]
    store = _store_with(timeline)
    sent: list[dict] = []
    session, console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)

    event = session.beat_grid_timecode_set(7)

    assert event["ok"] is True
    assert store.latest["timecode_number"] == 7
    saved = [entry["timeline"]["timecode_number"] for entry in session._timeline_library.items()]
    assert saved == [7]
    assert [e["timeline"]["timecode_number"] for e in _timeline_events(sent)] == [7]
    assert console.executed == []  # 번호를 적는 것만으로는 콘솔에 아무것도 나가지 않는다
    assert session.beat_grid_apply()["ok"] is True  # 이제 반영은 번호 문제로 막히지 않는다


def test_cells_without_dimmer_readout_are_excluded_and_the_rest_is_sent(tmp_path):
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = [
        _cue(1, position_preset_no="1.1"),
        _cue(2, brightness={"mode": "value", "value_percent": 50}),
        _cue(3, brightness={"mode": "value", "value_percent": 30}),
        _cue(4, position_preset_no="1.2"),
    ]
    session, console, _approval, _audit = _new_session(tmp_path, store=_store_with(timeline))

    event = session.beat_grid_apply()

    assert event["ok"] is True
    assert [cell["bar"] for cell in event["blocked_cells"]] == [2, 3]
    assert event["notices"] == [
        "이 장비는 밝기 정보를 아직 읽지 않았어요 — 2칸 제외",
        "4마디 MIB 불가 — 앞 큐 바로 다음 마디라 어두운 시간이 없습니다",
    ]
    writes = [line for line in console.executed if line != "SaveShow"]
    assert any(line.endswith("At Preset 1.1") for line in writes)
    assert any(line.endswith("At Preset 1.2") for line in writes)
    assert not any("Attribute" in line for line in writes)  # 밝기 값 줄은 하나도 나가지 않는다


def test_notice_counts_only_cells_whose_dimmer_readout_is_missing():
    cells = [
        (
            "SPIDERS",
            2,
            "장비 능력을 콘솔에서 읽지 못해 'SPIDERS' 그룹의 디머 속성을 고를 수 없습니다",
        ),
        ("PARS", 3, "'PARS' 그룹 안에 디머 속성이 다른 장비가 섞여 있어 하나로 고를 수 없습니다"),
        ("PARS", 4, "'PARS' 그룹 장비(fid 5)의 능력을 다 읽지 못해 디머 속성을 고를 수 없습니다"),
    ]

    assert dimmer_unread_notices(cells) == ["이 장비는 밝기 정보를 아직 읽지 않았어요 — 2칸 제외"]
    assert dimmer_unread_notices(cells[1:2]) == []
    assert dimmer_unread_notices([]) == []
