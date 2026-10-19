"""카드 WT-wave-presets — 웨이브 효과 프리셋 다섯 개의 저장 묶음(순수 함수 · 콘솔 접촉 0건).

디머·컬러 웨이브는 출하 fx 라이브러리의 틀에 한 주기 박 수를 얹어 「All 1」 효과 풀(풀 21)의
빈 번호에 저장한다. 속도는 곡 BPM 과 SpeedMaster 로 묶고, 고정 ``At Speed`` 는 쓰지 않는다.
다섯 프리셋은 한 송신 묶음으로 나가므로 마스터 BPM 줄은 맨 앞에 한 번만 있다.
"""

from __future__ import annotations

import re

import pytest

from server.design.wave_presets import (
    WAVE_PRESETS,
    WavePreset,
    plan_wave_slots,
    plan_wave_writes,
    wave_master_line,
    wave_preset_bundle,
    wave_save_commands,
    wave_templates,
)

BPM = 112.35
SPEED_MASTER = 15
POOL = 21


def _bundle(preset: WavePreset, *, group_no: int = 11, slot: int = 3) -> tuple[str, ...]:
    return wave_preset_bundle(
        preset,
        wave_templates()[preset.fx_id],
        group_no=group_no,
        preset_pool=POOL,
        preset_slot=slot,
        speed_master=SPEED_MASTER,
    )


def _batch(writes) -> tuple[str, ...]:
    return wave_save_commands(
        writes, group_no=11, preset_pool=POOL, bpm=BPM, speed_master=SPEED_MASTER
    )


class TestWavePresetBundles:
    def test_the_draft_list_is_five_presets(self) -> None:
        assert len(WAVE_PRESETS) == 5

    @pytest.mark.parametrize("preset", WAVE_PRESETS, ids=lambda p: p.console_label)
    def test_console_labels_are_ascii_and_fit_the_console(self, preset) -> None:
        # 콘솔 프리셋 이름은 영문·숫자만(REQ-LDBEAT-015(d)). 화면 이름만 한글이다.
        assert preset.console_label.isascii()
        assert len(preset.console_label) <= 20

    @pytest.mark.parametrize("preset", WAVE_PRESETS, ids=lambda p: p.console_label)
    def test_speed_is_bound_to_the_master_not_a_fixed_speed(self, preset) -> None:
        text = "\n".join(_bundle(preset))

        assert f"At SpeedMaster {SPEED_MASTER}" in text
        assert f"At Measure {preset.beats}" in text
        assert re.search(r"At Speed \d", text) is None

    @pytest.mark.parametrize("preset", WAVE_PRESETS, ids=lambda p: p.console_label)
    def test_store_and_label_go_to_the_effect_pool_under_the_console_label(self, preset) -> None:
        bundle = _bundle(preset, slot=3)

        assert f"Store Preset 21.3 '{preset.console_label}' /Universal" in bundle
        assert f"Label Preset 21.3 '{preset.console_label}'" in bundle

    def test_the_selected_line_is_the_group_argument_and_no_other_group_is_written(self) -> None:
        bundle = _bundle(WAVE_PRESETS[0], group_no=7)

        assert "Group 7" in bundle
        assert not [line for line in bundle if line.startswith("Group ") and line != "Group 7"]

    def test_the_phase_fans_across_the_selection_in_device_order(self) -> None:
        bundle = _bundle(WAVE_PRESETS[0])

        assert "Attribute 'Dimmer' At Phase 0 Thru 360" in bundle

    def test_a_bundle_carries_no_master_line_because_the_batch_sends_it_once(self) -> None:
        assert not [line for line in _bundle(WAVE_PRESETS[0]) if line.startswith("Master ")]

    @pytest.mark.parametrize("preset", WAVE_PRESETS, ids=lambda p: p.console_label)
    def test_each_bundle_starts_and_ends_on_a_clear_so_presets_do_not_mix(self, preset) -> None:
        bundle = _bundle(preset)

        assert bundle[0] == "ChangeDestination Root"
        assert bundle[1] == "ClearAll"
        assert bundle[-1] == "ClearAll"


class TestWaveSaveCommands:
    def test_the_master_bpm_line_is_first_and_appears_exactly_once(self) -> None:
        batch = _batch(plan_wave_writes({})[0])

        assert batch[0] == wave_master_line(BPM, SPEED_MASTER) == "Master 3.15 At BPM 112.35"
        assert batch.count(batch[0]) == 1

    def test_every_preset_is_stored_under_its_slot_in_one_batch(self) -> None:
        writes = plan_wave_writes({})[0]
        batch = _batch(writes)

        for write in writes:
            store = f"Store Preset 21.{write.slot} '{write.preset.console_label}' /Universal"
            assert store in batch
        assert sum(line.startswith("Store Preset 21.") for line in batch) == len(WAVE_PRESETS)

    def test_shared_lines_repeat_inside_the_one_batch_on_purpose(self) -> None:
        # 같은 묶음 안의 반복은 중복 제거 대상이 아니다(카드 t601). 이 테스트가 그 전제를 고정한다.
        batch = _batch(plan_wave_writes({})[0])

        assert batch.count("ChangeDestination Root") == len(WAVE_PRESETS)

    def test_no_fixed_speed_anywhere_in_the_batch(self) -> None:
        assert re.search(r"At Speed \d", "\n".join(_batch(plan_wave_writes({})[0]))) is None


class TestWaveSlotPlanner:
    def test_takes_the_lowest_free_numbers_in_order(self) -> None:
        assert plan_wave_slots({1, 2, 4}, 3) == [3, 5, 6]

    def test_an_empty_pool_gives_the_first_numbers(self) -> None:
        assert plan_wave_slots(set(), 2) == [1, 2]


class TestWritePlan:
    def test_an_empty_pool_takes_slots_one_to_five_in_list_order(self) -> None:
        writes, skipped = plan_wave_writes({})

        assert [write.slot for write in writes] == [1, 2, 3, 4, 5]
        assert [write.preset for write in writes] == list(WAVE_PRESETS)
        assert skipped == ()

    def test_a_name_already_in_the_pool_is_skipped_and_the_rest_take_free_slots(self) -> None:
        writes, skipped = plan_wave_writes({1: "P1", 2: None, 3: "WAVE DIM SINE 2B"})

        assert [preset.console_label for preset in skipped] == ["WAVE DIM SINE 2B"]
        assert [(write.slot, write.preset.console_label) for write in writes] == [
            (4, "WAVE DIM SINE 1B"),
            (5, "WAVE DIM SINE 4B"),
            (6, "WAVE COL RAINBOW 2B"),
            (7, "WAVE COL WARMCOOL 2B"),
        ]

    def test_a_full_set_of_names_stores_nothing(self) -> None:
        pool = {number: preset.console_label for number, preset in enumerate(WAVE_PRESETS, 1)}
        writes, skipped = plan_wave_writes(pool)

        assert writes == ()
        assert len(skipped) == len(WAVE_PRESETS)

    def test_the_name_match_is_exact(self) -> None:
        writes, skipped = plan_wave_writes({1: "WAVE DIM SINE 2B (old)"})

        assert skipped == ()
        assert [write.slot for write in writes] == [2, 3, 4, 5, 6]
