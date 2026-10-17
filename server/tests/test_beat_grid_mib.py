"""MIB(어둠 속 사전이동) — 칸 전환의 위치 전용 큐와 불가 사유 (박자 격자 반영).

- 위치가 바뀌고 앞 칸이 꺼져 있으면, 앞 칸 다음 마디에 위치 전용 큐를 끼운다.
- 앞 칸이 켜져 있으면 MIB 가 아니다(켜진 채 이동). 어두운 시간이 이동+정착보다 짧으면 못 끼운다.
  둘 다 미리보기에 「MIB 불가 — …」 한 줄로 보인다.

콘솔 접촉: ``FakeConsole`` 만, 실기 쓰기 0건.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming
from server.design.beat_grid_mib import MIB_MIN_DARK_SECONDS, cue_is_lit, plan_mib_premoves
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _APPROVED_EVIDENCE, _new_session, _timeline

#: 112 BPM, 4/4 — 한 마디 약 2.142857초. 첫 다운비트는 1초에서 시작한다고 둔다.
TIMING = SongTiming(bpm=112.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
BAR_SECONDS = 4 * 60.0 / 112.0
DIMMER_ON = {"mode": "dimmer_preset", "preset_no": "1.1"}


def _cue(bar: int, **fields: object) -> dict:
    return {"bar": bar, "evidence": _APPROVED_EVIDENCE, **fields}


def _store_with_cues(cues: list[dict]) -> SongTimelineStore:
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = cues
    store = SongTimelineStore()
    store.latest = timeline
    return store


def test_a_cue_is_unlit_when_its_value_is_zero_or_its_label_is_empty_or_a_dash():
    assert cue_is_lit({"label": "FOH"}) is True
    assert cue_is_lit({"label": ""}) is False
    assert cue_is_lit({"label": "—"}) is False
    assert (
        cue_is_lit({"label": "FOH", "brightness": {"mode": "value", "value_percent": 0}}) is False
    )


def test_no_premove_when_the_position_does_not_change():
    cues = [
        _cue(14, position_preset_no="1.1", label=""),
        _cue(19, position_preset_no="1.1", label="FOH"),
    ]

    assert plan_mib_premoves(cues, TIMING) == ([], [])


def test_a_lit_previous_cue_gives_the_lit_move_reason_and_no_premove():
    cues = [
        _cue(14, position_preset_no="1.1", label="FOH"),
        _cue(19, position_preset_no="1.2", label="FOH"),
    ]

    premoves, notes = plan_mib_premoves(cues, TIMING)

    assert premoves == []
    assert notes == ["19마디 MIB 불가 — 앞 큐가 켜져 있어 켜진 채 이동합니다"]


def test_a_long_enough_dark_stretch_gets_one_premove_right_after_the_previous_cue():
    cues = [
        _cue(14, position_preset_no="1.1", label=""),
        _cue(19, position_preset_no="1.2", label="FOH"),
    ]

    premoves, notes = plan_mib_premoves(cues, TIMING)

    assert notes == []
    assert [(p["bar"], p["position_preset_no"]) for p in premoves] == [(15, "1.2")]
    assert (19 - 15) * BAR_SECONDS >= MIB_MIN_DARK_SECONDS


def test_a_dark_stretch_shorter_than_move_plus_settle_is_refused_with_the_reason():
    cues = [
        _cue(14, position_preset_no="1.1", label=""),
        _cue(16, position_preset_no="1.2", label="FOH"),
    ]

    premoves, notes = plan_mib_premoves(cues, TIMING)

    assert premoves == []
    assert len(notes) == 1
    assert notes[0].startswith("16마디 MIB 불가 — 어두운 시간")
    assert "짧습니다" in notes[0]


def test_apply_puts_the_premove_in_the_dark_and_the_lit_cue_keeps_its_position(tmp_path):
    cues = [
        _cue(14, position_preset_no="1.1", label="", brightness=DIMMER_ON),
        _cue(19, position_preset_no="1.2", label="FOH", brightness=DIMMER_ON),
    ]
    session, console, approval, _audit = _new_session(tmp_path, store=_store_with_cues(cues))

    event = session.beat_grid_apply()

    assert event["ok"] is True
    assert event["notices"] == []
    # 사전이동 큐(15마디)와 켜지는 칸(19마디)이 각각 위치 명령을 한 줄씩 낸다.
    position_lines = [line for line in console.executed if line.endswith("At Preset 1.2")]
    assert len(position_lines) == 2
    # 전체 실행 C-11 — 카드가 격자 칸 2개와 큐 3개의 차이(미리 이동 큐 1개)를 적는다.
    reasons = [r for item in approval.requests[-1].items for r in item.risk_reasons]
    assert any(
        "큐 3개(격자 칸 2개 중 보내는 칸 2개 + 어둠 속 미리 이동 큐 1개" in r for r in reasons
    ), reasons


def test_apply_shows_the_reason_when_the_dark_stretch_is_too_short(tmp_path):
    cues = [
        _cue(14, position_preset_no="1.1", label="", brightness=DIMMER_ON),
        _cue(16, position_preset_no="1.2", label="FOH", brightness=DIMMER_ON),
    ]
    session, console, _approval, _audit = _new_session(tmp_path, store=_store_with_cues(cues))

    event = session.beat_grid_apply()

    assert event["ok"] is True
    assert len(event["notices"]) == 1
    assert event["notices"][0].startswith("16마디 MIB 불가 — 어두운 시간")
    # 짧은 어둠에서는 사전이동이 빠진다 — 16마디의 위치 명령 한 줄만 나간다.
    assert sum(1 for line in console.executed if line.endswith("At Preset 1.2")) == 1
