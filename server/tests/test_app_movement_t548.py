"""SPEC-LDBEAT-001 M8 — ``app_movement`` 셀 에미터 (카드 t548).

콘솔 접촉 0건, 콘솔 쓰기 0건 — 순수 함수가 명령 문자열 리스트만 만든다.

이 시험이 재는 것:

1. AC-LDBEAT-016(u) — 기준 위치 출처(그 칸 자신의 `position_preset_no`,
   뱅크 프리셋 레이블 리콜 0건).
2. AC-LDBEAT-016(n) — `shape="wave"`+`axes={"Pan"}` 유효, 거절 0건.
3. AC-LDBEAT-016(s) — 장비 ID·그룹 번호·프리셋 번호 코드 상수 0건.
4. BPM·마디당 박·주기 중 하나라도 없으면 거절(지어내지 않음).
5. 리드 추가 지시(2026-10-11 교정) — Dimmer 단독 기구는 Dimmer2 줄 없이
   정확히 한 줄만 낸다.
"""

from __future__ import annotations

import inspect

from server.design import app_movement as app_movement_module
from server.design.app_movement import (
    app_movement_commands,
    brightness_value_commands,
    dimmer_attribute_names,
)
from server.spatial.pointing import FX_POSITION_SEQUENCE


class TestDimmerAttributeNames:
    def test_dimmer_only_fixture(self) -> None:
        assert dimmer_attribute_names(("Dimmer", "Pan", "Tilt")) == ("Dimmer",)

    def test_dimmer_and_dimmer2_fixture(self) -> None:
        # 리드 추가 지시 — MOVER-D(Spiider)는 Dimmer+Dimmer2 둘 다 가진
        # 기구다(.moai/reports/t548/probe-moverd.md v0b 실측).
        names = dimmer_attribute_names(("Dimmer", "Dimmer2", "Pan", "Tilt"))
        assert names == ("Dimmer", "Dimmer2")

    def test_dimmer_curve_is_not_a_dimmer_attribute(self) -> None:
        # 패밀리 정확 일치 — 접두 일치가 아니다. "DimmerCurve"는 밝기
        # 조정이 아니다.
        assert dimmer_attribute_names(("Dimmer", "DimmerCurve")) == ("Dimmer",)

    def test_no_dimmer_attribute_at_all(self) -> None:
        assert dimmer_attribute_names(("Pan", "Tilt")) == ()

    def test_case_insensitive_and_order_preserved(self) -> None:
        assert dimmer_attribute_names(("dimmer2", "DIMMER")) == ("dimmer2", "DIMMER")


class TestBrightnessValueCommands:
    def test_dimmer_only_fixture_emits_exactly_one_line_and_no_dimmer2(self) -> None:
        # 리드 추가 지시(2026-10-11) — Dimmer 하나뿐인 기구는 Dimmer2 줄이
        # 전혀 없이 정확히 한 줄만 낸다.
        attrs = dimmer_attribute_names(("Dimmer", "Pan", "Tilt"))
        commands = brightness_value_commands(group_no=4, value_percent=60, dimmer_attributes=attrs)
        assert commands == ("Group 4 ; Attribute 'Dimmer' At 60",)
        assert not any("Dimmer2" in line for line in commands)

    def test_dimmer_and_dimmer2_fixture_emits_one_line_per_attribute(self) -> None:
        attrs = dimmer_attribute_names(("Dimmer", "Dimmer2", "Pan", "Tilt"))
        commands = brightness_value_commands(group_no=12, value_percent=70, dimmer_attributes=attrs)
        assert commands == (
            "Group 12 ; Attribute 'Dimmer' At 70",
            "Group 12 ; Attribute 'Dimmer2' At 70",
        )

    def test_no_dimmer_attributes_emits_nothing(self) -> None:
        assert brightness_value_commands(group_no=4, value_percent=60, dimmer_attributes=()) == ()


class TestAppMovementCommandsBasePositionSource:
    """AC-LDBEAT-016(u) — REQ-LDBEAT-006(vi-8)."""

    _MOVEMENT = {
        "shape": "wave",
        "axes": ("Pan",),
        "period_unit": "beat",
        "period_value": 2,
        "phase_spread": None,
    }

    def test_positive_recall_appears_exactly_once_before_first_relative(self) -> None:
        commands, reason = app_movement_commands(
            self._MOVEMENT,
            group_no=11,
            position_preset_no="2.1",
            bpm=112.0,
            beats_per_bar=4,
        )
        assert reason is None
        recall_indices = [i for i, line in enumerate(commands) if "At Preset 2.1" in line]
        relative_indices = [i for i, line in enumerate(commands) if "At Relative" in line]
        assert len(recall_indices) == 1
        assert recall_indices[0] < relative_indices[0]

    def test_positive_never_recalls_a_bank_preset_label(self) -> None:
        commands, _reason = app_movement_commands(
            self._MOVEMENT,
            group_no=11,
            position_preset_no="2.1",
            bpm=112.0,
            beats_per_bar=4,
        )
        for label in FX_POSITION_SEQUENCE:
            assert not any(label in line for line in commands)

    def test_null_position_preset_no_emits_zero_recall_lines(self) -> None:
        commands, reason = app_movement_commands(
            self._MOVEMENT,
            group_no=11,
            position_preset_no=None,
            bpm=112.0,
            beats_per_bar=4,
        )
        assert reason is None
        assert not any("At Preset" in line for line in commands)
        for label in FX_POSITION_SEQUENCE:
            assert not any(label in line for line in commands)
        # 상대 단계는 그래도 나간다(기본 수직 중심으로).
        assert any("At Relative" in line for line in commands)


