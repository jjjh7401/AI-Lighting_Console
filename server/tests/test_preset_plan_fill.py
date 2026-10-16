"""SPEC-LDRHYTHM-001 stage 2 — 미정 6건 채우기: 기본값 · 「감독이 고칠 값」 · 승인 카드 사유.

계획 함수는 순수 함수다(콘솔 무접촉). 픽스처는 기존 계획 테스트(test_preset_plan)와 같다.
"""

from __future__ import annotations

from server.design.color_names import resolve_color_name
from server.design.preset_plan import card_reason, save_commands

from .test_preset_plan import _love_attack_grid, _plan, _preset


class TestMultiGroupDimmer:
    def test_dim_100_is_one_ready_preset_over_five_groups(self) -> None:
        preset = _preset(_plan(), "DIM-100")
        assert preset.ready is True
        assert preset.hold is None
        assert preset.group_nos == (4, 7, 11, 12, 14)
        assert preset.group_no is None
        assert preset.groups == ("BACK", "SIDE-ALL", "MOVER-U", "MOVER-D", "BLIND")

    def test_dim_100_saves_as_one_multi_group_selection(self) -> None:
        lines = save_commands(_plan())
        assert "Group 4 + 7 + 11 + 12 + 14 ; Attribute 'Dimmer' At 100" in lines
        assert "Store Preset 1.12" in lines
        assert "Label Preset 1.12 'DIM-100'" in lines

    def test_a_group_without_a_confirmed_number_holds_dim_100(self) -> None:
        grid = _love_attack_grid()
        for track in grid["tracks"]:
            if track["group_name"] == "BLIND":
                track["group_no_confirmed"] = False
        preset = _preset(_plan(grid), "DIM-100")
        assert preset.ready is False
        assert "그룹 번호가 확인되지 않음: BLIND" in (preset.hold or "")

    def test_the_multi_group_rule_is_marked_for_the_supervisor(self) -> None:
        fixes = "\n".join(_plan().supervisor_fixes)
        assert "DIM-100 다중 그룹 저장" in fixes
        assert "Group 4 + 7 + 11 + 12 + 14" in fixes
        assert "감독이 고칠 값" in fixes


class TestDefaultDimmerAttribute:
    def test_default_attribute_is_used_and_marked_when_the_read_is_empty(self) -> None:
        plan = _plan(attributes={})
        dimmer_40 = _preset(plan, "DIM-40")
        assert dimmer_40.ready is True
        assert dimmer_40.attributes == ("Dimmer",)
        assert any("기본 'Dimmer'" in fix for fix in plan.supervisor_fixes)
        assert "Group 10 ; Attribute 'Dimmer' At 40" in save_commands(plan)

    def test_read_attributes_are_not_marked_as_defaults(self) -> None:
        plan = _plan()
        assert not any("기본 'Dimmer'" in fix for fix in plan.supervisor_fixes)


class TestColorAndPositionStayOnTheirOwnPaths:
    def test_lavender_keeps_the_palette_rgb_marked_and_out_of_this_card(self) -> None:
        plan = _plan()
        preset = _preset(plan, "LAVENDER")
        assert preset.value == "RGB 55 35 100"
        assert preset.ready is False
        assert preset.deferred is True
        assert any("LAVENDER RGB 55 35 100" in fix for fix in plan.supervisor_fixes)
        assert any(
            line.startswith("LAVENDER") and "이 카드 범위 밖" in line for line in plan.deferred
        )
        assert not any("LAVENDER" in line for line in plan.unresolved)

    def test_floor_keeps_its_approximate_target_marked_and_out_of_this_card(self) -> None:
        plan = _plan()
        preset = _preset(plan, "FLOOR")
        assert "무대 중앙 깊이 바닥" in preset.value
        assert preset.deferred is True
        assert any("바닥 쪽 목표" in fix for fix in plan.supervisor_fixes)
        assert any(line.startswith("FLOOR") for line in plan.deferred)
        assert not any("FLOOR" in line for line in plan.unresolved)

    def test_color_table_resolves_lavender_to_the_palette_slot(self) -> None:
        assert resolve_color_name("라벤더") == (55, 35, 100)
        assert resolve_color_name("퍼플") == (55, 35, 100)


class TestCardReason:
    def test_card_reason_shows_saved_deferred_undecided_and_supervisor_marks(self) -> None:
        reason = card_reason(_plan())
        assert reason.startswith("디머 프리셋 5개 저장")
        assert "DIM-100(100%)" in reason
        assert "이 카드 밖(저장 안 함):" in reason
        assert "미정(이번 계획에서 제외):" in reason
        assert "감독이 고칠 값:" in reason

    def test_excluded_relative_moves_and_scene_memos_keep_their_reasons(self) -> None:
        reason = card_reason(_plan())
        assert "5마디 1박 위치 한 칸 올림" in reason
        assert "11마디 1박 새 자리" in reason
        assert "SCENE 메모 0마디" in reason
        # 리드 결정 2026-10-16 — 색 메모 18·22마디는 WASH-ALL 칸으로 옮겨져 카드 사유에서 빠졌다.
        assert "SCENE 메모 18마디" not in reason
        assert "이번 계획에서 제외" in reason

    def test_unconfirmed_preset_pool_is_a_supervisor_mark_not_a_silent_line(self) -> None:
        plan = _plan()
        assert any("confirmed: false" in fix for fix in plan.supervisor_fixes)
        assert not any("confirmed: false" in line for line in plan.unresolved)
