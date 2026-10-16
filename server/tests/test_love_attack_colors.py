"""LOVE ATTACK 격자 칸의 색 — 계획표에 색 줄이 나오고, 칸 없는 색은 「칸 미정」으로 드러난다.

색 값은 곡별 주석 파일(``preset_annotations/love_attack.yaml``)에만 산다. 이 시험은 그 값을
코드에 옮기지 않고, 계획이 주석에서 색을 읽어 계획표 줄로 내는지만 잰다. 고른 값은 전부
「감독이 고칠 값」이다.
"""

from __future__ import annotations

import copy

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import (
    build_preset_plan,
    load_preset_annotations,
    plan_table_markdown,
)

#: 색 풀 — 1~10 과 32 가 이미 쓰이고 있다(테스트 픽스처). 나머지 번호는 빈 것으로 본다.
_COLOR_POOL = (4, {**{slot: f"COLOR {slot}" for slot in range(1, 11)}, 32: "COLOR 32"})

#: 주석이 적은 색 줄 네 개 — 라벤더·하늘·핑크·피치. 네 색 모두 칸을 받았다(리드 결정 2026-10-16).
_EXPECTED_COLOR_NAMES = {"LAVENDER", "SKY", "PINK", "PITCH"}

#: 색 → 칸(리드 결정 2026-10-16). 드롭 앞 갈라짐(63마디 L·R)은 격자 밖이라 이번 PR 에 없다.
_EXPECTED_CELLS = {
    "LAVENDER": {("WASH-ALL", 7), ("WASH-ALL", 14)},
    "SKY": {("BACK", 0)},
    "PINK": {("WASH-ALL", 18)},
    "PITCH": {("WASH-ALL", 22)},
}


def _plan(annotations=None):
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    if annotations is None:
        annotations = load_preset_annotations(LOVE_ATTACK_TITLE)
    return build_preset_plan(
        grid,
        annotations=annotations,
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_COLOR_POOL,
        position_pool=None,
        dimmer_attributes={},
    )


def _colors(plan):
    return [preset for preset in plan.presets if preset.kind == "color"]


def test_the_plan_lists_each_color_as_its_own_row_with_distinct_values():
    colors = _colors(_plan())
    names = [preset.name for preset in colors]

    assert len(colors) >= 4, names
    assert set(names) >= _EXPECTED_COLOR_NAMES, names
    values = [preset.value for preset in colors]
    assert len(set(values)) == len(values), f"같은 색이 두 줄이면 안 된다: {values}"


def test_every_color_has_a_grid_cell_and_a_slot():
    colors = {preset.name: preset for preset in _colors(_plan())}

    for name in _EXPECTED_COLOR_NAMES:
        assert colors[name].cells, f"{name} 에 칸이 없다"
        assert colors[name].slot is not None, f"{name} 에 번호가 없다"


def test_color_placement_follows_the_2026_10_16_lead_decision():
    placed = {
        preset.name: {(cell.group_name, cell.bar) for cell in preset.cells}
        for preset in _colors(_plan())
    }

    assert placed == _EXPECTED_CELLS


def test_a_color_without_a_cell_keeps_no_slot_and_says_why():
    """칸 미정 색은 번호를 잡지 않고, 보류 사유에 「칸 미정」을 적는다.

    지금 곡에는 칸 미정 색이 없어서, 가상의 색 줄 하나를 주석에 덧붙여 잰다."""
    annotations = load_preset_annotations(LOVE_ATTACK_TITLE)
    ghost = {
        "name": "가상",
        "console_name": "GHOST",
        "rgb": [1, 2, 3],
        "director_tunable": True,
        "note": "가상",
        "cells": [],
    }
    annotations = {**annotations, "colors": [*annotations["colors"], ghost]}

    unplaced = [preset for preset in _colors(_plan(annotations)) if not preset.cells]

    assert [preset.name for preset in unplaced] == ["GHOST"]
    assert unplaced[0].slot is None
    assert "칸 미정" in (unplaced[0].hold or "")


def test_every_chosen_color_is_marked_for_director_review():
    plan = _plan()

    for preset in _colors(plan):
        marked = [
            fix for fix in plan.supervisor_fixes if preset.name in fix and "감독이 고칠 값" in fix
        ]
        assert marked, f"{preset.name} 이 「감독이 고칠 값」 목록에 없다: {plan.supervisor_fixes}"


def test_every_color_cell_exists_in_the_grid():
    plan = _plan()

    missing = [item for item in plan.unresolved if "주석 칸" in item and "격자에 없음" in item]
    assert missing == [], missing


def test_the_plan_table_shows_each_color_row():
    table = plan_table_markdown(_plan())

    for name in sorted(_EXPECTED_COLOR_NAMES):
        assert name in table, f"계획표에 {name} 줄이 없다"