class TestAppMovementCommandsAxesGeneralization:
    def test_pan_only_wave_is_valid_not_rejected(self) -> None:
        commands, reason = app_movement_commands(
            {
                "shape": "wave",
                "axes": ("Pan",),
                "period_unit": "beat",
                "period_value": 2,
                "phase_spread": None,
            },
            group_no=11,
            position_preset_no="2.1",
            bpm=112.0,
            beats_per_bar=4,
        )
        assert reason is None
        assert any("Attribute 'Pan' At Relative" in line for line in commands)
        assert not any("Tilt" in line for line in commands)

    def test_invented_shape_names_are_absent_from_source(self) -> None:
        source = inspect.getsource(app_movement_module)
        assert "pan_sway" not in source
        assert "tilt_wave" not in source

    def test_no_seconds_constant_in_module(self) -> None:
        source = inspect.getsource(app_movement_module)
        assert "fade_seconds" not in source
        assert "_seconds" not in source


class TestAppMovementCommandsRefusals:
    _BASE = {
        "shape": "wave",
        "axes": ("Tilt",),
        "period_unit": "beat",
        "period_value": 2,
        "phase_spread": None,
    }

    def test_missing_bpm_is_refused(self) -> None:
        commands, reason = app_movement_commands(
            self._BASE, group_no=11, position_preset_no="2.1", bpm=None, beats_per_bar=4
        )
        assert commands == ()
        assert reason is not None

    def test_missing_beats_per_bar_for_bar_period_unit_is_refused(self) -> None:
        movement = {**self._BASE, "period_unit": "bar", "period_value": 2}
        commands, reason = app_movement_commands(
            movement, group_no=11, position_preset_no="2.1", bpm=112.0, beats_per_bar=None
        )
        assert commands == ()
        assert reason is not None

    def test_beat_period_unit_does_not_need_beats_per_bar(self) -> None:
        commands, reason = app_movement_commands(
            self._BASE, group_no=11, position_preset_no="2.1", bpm=112.0, beats_per_bar=None
        )
        assert reason is None
        assert commands

    def test_missing_period_value_is_refused(self) -> None:
        movement = {**self._BASE, "period_value": None}
        commands, reason = app_movement_commands(
            movement, group_no=11, position_preset_no="2.1", bpm=112.0, beats_per_bar=4
        )
        assert commands == ()
        assert reason is not None

    def test_no_app_movement_emits_nothing_without_reason(self) -> None:
        commands, reason = app_movement_commands(
            None, group_no=11, position_preset_no="2.1", bpm=112.0, beats_per_bar=4
        )
        assert commands == ()
        assert reason is None

    def test_unimplemented_shape_is_refused_not_guessed(self) -> None:
        # M8 범위 — wave만 구현. 다른 shape는 추측 없이 거절(reason 있음).
        movement = {**self._BASE, "shape": "circle"}
        commands, reason = app_movement_commands(
            movement, group_no=11, position_preset_no="2.1", bpm=112.0, beats_per_bar=4
        )
        assert commands == ()
        assert reason is not None


class TestAppMovementCommandsSpeedComputation:
    def test_beat_period_speed_is_bpm_over_period_value(self) -> None:
        movement = {
            "shape": "wave",
            "axes": ("Tilt",),
            "period_unit": "beat",
            "period_value": 2,
            "phase_spread": None,
        }
        commands, _reason = app_movement_commands(
            movement, group_no=12, position_preset_no=None, bpm=112.0, beats_per_bar=4
        )
        # 112 / 2 = 56
        assert any("At Speed 56" in line for line in commands)

    def test_bar_period_speed_divides_by_beats_per_bar_too(self) -> None:
        movement = {
            "shape": "wave",
            "axes": ("Tilt",),
            "period_unit": "bar",
            "period_value": 2,
            "phase_spread": True,
        }
        commands, _reason = app_movement_commands(
            movement, group_no=12, position_preset_no=None, bpm=112.0, beats_per_bar=4
        )
        # 112 / (2 * 4) = 14
        assert any("At Speed 14" in line for line in commands)

    def test_phase_spread_line_present_only_when_true(self) -> None:
        on = {
            "shape": "wave",
            "axes": ("Tilt",),
            "period_unit": "beat",
            "period_value": 2,
            "phase_spread": True,
        }
        off = {**on, "phase_spread": False}
        unset = {**on, "phase_spread": None}
        commands_on, _ = app_movement_commands(
            on, group_no=12, position_preset_no=None, bpm=112.0, beats_per_bar=4
        )
        commands_off, _ = app_movement_commands(
            off, group_no=12, position_preset_no=None, bpm=112.0, beats_per_bar=4
        )
        commands_unset, _ = app_movement_commands(
            unset, group_no=12, position_preset_no=None, bpm=112.0, beats_per_bar=4
        )
        assert any("At Phase" in line for line in commands_on)
        assert not any("At Phase" in line for line in commands_off)
        assert not any("At Phase" in line for line in commands_unset)
