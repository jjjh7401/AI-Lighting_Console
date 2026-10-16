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

#: 주석이 적은 색 줄 네 개 — 라벤더(칸 있음), 하늘·핑크·피치(칸 미정 자리표시).
_EXPECTED_COLOR_NAMES = {"LAVENDER", "SKY", "PINK", "PITCH"}


def _plan():
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
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


def test_only_lavender_has_a_grid_cell_for_now():
    """칸이 붙은 색은 지금 라벤더뿐이다. 나머지는 SCENE 메모라 칸 배정 결정을 기다린다."""
    placed = {preset.name for preset in _colors(_plan()) if preset.cells}

    assert placed == {"LAVENDER"}, placed


def test_colors_without_a_cell_keep_no_slot_and_say_why():
    """칸 미정인 색은 번호를 잡지 않고, 보류 사유에 「칸 미정」을 적는다."""
    unplaced = [preset for preset in _colors(_plan()) if not preset.cells]

    assert {preset.name for preset in unplaced} == {"SKY", "PINK", "PITCH"}
    for preset in unplaced:
        assert preset.slot is None, preset.name
        assert "칸 미정" in (preset.hold or ""), preset.name


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
