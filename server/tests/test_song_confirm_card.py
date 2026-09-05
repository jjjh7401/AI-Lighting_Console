"""M2 — 확인 카드는 **오늘 스키마로**, **서버 코드가** 세운다 (AC-MUSICSYNC-015).

REQ-MUSICSYNC-009 · REQ-MUSICSYNC-015.

두 가지를 함께 판정한다.

1. **오늘 스키마 그대로다.** ``QuestionRequest`` 의 필드 집합은 변하지 않았고,
   구간표는 ``multi=True`` + 구간당 옵션 1개로 선다(design.md §4.3). 구조화
   payload 신설은 이 SPEC 밖이다.
2. **모델이 세우는 카드가 아니다.** ``ask_user`` 툴 스키마는 「EXACTLY ONE
   question」이고 ``selected``·``multi``·``commands`` 를 모델에 노출하지 않는다.
   즉 모델에게 구간표 카드를 부탁하는 경로는 **존재하지 않으며**, 존재하는
   것처럼 설계하면 런타임에 조용히 축소된 카드가 뜬다.

콘솔 접촉: 0건.
"""

from __future__ import annotations

import json

import pytest

from server.web.question import (
    ANSWER_FREEFORM,
    UNANSWERED,
    QuestionRequest,
    SongSectionProposal,
    build_song_confirmation_card,
    parse_confirmed_bpm,
)

PROPOSALS = (
    SongSectionProposal(start_ms=0, end_ms=16_000, d_level=1),
    SongSectionProposal(start_ms=16_000, end_ms=32_000, d_level=3),
    SongSectionProposal(start_ms=32_000, end_ms=36_000, d_level=5),
    SongSectionProposal(start_ms=36_000, end_ms=40_000, d_level=2),
)


def _card(**overrides) -> QuestionRequest:
    kwargs = {"proposals": PROPOSALS, "measured_bpm": 128.0, "bpm_confidence": 0.98}
    kwargs.update(overrides)
    return build_song_confirmation_card(**kwargs)


class TestTheCardStandsOnTodaysSchema:
    def test_the_card_is_a_plain_question_request(self):
        assert isinstance(_card(), QuestionRequest)

    def test_the_card_is_multi_select(self):
        # 단일 선택 카드는 구간 하나만 받고 나머지를 조용히 버린다.
        assert _card().multi is True

    def test_there_is_exactly_one_option_per_section(self):
        for count in (1, 2, 4):
            card = _card(proposals=PROPOSALS[:count])
            assert len(card.options) == count

    def test_every_dsp_proposed_section_arrives_pre_checked(self):
        # 사람이 **끄는 방식**으로 부분 수정할 수 있게 하는 것이 목적이다.
        assert all(option.selected for option in _card().options)

    def test_a_section_the_dsp_did_not_propose_arrives_unchecked(self):
        # 대조군: 전부 무조건 켜는 빌더면 위 시험은 공허하다.
        proposals = (*PROPOSALS[:3], SongSectionProposal(36_000, 40_000, 2, selected=False))
        assert [o.selected for o in _card(proposals=proposals).options] == [
            True,
            True,
            True,
            False,
        ]

    def test_each_option_label_names_the_span_and_the_grade(self):
        labels = [option.label for option in _card().options]
        assert "0:00" in labels[0]
        assert "D1" in labels[0]
        assert "D5" in labels[2]

    def test_the_measured_bpm_is_stated_on_the_card(self):
        card = _card()
        blob = json.dumps(card.to_dict(), ensure_ascii=False)
        assert "128" in blob

    def test_the_card_serialises_through_the_existing_to_dict(self):
        payload = _card().to_dict()
        assert payload["multi"] is True
        assert len(payload["options"]) == len(PROPOSALS)
        assert payload["options"][0]["selected"] is True


class TestTheQuestionRequestSchemaDidNotChange:
    """AC-MUSICSYNC-015 — 스키마 diff 가 비어 있다.

    빌더를 더한 것과 스키마를 고친 것은 다르다. 이 클래스는 후자가 일어나지
    않았음을 필드 집합으로 고정한다 — 필드가 하나라도 늘거나 줄면 실패한다.
    """

    def test_the_field_set_is_exactly_the_six_it_was(self):
        from dataclasses import fields

        assert [f.name for f in fields(QuestionRequest)] == [
            "prompt",
            "why",
            "steps",
            "commands",
            "options",
            "multi",
        ]

    def test_the_serialised_key_set_is_unchanged(self):
        assert set(QuestionRequest(prompt="x").to_dict()) == {
            "prompt",
            "why",
            "steps",
            "commands",
            "options",
            "multi",
        }


class TestTheModelIsNotTheOneBuildingThisCard:
    """AC-MUSICSYNC-015 — 카드를 세운 주체가 서버 코드임을 호출 경로로 본다."""

    def test_the_builder_is_a_plain_server_function_with_no_model_in_its_path(self):
        import inspect

        source = inspect.getsource(build_song_confirmation_card)
        # 모델을 부르는 어떤 경로도 이 함수 안에 없다.
        for needle in ("provider", "complete(", "ask_user", "ToolCall", "llm"):
            assert needle not in source, f"빌더가 {needle!r} 를 부른다"

    def test_the_ask_user_tool_schema_exposes_none_of_the_fields_this_card_needs(self):
        # 모델에게 이 카드를 부탁하는 경로가 **없다**는 것의 기계적 근거.
        from server.orchestrator.tools import build_toolset

        registry = build_toolset(execution_port=None, state_port=None)
        definition = next(d for d in registry.definitions() if d.name == "ask_user")
        schema = json.dumps(definition.parameters, ensure_ascii=False)
        assert "selected" not in schema
        assert '"multi"' not in schema
        assert '"commands"' not in schema

    def test_the_ask_user_tool_still_exists_unchanged(self):
        # 대조군: 툴이 사라졌다면 위 시험은 잘못된 이유로 통과한다.
        from server.orchestrator.tools import build_toolset

        registry = build_toolset(execution_port=None, state_port=None)
        names = [d.name for d in registry.definitions()]
        assert "ask_user" in names


