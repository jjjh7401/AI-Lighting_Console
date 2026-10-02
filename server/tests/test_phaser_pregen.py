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
from server.fx.instantiate import PRESET_OCCUPIED, FxInstantiationError


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
        """측정됨(M6) — 5개 필요 라벨 중 ``Wave CM`` 은 두 스텝이 채널마다
        다른 값이라 M6 당시에도 FXLIB 의 ``_guard_collision``을 그냥
        통과했다. 다른 4개(``Drop Slam``·``Breathe Cool``·``Finale Slam``·
        ``Breathe Warm``)는 두 스텝 사이에 **적어도 한 채널 값이 우연히
        같아** M6 당시엔 ``VALUE_LINE_COLLISION`` 으로 거부됐었다 — M6b
        (카드 t501, 2026-10-02 리드 결정)가 그 거부를 스텝 경계 단위로
        좁혀, 같은 값이 **다른 스텝**에 있으면 더 이상 충돌이 아니게
        했다(``test_the_other_four_needed_labels_now_build_cleanly_too``
        참조). 이 테스트는 Wave CM 이 그 변경 전후로 계속 빌드된다는
        것만 고정한다."""
        section = presets_section_from_pool_children({})
        plan = pregenerate_phaser_bundle("Wave CM", presets_section=section, preset_pool=9)
        assert plan.label == "Wave CM"
        assert plan.commands

    @pytest.mark.parametrize("label", ["Drop Slam", "Breathe Cool", "Finale Slam", "Breathe Warm"])
    def test_the_other_four_needed_labels_now_build_cleanly_too(self, label):
        """측정됨(M6b, 카드 t501, 2026-10-02 리드 결정) — 이 4개 라벨은 M6
        당시 ``VALUE_LINE_COLLISION`` 으로 거부됐다(두 스텝 모두 같은
        채널 값을 낸다, 예: Drop Slam 의 두 스텝 모두
        ``Attribute 'ColorRGB_R' At 100``). 리드가 ``run_commands`` 의
        중복 제거 범위를 ``Step <n>`` 경계에서 리셋하도록 좁히고
        FXLIB ``_guard_collision`` 을 그에 맞춰 완화한 뒤로는, 같은 값이
        **스텝 경계를 건너** 반복되는 것은 충돌이 아니다 — 두 번째 줄은
        이제 ``run_commands`` 에서도 실제로 실행된다(``skipped_already_
        executed`` 로 떨어지지 않는다, ``server/tests/test_tools.py``
        ``TestStepBoundaryResetsDedupeScope`` 참조). 카탈로그 색을 바꿔
        충돌을 피하지 않는다(새 RGB 발명 금지, §D) — 이 4개는 카탈로그
        값 그대로 빌드된다."""
        section = presets_section_from_pool_children({})
        plan = pregenerate_phaser_bundle(label, presets_section=section, preset_pool=9)
        assert plan.label == label
        assert plan.commands
        # 두 스텝 모두 전건 살아있다 — 더 이상 2번째 스텝이 드롭되지 않는다.
        assert any(c == "Step 2" for c in plan.commands)
        non_exempt = [
            c
            for c in plan.commands
            if c not in ("ChangeDestination Root", "ClearAll", "Group 1")
            and not c.startswith("Store ")
            and not c.startswith("Label ")
        ]
        assert non_exempt, "a bundle of nothing but structural lines would prove nothing"

    def test_a_genuine_same_step_collision_is_still_refused(self, monkeypatch):
        """``_guard_collision`` 완화는 스텝 **경계를 건넌** 반복에만 적용된다
        — 같은 스텝 **안**에서 같은 값 줄이 두 번 나오면 여전히 거부된다
        (리드 결정이 명시한 "collisions within one step still refused").
        카탈로그에는 이 모양의 라벨이 없어 ``fx_for_catalog_label`` 을
        몽키패치해 합성 Fx로 직접 재현한다."""
        from server.fx.schema import Fx, FxStep, StepValue

        def _same_step_collision(label: str):
            return Fx(
                fx_id="synthetic-same-step-collision",
                display_name=label,
                pattern="chase",
                steps=(
                    FxStep(
                        values=(
                            StepValue(attribute="ColorRGB_R", value=100),
                            StepValue(attribute="ColorRGB_R", value=100),
                        )
                    ),
                    FxStep(values=(StepValue(attribute="ColorRGB_R", value=0),)),
                ),
                speed=30,
            )

        import server.design.phaser_pregen as phaser_pregen

        monkeypatch.setattr(phaser_pregen, "fx_for_catalog_label", _same_step_collision)
        section = presets_section_from_pool_children({})
        with pytest.raises(FxInstantiationError) as excinfo:
            pregenerate_phaser_bundle("Wave CM", presets_section=section, preset_pool=9)
        from server.fx.instantiate import VALUE_LINE_COLLISION

        assert excinfo.value.reason == VALUE_LINE_COLLISION
