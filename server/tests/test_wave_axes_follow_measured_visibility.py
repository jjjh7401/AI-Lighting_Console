"""웨이브 축은 실측 기록에서 「보이는 축」을 고른다 (full2 4번 · 리드 결정 2026-10-17).

SPEC-LDBEAT-001 progress.md · ``measured_movements.yaml``: 팬 단독 웨이브는 기준이 거의 수직이면
안 보인다(``requires_tilted_base_unverifiable``). 같은 그룹에 기준과 무관하게 보이는 웨이브 기록
(``base_condition: any``)이 있으면 생성기는 그 축으로 낸다. 그룹 번호는 기록 파일이 쥔다 — 이 시험도
기대값을 기록에서 읽는다(리그 번호를 시험에 적지 않는다).
"""

from __future__ import annotations

import copy

import pytest

from server.design import beat_grid_measured
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_measured import (
    MEASURED_MOVEMENTS,
    MeasuredMovement,
    visible_axes,
)

from .test_arrange_segments import _real_love_attack


def _entry(group_no: int, axes: tuple[str, ...], base: str) -> MeasuredMovement:
    return MeasuredMovement(
        group_no=group_no, shape="wave", axes=frozenset(axes), base_condition=base, source="시험"
    )


class TestVisibleAxes:
    def test_a_closed_pan_with_an_open_tilt_record_uses_tilt(self, monkeypatch) -> None:
        monkeypatch.setattr(
            beat_grid_measured,
            "MEASURED_MOVEMENTS",
            (
                _entry(7, ("Tilt",), "any"),
                _entry(7, ("Pan",), "requires_tilted_base_unverifiable"),
            ),
        )
        assert visible_axes(7, "wave", ("Pan",)) == ("Tilt",)

    def test_a_closed_pan_without_an_open_alternative_stays_pan(self, monkeypatch) -> None:
        monkeypatch.setattr(
            beat_grid_measured,
            "MEASURED_MOVEMENTS",
            (_entry(7, ("Pan",), "requires_tilted_base_unverifiable"),),
        )
        assert visible_axes(7, "wave", ("Pan",)) == ("Pan",)

    @pytest.mark.parametrize("group_no", [None, 99])
    def test_no_group_or_no_record_keeps_the_default(self, monkeypatch, group_no) -> None:
        monkeypatch.setattr(
            beat_grid_measured,
            "MEASURED_MOVEMENTS",
            (_entry(7, ("Tilt",), "any"), _entry(7, ("Pan",), "requires_tilted_base_unverifiable")),
        )
        assert visible_axes(group_no, "wave", ("Pan",)) == ("Pan",)


def test_the_generator_draws_each_mover_wave_on_its_visible_axes() -> None:
    bar_map = _real_love_attack()
    base = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    draft = generate_segment_draft(bar_map, base["tracks"])
    closed_pan = {
        entry.group_no
        for entry in MEASURED_MOVEMENTS
        if entry.shape == "wave"
        and entry.axes == frozenset({"Pan"})
        and entry.base_condition != "any"
    }
    open_axes = {
        entry.group_no: entry.axes
        for entry in MEASURED_MOVEMENTS
        if entry.shape == "wave" and entry.base_condition == "any"
    }
    switched = 0
    for track in draft["tracks"]:
        if track["layer_role"] != "mover":
            continue
        waves = [cue for cue in track["cues"] if cue.get("app_movement")]
        assert waves, track["group_name"]
        group_no = track["group_no"]
        if group_no in closed_pan and group_no in open_axes:
            expected = sorted(open_axes[group_no])
            switched += 1
        else:
            expected = ["Pan"]
        for cue in waves:
            assert sorted(cue["app_movement"]["axes"]) == expected, (track["group_name"], cue)
            if expected == ["Tilt"]:
                assert cue["label"].startswith("틸트 웨이브")
    # 전제: 이 리그 기록에는 바꿀 그룹이 적어도 하나 있다(없으면 이 시험은 아무것도 재지 않는다).
    assert switched >= 1
