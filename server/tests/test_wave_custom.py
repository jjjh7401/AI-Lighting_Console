"""카드 WT-wave-custom — 감독이 고른 웨이브 값의 검사(순수 함수 · 콘솔 접촉 0건).

모양·박 수·콘솔 이름·화면 이름을 검사하고, 같은 콘솔 이름이 효과 풀에 있으면 거절하는지 본다.
"""

from __future__ import annotations

import pytest

from server.design.wave_custom import (
    WAVE_BEATS,
    WAVE_SHAPES,
    custom_wave_problem,
    wave_spec_from_fields,
    wave_spec_preset,
)


class TestWaveSpecFields:
    def test_a_good_spec_becomes_a_preset_with_the_shape_template(self) -> None:
        spec, problem = wave_spec_from_fields("sine", 2, "MY SINE 2B", "  내 사인 2박  ")

        assert problem is None
        assert spec is not None
        assert spec.display_name == "내 사인 2박"
        preset = wave_spec_preset(spec)
        assert preset.console_label == "MY SINE 2B"
        assert preset.fx_id == "pulse-sine-breath"
        assert preset.kind == "dimmer"
        assert preset.beats == 2

    def test_a_color_shape_is_a_color_preset(self) -> None:
        spec, _problem = wave_spec_from_fields("rainbow", 4, "MY RAINBOW 4B", "내 무지개")

        assert spec is not None
        preset = wave_spec_preset(spec)
        assert preset.fx_id == "chase-rainbow-wave"
        assert preset.kind == "color"

    def test_every_listed_shape_and_beat_count_is_accepted(self) -> None:
        for shape in WAVE_SHAPES:
            for beats in WAVE_BEATS:
                spec, problem = wave_spec_from_fields(shape.shape_id, beats, "A1", "이름")
                assert problem is None, (shape.shape_id, beats)
                assert spec is not None

    @pytest.mark.parametrize(
        ("shape", "beats", "label", "name", "word"),
        [
            ("square", 2, "X", "이름", "웨이브 모양"),
            ("sine", 3, "X", "이름", "박 수"),
            ("sine", True, "X", "이름", "박 수"),
            ("sine", "2", "X", "이름", "박 수"),
            ("sine", 2, "내 사인", "이름", "콘솔 이름"),
            ("sine", 2, " X", "이름", "콘솔 이름"),
            ("sine", 2, "X ", "이름", "콘솔 이름"),
            ("sine", 2, "X" * 21, "이름", "콘솔 이름"),
            ("sine", 2, "X", "   ", "화면 이름"),
            ("sine", 2, "X", "n" * 41, "화면 이름"),
        ],
    )
    def test_a_bad_value_is_refused_with_a_reason_that_names_it(
        self, shape: object, beats: object, label: object, name: object, word: str
    ) -> None:
        spec, problem = wave_spec_from_fields(shape, beats, label, name)

        assert spec is None
        assert problem is not None
        assert word in problem


class TestCustomWaveProblem:
    def test_a_console_name_already_in_the_pool_is_refused(self) -> None:
        spec, _problem = wave_spec_from_fields("sine", 2, "MY SINE 2B", "내 사인")
        assert spec is not None

        problem = custom_wave_problem(spec, {3: "MY SINE 2B"})

        assert problem is not None
        assert "이미 있습니다" in problem

    def test_a_free_name_passes_whatever_the_slots_hold(self) -> None:
        spec, _problem = wave_spec_from_fields("sine", 2, "MY SINE 2B", "내 사인")
        assert spec is not None

        assert custom_wave_problem(spec, {1: "P1", 2: None}) is None
