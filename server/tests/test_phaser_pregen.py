"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-011, 카드 t501) — ``server.design.phaser_pregen``.

콘솔 접촉 0건 — 순수 함수만 겨눈다. 세 축:
  - ``TestFxForCatalogLabel``   : 라벨 -> Fx 변환(5개 필요 라벨 + 계열별 대표 +
    미지 라벨 거부).
  - ``TestPoolNameAndSection``  : 풀 이름 조회 + ``presets_section`` 변환.
  - ``TestPregenerateBundle``   : 번들 조립(성공 + 충돌 거부, FXLIB 기존
    사유 코드 재사용).

M6c(카드 t501, 리드 결정 C) — M6 이 측정한 "5개 필요 라벨 중 Wave CM 하나만
빌드된다"는 사실은 저작 쪽 처방(``Fx.compound_step_values`` + ``pregenerate_
phaser_bundle`` 의 충돌-후-재시도, ``phaser_pregen.py`` 모듈 독스트링 참조)으로
해소됐다 — 이제 5개 전부 빌드된다. ``_guard_collision`` 자체는 손대지 않았다는
증거로 ``test_a_genuinely_duplicated_step_is_still_refused_by_the_unchanged_
guard``가 진짜 완전 중복 스텝은 여전히 거부됨을 직접 확인한다.
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

    def test_wave_cm_is_the_one_needed_label_that_builds_on_the_first_try(self):
        """측정됨(M6) — 5개 필요 라벨 중 ``Wave CM`` 만 평범한 폼(채널별 한 줄)
        으로 ``_guard_collision``을 통과했다. M6c 가 나머지 넷을 저작 쪽에서
        고쳤으므로(``test_the_four_previously_refused_labels_now_build_
        cleanly`` 참조), 이 시험이 증명하는 것은 ``Wave CM`` 이 그 처방의
        재시도 경로를 **전혀 타지 않는다**는 것 — 첫 시도 성공이므로 출력이
        바이트 동일하다는 구조적 보장의 근거다."""
        section = presets_section_from_pool_children({})
        plan = pregenerate_phaser_bundle("Wave CM", presets_section=section, preset_pool=9)
        assert plan.label == "Wave CM"
        assert plan.commands
        # 평범한 폼 그대로(압축 안 됨) — 채널별 한 줄씩.
        assert "Attribute 'ColorRGB_R' At 0" in plan.commands
        assert not any(" ; " in c and c.count("At ") > 1 for c in plan.commands[:7])

    @pytest.mark.parametrize("label", ["Drop Slam", "Breathe Cool", "Finale Slam", "Breathe Warm"])
    def test_the_four_previously_refused_labels_now_build_cleanly(self, label):
        """M6c(카드 t501, 리드 결정 C) — M6 이 측정한 ``VALUE_LINE_COLLISION``
        거부(저작 쪽 ``compound_step_values`` 처방 전)가 이제 해소됐다. 각
        라벨이 ``_guard_collision`` 을 통과하고, Store/Label 줄을 낸다 — 카탈로그
        값을 바꾸지 않고(새 RGB 발명 없음) 저작 형태만 바꿔 얻은 결과다."""
        section = presets_section_from_pool_children({})
        plan = pregenerate_phaser_bundle(label, presets_section=section, preset_pool=9)
        assert plan.label == label
        quoted = f"'{label}'"
        assert any(line.startswith("Store Preset 9.") and quoted in line for line in plan.commands)
        assert any(line.startswith("Label Preset 9.") and quoted in line for line in plan.commands)

    def test_a_genuinely_duplicated_step_is_still_refused_by_the_unchanged_guard(self, monkeypatch):
        """두 가지 모두 증명한다: (a) 저작 처방은 ``_guard_collision`` 의 판정
        로직을 전혀 바꾸지 않았고 — 스텝의 전체 값 집합이 진짜로 똑같으면
        (``compound_step_values=True`` 라도) 여전히 ``VALUE_LINE_COLLISION``
        으로 거부된다. (b) ``pregenerate_phaser_bundle`` 의 충돌-후-재시도는
        **한 번만** 일어난다 — 압축해도 여전히 충돌하면 압축된 사유를 그대로
        전파하지, 무한 재시도나 다른 사유로 둔갑시키지 않는다."""
        import server.design.phaser_pregen as pregen_module

        # "Drop Slam" 을 두 스텝이 완전히 동일한(색 + 디머 모두 같음) 라벨로
        # 임시 교체 — compound 로 묶어도 텍스트가 똑같아 여전히 충돌해야 한다.
        # ``phaser_pregen.py`` 는 `from ... import COMBO_PHASER_SEQUENCE`로 이
        # 모듈 안에 자기 이름을 갖고 있으므로, 그 이름 자체를 patch 한다(원본
        # ``phaser_catalog.COMBO_PHASER_SEQUENCE``를 바꾸면 이 바인딩에 안
        # 보인다).
        monkeypatch.setattr(
            pregen_module,
            "COMBO_PHASER_SEQUENCE",
            (("Drop Slam", (("Red", 50), ("Red", 50)), "rectangle", "0"),),
        )
        section = presets_section_from_pool_children({})
        with pytest.raises(FxInstantiationError) as excinfo:
            pregenerate_phaser_bundle("Drop Slam", presets_section=section, preset_pool=9)
        assert excinfo.value.reason == VALUE_LINE_COLLISION
