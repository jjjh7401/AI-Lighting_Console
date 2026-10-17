"""SPEC-LDRHYTHM-001 stage 2 — 「프리셋 계획 만들기」 카드 한 장이 색·위치까지 한 번에 저장한다.

디머뿐이던 승인 카드에 색(t594 의 ``color_preset_outcomes`` 가 만드는 줄과 같은 줄)과 위치(t592 의
조각, 그룹마다 따로)를 함께 싣는다. 콘솔 접촉 0건 — 그룹 소속 · 컬러 채널 · 장비 좌표는 합성 값이고,
카드는 가짜 콘솔(`FakeConsole`)과 가짜 승인으로 돌린다.

세 층: ① 순수 함수(저장 줄 붙이기 · 사유) ② 저장 줄 · 사유 문장 · 참조 갱신 ③ 세션의 승인 카드.
"""

from __future__ import annotations

import copy
from dataclasses import replace

from server.design.beat_grid import LOVE_ATTACK_TITLE, check_evidence_approval
from server.design.beat_grid_color_presets import (
    COLOR_ATTRS_MISSING,
    COLOR_CHANNELS_UNREAD,
    COLOR_MEMBERS_UNREAD,
    attach_color_rgb_to_cues,
    color_preset_outcomes,
    record_color_preset_rgb,
)
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_position_presets import (
    POSITION_COORDS_UNREAD,
    POSITION_GROUP_UNCONFIRMED,
    POSITION_MEMBERS_UNREAD,
    POSITION_UNAIMABLE,
    PointingFrames,
)
from server.design.beat_grid_presets import record_app_preset_label
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    card_reason,
    load_preset_annotations,
    plan_table_markdown,
    save_commands,
    saved_summary,
)
from server.design.preset_plan_store import (
    attach_color_store,
    attach_floor_position_store,
    store_candidates,
)
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import _new_session, _timeline_for_apply
from .test_preset_plan import (
    _ATTRIBUTES,
    _COLOR_CHILDREN,
    _DIMMER_CHILDREN,
    _EXPECTED_SAVE,
    _POSITION_CHILDREN,
    _cue_of,
    _love_attack_grid,
    _love_attack_session,
    _plan,
    _preset,
)

# -- 합성 장비 값 — 실기 리그가 아니다. 합성 좌표(미터)와 컬러 채널 이름만 쓴다. -----------------
_RGB_CHANNELS = ["Main Module#2_ColorRGB_R", "Main Module#2_ColorRGB_G", "Main Module#2_ColorRGB_B"]
_MEMBERS = {
    "WASH-ALL": [101, 102],
    "BACK": [111, 112],
    "MOVER-U": [201, 202],
    "MOVER-D": [211, 212],
}
_CHANNELS = {fid: list(_RGB_CHANNELS) for fid in (101, 102, 111, 112)}
_POSITIONS = {
    101: (0.0, 4.0, 6.0),
    102: (1.0, 4.0, 6.0),
    111: (0.0, 9.0, 6.0),
    112: (1.0, 9.0, 6.0),
    201: (-3.0, 0.0, 6.0),
    202: (3.0, 0.0, 6.0),
    211: (-3.0, 8.0, 6.0),
    212: (3.0, 8.0, 6.0),
}
_FRAMES = PointingFrames(positions=_POSITIONS, rotz={}, rotation_skipped=())

_COLOR_NUMBERS = {"LAVENDER": "4.33", "SKY": "4.34", "PINK": "4.35", "PITCH": "4.36"}
_FLOOR_NUMBERS = {"FLOOR MOVER-U": "2.31", "FLOOR MOVER-D": "2.32"}
_DATE = "2026-10-16T00:00:00+00:00"


def _with_stores(grid=None, *, members=_MEMBERS, channels=_CHANNELS, frames=_FRAMES):
    """계획을 세우고 색·위치 저장 줄을 붙인다(세션이 하는 순서 그대로)."""
    grid = grid if grid is not None else _love_attack_grid()
    plan = _plan(grid)
    plan = attach_color_store(plan, grid, members=members, channel_names=channels)
    plan = attach_floor_position_store(plan, grid, members=members, frames=frames)
    return grid, plan


def _plan_with(**annotation_overrides):
    """LOVE ATTACK 주석에 줄 몇 개를 바꿔 끼운 계획 — 주석 모양이 다른 경우를 잰다."""
    grid = _love_attack_grid()
    plan = build_preset_plan(
        grid,
        annotations={**load_preset_annotations(LOVE_ATTACK_TITLE), **annotation_overrides},
        policy=load_preset_pool_policy(),
        dimmer_pool=(1, _DIMMER_CHILDREN),
        color_pool=(4, _COLOR_CHILDREN),
        position_pool=(2, _POSITION_CHILDREN),
        dimmer_attributes=_ATTRIBUTES,
    )
    return grid, plan


