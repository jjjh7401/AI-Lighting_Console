"""닫힌 어휘(vocabulary) 시험 — SPEC-LDDESIGN-001 M1 (REQ-LDDESIGN-005~010).

네 어휘(구간 9종·트리거 10종·원샷 7종·동작 9종) 각각에 대해 두 팔을 모두
잰다 — 목록에 있는 값은 전부 통과하고, 조작한 근접값은 전부 거부돼야
한다. 통과 팔만 재는 가드는 공허하다(``verification-claim-integrity`` 의
"양팔 대조" 규율).

REQ-008/009 재매핑 계층(판정기 5종 → 어휘 9종)은 원래 판정기 이름을
보존하는지와 "감독 확인" 플래그가 올바른 자리에만 서는지를 함께 잰다.
"""

from __future__ import annotations

import pytest

from server.concept.vocab import (
    CLASSIFIER_ROLES,
    DIRECTOR_ONLY_TRIGGERS,
    ONE_SHOTS,
    OPERATIONS,
    SECTIONS,
    TRIGGERS,
    VocabError,
    is_director_only_trigger,
    remap_classifier_role,
    remap_classifier_roles,
    validate_one_shot,
    validate_operation,
    validate_section,
    validate_trigger,
)


class TestSectionsClosedNine:
    """REQ-005 — 구간 어휘 정확히 9종, 닫힘."""

    def test_count_is_exactly_nine(self):
        assert len(SECTIONS) == 9
        assert len(set(SECTIONS)) == 9  # 중복 없음

    def test_all_nine_named_sections_are_present(self):
        expected = {
            "Intro",
            "Verse",
            "Pre-Chorus",
            "Chorus",
            "Post-Chorus",
            "Bridge",
            "Rap/Solo/Dance Break",
            "Final Chorus",
            "Outro",
        }
        assert set(SECTIONS) == expected

    @pytest.mark.parametrize("value", list(SECTIONS))
    def test_every_listed_section_is_accepted(self, value):
        assert validate_section(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "Interlude",  # 문서 어휘 밖 이름
            "Post Chorus",  # 하이픈 누락 근접값
            "Chorus 2",  # 회차 접미사가 붙은 근접값
            "pre-chorus",  # 대소문자 다른 근접값
            "",
            "Refrain",
        ],
    )
    def test_fabricated_near_miss_is_rejected(self, value):
        with pytest.raises(VocabError):
            validate_section(value)


class TestTriggersClosedTen:
    """REQ-006 — 트리거 어휘 정확히 10 토큰, 닫힘.

    문서 8항목 중 "보컬 시작/종료"·"악기 추가/제거" 를 각각 독립 토큰으로
    분리해 10 토큰이 된다(spec.md REQ-LDDESIGN-006 괄호주).
    """

    def test_count_is_exactly_ten(self):
        assert len(TRIGGERS) == 10
        assert len(set(TRIGGERS)) == 10

    def test_all_ten_tokens_are_present(self):
        expected = {
            "보컬 시작",
            "보컬 종료",
            "악기 추가",
            "악기 제거",
            "코드·조성 변화",
            "빌드업 시작",
            "드롭 직전의 정적",
            "핵심 가사",
            "안무 대형 변화",
            "중심 멤버·솔로 변경",
        }
        assert set(TRIGGERS) == expected

    @pytest.mark.parametrize("value", list(TRIGGERS))
    def test_every_listed_trigger_is_accepted(self, value):
        assert validate_trigger(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "보컬 등장",  # 근접하지만 다른 문구
            "악기 변화",  # 추가/제거 분리 전 합성 이름
            "가사",  # "핵심 가사" 의 부분 문자열
            "",
        ],
    )
    def test_fabricated_near_miss_is_rejected(self, value):
        with pytest.raises(VocabError):
            validate_trigger(value)


