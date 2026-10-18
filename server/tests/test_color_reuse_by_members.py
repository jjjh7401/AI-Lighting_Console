"""SPEC-LDRHYTHM-001 WT-back-side-dark ③ — 같은 색을 그룹 이름이 아니라 소속 장비로 재사용한다.

새 곡 2차 점검(2026-10-18, 「FRESH TEST 1018-2」): 콘솔에 LAVENDER 4.157(``Group 10 + 7 + 11 + 12``
= WASH-ALL·SIDE-ALL·MOVER-U·MOVER-D 로 저장)이 있었는데, 줄이 SIDE-L·SIDE-R·WASH-U·WASH-D 로
나뉘자 같은 RGB 를 4.162 에 다시 저장했다(4.162~4.165, 감사로그). 재사용 판정이 기록된 그룹
**이름**에 이 그룹 이름이 있는지만 봤기 때문이다.

실기 그룹 소속(응답기 SELECTIONDATA 전수 판독, 2026-10-18): SIDE-L 6대·SIDE-R 6대는 SIDE-ALL
12대에, WASH-U 10대·WASH-D 10대는 WASH-ALL 20대에 그대로 들어 있다. 이 번호들은 그 판독의
sf_index 를 줄여 쓴 시험 입력이다. 콘솔 접촉 0건.
"""

from __future__ import annotations

from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import _reusable_color_slot, build_preset_plan, save_commands
from server.web.session import _recorded_color_groups

_LAVENDER = (55, 35, 100)
_RECORDS = {
    "preset_colors": {
        "4.157": {
            "r": 55,
            "g": 35,
            "b": 100,
            "groups": ["WASH-ALL", "SIDE-ALL", "MOVER-U", "MOVER-D"],
        }
    },
    "preset_labels": {"4.157": "LAVENDER"},
}
_POOL = (4, {157: "LAVENDER#5"})
_MEMBERS = {
    "SIDE-L": [94, 96, 98],
    "SIDE-R": [106, 108, 110],
    "SIDE-ALL": [94, 96, 98, 106, 108, 110],
    "WASH-U": [118, 119],
    "WASH-D": [128, 129],
    "WASH-ALL": [118, 119, 128, 129],
    "MOVER-U": [30, 31],
    "MOVER-D": [38, 42],
}


def _grid(tracks=("SIDE-L",)) -> dict:
    return {
        **_RECORDS,
        "tracks": [
            {
                "group_name": name,
                "group_no": 5 + index,
                "group_no_confirmed": True,
                "cues": [{"bar": 1, "planned_color": list(_LAVENDER)}],
            }
            for index, name in enumerate(tracks)
        ],
    }


def test_a_split_group_reuses_the_color_its_parent_group_stored() -> None:
    slot = _reusable_color_slot(_grid(), _POOL, _LAVENDER, "SIDE-L", members=_MEMBERS)
    assert slot == "4.157"


def test_without_member_reads_the_name_rule_still_holds() -> None:
    assert _reusable_color_slot(_grid(), _POOL, _LAVENDER, "SIDE-L") is None


def test_a_group_with_a_fixture_outside_the_stored_groups_is_not_reused() -> None:
    members = {**_MEMBERS, "SIDE-L": [94, 96, 98, 999]}
    assert _reusable_color_slot(_grid(), _POOL, _LAVENDER, "SIDE-L", members=members) is None


def test_an_unread_stored_group_does_not_count_as_covering() -> None:
    members = {name: fids for name, fids in _MEMBERS.items() if name != "SIDE-ALL"}
    assert _reusable_color_slot(_grid(), _POOL, _LAVENDER, "SIDE-L", members=members) is None


def test_an_unread_group_is_not_reused_by_members() -> None:
    members = {name: fids for name, fids in _MEMBERS.items() if name != "SIDE-L"}
    assert _reusable_color_slot(_grid(), _POOL, _LAVENDER, "SIDE-L", members=members) is None


def test_the_plan_reuses_4_157_for_the_split_lines_and_stores_nothing() -> None:
    grid = _grid(("SIDE-L", "SIDE-R", "WASH-U", "WASH-D"))
    plan = build_preset_plan(
        grid,
        annotations={},
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_POOL,
        position_pool=None,
        dimmer_attributes={},
        group_members=_MEMBERS,
    )
    colors = [p for p in plan.presets if p.kind == "color"]
    assert [(p.slot, p.reused, set(p.groups)) for p in colors] == [
        ("4.157", True, {"SIDE-L", "SIDE-R", "WASH-U", "WASH-D"})
    ]
    assert not [line for line in save_commands(plan) if "Store Preset 4." in line]


def test_the_session_reads_the_groups_named_in_the_color_records() -> None:
    grid = {"preset_colors": {**_RECORDS["preset_colors"], "4.120": {"r": 1, "g": 2, "b": 3}}}
    assert _recorded_color_groups(grid) == {"WASH-ALL", "SIDE-ALL", "MOVER-U", "MOVER-D"}
    assert _recorded_color_groups({}) == set()