def _approve(grid, plan, **kwargs):
    return apply_plan_references(
        grid, plan, by="supervisor", date=_DATE, source="fake-approval", **kwargs
    )


# == ① 색 저장 줄 ================================================================


class TestColorStore:
    def test_lavender_store_is_exactly_the_t594_bundle(self) -> None:
        _grid, plan = _with_stores()
        lavender = _preset(plan, "LAVENDER")
        assert lavender.ready is True
        assert lavender.deferred is False
        assert lavender.hold is None
        assert lavender.store == (
            "ClearAll",
            "Group 10 ; Attribute 'ColorRGB_R' At 55 ; Attribute 'ColorRGB_G' At 35"
            " ; Attribute 'ColorRGB_B' At 100",
            "Store Preset 4.33",
            "Label Preset 4.33 'LAVENDER'",
            "ClearAll",
        )

    def test_the_bundle_equals_what_the_t594_path_makes_for_the_same_grid(self) -> None:
        # 같은 상태(칸이 번호를 가리키고 RGB·이름이 적힌 격자)를 기존 색 경로에 직접 주면
        # 같은 줄이 나온다.
        grid = _love_attack_grid()
        for bar in (7, 14):
            _cue_of(grid, "WASH-ALL", bar)["color_preset_no"] = "4.33"
        grid = record_color_preset_rgb(grid, "4.33", (55, 35, 100))
        grid = record_app_preset_label(grid, "4.33", "LAVENDER")
        expected, hold = color_preset_outcomes(
            grid, ["4.33"], members=_MEMBERS, channel_names=_CHANNELS
        )["4.33"]
        assert hold is None

        _grid, plan = _with_stores()
        assert _preset(plan, "LAVENDER").store == expected

    def test_each_color_is_stored_on_the_group_of_its_own_cells(self) -> None:
        _grid, plan = _with_stores()
        first_line = {
            name: _preset(plan, name).store[1].partition(" ;")[0] for name in _COLOR_NUMBERS
        }
        # 라벤더·핑크·피치는 워시(그룹 10), 하늘은 역광(그룹 4)이다.
        assert first_line == {
            "LAVENDER": "Group 10",
            "SKY": "Group 4",
            "PINK": "Group 10",
            "PITCH": "Group 10",
        }
        for name, number in _COLOR_NUMBERS.items():
            assert f"Store Preset {number}" in _preset(plan, name).store

    def test_channels_without_colorrgb_hold_every_color_as_undecided(self) -> None:
        cmy = {fid: ["Cyan", "Magenta", "Yellow"] for fid in (101, 102, 111, 112)}
        _grid, plan = _with_stores(channels=cmy)

        for name in _COLOR_NUMBERS:
            preset = _preset(plan, name)
            assert preset.ready is False
            assert preset.store is None
            assert preset.deferred is False  # 이 카드 밖이 아니라 「미정」이다
            assert COLOR_ATTRS_MISSING in (preset.hold or "")
        assert not any(line.startswith("LAVENDER") for line in plan.deferred)
        assert any(
            line.startswith("LAVENDER") and COLOR_ATTRS_MISSING in line for line in plan.unresolved
        )
        assert "ColorRGB" not in "\n".join(save_commands(plan))
        # 컬러 채널은 색만 막는다 — 같은 카드의 위치는 그대로 저장된다.
        assert saved_summary(plan) == "프리셋 7개(디머 5 · 위치 2)"

    def test_unread_channel_names_and_unread_members_hold_with_the_t594_reasons(self) -> None:
        _grid, unread = _with_stores(channels={})
        assert COLOR_CHANNELS_UNREAD in (_preset(unread, "LAVENDER").hold or "")

        _grid, no_members = _with_stores(members={})
        assert _preset(no_members, "LAVENDER").hold == COLOR_MEMBERS_UNREAD
        assert _preset(no_members, "LAVENDER").store is None

    def test_planning_never_mutates_the_real_grid(self) -> None:
        grid = _love_attack_grid()
        before = copy.deepcopy(grid)
        _with_stores(grid)
        assert grid == before

    def test_a_cell_that_already_has_a_color_number_is_never_overwritten(self) -> None:
        grid = _love_attack_grid()
        _cue_of(grid, "WASH-ALL", 14)["color_preset_no"] = "4.5"
        _grid, plan = _with_stores(grid)

        # 번호가 있는 칸만 후보에서 빠지고, 나머지 칸은 저장된다(리드 지시 2026-10-16). 한 칸
        # 때문에 후보 전체를 보류하면 같은 후보의 다른 칸이 전부 번호 없이 남는다.
        lavender = _preset(plan, "LAVENDER")
        assert lavender.ready is True
        assert ("WASH-ALL", 14) not in {(c.group_name, c.bar) for c in lavender.cells}
        assert "Store Preset 4.33" in "\n".join(save_commands(plan))
        approved = _approve(grid, plan)
        assert _cue_of(approved, "WASH-ALL", 14)["color_preset_no"] == "4.5"
        assert _cue_of(approved, "WASH-ALL", 7)["color_preset_no"] == "4.33"

    def test_a_color_spread_over_two_groups_is_one_preset_with_one_multi_group_selection(
        self,
    ) -> None:
        # 2차 전체 실행 E-08 — 같은 RGB 를 그룹마다 따로 저장하지 않는다. 두 그룹을 한 선택
        # (``Group a + b``)으로 한 번 저장한다(디머 저장이 실기로 쓴 꼴).
        spread = {
            "name": "라벤더",
            "console_name": "LAVENDER",
            "rgb": None,
            "cells": [{"group_name": "WASH-ALL", "bar": 7}, {"group_name": "BACK", "bar": 7}],
        }
        grid, plan = _plan_with(colors=[spread])
        plan = attach_color_store(plan, grid, members=_MEMBERS, channel_names=_CHANNELS)

        lavender = _preset(plan, "LAVENDER")
        assert lavender.ready is True and lavender.store is not None
        assert set(lavender.groups) == {"WASH-ALL", "BACK"}
        selections = [line for line in lavender.store if "ColorRGB_R" in line]
        assert len(selections) == 1
        assert selections[0].startswith("Group ") and " + " in selections[0].split(" ; ")[0]