class TestDirectorOnlyTriggers:
    """REQ-010 — 오디오 분석 검출 불가 트리거 4종은 감독 전용 자유 입력."""

    def test_count_is_exactly_four(self):
        assert len(DIRECTOR_ONLY_TRIGGERS) == 4

    def test_director_only_triggers_are_subset_of_triggers(self):
        assert set(TRIGGERS) >= DIRECTOR_ONLY_TRIGGERS

    def test_named_four_are_director_only(self):
        expected = {"코드·조성 변화", "핵심 가사", "안무 대형 변화", "중심 멤버·솔로 변경"}
        assert set(DIRECTOR_ONLY_TRIGGERS) == expected
        for trigger in expected:
            assert is_director_only_trigger(trigger) is True

    def test_remaining_six_triggers_are_not_director_only(self):
        remaining = set(TRIGGERS) - set(DIRECTOR_ONLY_TRIGGERS)
        assert len(remaining) == 6
        for trigger in remaining:
            assert is_director_only_trigger(trigger) is False


class TestOneShotsClosedSeven:
    """REQ-007 — 원샷 어휘 정확히 7종, 닫힘.

    문면 검토: "Kick·Snare·Cymbal accent" 는 내부 구분자 "·"(공백 없음)로
    세 타악기를 하나의 원샷 개념으로 묶은 **단일 항목**이고, 항목 사이
    구분자는 공백을 낀 " · " 다. spec.md 의 Out of Scope 절이 이 항목을
    "원샷 어휘 7종 중 Kick·Snare·Cymbal accent(...), Color bump(...),
    Position snap(...)" 로 다시 나열하며 7종 중 하나로 명시 재확인한다
    (spec.md:379) — 문면과 열거가 불일치하는 결함이 아니라 7종이 맞다.
    """

    def test_count_is_exactly_seven(self):
        assert len(ONE_SHOTS) == 7
        assert len(set(ONE_SHOTS)) == 7

    def test_all_seven_named_one_shots_are_present(self):
        expected = {
            "Kick·Snare·Cymbal accent",
            "Dimmer bump",
            "White hit",
            "짧은 Strobe",
            "Color bump",
            "Position snap",
            "Blinder hit",
        }
        assert set(ONE_SHOTS) == expected

    @pytest.mark.parametrize("value", list(ONE_SHOTS))
    def test_every_listed_one_shot_is_accepted(self, value):
        assert validate_one_shot(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "Kick accent",  # 셋 중 하나만 분리한 근접값(항목은 결합형 하나뿐)
            "Snare accent",
            "Cymbal accent",
            "Strobe",  # "짧은" 수식어가 빠진 근접값
            "White flash",
            "",
        ],
    )
    def test_fabricated_near_miss_is_rejected(self, value):
        with pytest.raises(VocabError):
            validate_one_shot(value)


class TestOperationsClosedNine:
    """REQ-019(§3.5) — `operation` 필드가 참조하는 동작 어휘 9종."""

    def test_count_is_exactly_nine(self):
        assert len(OPERATIONS) == 9
        assert len(set(OPERATIONS)) == 9

    def test_all_nine_operations_are_present(self):
        expected = {
            "retain",
            "add",
            "remove",
            "reduce",
            "replace",
            "isolate",
            "expand",
            "restore",
            "release",
        }
        assert set(OPERATIONS) == expected

    @pytest.mark.parametrize("value", list(OPERATIONS))
    def test_every_listed_operation_is_accepted(self, value):
        assert validate_operation(value) == value

    @pytest.mark.parametrize("value", ["hold", "set", "REMOVE", "add ", "delete", ""])
    def test_fabricated_near_miss_is_rejected(self, value):
        with pytest.raises(VocabError):
            validate_operation(value)


