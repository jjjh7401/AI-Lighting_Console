"""카드 t469 — 초안의 트래킹·포지션 칸을 콘솔로 보낸다 (SPEC-LDDESIGN-001).

명령 형태는 실기 실측에서 가져왔다(`.moai/reports/t469/verdict.md`):

* Release — ``Set Cue <n> Sequence <s> Property 'Release' 1|0`` (되읽기 true/false,
  가짜 값은 ``Illegal value``)
* Block — ``Block Sequence <s> Cue <n>`` / ``Unblock …`` (t459, 트래킹 시트 색)
* Cue Only — ``Store … /Merge /CueOnly`` (다음 큐 팬이 자홍 → 청록, 캡처)
* 포지션 — ``<선택> ; At Preset 2.<n>`` 뒤 ``Store … /Merge`` (Q6 2.2·Q9 2.5 캡처)

MIB 모드·페이저는 계속 보내지 않는다(사유만 바뀜).
"""

from __future__ import annotations

import copy

import pytest

from server.design.cue_sheet_apply import (
    UNSOURCED_FIELD_REASONS,
    plan_console_apply,
    plan_cue_console_apply,
)


def _timeline() -> dict:
    return {
        "song_title": "Sugar",
        "sequence_number": 210,
        "layer_mapping": [
            {"role": "key", "group_no": 11, "group_name": "KEY"},
            {"role": "back", "group_no": 12, "group_name": "BACK"},
        ],
        "sections": [
            {
                "index": 1,
                "label": "INTRO",
                "cue_number": 10,
                "start_ms": 0,
                "d_level": 3,
                "intensity": [{"group": "KEY", "level": 55}],
                "fixture_groups": ["KEY"],
            },
            {
                "index": 2,
                "label": "VERSE1",
                "cue_number": 20,
                "start_ms": 8_000,
                "d_level": 4,
                "intensity": [{"group": "KEY", "level": 70}],
                "fixture_groups": ["KEY"],
            },
        ],
    }


def _plan_with(base_fields: dict, new_fields: dict):
    baseline = _timeline()
    baseline["sections"][1].update(base_fields)
    current = copy.deepcopy(baseline)
    current["sections"][1].update(new_fields)
    return plan_console_apply(baseline, current)


def _cue_commands(plan) -> list[str]:
    return [line for line in plan.commands if line != "ChangeDestination Root"]


# --- 트래킹 ---------------------------------------------------------------------


def test_release_is_set_after_the_store():
    plan = _plan_with({}, {"tracking": "Release"})
    assert plan.applied == (20,)
    commands = _cue_commands(plan)
    store = next(
        i for i, line in enumerate(commands) if line.startswith("Store Sequence 210 Cue 20")
    )
    assert "Set Cue 20 Sequence 210 Property 'Release' 1" in commands[store + 1 :]
    assert "트래킹 Release" in plan.summaries[20]


def test_block_uses_the_block_keyword():
    plan = _plan_with({}, {"tracking": "Block"})
    assert "Block Sequence 210 Cue 20" in _cue_commands(plan)


def test_cue_only_is_a_store_option_not_a_property():
    plan = _plan_with({}, {"tracking": "Cue Only"})
    stores = [line for line in _cue_commands(plan) if line.startswith("Store Sequence 210 Cue 20")]
    assert stores == ["Store Sequence 210 Cue 20 /Merge /CueOnly"]
    assert not any("Property 'CueOnly'" in line for line in plan.commands)


@pytest.mark.parametrize(
    ("before", "expected"),
    [
        ("Release", "Set Cue 20 Sequence 210 Property 'Release' 0"),
        ("Block", "Unblock Sequence 210 Cue 20"),
    ],
)
def test_back_to_track_undoes_the_previous_mark(before, expected):
    plan = _plan_with({"tracking": before}, {"tracking": "Track"})
    assert expected in _cue_commands(plan)