# == ① 위치 저장 줄 ==============================================================


class TestPositionStore:
    def test_floor_splits_into_one_preset_per_group(self) -> None:
        plan = _plan()
        positions = [preset for preset in plan.presets if preset.kind == "position"]

        assert [preset.name for preset in positions] == list(_FLOOR_NUMBERS)
        assert [preset.slot for preset in positions] == list(_FLOOR_NUMBERS.values())
        assert [preset.groups for preset in positions] == [("MOVER-U",), ("MOVER-D",)]
        assert [[(c.group_name, c.bar) for c in p.cells] for p in positions] == [
            [("MOVER-U", 0)],
            [("MOVER-D", 0)],
        ]

    def test_each_group_is_stored_as_its_own_preset(self) -> None:
        _grid, plan = _with_stores()
        up = _preset(plan, "FLOOR MOVER-U")
        down = _preset(plan, "FLOOR MOVER-D")

        assert up.ready is True and down.ready is True
        # 줄마다 자기 그룹의 장비만 조준하고, 번호·이름도 줄마다 따로다.
        assert [line.split(" ;")[0] for line in up.store[:-3]] == ["Fixture 201", "Fixture 202"]
        assert up.store[-3:] == (
            "Store Preset 2.31",
            "Label Preset 2.31 'FLOOR MOVER-U'",
            "ClearAll",
        )
        assert [line.split(" ;")[0] for line in down.store[:-3]] == ["Fixture 211", "Fixture 212"]
        assert down.store[-3:] == (
            "Store Preset 2.32",
            "Label Preset 2.32 'FLOOR MOVER-D'",
            "ClearAll",
        )

    def test_the_aim_target_is_the_fixture_x_the_mean_y_of_every_fixture_and_the_floor(
        self,
    ) -> None:
        # 합성 장비 셋: y 평균은 (0 + 3 + 6) / 3 = 3.0. MOVER-U 는 1·2 번만 쥐고 3 번은
        # 평균에만 든다.
        frames = PointingFrames(
            positions={1: (-2.0, 0.0, 6.0), 2: (0.0, 3.0, 6.0), 3: (2.0, 6.0, 6.0)},
            rotz={},
            rotation_skipped=(),
        )
        grid = _love_attack_grid()
        plan = attach_floor_position_store(
            _plan(grid), grid, members={"MOVER-U": [1, 2], "MOVER-D": [3]}, frames=frames
        )

        up = _preset(plan, "FLOOR MOVER-U")
        # 1 번: 목표 (-2, 3, 0) → 앞(+y)으로 3 m, 아래로 6 m → 기울기 atan(3/6) = 26.6 도.
        # (그룹 안 평균 1.5 를 썼다면 14.0 도다 — 평균이 리그 전체 값이라는 증거.)
        assert up.store[0] == "Fixture 1 ; Attribute 'Pan' At 0 ; Attribute 'Tilt' At 26.6"
        # 2 번은 y 가 cy 와 같고 x 도 같아서 목표가 바로 아래다.
        assert up.store[1] == "Fixture 2 ; Attribute 'Pan' At 0 ; Attribute 'Tilt' At 0"
        down = _preset(plan, "FLOOR MOVER-D")
        # 3 번은 cy 보다 뒤(+y)에 있어 -y 쪽(Pan 180)으로 기울인다.
        assert down.store[0] == "Fixture 3 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 26.6"

    def test_a_rotation_skipped_fixture_holds_only_its_own_group(self) -> None:
        frames = replace(_FRAMES, rotation_skipped=(201,))
        _grid, plan = _with_stores(frames=frames)

        up = _preset(plan, "FLOOR MOVER-U")
        assert up.ready is False
        assert up.store is None
        assert up.hold == f"{POSITION_UNAIMABLE}(FID 201)"
        assert _preset(plan, "FLOOR MOVER-D").ready is True  # 다른 그룹은 그대로 간다
        assert any(line.startswith("FLOOR MOVER-U") for line in plan.unresolved)
        assert not any(line.startswith("FLOOR MOVER-U") for line in plan.deferred)

    def test_unread_members_or_coordinates_hold_with_the_t592_reasons(self) -> None:
        _grid, no_frames = _with_stores(frames=None)
        assert _preset(no_frames, "FLOOR MOVER-U").hold == POSITION_COORDS_UNREAD

        _grid, no_members = _with_stores(members={})
        assert _preset(no_members, "FLOOR MOVER-U").hold == POSITION_MEMBERS_UNREAD

        partial = PointingFrames(
            positions={fid: p for fid, p in _POSITIONS.items() if fid != 202},
            rotz={},
            rotation_skipped=(),
        )
        _grid, missing = _with_stores(frames=partial)
        assert _preset(missing, "FLOOR MOVER-U").hold == POSITION_COORDS_UNREAD
        assert _preset(missing, "FLOOR MOVER-D").ready is True

    def test_a_group_with_an_unconfirmed_number_holds_with_the_t592_reason(self) -> None:
        grid = _love_attack_grid()
        for track in grid["tracks"]:
            if track["group_name"] == "MOVER-U":
                track["group_no_confirmed"] = False
        _grid, plan = _with_stores(grid)

        assert _preset(plan, "FLOOR MOVER-U").hold == POSITION_GROUP_UNCONFIRMED
        assert _preset(plan, "FLOOR MOVER-U").ready is False
        assert _preset(plan, "FLOOR MOVER-D").ready is True

    def test_the_approximate_target_is_marked_for_the_supervisor_once_per_group(self) -> None:
        _grid, plan = _with_stores()
        notes = [fix for fix in plan.supervisor_fixes if "바닥점 대략값" in fix]

        assert len(notes) == 2
        for name in _FLOOR_NUMBERS:
            assert any(fix.startswith(name) and "감독이 고칠 값" in fix for fix in notes)

    def test_a_held_group_gets_no_supervisor_note(self) -> None:
        _grid, plan = _with_stores(frames=None)
        assert not any("바닥점 대략값" in fix for fix in plan.supervisor_fixes)

    def test_a_cell_that_already_has_a_position_number_is_never_overwritten(self) -> None:
        grid = _love_attack_grid()
        _cue_of(grid, "MOVER-U", 0)["position_preset_no"] = "2.1"
        _grid, plan = _with_stores(grid)

        assert _preset(plan, "FLOOR MOVER-U").ready is False
        assert "MOVER-U 0마디" in (_preset(plan, "FLOOR MOVER-U").hold or "")
        assert _preset(plan, "FLOOR MOVER-D").ready is True
        approved = _approve(grid, plan)
        assert _cue_of(approved, "MOVER-U", 0)["position_preset_no"] == "2.1"

    def test_cells_of_one_group_share_one_position_preset(self) -> None:
        sweep = {
            "name": "바닥 쪽",
            "console_name": "FLOOR",
            "target": "무대 중앙 깊이 바닥 (장비 x 유지 · y=cy · z=0)",
            "cells": [{"group_name": "MOVER-U", "bar": 0}, {"group_name": "MOVER-U", "bar": 7}],
        }
        grid, plan = _plan_with(directions=[sweep])
        plan = attach_floor_position_store(plan, grid, members=_MEMBERS, frames=_FRAMES)

        positions = [preset for preset in plan.presets if preset.kind == "position"]
        assert [preset.name for preset in positions] == ["FLOOR MOVER-U"]  # 그룹 하나 = 줄 하나
        assert len(positions[0].cells) == 2 and positions[0].ready is True
        approved = _approve(grid, plan)
        assert _cue_of(approved, "MOVER-U", 0)["position_preset_no"] == "2.31"
        assert _cue_of(approved, "MOVER-U", 7)["position_preset_no"] == "2.31"

    def test_a_direction_without_a_target_is_never_a_store_candidate(self) -> None:
        targetless = {
            "name": "정면",
            "console_name": "FRONT",
            "target": "",
            "cells": [{"group_name": "MOVER-U", "bar": 0}],
        }
        grid, plan = _plan_with(directions=[targetless])
        assert store_candidates(plan, "position") == ()

        plan = attach_floor_position_store(plan, grid, members=_MEMBERS, frames=_FRAMES)
        front = _preset(plan, "FRONT MOVER-U")
        assert front.ready is False and front.deferred is False
        assert "목표 좌표 미정" in (front.hold or "")
        assert "Store Preset 2." not in "\n".join(save_commands(plan))


