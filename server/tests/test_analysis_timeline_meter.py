"""새 분석 작업본의 박자 머리값 — 2차 전체 실행 N9 (2026-10-16).

새 분석으로 만든 작업본은 ``bar_map`` 만 싣고 ``seconds_per_bar``·``time_signature``·
``bar_count`` 를 비웠다(실저장본에서 셋 다 ``None``). 화면은 한 마디 길이로 재생 위치를
마디로 바꾸므로, 시계는 가는데 격자 스크롤·재생선·「N마디」·무대가 0 에 멈췄다.
값은 마디 지도에서만 온다(BPM 이 없거나 박자표를 모르면 비운다 — 지어내지 않는다).
"""

from __future__ import annotations

import pytest

from server.design.analysis_timeline import build_analysis_timeline, timeline_meter_from_bar_map
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values


def _bar_map(**over: object) -> dict:
    bar_map: dict = {
        "schema_version": 1,
        "bpm": 112.00191993244025,
        "time_signature": [4, 4],
        "first_beat_offset": 1,
        "bars": [{"bar": bar, "start_ms": 964 + bar * 2143} for bar in range(83)],
    }
    bar_map.update(over)
    return bar_map


class _Section:
    def __init__(self, label: str, start_ms: int, end_ms: int, d_level: int) -> None:
        self.label, self.start_ms, self.end_ms, self.d_level = label, start_ms, end_ms, d_level


def test_meter_comes_from_the_bar_map() -> None:
    meter = timeline_meter_from_bar_map(_bar_map())
    assert meter["time_signature"] == "4/4"
    assert meter["bar_count"] == 83
    assert meter["seconds_per_bar"] == pytest.approx(4 * 60 / 112.00191993244025)


@pytest.mark.parametrize(
    "over",
    [
        {"bpm": None},
        {"bpm": 0},
        {"time_signature": None},
        {"time_signature": [0, 4]},
        {"time_signature": "x"},
    ],
)
def test_unknown_tempo_or_meter_is_not_invented(over: dict) -> None:
    assert "seconds_per_bar" not in timeline_meter_from_bar_map(_bar_map(**over))


def test_new_analysis_timeline_carries_the_meter() -> None:
    timeline = build_analysis_timeline(
        song_title="LOVE ATTACK",
        sections=[_Section("D1", 0, 20000, 1), _Section("D4", 20000, 177000, 4)],
        bar_map=_bar_map(),
        layout=[{"group_name": "MOVER-U", "layer_role": "mover"}],
        source_sha256="abc",
    )
    assert timeline["seconds_per_bar"] == pytest.approx(4 * 60 / 112.00191993244025)
    assert timeline["time_signature"] == "4/4"
    assert timeline["bar_count"] == 83


def test_an_already_stored_analysis_timeline_is_served_with_the_meter() -> None:
    # 실저장본 모양: bar_map 은 있고 머리값 셋이 None.
    stored = {
        "song_title": "LOVE ATTACK",
        "sections": [],
        "bar_map": _bar_map(),
        "seconds_per_bar": None,
        "time_signature": None,
        "bar_count": None,
        "beat_grid": {"tracks": []},
    }
    served = attach_beat_grid_ui_values(stored)
    assert served["seconds_per_bar"] == pytest.approx(4 * 60 / 112.00191993244025)
    assert served["time_signature"] == "4/4"
    assert served["bar_count"] == 83
    assert stored["seconds_per_bar"] is None  # 원본은 그대로


def test_a_declared_meter_is_never_overwritten() -> None:
    timeline = {
        "bar_map": _bar_map(),
        "seconds_per_bar": 2.0,
        "time_signature": "3/4",
        "bar_count": 10,
    }
    served = attach_beat_grid_ui_values(timeline)
    assert (served["seconds_per_bar"], served["time_signature"], served["bar_count"]) == (
        2.0,
        "3/4",
        10,
    )