def test_switching_block_to_release_unblocks_first():
    commands = _cue_commands(_plan_with({"tracking": "Block"}, {"tracking": "Release"}))
    unblock = commands.index("Unblock Sequence 210 Cue 20")
    release = commands.index("Set Cue 20 Sequence 210 Property 'Release' 1")
    assert unblock < release


def test_cue_only_cannot_be_undone_so_track_is_skipped_loudly():
    # Cue Only 는 저장 순간 다음 큐에 값을 박는다 — 풀 명령이 없다. 조용히 넘어가지 않는다.
    plan = _plan_with({"tracking": "Cue Only"}, {"tracking": "Track"})
    assert not any("Release" in line or "Block" in line for line in plan.commands)
    assert any("Cue Only" in skip.detail for skip in plan.skipped)


def test_an_unknown_tracking_value_is_rejected_not_guessed():
    plan = _plan_with({}, {"tracking": "Blok"})
    assert not any("Block" in line or "Release" in line for line in plan.commands)
    assert any("Blok" in skip.detail for skip in plan.skipped)


def test_full_apply_with_default_track_sends_no_tracking_command():
    section = _timeline()["sections"][1]
    decision = plan_cue_console_apply(section, None, _timeline()["layer_mapping"], {})
    assert decision.tracking_ops == ()
    assert decision.store_options == ()


# --- 포지션 ---------------------------------------------------------------------


def test_position_preset_number_is_recalled_on_the_cue_groups_before_the_store():
    plan = _plan_with({}, {"position": "Sweep L", "position_preset_no": "2.11"})
    commands = _cue_commands(plan)
    value = next(line for line in commands if line.startswith("Group 11"))
    assert value.endswith(" ; Group 11 ; At Preset 2.11")
    assert commands.index(value) < next(
        i for i, line in enumerate(commands) if line.startswith("Store Sequence")
    )
    assert "포지션 2.11" in plan.summaries[20]


def test_position_name_without_number_is_skipped_with_a_reason():
    plan = _plan_with({}, {"position": "Sweep L"})
    assert not any("At Preset" in line for line in plan.commands)
    assert any("번호" in skip.detail for skip in plan.skipped)


def test_full_apply_does_not_flag_composer_movement_labels():
    # 곡 전체 반영의 position 은 조립기의 움직임 이름(STATIC 등)이다 — 사유를 달지 않는다.
    section = {**_timeline()["sections"][1], "position": "TILT-UP @slow"}
    decision = plan_cue_console_apply(section, None, _timeline()["layer_mapping"], {})
    assert decision.would_apply
    assert not any("포지션" in skip.detail for skip in decision.skips)
    assert "At Preset" not in decision.value_line


def test_full_apply_sends_a_preset_number_when_one_is_present():
    section = {**_timeline()["sections"][1], "position_preset_no": "2.5", "tracking": "Release"}
    decision = plan_cue_console_apply(section, None, _timeline()["layer_mapping"], {})
    assert decision.value_line.endswith(" ; Group 11 ; At Preset 2.5")
    assert decision.tracking_ops == ("release_on",)


@pytest.mark.parametrize("number", ["4.2", "2.", "2.x", "12"])
def test_position_number_outside_pool_2_is_not_sent(number):
    plan = _plan_with({}, {"position": "Sweep L", "position_preset_no": number})
    assert not any("At Preset" in line for line in plan.commands)


# --- 여전히 안 보내는 칸 ----------------------------------------------------------


@pytest.mark.parametrize("field", ["mib_mode", "phaser"])
def test_mib_mode_and_phaser_stay_unsent(field):
    plan = _plan_with({}, {field: "무엇이든"})
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert UNSOURCED_FIELD_REASONS[field] in skip.detail


def test_mib_mode_reason_points_at_the_composer_premove_design():
    # t468 — 우리 MIB 는 조립기가 사전이동 큐를 직접 넣는다. 콘솔 MIB 속성을 건드리지 않는다.
    assert "사전이동" in UNSOURCED_FIELD_REASONS["mib_mode"]
    assert "tracking" not in UNSOURCED_FIELD_REASONS
    assert "position" not in UNSOURCED_FIELD_REASONS