# == ② 저장 줄 · 사유 · 계획표 ====================================================


class TestSaveCommandsAndReason:
    def test_dimmer_lines_stay_first_and_unchanged_then_colors_then_positions(self) -> None:
        _grid, plan = _with_stores()
        lines = save_commands(plan)

        assert lines[: len(_EXPECTED_SAVE)] == _EXPECTED_SAVE
        stores = [line for line in lines[len(_EXPECTED_SAVE) :] if line.startswith("Store Preset")]
        assert stores == [
            f"Store Preset {n}" for n in (*_COLOR_NUMBERS.values(), *_FLOOR_NUMBERS.values())
        ]
        # 묶음 사이에 ClearAll 이 겹쳐 나오지 않는다.
        assert not any(a == b == "ClearAll" for a, b in zip(lines, lines[1:], strict=False))
        assert lines[-1] == "ClearAll"

    def test_a_plan_without_dimmers_still_opens_with_one_clearall(self) -> None:
        _grid, plan = _with_stores()
        colors_only = replace(plan, presets=tuple(p for p in plan.presets if p.kind == "color"))
        positions_only = replace(
            plan, presets=tuple(p for p in plan.presets if p.kind == "position")
        )

        lines = save_commands(colors_only)
        assert lines[0] == "ClearAll"
        assert lines[1].startswith("Group 10 ; Attribute 'ColorRGB_R'")
        lines = save_commands(positions_only)
        assert lines[0] == "ClearAll"
        assert lines[1].startswith("Fixture 201 ; Attribute 'Pan'")

    def test_ready_without_a_store_line_is_not_saved_or_counted(self) -> None:
        plan = _plan()
        lavender = _preset(plan, "LAVENDER")
        bare = replace(
            plan,
            presets=tuple(replace(p, ready=True) if p is lavender else p for p in plan.presets),
        )

        assert save_commands(bare) == _EXPECTED_SAVE
        assert saved_summary(bare) == "프리셋 5개(디머 5)"

    def test_the_card_reason_counts_the_saved_presets_by_kind(self) -> None:
        _grid, plan = _with_stores()

        assert saved_summary(plan) == "프리셋 11개(디머 5 · 색 4 · 위치 2)"
        reason = card_reason(plan)
        assert reason.startswith("프리셋 11개(디머 5 · 색 4 · 위치 2) 저장: DIM-40(40%)")
        assert "LAVENDER(RGB 55 35 100)" in reason
        assert "FLOOR MOVER-U(" in reason and "FLOOR MOVER-D(" in reason

    def test_a_saved_color_is_not_listed_as_outside_the_card(self) -> None:
        _grid, plan = _with_stores()
        reason = card_reason(plan)

        # 카드가 저장하는 색·위치는 「이 카드 밖」에도 「미정」에도 적히지 않는다.
        assert "이 카드 밖" not in reason
        assert plan.deferred == ()
        for name in (*_COLOR_NUMBERS, *_FLOOR_NUMBERS):
            assert not any(line.startswith(name) for line in plan.unresolved)

    def test_the_plan_table_shows_every_saved_row_and_no_outside_section(self) -> None:
        _grid, plan = _with_stores()
        table = plan_table_markdown(plan)

        assert "| LAVENDER | RGB 55 35 100 | 4.33 | 2 | 저장(이 카드) |" in table
        assert "| FLOOR MOVER-U |" in table and "| 2.31 | 1 | 저장(이 카드) |" in table
        assert "| FLOOR MOVER-D |" in table and "| 2.32 | 1 | 저장(이 카드) |" in table
        assert "**이 카드 밖**" not in table

    def test_store_candidates_are_only_the_waiting_colors_and_positions(self) -> None:
        plan = _plan()
        assert [p.name for p in store_candidates(plan)] == [*_COLOR_NUMBERS, *_FLOOR_NUMBERS]
        assert [p.name for p in store_candidates(plan, "position")] == list(_FLOOR_NUMBERS)

        _grid, resolved = _with_stores()
        assert store_candidates(resolved) == ()