class TestValidationErrorNamesFieldAndValue:
    """REQ-016 — 거부 오류는 어느 필드에 어떤 값이 왔는지 메시지에 명시한다.

    타입만 확인하는 시험은 잘못된 이유로 거부됐는지 옳은 이유로 거부됐는지
    구별할 수 없다 — 메시지 *내용* 을 단언한다.
    """

    def test_section_error_names_field_and_value(self):
        with pytest.raises(VocabError) as excinfo:
            validate_section("Interlude")
        message = str(excinfo.value)
        assert "section" in message
        assert "Interlude" in message

    def test_trigger_error_names_field_and_value(self):
        with pytest.raises(VocabError) as excinfo:
            validate_trigger("보컬 등장")
        message = str(excinfo.value)
        assert "trigger" in message
        assert "보컬 등장" in message

    def test_one_shot_error_names_field_and_value(self):
        with pytest.raises(VocabError) as excinfo:
            validate_one_shot("Kick accent")
        message = str(excinfo.value)
        assert "shot" in message
        assert "Kick accent" in message

    def test_operation_error_names_field_and_value(self):
        with pytest.raises(VocabError) as excinfo:
            validate_operation("delete")
        message = str(excinfo.value)
        assert "operation" in message
        assert "delete" in message


class TestClassifierRoleRemapping:
    """REQ-008/009 — 판정기 5종 → 어휘 9종 재매핑 + "감독 확인" 플래그.

    판정기 5종의 실측 출처: ``server/web/session.py`` 의
    ``_infer_confirmed_role``(835~861행) 구현 + 866행 주석("`_infer_confirmed_role`
    이 내는 역할 5종만 다루면 되므로 "other" 는 방어적으로만 존재한다").
    """

    def test_classifier_roles_constant_is_exactly_five(self):
        assert len(CLASSIFIER_ROLES) == 5
        assert set(CLASSIFIER_ROLES) == {"intro", "verse", "chorus", "bridge", "finale"}

    def test_finale_remaps_to_outro_and_sets_director_confirm(self):
        result = remap_classifier_role("finale")
        assert result.section == "Outro"
        assert result.original == "finale"  # REQ-008 — 원래 판정기 이름 보존
        assert result.director_confirm is True  # REQ-009

    def test_last_chorus_remaps_to_final_chorus_and_sets_director_confirm(self):
        result = remap_classifier_role("chorus", is_last_chorus=True)
        assert result.section == "Final Chorus"
        assert result.original == "chorus"
        assert result.director_confirm is True

    def test_non_last_chorus_remaps_to_plain_chorus_without_confirm(self):
        result = remap_classifier_role("chorus", is_last_chorus=False)
        assert result.section == "Chorus"
        assert result.original == "chorus"
        assert result.director_confirm is False

    @pytest.mark.parametrize(
        ("role", "expected_section"),
        [("intro", "Intro"), ("verse", "Verse"), ("bridge", "Bridge")],
    )
    def test_plain_roles_remap_without_director_confirm(self, role, expected_section):
        result = remap_classifier_role(role)
        assert result.section == expected_section
        assert result.original == role
        assert result.director_confirm is False

    def test_unknown_classifier_role_is_rejected_with_field_and_value(self):
        with pytest.raises(VocabError) as excinfo:
            remap_classifier_role("prechorus")
        message = str(excinfo.value)
        assert "prechorus" in message

    def test_remap_sequence_finds_last_chorus_by_position(self):
        # 6개 후렴 중 마지막(인덱스 4)만 Final Chorus 로 승급해야 한다.
        roles = ["intro", "verse", "chorus", "verse", "chorus", "finale"]
        results = remap_classifier_roles(roles)
        assert [r.section for r in results] == [
            "Intro",
            "Verse",
            "Chorus",
            "Verse",
            "Final Chorus",
            "Outro",
        ]
        assert [r.director_confirm for r in results] == [
            False,
            False,
            False,
            False,
            True,
            True,
        ]
        # 원래 판정기 이름은 전부 보존된다(REQ-008).
        assert [r.original for r in results] == roles

    def test_remap_sequence_with_no_chorus_at_all(self):
        roles = ["intro", "verse", "bridge", "finale"]
        results = remap_classifier_roles(roles)
        assert [r.section for r in results] == ["Intro", "Verse", "Bridge", "Outro"]
