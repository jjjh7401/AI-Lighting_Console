"""SPEC-LDRHYTHM-001 전체 실행 E-10·I-08 — 콘솔이 「#숫자」를 붙인 디머 프리셋을 재사용한다.

같은 프리셋 계획을 다시 요청하면 이미 저장한 DIM-100(콘솔 이름 'DIM-100#5')이 있는데도 새
번호에 또 저장했다(콘솔 이름 'DIM-100#6'). 디머에는 재사용 단계가 없었다.

재사용 조건: 콘솔 이름이 같고(「#숫자」 허용), 격자의 저장 기록이 같은 값이며 이번에 필요한
속성·그룹을 전부 덮는다. 이름만으로는 내용이 같은지 모르므로 기록이 없으면 재사용하지 않는다.

콘솔 접촉 0건.
"""

from __future__ import annotations

from server.design.preset_plan import apply_plan_references, save_commands

from .test_preset_plan import _DIMMER_CHILDREN, _love_attack_grid, _plan


def _dimmer(plan, percent: int):
    (preset,) = [p for p in plan.presets if p.kind == "dimmer" and p.value_percent == percent]
    return preset


def _stored_once():
    grid = _love_attack_grid()
    first = _plan(grid)
    dim100 = _dimmer(first, 100)
    assert dim100.ready and not dim100.reused
    applied = apply_plan_references(grid, first, by="supervisor", date="2026-10-17", source="t")
    pool_no, slot = (int(part) for part in dim100.slot.split("."))
    return grid, applied, dim100, pool_no, slot


def test_second_plan_reuses_the_dimmer_the_console_renamed_with_a_suffix() -> None:
    grid, applied, dim100, pool_no, slot = _stored_once()
    # 칸은 처음 그대로(밝기 값) 두고, 격자의 저장 기록만 이어받는다.
    regrid = {**grid, "dimmer_presets": applied["dimmer_presets"]}
    console = {**_DIMMER_CHILDREN, slot: "DIM-100#6"}

    second = _plan(regrid, dimmer=(pool_no, console))

    again = _dimmer(second, 100)
    assert again.reused is True
    assert again.slot == dim100.slot
    assert not any(f"Preset {dim100.slot}" in line for line in save_commands(second))


def test_no_record_means_no_reuse_even_with_the_same_name() -> None:
    grid, _applied, dim100, pool_no, slot = _stored_once()
    console = {**_DIMMER_CHILDREN, slot: "DIM-100#6"}

    second = _plan(grid, dimmer=(pool_no, console))

    again = _dimmer(second, 100)
    assert again.reused is False
    assert again.slot != dim100.slot


def test_a_record_that_misses_a_group_is_not_reused() -> None:
    grid, applied, dim100, pool_no, slot = _stored_once()
    record = dict(applied["dimmer_presets"][dim100.slot])
    record["attribute_group_nos"] = [
        [attr, nos[:-1]] for attr, nos in record["attribute_group_nos"]
    ]
    regrid = {**grid, "dimmer_presets": {dim100.slot: record}}
    console = {**_DIMMER_CHILDREN, slot: "DIM-100#6"}

    second = _plan(regrid, dimmer=(pool_no, console))

    assert _dimmer(second, 100).reused is False


def test_another_name_on_the_slot_is_not_reused() -> None:
    grid, applied, dim100, pool_no, slot = _stored_once()
    regrid = {**grid, "dimmer_presets": applied["dimmer_presets"]}
    console = {**_DIMMER_CHILDREN, slot: "DIM-100 OLD"}

    second = _plan(regrid, dimmer=(pool_no, console))

    assert _dimmer(second, 100).reused is False