# == ② 승인 뒤 칸 참조 ===========================================================


class TestReferenceUpdate:
    def test_cells_point_at_the_new_numbers_and_the_app_records_rgb_and_labels(self) -> None:
        grid, plan = _with_stores()
        approved = _approve(grid, plan)

        for group, bar, number in (
            ("WASH-ALL", 7, "4.33"),
            ("WASH-ALL", 14, "4.33"),
            ("BACK", 0, "4.34"),
            ("WASH-ALL", 18, "4.35"),
            ("WASH-ALL", 22, "4.36"),
        ):
            assert _cue_of(approved, group, bar)["color_preset_no"] == number
        assert _cue_of(approved, "MOVER-U", 0)["position_preset_no"] == "2.31"
        assert _cue_of(approved, "MOVER-D", 0)["position_preset_no"] == "2.32"
        # 한 번의 승인이 칸의 모든 새 번호를 덮는다(디머 + 색 + 위치).
        for group, bar in (("WASH-ALL", 7), ("BACK", 0), ("MOVER-U", 0), ("MOVER-D", 0)):
            assert check_evidence_approval(_cue_of(approved, group, bar)) is None
        assert approved["preset_colors"] == {
            # 담아 저장한 그룹도 남는다 — 다음 계획의 재사용이 그 그룹만 쓰게(1차 전체 실행).
            "4.33": {"r": 55.0, "g": 35.0, "b": 100.0, "group": "WASH-ALL"},
            "4.34": {"r": 40.0, "g": 65.0, "b": 95.0, "group": "BACK"},
            "4.35": {"r": 100.0, "g": 50.0, "b": 75.0, "group": "WASH-ALL"},
            "4.36": {"r": 100.0, "g": 75.0, "b": 60.0, "group": "WASH-ALL"},
        }
        assert approved["preset_labels"] == {
            "4.33": "LAVENDER",
            "4.34": "SKY",
            "4.35": "PINK",
            "4.36": "PITCH",
            "2.31": "FLOOR MOVER-U",
            "2.32": "FLOOR MOVER-D",
        }

    def test_the_cell_color_is_derived_from_the_recorded_rgb(self) -> None:
        grid, plan = _with_stores()
        shown = attach_color_rgb_to_cues(_approve(grid, plan))

        assert _cue_of(shown, "WASH-ALL", 7)["color_rgb"] == [55.0, 35.0, 100.0]
        assert _cue_of(shown, "BACK", 0)["color_rgb"] == [40.0, 65.0, 95.0]
        assert _cue_of(shown, "WASH-ALL", 22)["color_rgb"] == [100.0, 75.0, 60.0]

    def test_dimmer_references_are_unchanged_by_the_new_edits(self) -> None:
        grid, plan = _with_stores()
        approved = _approve(grid, plan)

        assert _cue_of(approved, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        assert _cue_of(approved, "MOVER-U", 0)["brightness"]["preset_no"] == "1.12"
        # 칸의 기존 승인(t543 proposal #6)의 출처는 지우지 않고 덧붙인다.
        back = _cue_of(approved, "BACK", 7)
        assert "proposal-table.md#6" in back["evidence"]["approval"]["source"]
        assert "fake-approval" in back["evidence"]["approval"]["source"]

    def test_the_input_grid_is_untouched(self) -> None:
        grid, plan = _with_stores()
        before = copy.deepcopy(grid)
        _approve(grid, plan)
        assert grid == before
        assert "preset_colors" not in grid and "preset_labels" not in grid

    def test_a_color_edited_while_the_card_was_open_is_not_repointed(self) -> None:
        planned, plan = _with_stores()
        now = copy.deepcopy(planned)
        _cue_of(now, "WASH-ALL", 14)["color_preset_no"] = "4.5"  # 카드가 떠 있는 사이 감독이 고쳤다

        approved = _approve(now, plan, planned_from=planned)

        assert _cue_of(approved, "WASH-ALL", 14)["color_preset_no"] == "4.5"
        assert _cue_of(approved, "WASH-ALL", 7)["color_preset_no"] == "4.33"
        # 콘솔에는 이 프리셋이 이미 있다 — 값·이름은 칸이 안 바뀌어도 격자에 남는다.
        assert approved["preset_colors"]["4.33"] == {
            "r": 55.0,
            "g": 35.0,
            "b": 100.0,
            "group": "WASH-ALL",
        }

    def test_a_position_edited_while_the_card_was_open_is_not_repointed(self) -> None:
        planned, plan = _with_stores()
        now = copy.deepcopy(planned)
        _cue_of(now, "MOVER-D", 0)["position_preset_no"] = "2.1"

        approved = _approve(now, plan, planned_from=planned)

        assert _cue_of(approved, "MOVER-D", 0)["position_preset_no"] == "2.1"
        assert _cue_of(approved, "MOVER-U", 0)["position_preset_no"] == "2.31"

    def test_running_the_plan_again_stores_nothing_twice(self) -> None:
        grid, plan = _with_stores()
        approved = _approve(grid, plan)

        # 승인된 격자로 계획을 다시 세운다 — 디머 칸은 이미 프리셋을 가리키고, 색·위치 칸은
        # 번호가 있어 덮어쓰지 않는다. 같은 프리셋이 겹으로 생기지 않는다.
        again_grid, again = _with_stores(approved)
        assert save_commands(again) == ()
        assert saved_summary(again) == "프리셋 0개"
        assert _preset(again, "LAVENDER").ready is False
        assert "이미 있는 칸" in (_preset(again, "LAVENDER").hold or "")
        assert again_grid == approved


# == ③ 세션의 승인 카드 (가짜 콘솔) ================================================


def _store_session(tmp_path, monkeypatch, *, decisions, members=_MEMBERS, frames=_FRAMES):
    """디머 카드 세션(test_preset_plan)에 장비 판독 셋을 합성 값으로 채운다(읽기 전용 판독)."""
    session, console, approval, store = _love_attack_session(
        tmp_path, decisions=decisions, monkeypatch=monkeypatch
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_group_members",
        lambda names: {group: list(members[group]) for group in names if group in members},
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_color_channel_names",
        lambda fids: {fid: list(_RGB_CHANNELS) for fid in fids},
    )
    monkeypatch.setattr(session, "_beat_grid_pointing_frames", lambda: frames)
    return session, console, approval, store


class TestApprovalCard:
    def test_the_card_carries_the_color_and_position_store_lines(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, approval, _store = _store_session(
            tmp_path, monkeypatch, decisions=(False,)
        )

        session.beat_grid_preset_plan()

        assert len(approval.requests) == 1  # 카드는 한 장이다
        card = list(approval.requests[0].commands)
        assert card[: len(_EXPECTED_SAVE)] == list(_EXPECTED_SAVE)  # 디머 줄은 그대로
        for number in (*_COLOR_NUMBERS.values(), *_FLOOR_NUMBERS.values()):
            assert f"Store Preset {number}" in card
        assert "Label Preset 4.33 'LAVENDER'" in card
        assert "Label Preset 2.31 'FLOOR MOVER-U'" in card
        assert any(line.startswith("Store Preset 4.") for line in card)
        assert any(line.startswith("Store Preset 2.") for line in card)

    def test_a_rejected_card_sends_nothing_and_keeps_every_cell(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, approval, store = _store_session(
            tmp_path, monkeypatch, decisions=(False,)
        )
        before = copy.deepcopy(store.latest["beat_grid"])

        event = session.beat_grid_preset_plan()

        assert len(approval.requests) == 1
        assert console.executed == []
        assert store.latest["beat_grid"] == before
        assert event["ok"] is False

    def test_an_approved_card_sends_the_same_lines_and_repoints_the_cells(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, approval, store = _store_session(tmp_path, monkeypatch, decisions=(True,))

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        card = list(approval.requests[0].commands)
        assert console.executed == card  # 카드에 보인 줄이 그대로 나갔다
        for number in (*_COLOR_NUMBERS.values(), *_FLOOR_NUMBERS.values()):
            assert f"Store Preset {number}" in console.executed
        assert "프리셋 11개(디머 5 · 색 4 · 위치 2)" in event["reason"]

        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["color_preset_no"] == "4.33"
        assert _cue_of(grid, "WASH-ALL", 14)["color_preset_no"] == "4.33"
        assert _cue_of(grid, "BACK", 0)["color_preset_no"] == "4.34"
        assert _cue_of(grid, "WASH-ALL", 18)["color_preset_no"] == "4.35"
        assert _cue_of(grid, "WASH-ALL", 22)["color_preset_no"] == "4.36"
        assert _cue_of(grid, "MOVER-U", 0)["position_preset_no"] == "2.31"
        assert _cue_of(grid, "MOVER-D", 0)["position_preset_no"] == "2.32"
        assert grid["preset_labels"]["4.33"] == "LAVENDER"
        assert grid["preset_colors"]["4.34"] == {"r": 40.0, "g": 65.0, "b": 95.0, "group": "BACK"}
        for group, bar in (("WASH-ALL", 7), ("BACK", 0), ("MOVER-U", 0), ("MOVER-D", 0)):
            assert check_evidence_approval(_cue_of(grid, group, bar)) is None

    def test_the_card_reason_names_the_kinds_and_leaves_nothing_outside(
        self, tmp_path, monkeypatch
    ) -> None:
        session, _console, approval, _store = _store_session(
            tmp_path, monkeypatch, decisions=(False,)
        )
        session.beat_grid_preset_plan()

        reasons = {r for item in approval.requests[0].items for r in item.risk_reasons}
        (declared,) = [r for r in reasons if r.startswith("연출 프리셋 저장 — ")]
        assert declared.startswith(
            "연출 프리셋 저장 — 프리셋 11개(디머 5 · 색 4 · 위치 2) 저장: DIM-40(40%)"
        )
        assert "이 카드 밖" not in declared

    def test_an_unreadable_rig_still_saves_the_dimmers_and_lists_the_rest_as_undecided(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, approval, store = _store_session(
            tmp_path, monkeypatch, decisions=(True,), members={}, frames=None
        )

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert console.executed == list(_EXPECTED_SAVE)  # 디머뿐이다
        card = list(approval.requests[0].commands)
        assert not any(line.startswith(("Store Preset 4.", "Store Preset 2.")) for line in card)
        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["color_preset_no"] is None
        assert _cue_of(grid, "MOVER-U", 0)["position_preset_no"] is None
        assert "프리셋 5개(디머 5)" in event["reason"]
        # 못 저장한 색·위치는 카드 사유의 「미정」에 이유와 함께 적힌다.
        reasons = {r for item in approval.requests[0].items for r in item.risk_reasons}
        (declared,) = [r for r in reasons if r.startswith("연출 프리셋 저장 — ")]
        undecided = declared.partition("미정(이번 계획에서 제외): ")[2]
        assert f"LAVENDER RGB 55 35 100(칸 2개, 후보 4.33): {COLOR_MEMBERS_UNREAD}" in undecided
        assert "FLOOR MOVER-U 바닥 쪽 (대략: 무대 중앙 깊이 바닥" in undecided
        assert f"(칸 1개, 후보 2.31): {POSITION_MEMBERS_UNREAD}" in undecided

    def test_unreadable_pools_leave_no_candidate_so_the_rig_is_never_read(
        self, tmp_path, monkeypatch
    ) -> None:
        store = SongTimelineStore()
        store.latest = _timeline_for_apply(beat_grid=_love_attack_grid())
        sent: list[dict] = []
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,), state_tree={}, sent=sent
        )
        monkeypatch.setattr(session, "_beat_grid_preset_dimmer_attributes", lambda names: {})

        def _forbidden(*args, **kwargs):
            raise AssertionError("저장 후보가 없으면 장비를 읽지 않는다")

        for name in (
            "_beat_grid_group_members",
            "_beat_grid_color_channel_names",
            "_beat_grid_pointing_frames",
        ):
            monkeypatch.setattr(session, name, _forbidden)

        event = session.beat_grid_preset_plan()

        assert event["ok"] is False
        assert approval.requests == [] and console.executed == []
        (table,) = [e["text"] for e in sent if e.get("summary") == "연출 프리셋 계획"]
        # 풀을 못 읽은 색·위치는 「이 카드 밖」이 아니라 「미정」이고, 사유가 풀 판독이다.
        assert "**이 카드 밖**" not in table
        assert "LAVENDER RGB 55 35 100(칸 2개, 후보 없음): 색 풀을 콘솔에서 읽지 못해" in table
        assert "위치 풀을 콘솔에서 읽지 못해" in table
