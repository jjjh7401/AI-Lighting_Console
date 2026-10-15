"""박자 배치 색 프리셋 RGB 노출 — 기록이 있을 때만 `rgb`/`color_rgb`, 없으면 키 없음."""

from __future__ import annotations

from server.design.beat_grid_color_presets import (
    attach_color_rgb_to_cues,
    attach_color_rgb_to_drawer,
)
from server.design.beat_grid_presets import build_preset_drawer
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values


def _grid() -> dict:
    return {
        "preset_colors": {
            "4.41": {"r": 50, "g": 0, "b": 12.5},
            "4.99": {"r": 120, "g": 0, "b": 0},  # 범위 밖 — 쓰지 않는다
        },
        "tracks": [
            {
                "group_name": "G1",
                "cues": [
                    {"bar": 1, "color_preset_no": "4.41"},
                    {"bar": 2, "color_preset_no": "4.7"},
                    {"bar": 3, "color_preset_no": "4.99"},
                    {"bar": 4},
                ],
            }
        ],
    }


def test_cue_color_rgb_present_only_when_recorded() -> None:
    cues = attach_color_rgb_to_cues(_grid())["tracks"][0]["cues"]
    assert cues[0]["color_rgb"] == [50.0, 0.0, 12.5]
    for cue in cues[1:]:
        assert "color_rgb" not in cue


def test_cue_attach_does_not_mutate_input() -> None:
    grid = _grid()
    attach_color_rgb_to_cues(grid)
    assert "color_rgb" not in grid["tracks"][0]["cues"][0]


def test_ui_values_carries_cue_color_rgb() -> None:
    merged = attach_beat_grid_ui_values({"beat_grid": _grid()})
    assert merged["beat_grid"]["tracks"][0]["cues"][0]["color_rgb"] == [50.0, 0.0, 12.5]


def test_drawer_color_entries_get_rgb_only_when_known() -> None:
    grid = _grid()
    pools = {
        "Dimmer": (1, {1: "Full"}),
        "Position": (2, {1: "Center"}),
        "Color": (4, {41: "LA Wave", 7: "Show Red"}),
    }
    sections = build_preset_drawer(grid, pools=pools, policy={"confirmed": True})
    out = attach_color_rgb_to_drawer(sections, grid)
    by_name = {s["pool_name"]: s for s in out}
    color = {e["preset_no"]: e for e in by_name["Color"]["entries"]}
    assert color["4.41"]["rgb"] == [50.0, 0.0, 12.5]
    assert "rgb" not in color["4.7"]
    assert all("rgb" not in e for e in by_name["Dimmer"]["entries"])
    assert all("rgb" not in e for e in by_name["Position"]["entries"])


def test_drawer_unread_color_section_stays_empty() -> None:
    grid = _grid()
    pools = {"Dimmer": None, "Position": None, "Color": None}
    sections = build_preset_drawer(grid, pools=pools, policy={"confirmed": False})
    out = attach_color_rgb_to_drawer(sections, grid)
    assert all(s["entries"] == [] and s["unread"] is True for s in out)
