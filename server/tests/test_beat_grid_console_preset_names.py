"""박자 배치 칸의 콘솔 프리셋 이름 — 이미 읽어 둔 풀에 이름이 있을 때만 노출한다."""

from __future__ import annotations

from server.design.beat_grid_ui_values import (
    attach_beat_grid_ui_values,
    attach_console_preset_names,
)


def _grid() -> dict:
    return {
        "tracks": [
            {
                "group_name": "MOVER",
                "cues": [
                    {"position_preset_no": "2.3", "color_preset_no": "4.5"},
                    {"position_preset_no": "2.9", "color_preset_no": "4.6"},
                    {"position_preset_no": "garbage", "color_preset_no": None},
                    {"color_preset_no": "4.5", "color_preset_name": "내 이름"},
                ],
            }
        ]
    }


def _cues(grid: dict) -> list[dict]:
    return grid["tracks"][0]["cues"]


def test_names_attached_from_cached_pools() -> None:
    pools = {2: {3: "Center"}, 4: {5: "Red", 6: "Blue"}}
    cues = _cues(attach_console_preset_names(_grid(), pools))
    assert cues[0]["position_preset_name"] == "Center"
    assert cues[0]["color_preset_name"] == "Red"
    assert cues[1]["color_preset_name"] == "Blue"
    assert "position_preset_name" not in cues[1]  # 2.9 슬롯 없음


def test_console_offline_pool_unread_omits_silently() -> None:
    cues = _cues(attach_console_preset_names(_grid(), {2: None, 4: None}))
    assert all("position_preset_name" not in c and "color_preset_name" not in c for c in cues[:3])


def test_malformed_values_are_not_invented() -> None:
    pools = {2: {3: ""}, 4: {5: 42, 6: "  "}}
    cues = _cues(attach_console_preset_names(_grid(), pools))  # type: ignore[arg-type]
    assert not any("position_preset_name" in c for c in cues)
    assert "color_preset_name" not in cues[0]
    assert "color_preset_name" not in cues[1]
    assert cues[2] == {"position_preset_no": "garbage", "color_preset_no": None}


def test_existing_name_not_overwritten_and_input_unchanged() -> None:
    grid = _grid()
    out = _cues(attach_console_preset_names(grid, {4: {5: "Red"}}))
    assert out[3]["color_preset_name"] == "내 이름"
    assert "color_preset_name" not in grid["tracks"][0]["cues"][0]


def test_display_names_do_not_make_cells_unsent() -> None:
    from server.design.beat_grid_send import beat_grid_cell_snapshot, unsent_beat_grid_cells

    grid = {"tracks": [{"group_name": "MOVER", "cues": [{"bar": 1, "position_preset_no": "2.3"}]}]}
    snapshot = beat_grid_cell_snapshot(grid)
    named = attach_console_preset_names(grid, {2: {3: "Center"}})
    assert unsent_beat_grid_cells(named, snapshot) == []


def test_ui_values_wires_pool_slots_and_is_optional() -> None:
    timeline = {"beat_grid": _grid()}
    with_names = attach_beat_grid_ui_values(timeline, pool_slots={4: {5: "Red"}})
    assert _cues(with_names["beat_grid"])[0]["color_preset_name"] == "Red"
    without = attach_beat_grid_ui_values(timeline)
    assert "color_preset_name" not in _cues(without["beat_grid"])[0]
