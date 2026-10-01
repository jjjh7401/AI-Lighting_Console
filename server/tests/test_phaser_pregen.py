"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-011, 카드 t501) — ``server.design.phaser_pregen``.

콘솔 접촉 0건 — 순수 함수만 겨눈다. 세 축:
  - ``TestFxForCatalogLabel``   : 라벨 -> Fx 변환(5개 필요 라벨 + 계열별 대표 +
    미지 라벨 거부).
  - ``TestPoolNameAndSection``  : 풀 이름 조회 + ``presets_section`` 변환.
  - ``TestPregenerateBundle``   : 번들 조립(성공 + 충돌 거부, FXLIB 기존
    사유 코드 재사용).
"""

from __future__ import annotations

import pytest

from server.design.phaser_pregen import (
    CATALOG_AUTHORING_GROUP_NO,
    PhaserPregenError,
    fx_for_catalog_label,
    pool_name_for_label,
    pregenerate_phaser_bundle,
    presets_section_from_pool_children,
)
from server.fx.instantiate import PRESET_OCCUPIED, VALUE_LINE_COLLISION, FxInstantiationError


class TestFxForCatalogLabel:
    # M6 이 실제로 생성해야 하는 5개 라벨(Rain, 배차서 지시).
    @pytest.mark.parametrize(
        ("label", "pattern", "attributes"),
        [
            ("Drop Slam", "chase", ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Dimmer")),
            ("Wave CM", "chase", ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")),
            ("Breathe Cool", "chase", ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")),
            ("Finale Slam", "chase", ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Dimmer")),
            ("Breathe Warm", "chase", ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")),
        ],
    )
    def test_the_five_needed_labels_convert(self, label, pattern, attributes):
        fx = fx_for_catalog_label(label)
        assert fx.display_name == label
        assert fx.pattern == pattern
        assert fx.attributes == attributes
        assert len(fx.steps) >= 2  # MIN_STEPS — build_fx_preset_bundle 가 또 검사한다

    def test_a_pure_dimmer_catalog_entry_converts_too(self):
        # 디머 계열(COMBO/COLOR 가 아닌)도 변환 가능해야 한다 — 이 SPEC 의 5개
        # 라벨에는 없지만, 모듈이 세 계열 전부를 지원한다는 계약.
        fx = fx_for_catalog_label("Breathe Soft")
        assert fx.pattern == "pulse"
        assert fx.attributes == ("Dimmer",)
        assert fx.phase_from == 0.0
        assert fx.phase_to is None

    def test_phase_token_0_thru_360_becomes_a_spread(self):
        fx = fx_for_catalog_label("Wave CM")
        assert fx.phase_from == 0.0
        assert fx.phase_to == 360.0

    def test_sine_form_becomes_the_measured_curve(self):
        fx = fx_for_catalog_label("Breathe Warm")  # sine
        assert fx.accel == -100.0
        assert fx.decel == -100.0

    def test_rectangle_form_becomes_zero_curve(self):
        fx = fx_for_catalog_label("Drop Slam")  # rectangle
        assert fx.accel == 0.0
        assert fx.decel == 0.0

    def test_an_unknown_label_is_refused_not_guessed(self):
        with pytest.raises(PhaserPregenError, match="사전 생성 카탈로그"):
            fx_for_catalog_label("No Such Phaser")

    def test_combo_step_colours_resolve_to_the_standard_palette(self):
        # Drop Slam step 1 = Red @ 100% dimmer — RGB 는 표준 팔레트 Red.
        fx = fx_for_catalog_label("Drop Slam")
        first_step = fx.steps[0]
        assert first_step.value_of("ColorRGB_R") > 0
        assert first_step.value_of("Dimmer") == 100.0


class TestPoolNameAndSection:
    def test_the_five_needed_labels_resolve_a_pool_name(self):
        assert pool_name_for_label("Wave CM") == "Color"
        assert pool_name_for_label("Breathe Cool") == "Color"
        assert pool_name_for_label("Breathe Warm") == "Color"
        assert pool_name_for_label("Drop Slam") == "All 1"
        assert pool_name_for_label("Finale Slam") == "All 1"

    def test_an_unknown_label_has_no_pool(self):
        with pytest.raises(PhaserPregenError):
            pool_name_for_label("No Such Phaser")

    def test_presets_section_carries_only_numbers(self):
        section = presets_section_from_pool_children({41: "Breathe Warm", 42: None})
        assert section == {"objects": [{"no": 41}, {"no": 42}], "truncated": False}

    def test_an_empty_pool_is_a_valid_empty_section(self):
        assert presets_section_from_pool_children({}) == {"objects": [], "truncated": False}


class TestPregenerateBundle:
    def test_a_free_pool_builds_a_landable_bundle(self):
        section = presets_section_from_pool_children({41: "Breathe Warm", 42: "Breathe Cool"})
        plan = pregenerate_phaser_bundle("Wave CM", presets_section=section, preset_pool=4)
        assert plan.preset_pool == 4
        assert plan.preset == 1  # 41/42 점유 — 번호 축은 번호만 보므로 1부터
        assert plan.group == CATALOG_AUTHORING_GROUP_NO
        assert "ChangeDestination Root" in plan.commands
        assert any(line.startswith("Store Preset 4.1 ") for line in plan.commands)
        assert any(line.startswith("Label Preset 4.1 ") for line in plan.commands)
        assert plan.commands[0] == "ChangeDestination Root"
        assert plan.commands[-1] == "ClearAll"

    def test_an_occupied_requested_slot_is_refused_not_overwritten(self):
        # select_preset_number 의 기존 거부 의미론 재사용 — 새 충돌 검사 없음.
        section = presets_section_from_pool_children({5: "Taken"})
        with pytest.raises(FxInstantiationError) as excinfo:
            pregenerate_phaser_bundle(
                "Wave CM", presets_section=section, preset_pool=4, requested_slot=5
            )
        assert excinfo.value.reason == PRESET_OCCUPIED

    def test_an_unreadable_pool_refuses_with_the_fxlib_reason(self):
        with pytest.raises(FxInstantiationError):
            pregenerate_phaser_bundle(
                "Wave CM", presets_section={"ok": False, "reason": "timeout"}, preset_pool=4
            )

    def test_an_unknown_label_refuses_before_touching_the_pool(self):
        with pytest.raises(PhaserPregenError):
            pregenerate_phaser_bundle(
                "No Such Phaser", presets_section={"objects": []}, preset_pool=4
            )

    def test_wave_cm_is_the_one_needed_label_that_builds_cleanly(self):
        """측정됨(M6) — 5개 필요 라벨 중 ``Wave CM`` 만 FXLIB 의 ``_guard_
        collision``을 통과한다. 다른 4개(``Drop Slam``·``Breathe Cool``·
        ``Finale Slam``·``Breathe Warm``)는 두 스텝 사이에 **적어도 한 채널
        값이 우연히 같아** ``VALUE_LINE_COLLISION`` 으로 거부된다 — 아래
        ``test_the_other_four_needed_labels_collide_and_are_refused_not_
        guessed`` 가 그 전부를 개별로 확인한다. 이것은 스타일 차이가 아니라
        **빌드 실패**다(모듈 독스트링 [ASSUMPTION] 참조 — FXLIB 의
        "모든 채널이 스텝 사이에서 움직여야 한다" 규율, ``color.yaml``
        자신의 저작 규율과 같은 축인데, 이 카탈로그는 그 규율을 염두에
        두고 색을 고르지 않았다)."""
        section = presets_section_from_pool_children({})
        plan = pregenerate_phaser_bundle("Wave CM", presets_section=section, preset_pool=9)
        assert plan.label == "Wave CM"
        assert plan.commands

    @pytest.mark.parametrize("label", ["Drop Slam", "Breathe Cool", "Finale Slam", "Breathe Warm"])
    def test_the_other_four_needed_labels_collide_and_are_refused_not_guessed(self, label):
        """측정됨(M6, 날조 아님) — 각 라벨이 정확히 ``VALUE_LINE_COLLISION``
        으로 거부되는지(새로 지어낸 사유가 아니라 FXLIB 기존 사유 코드)
        직접 확인한다. 충돌을 피하려고 색 값을 바꾸는 것(새 RGB 발명)은
        하지 않는다 — 카탈로그 값 그대로 거부되는 것이 올바른 동작이다."""
        section = presets_section_from_pool_children({})
        with pytest.raises(FxInstantiationError) as excinfo:
            pregenerate_phaser_bundle(label, presets_section=section, preset_pool=9)
        assert excinfo.value.reason == VALUE_LINE_COLLISION
