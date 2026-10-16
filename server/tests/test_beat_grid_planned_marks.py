"""계획 표시(계획 색 · 계획 이름)를 격자 칸에 얹는 규칙 — 콘솔 무접촉, 원본 격자 불변,
「반영 이후 바뀐 칸」 비교에서는 빠진다."""

from __future__ import annotations

import copy

from server.design import beat_grid_planned
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_planned import attach_planned_marks
from server.design.beat_grid_send import beat_grid_cell_snapshot, unsent_beat_grid_cells
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values


def _cue(grid: dict, group: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group)
    return next(c for c in track["cues"] if c["bar"] == bar)


def _attached(grid: dict, title: str = LOVE_ATTACK_TITLE) -> dict:
    """화면에 보내는 것과 같은 경로(``attach_beat_grid_ui_values``)로 붙인 격자."""
    return attach_beat_grid_ui_values({"song_title": title, "beat_grid": grid})["beat_grid"]


def _annotations_with(colors: list[dict]) -> dict:
    return {"colors": colors}


class TestPlannedColorOnCells:
    def test_a_cell_without_a_console_color_gets_its_planned_rgb_and_the_flag(self) -> None:
        out = _attached(default_beat_grid(LOVE_ATTACK_TITLE))

        assert _cue(out, "WASH-ALL", 18)["color_rgb"] == [100, 50, 75]  # 핑크
        assert _cue(out, "WASH-ALL", 18)["color_planned"] is True
        assert _cue(out, "WASH-ALL", 22)["color_rgb"] == [100, 75, 60]  # 피치
        assert _cue(out, "BACK", 0)["color_rgb"] == [40, 65, 95]  # 하늘(역광 0마디)
        assert _cue(out, "WASH-ALL", 7)["color_rgb"] == [55, 35, 100]  # 라벤더(팔레트)
        assert _cue(out, "WASH-ALL", 14)["color_planned"] is True
        assert "color_planned" not in _cue(out, "BACK", 7)  # 색 계획이 없는 칸

    def test_a_cell_with_a_console_color_keeps_its_real_rgb_and_no_planned_flag(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        _cue(grid, "WASH-ALL", 18)["color_preset_no"] = "4.21"
        grid["preset_colors"] = {"4.21": {"r": 10, "g": 20, "b": 30}}

        out = _attached(grid)

        assert _cue(out, "WASH-ALL", 18)["color_rgb"] == [10, 20, 30]
        assert "color_planned" not in _cue(out, "WASH-ALL", 18)

    def test_the_stored_grid_is_not_changed_by_the_planned_marks(self) -> None:
        stored = default_beat_grid(LOVE_ATTACK_TITLE)
        before = copy.deepcopy(stored)

        attach_planned_marks(stored, LOVE_ATTACK_TITLE)

        assert stored == before

    def test_a_song_without_a_plan_annotation_gets_no_marks(self) -> None:
        out = attach_planned_marks(default_beat_grid(LOVE_ATTACK_TITLE), "Sugar")

        for track in out["tracks"]:
            for cue in track["cues"]:
                assert not {
                    "color_planned",
                    "planned_dimmer_name",
                    "planned_position_name",
                    "color_rgb",
                } & set(cue)

    def test_two_planned_colors_on_one_cell_are_not_guessed(self, monkeypatch) -> None:
        annotations = _annotations_with(
            [
                {
                    "name": "가",
                    "console_name": "ALPHA",
                    "rgb": [1, 2, 3],
                    "cells": [{"group_name": "WASH-ALL", "bar": 18}],
                },
                {
                    "name": "나",
                    "console_name": "BETA",
                    "rgb": [4, 5, 6],
                    "cells": [{"group_name": "WASH-ALL", "bar": 18}],
                },
            ]
        )
        monkeypatch.setattr(beat_grid_planned, "load_preset_annotations", lambda title: annotations)

        out = attach_planned_marks(default_beat_grid(LOVE_ATTACK_TITLE), LOVE_ATTACK_TITLE)

        assert "color_rgb" not in _cue(out, "WASH-ALL", 18)
        assert "color_planned" not in _cue(out, "WASH-ALL", 18)

    def test_an_out_of_range_planned_rgb_is_not_attached(self, monkeypatch) -> None:
        annotations = _annotations_with(
            [
                {
                    "name": "가",
                    "console_name": "ALPHA",
                    "rgb": [150, 1, 2],
                    "cells": [{"group_name": "WASH-ALL", "bar": 18}],
                }
            ]
        )
        monkeypatch.setattr(beat_grid_planned, "load_preset_annotations", lambda title: annotations)

        out = attach_planned_marks(default_beat_grid(LOVE_ATTACK_TITLE), LOVE_ATTACK_TITLE)

        assert "color_rgb" not in _cue(out, "WASH-ALL", 18)
        assert "color_planned" not in _cue(out, "WASH-ALL", 18)


class TestPlannedNames:
    def test_a_value_cell_without_a_dimmer_number_gets_its_planned_dimmer_name_name(self) -> None:
        out = _attached(default_beat_grid(LOVE_ATTACK_TITLE))

        assert _cue(out, "WASH-ALL", 18)["planned_dimmer_name"] == "DIM-70"
        assert _cue(out, "WASH-ALL", 22)["planned_dimmer_name"] == "DIM-70"
        assert _cue(out, "WASH-ALL", 7)["planned_dimmer_name"] == "DIM-40"
        assert _cue(out, "MOVER-U", 0)["planned_dimmer_name"] == "DIM-100"

    def test_the_floor_cells_get_the_planned_position_name_name(self) -> None:
        out = _attached(default_beat_grid(LOVE_ATTACK_TITLE))

        assert _cue(out, "MOVER-U", 0)["planned_position_name"] == "FLOOR"
        assert _cue(out, "MOVER-D", 0)["planned_position_name"] == "FLOOR"
        assert "planned_position_name" not in _cue(out, "MOVER-U", 7)

    def test_a_position_number_suppresses_the_planned_position_name_name(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        _cue(grid, "MOVER-U", 0)["position_preset_no"] = "2.1"

        out = _attached(grid)

        assert "planned_position_name" not in _cue(out, "MOVER-U", 0)
        assert _cue(out, "MOVER-U", 0)["planned_dimmer_name"] == "DIM-100"  # 디머 번호는 따로 본다

    def test_a_dimmer_number_suppresses_the_planned_dimmer_name_name(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        _cue(grid, "WASH-ALL", 7)["brightness"] = {
            "mode": "dimmer_preset",
            "value_percent": None,
            "preset_no": "1.8",
        }

        out = _attached(grid)

        assert "planned_dimmer_name" not in _cue(out, "WASH-ALL", 7)


class TestPlannedMarksStayOutOfTheConsoleDiff:
    def test_planned_marks_alone_never_make_a_cell_look_unsent(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        snapshot = beat_grid_cell_snapshot(grid)

        assert unsent_beat_grid_cells(_attached(grid), snapshot) == []

    def test_a_real_edit_next_to_the_planned_marks_is_still_unsent(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        snapshot = beat_grid_cell_snapshot(grid)
        attached = _attached(grid)
        _cue(attached, "WASH-ALL", 18)["label"] = "고친 글"

        assert unsent_beat_grid_cells(attached, snapshot) == [{"group_name": "WASH-ALL", "bar": 18}]