class TestTheConfirmedBpmComesFromThePersonNotFromProse:
    """AC-MUSICSYNC-015 — BPM 이 LLM 응답에서 파생된 경로가 0건이다.

    사람의 답만이 BPM 을 정한다. 답을 읽는 규칙은 **명시적 토큰**이다 — 구간
    라벨에도 숫자가 들어 있으므로, 「답 안의 아무 숫자」를 BPM 으로 읽으면
    라벨의 초 단위 숫자가 템포가 된다.
    """

    def test_accepting_the_card_as_is_confirms_the_measured_value(self):
        answer = ", ".join(option.label for option in _card().options)
        assert parse_confirmed_bpm(answer, measured_bpm=128.0) == 128.0

    def test_a_typed_override_wins_over_the_measured_value(self):
        assert parse_confirmed_bpm("BPM 130", measured_bpm=128.0) == 130.0

    def test_the_override_token_is_case_insensitive_and_tolerates_spacing(self):
        assert parse_confirmed_bpm("bpm140", measured_bpm=128.0) == 140.0
        assert parse_confirmed_bpm("템포는 bpm  92.5 로 갑니다", measured_bpm=128.0) == 92.5

    def test_a_bare_number_in_a_section_label_is_not_read_as_a_tempo(self):
        # 이 시험이 없으면 「0:00–0:16 · D1」 의 16 이 BPM 이 된다.
        assert parse_confirmed_bpm("0:00–0:16 · D1", measured_bpm=128.0) == 128.0

    def test_an_unanswered_card_confirms_nothing(self):
        # 미응답은 거부가 아니라 **답을 못 받은 것**이다. 없는 답을 지어내지 않는다.
        assert parse_confirmed_bpm(UNANSWERED, measured_bpm=128.0) is None

    def test_a_freeform_handoff_confirms_nothing(self):
        assert parse_confirmed_bpm(ANSWER_FREEFORM, measured_bpm=128.0) is None

    def test_nothing_is_confirmed_when_there_was_no_measurement_and_no_override(self):
        assert parse_confirmed_bpm("네", measured_bpm=None) is None

    def test_a_nonsense_tempo_is_refused_rather_than_adopted(self):
        # 0 이나 음수를 그대로 받으면 MusicProfile 이 ProfileError 로 터진다.
        assert parse_confirmed_bpm("BPM 0", measured_bpm=128.0) == 128.0
        assert parse_confirmed_bpm("BPM 9999", measured_bpm=128.0) == 128.0


class TestTheFallbackCardIsTheSameCard:
    """plan.md §C 결정 1 폴백 — 분석기가 없어도 카드 경로는 산다.

    번들 델타가 상한을 넘어 분석을 개발 모드로만 열더라도, 패키징된 앱은
    **같은 확인 카드**로 수동 BPM 입력을 받는다(AC-MUSICSYNC-017).
    """

    def test_a_fallback_card_is_still_a_question_request(self):
        card = build_song_confirmation_card(
            proposals=(), measured_bpm=None, fallback_reason="분석기 없음"
        )
        assert isinstance(card, QuestionRequest)

    def test_the_fallback_card_says_why_there_are_no_proposals(self):
        card = build_song_confirmation_card(
            proposals=(), measured_bpm=None, fallback_reason="분석기 없음"
        )
        blob = json.dumps(card.to_dict(), ensure_ascii=False)
        assert "분석기 없음" in blob

    def test_the_fallback_card_asks_for_a_typed_bpm(self):
        card = build_song_confirmation_card(
            proposals=(), measured_bpm=None, fallback_reason="분석기 없음"
        )
        assert "BPM" in card.prompt or "BPM" in card.why

    def test_a_typed_bpm_still_lands_through_the_fallback_card(self):
        assert parse_confirmed_bpm("BPM 128", measured_bpm=None) == 128.0


class TestASheetTempoIsShownForComparison:
    def test_a_disagreeing_sheet_value_is_named_on_the_card(self):
        blob = json.dumps(_card(sheet_bpm=120.0).to_dict(), ensure_ascii=False)
        assert "120" in blob

    def test_the_card_does_not_invent_a_sheet_value_when_none_was_given(self):
        # 대조군: 시트 값이 없는데 있는 것처럼 적으면 지어낸 숫자다.
        blob = json.dumps(_card().to_dict(), ensure_ascii=False)
        assert "시트" not in blob


@pytest.mark.parametrize("bad", [None, 0, -1])
def test_the_builder_refuses_a_nonsense_section_count(bad):
    # 구간 수가 옵션 수라는 계약을 지키려면 입력 자체가 시퀀스여야 한다.
    with pytest.raises((TypeError, ValueError)):
        build_song_confirmation_card(proposals=bad, measured_bpm=128.0)
