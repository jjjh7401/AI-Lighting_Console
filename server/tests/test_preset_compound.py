"""합성 프리셋 문장 — 한 문장이 계열을 둘 이상 지정했을 때의 행선지.

실측 근거(2026-08-19): "포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을
설정하고 복합 프리셋도 All에 설정해줘"가 사전 핸들러 22개 중 **하나도 매치하지
못해** LLM 경로로 흘러 'Home' 하나만 생겼다. 어휘를 넓히면(슬라이스 B) 이번에는
다른 사고가 남는다 — ``run_instruction``\\ 의 체인은 **첫 매칭 하나만 실행하고 턴을
끝내므로**, 여섯 계열을 지정한 문장에서 한 계열만 저장되고 나머지는 조용히
사라진다.

그래서 이 파일이 겨누는 계약은 둘이다.

1. **회귀 방지가 최우선이다.** 계열이 하나뿐인 문장은 카드도 새 문면도 없이
   기존 단일 경로로 그대로 흘러야 한다. 합성 경로가 단일 요청의 행선지를 한
   글자도 바꾸면 안 된다.
2. 계열이 둘 이상이면 **묻는다.** 사람 대신 고르는 것은 추측이고
   ``Store Preset``\\ 은 경고 없이 덮어쓴다. 카드는 계열마다 한 장이 아니라
   다중 선택 **한 장**이고, 고른 계열은 ``PRESET_FAMILIES`` 등록 순서로 이어서
   실행된다.

판정 방식: 계열 핸들러를 **더블로 갈아끼워** 호출 순서를 직접 단언한다. 시작
번호 카드·덮어쓰기 동의·계열별 독립 번들은 그 핸들러들 **안에** 있고 이미
``test_web_session.py``\\ 가 겨누고 있으므로, 여기서 다시 검증하면 합성 경로가
그 규율을 복제했다는 뜻이 된다 — 이 파일은 복제가 없음을, 즉 원본 핸들러가
그대로 불린다는 것만 증명한다.
"""

from __future__ import annotations

import pytest

from server.llm.types import ToolCall
from server.orchestrator.runner import InstructionResult
from server.orchestrator.tools import CommandOutcome
from server.web.question import UNANSWERED
from server.web.session import (
    _BASIC_COLORS_REQUEST,
    _BASIC_DIMMER_REQUEST,
    PRESET_FAMILIES,
)

from .test_runner_self_correction import ScriptedProvider, _final
from .test_web_session import (
    _M0_POOL_INDEX,
    _all_commands,
    _PresetPoolRegistry,
    _session,
    _writes,
)

#: 진단에 실린 그 문장 그대로 — 여섯 계열이 한 문장에 담겨 있다.
COMPOUND_TEXT = (
    "포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을 설정하고 복합 프리셋도 All에 설정해줘"
)

#: 진단 문장이 실제로 지정하는 계열 — 레지스트리 **전체**가 아니다. FX 포지션
#: (연출 포지션)은 이 문장에 없으므로 카드에도 오르면 안 된다. 레지스트리가
#: 자라도 이 파일이 조용히 틀리지 않도록 문장에서 유도한다.
DETECTED_FAMILIES = tuple(f for f in PRESET_FAMILIES if f.matches(COMPOUND_TEXT))

_FAMILY_HANDLERS = {
    "basic_position": "_basic_position_presets",
    "fx_position": "_fx_position_presets",
    "basic_color": "_basic_color_presets",
    "basic_dimmer": "_basic_dimmer_presets",
    "color_phaser": "_color_phaser_presets",
    "dimmer_phaser": "_dimmer_phaser_presets",
    "combo_phaser": "_combo_phaser_presets",
}


class _RecordingChannel:
    """질문 카드를 기록하고 대본대로 답한다(답이 없으면 미응답)."""

    def __init__(self, answers=()):
        self.answers = list(answers)
        self.asked = []

    def ask(self, request, **_kwargs):
        self.asked.append(request)
        return self.answers.pop(0) if self.answers else UNANSWERED


def _family_result(key: str) -> InstructionResult:
    """계열 하나가 실제로 저장했을 때와 같은 모양의 결과."""
    return InstructionResult(
        status="ok",
        text=f"{key} 프리셋 10종을 저장 요청했습니다.",
        command_outcomes=(
            CommandOutcome(command=f"Store Preset {key}", status="executed_ok", detail="d"),
        ),
        retries_used=0,
        model_calls=0,
        duration_seconds=0.0,
    )


def _stub_families(session, calls, *, raising=(), declining=()):
    """일곱 계열 핸들러를 호출 기록 더블로 갈아끼운다.

    ``raising``\\ 은 예외를 던지는 계열, ``declining``\\ 은 ``None``\\ 을 돌리는
    계열이다.

    더블은 실제 핸들러와 **같은 시그니처**여야 한다. 합성 경로는 `forced=True`
    로 부르는데(카드에서 확정된 계열은 트리거를 다시 묻지 않는다), 더블이 그
    인자를 못 받으면 TypeError가 나고 합성 핸들러의 예외 처리에 삼켜져 "오류로
    건너뜀"으로 보고된다 — 진짜 회귀와 구별되지 않는 침묵이다.
    """

    def make(key):
        def handler(text, *, forced=False):
            calls.append((key, text, forced))
            if key in raising:
                raise RuntimeError(f"{key} 콘솔 왕복 실패")
            if key in declining:
                return None
            return _family_result(key)

        return handler

    for key, name in _FAMILY_HANDLERS.items():
        setattr(session, name, make(key))


def _build(tmp_path, *, answers=(), channel=True, raising=(), declining=()):
    session, _console, _audit, _sent, _chan = _session(tmp_path, ScriptedProvider([]))
    calls: list[tuple[str, str]] = []
    _stub_families(session, calls, raising=raising, declining=declining)
    question = _RecordingChannel(answers) if channel else None
    session._question_channel = question
    return session, calls, question


def _ordered(keys):
    """``PRESET_FAMILIES`` 등록 순서로 정렬된 키 목록."""
    wanted = set(keys)
    return [family.key for family in PRESET_FAMILIES if family.key in wanted]


class TestFamilyRegistry:
    """레지스트리는 합성 경로의 어휘·순서·표시명을 모두 결정한다."""

    def test_the_registry_order_and_keys_are_the_contract(self):
        assert [family.key for family in PRESET_FAMILIES] == [
            "basic_position",
            "fx_position",
            "basic_color",
            "basic_dimmer",
            "color_phaser",
            "dimmer_phaser",
            "combo_phaser",
        ]

    def test_the_set_is_seven_families_of_ten(self):
        """7계열 × 10종 = 70종이 이 앱의 프리셋 세트 전부다.

        FX 포지션이 레지스트리에서 빠져 카드에 60종만 올랐던 적이 있다
        (2026-08-19 사용자 지적) — 계열 수와 카탈로그 길이를 함께 못 박는다.
        """
        from server.spatial.pointing import BASIC_POSITION_SEQUENCE, FX_POSITION_SEQUENCE
        from server.web.session import (
            COLOR_PHASER_SEQUENCE,
            COMBO_PHASER_SEQUENCE,
            DIMMER_PHASER_SEQUENCE,
        )

        assert len(PRESET_FAMILIES) == 7
        for catalogue in (
            BASIC_POSITION_SEQUENCE,
            FX_POSITION_SEQUENCE,
            COLOR_PHASER_SEQUENCE,
            DIMMER_PHASER_SEQUENCE,
            COMBO_PHASER_SEQUENCE,
        ):
            assert len(catalogue) == 10

    def test_the_diagnostic_sentence_does_not_summon_the_fx_positions(self):
        # 진단 문장은 '기본' 포지션만 말한다 — 연출 포지션까지 끌어오면
        # 사용자가 요청하지 않은 10종을 덮어쓸 후보로 올리는 셈이다.
        assert [family.key for family in DETECTED_FAMILIES] == [
            "basic_position",
            "basic_color",
            "basic_dimmer",
            "color_phaser",
            "dimmer_phaser",
            "combo_phaser",
        ]

    @pytest.mark.parametrize(
        "text",
        [
            "이펙트 포지션 프리셋 저장해줘",
            "조명연출을 위한 포지션 프리셋 저장해줘",
            "연출용 포지션 프리셋 설정해줘",
            "FX 포지션 프리셋 만들어줘",
        ],
    )
    def test_the_fx_positions_are_their_own_family(self, text):
        # 기본 포지션과 **다른** 카탈로그다 — 둘 다 후보로 오르면 카드가
        # 같은 Position 풀에 두 벌을 제안한다.
        assert [family.key for family in PRESET_FAMILIES if family.matches(text)] == ["fx_position"]

    def test_both_position_families_ride_together_when_both_are_named(self):
        text = "기본 포지션이랑 이펙트 포지션 프리셋 저장해줘"
        assert [family.key for family in PRESET_FAMILIES if family.matches(text)] == [
            "basic_position",
            "fx_position",
        ]

    # 합성 경로는 키마다 **기존** 핸들러를 부른다 — 하나라도 이름이 틀리면
    # ``getattr``\가 런타임에 터지므로 대응을 여기서 고정한다.
    def test_every_family_maps_to_an_existing_handler(self, tmp_path):
        session, _console, _audit, _sent, _chan = _session(tmp_path, ScriptedProvider([]))
        mapping = session._COMPOUND_FAMILY_HANDLERS
        assert set(mapping) == {family.key for family in PRESET_FAMILIES}
        assert mapping == _FAMILY_HANDLERS
        for name in mapping.values():
            assert callable(getattr(session, name))


class TestSingleFamilyIsUntouched:
    """가장 중요한 계약 — 계열이 하나뿐인 문장의 행선지는 바뀌지 않는다."""

    @pytest.mark.parametrize(
        "text",
        [
            "기본 포지션 프리셋을 11번부터 저장해줘",
            "기본 컬러 프리셋을 21번부터 저장해줘",
            "기본 디머 프리셋을 11번부터 저장해줘",
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            "디머 페이저 프리셋을 21번부터 저장해줘",
            "콤보 페이저 프리셋을 41번부터 저장해줘",
        ],
    )
    def test_a_single_family_sentence_returns_none_without_asking(self, tmp_path, text):
        session, calls, question = _build(tmp_path)

        assert session._compound_preset_request(text) is None
        assert question.asked == []
        assert calls == []

    # 체인 수준 확인 — 합성 핸들러가 맨 앞에 등록됐어도 단일 문장을 가로채지
    # 않고, 턴은 그대로 **단일 계열 핸들러 하나**로 끝난다. 여기서 더블은
    # 트리거를 보지 않으므로 "어느 계열이 받는가"는 체인 등록 순서가 정하는
    # 별개 계약(PresetLexicon의 트리거 테스트)이다 — 이 테스트가 겨누는 것은
    # 「카드 없이, 정확히 한 계열만」이다.
    def test_the_compound_handler_declines_and_the_chain_runs_one_family(self, tmp_path):
        session, calls, question = _build(tmp_path)
        original = session._compound_preset_request
        seen: list[object] = []

        def spy(text):
            outcome = original(text)
            seen.append(outcome)
            return outcome

        session._compound_preset_request = spy

        session.run_instruction("기본 디머 프리셋을 11번부터 저장해줘")

        assert seen == [None]  # 합성 경로가 문장을 삼키지 않았다
        assert question.asked == []  # 새 카드도 없다
        assert len(calls) == 1  # 기존 체인대로 한 계열만 실행됐다

    # 계열이 0개인 문장(프리셋 요청이 아님)도 합성 경로를 건드리지 않는다.
    def test_a_sentence_with_no_family_is_not_a_compound_request(self, tmp_path):
        session, calls, question = _build(tmp_path)

        assert session._compound_preset_request("무빙 10대를 일렬로 배치해줘") is None
        assert question.asked == []
        assert calls == []


class TestExplicitPresetNounBypassesEveryPresetHandler:
    """이펙트 생성 요청은 신규 프리셋 저장 경로에 들어가지 않는다."""

    def test_color_effect_request_without_preset_never_raises_a_store_card(self, tmp_path):
        text = (
            "원형을 따라 회전하는 B-R 컬러 루프 이펙트를 만들어줘. "
            "전체가 바뀌는 것이 아니라 원형을 따라서 B/R 컬러 이펙트를 만들어줘."
        )
        provider = ScriptedProvider([_final("컬러 루프 이펙트 설계를 계속합니다.")])
        session, console, _audit, _sent, _approval = _session(tmp_path, provider)
        question = _RecordingChannel()
        session._question_channel = question

        event = session.run_instruction(text)

        assert question.asked == []
        assert console.executed == []
        # 프리셋 핸들러가 아니라 모델 연출 경로까지 실제로 흘렀다.
        assert len(provider.calls) == 1
        assert event["text"] == "컬러 루프 이펙트 설계를 계속합니다."


class TestCompositeVocabularyIsNotACompoundRequest:
    """어휘가 여러 개인 것과 **요청이** 여러 개인 것은 다르다.

    2026-08-17 리뷰가 등록 순서로 고정한 세 문장은 축 어휘를 둘씩 담고도 한
    계열을 요청한다("기본 디머 페이저"의 '기본'은 수식어이고, "컬러 디머"는
    콤보 계열의 **이름**이다). 합성 카드가 그 문장들을 가로채면 이미 출하된
    라우팅(``test_web_session.py``\\ 의 ``test_a_composite_*_routes_to_the_*``)이
    카드로 갈아치워진다.

    이 계약은 ``PRESET_FAMILIES``\\ 의 ``matches`` 한 곳에서 지켜진다 — 합성
    핸들러는 두 번째 판정 규칙을 두지 않는다. 그래서 여기서 겨누는 것은
    「감지 결과가 한 계열이므로 카드가 서지 않는다」는 연결이다.
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("기본 멀티컬러 페이저 프리셋을 31번부터 저장해줘", "color_phaser"),
            ("기본 디머 이펙트 프리셋을 21번부터 저장해줘", "dimmer_phaser"),
            ("컬러 디머 페이저 프리셋을 51번부터 저장해줘", "combo_phaser"),
        ],
    )
    def test_a_shipped_composite_routing_is_never_replaced_by_a_card(
        self, tmp_path, text, expected
    ):
        session, calls, question = _build(tmp_path)

        assert [f.key for f in PRESET_FAMILIES if f.matches(text)] == [expected]
        assert session._compound_preset_request(text) is None
        assert question.asked == []
        assert calls == []

    # 재생성 문장은 계열을 0개 내므로 카드가 서지 않는다 — 저장 동사('잡아')를
    # 공유하는 재생성 요청이 저장 카드로 바뀌면 제자리 갱신이 신규 저장으로
    # 둔갑한다.
    @pytest.mark.parametrize(
        "text",
        [
            "기본 컬러랑 기본 포지션 다시 잡아줘",
            "멀티컬러 페이저 재생성해줘",
        ],
    )
    def test_a_regeneration_sentence_never_raises_a_store_card(self, tmp_path, text):
        session, calls, question = _build(tmp_path)

        assert session._compound_preset_request(text) is None
        assert question.asked == []
        assert calls == []

    # 축을 말하지 않은 「페이저 프리셋 설정해줘」는 단일 트리거를 하나도
    # 매치하지 않는다 — 카드가 이 문장의 **유일한** 해소 경로다. 여기서 계열을
    # 추측하면 지정하지 않은 풀을 덮어쓴다.
    def test_an_axis_less_phaser_sentence_is_resolved_by_the_card(self, tmp_path):
        session, calls, question = _build(tmp_path, answers=["디머 페이저"])

        session.run_instruction("페이저 프리셋 설정해줘")

        assert len(question.asked) == 1
        # 카드는 일곱 계열을 모두 싣고, 문장이 지목한 것만 미리 체크한다.
        card = question.asked[0]
        assert [option.label for option in card.options] == [
            family.label for family in PRESET_FAMILIES
        ]
        assert [option.label for option in card.options if option.selected] == [
            "컬러 페이저",
            "디머 페이저",
            "콤보 페이저",
        ]
        assert [key for key, _text, _forced in calls] == ["dimmer_phaser"]


class TestCompoundCard:
    """계열이 둘 이상이면 다중 선택 카드 **한 장**이 선다."""

    def test_the_diagnostic_sentence_raises_exactly_one_multi_select_card(self, tmp_path):
        session, _calls, question = _build(tmp_path, channel=True)

        session.run_instruction(COMPOUND_TEXT)

        assert len(question.asked) == 1
        card = question.asked[0]
        assert card.multi is True
        # 카드는 일곱 계열 전부를 싣는다 — 문장이 여섯 개만 지목했어도 나머지
        # 하나를 부르려고 문장을 다시 쓰게 하지 않는다.
        assert [option.label for option in card.options] == [
            family.label for family in PRESET_FAMILIES
        ]
        # 체크된 것이 문장이 지목한 계열이다.
        assert [option.label for option in card.options if option.selected] == [
            family.label for family in DETECTED_FAMILIES
        ]
        assert [option.label for option in card.options if not option.selected] == ["연출 포지션"]
        # 왜 묻는지가 카드에 있다 — 계열마다 시작 번호를 따로 여쭤본다는 사실.
        assert "시작 번호" in card.why
        assert card.to_dict()["multi"] is True

    def test_choosing_every_family_runs_them_in_registry_order(self, tmp_path):
        labels = ", ".join(family.label for family in DETECTED_FAMILIES)
        session, calls, question = _build(tmp_path, answers=[labels])

        event = session.run_instruction(COMPOUND_TEXT)

        assert len(question.asked) == 1  # 계열마다 한 장이 아니라 한 장뿐
        assert [key for key, _text, _forced in calls] == [
            family.key for family in DETECTED_FAMILIES
        ]
        # 각 계열은 **원문 그대로** 받는다 — 그 안에서 「N번부터」를 스스로 읽는다.
        assert {text for _key, text, _forced in calls} == {COMPOUND_TEXT}
        # 카드에서 확정된 계열은 트리거를 다시 묻지 않는다.
        assert all(forced for _key, _text, forced in calls)
        assert event["status"] == "ok"
        for family in DETECTED_FAMILIES:
            assert family.label in event["text"]

    def test_only_the_chosen_families_run(self, tmp_path):
        session, calls, _question = _build(tmp_path, answers=["콤보 페이저, 기본 컬러"])

        event = session.run_instruction(COMPOUND_TEXT)

        # 체크 순서(콤보 먼저)가 아니라 등록 순서(기본 컬러 먼저)로 실행된다.
        assert [key for key, _text, _forced in calls] == _ordered({"basic_color", "combo_phaser"})
        assert [key for key, _text, _forced in calls] == ["basic_color", "combo_phaser"]
        assert "기본 포지션" not in event["text"]

    def test_a_single_chosen_family_runs_alone(self, tmp_path):
        session, calls, _question = _build(tmp_path, answers=["기본 디머"])

        session.run_instruction(COMPOUND_TEXT)

        assert [key for key, _text, _forced in calls] == ["basic_dimmer"]

    def test_the_answer_survives_a_comma_without_a_space(self, tmp_path):
        session, calls, _question = _build(tmp_path, answers=["기본 컬러,디머 페이저"])

        session.run_instruction(COMPOUND_TEXT)

        assert [key for key, _text, _forced in calls] == ["basic_color", "dimmer_phaser"]

    def test_every_offered_family_is_a_valid_answer(self, tmp_path):
        """카드가 **제시한** 것과 답으로 **받는** 것은 같은 집합이어야 한다.

        2026-08-19 실측: 카드에 일곱 줄이 뜨는데 답 검증은 문장이 지목한
        여섯 계열로만 해서, 일곱 줄을 다 체크하자 «연출 포지션»만 "알아보지
        못했다"며 전부 중단됐다. 미체크로 실어 둔 계열을 고를 수 있게 한
        것이 카드의 요점이므로, 실어 둔 이상 받아야 한다.
        """
        every_label = ", ".join(family.label for family in PRESET_FAMILIES)
        session, calls, question = _build(tmp_path, answers=[every_label])

        event = session.run_instruction(COMPOUND_TEXT)

        # 문장은 여섯 계열만 지목했지만 카드는 일곱을 실었다.
        assert len(DETECTED_FAMILIES) == 6
        assert [option.label for option in question.asked[0].options] == [
            family.label for family in PRESET_FAMILIES
        ]
        # 일곱 개 전부가 등록 순서대로 실행된다 — 거부되는 이름이 없다.
        assert [key for key, _text, _forced in calls] == [family.key for family in PRESET_FAMILIES]
        assert "알아보지 못해" not in event["text"]


class TestNoAnswerStoresNothing:
    """답을 못 받으면 아무것도 저장하지 않고 그 사실을 보고한다."""

    def test_an_unanswered_card_writes_nothing(self, tmp_path):
        session, calls, question = _build(tmp_path, answers=[])

        event = session.run_instruction(COMPOUND_TEXT)

        assert len(question.asked) == 1
        assert calls == []
        assert "저장하지 않았습니다" in event["text"]

    # UI가 붙지 않은 세션도 같다 — 계열을 몰래 고르지 않는다.
    def test_no_question_channel_writes_nothing(self, tmp_path):
        session, calls, _question = _build(tmp_path, channel=False)

        event = session.run_instruction(COMPOUND_TEXT)

        assert calls == []
        assert "저장하지 않았습니다" in event["text"]

    def test_an_unrecognised_answer_stops_without_guessing(self, tmp_path):
        session, calls, _question = _build(tmp_path, answers=["아무거나 다 해줘"])

        event = session.run_instruction(COMPOUND_TEXT)

        assert calls == []
        assert "아무거나 다 해줘" in event["text"]
        # 고를 수 있는 이름을 다시 보여 준다 — 막힌 벽으로 끝내지 않는다.
        assert "기본 포지션" in event["text"]

    # 일부만 알아본 답도 추측하지 않는다 — 알아본 계열만 몰래 저장하면
    # 사용자가 지정하지 않은 번호대를 덮어쓸 수 있다.
    def test_a_partly_unrecognised_answer_stores_nothing(self, tmp_path):
        session, calls, _question = _build(tmp_path, answers=["기본 컬러, 무드 프리셋"])

        event = session.run_instruction(COMPOUND_TEXT)

        assert calls == []
        assert "무드 프리셋" in event["text"]


class TestRealHandlersKeepTheirOwnGuards:
    """더블 없이 — 계열마다 **자기** 시작 번호 카드를 그대로 낸다.

    합성 경로가 규율을 복제하지 않았다는 것의 증명이다: 카드 문면·번호 파싱·
    덮어쓰기 가드·계열별 독립 번들은 전부 원본 핸들러 안에서 일어나고, 합성
    핸들러는 그 핸들러를 순서대로 부르기만 한다. 문장에 「N번부터」가 없으므로
    두 계열은 각각 번호를 물어야 하며, 두 계열이 같은 번호를 쓰지 않는지는
    운영자가 카드에서 정한다.
    """

    @staticmethod
    def _real_rig(tmp_path, *, pool_index, answers):
        """더블 없는 계열 핸들러 + 실측 풀 페이로드 리그.

        스텁은 **소재 공급**뿐이다(패치 열거, 컬러 판별) — 이 둘은
        ``TestColorCapabilityDiscrimination``\\ 이 따로 겨누고 있고, 여기서
        겨누는 것은 카드·가드·번들이다.
        """
        session, _console, _audit, _sent, _ = _session(tmp_path, ScriptedProvider([]))
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, pool_index=pool_index, pool=(1, 2, 3))
        session._color_rig_fixture_pairs = lambda: ([(20, 20), (26, 26)], [])
        session._color_capable_fids = lambda _pairs, *, probe_id_prefix: ([20, 26], [], [])
        question = _RecordingChannel(answers)
        session._question_channel = question
        return session, calls, question

    def test_two_families_each_raise_their_own_start_number_card(self, tmp_path):
        session, calls, question = self._real_rig(
            tmp_path,
            pool_index=_M0_POOL_INDEX,
            answers=["기본 컬러, 기본 디머", "21", "41"],
        )

        event = session.run_instruction("기본 컬러 프리셋과 기본 디머 프리셋을 저장해줘")

        # 카드 세 장: 계열 선택 한 장 + 계열마다 시작 번호 한 장.
        prompts = [card.prompt for card in question.asked]
        assert len(prompts) == 3
        assert question.asked[0].multi is True
        assert [card.multi for card in question.asked[1:]] == [False, False]
        assert "기본 컬러" in prompts[1] and "몇 번부터" in prompts[1]
        assert "디머 레벨" in prompts[2] and "몇 번부터" in prompts[2]

        # 각 계열은 자기 풀에, 운영자가 고른 번호부터 저장한다 (Color=4, Dimmer=1).
        commands = _all_commands(calls)
        assert "Store Preset 4.21" in commands
        assert "Store Preset 4.30" in commands
        assert "Store Preset 1.41" in commands
        assert "Store Preset 1.50" in commands
        # 계열별 독립 번들 그대로 — 룩마다 한 번의 run_commands, 20건.
        assert len(_writes(calls)) == 20
        # /Merge·/Overwrite는 어느 계열에서도 쓰지 않는다(블랙리스트).
        assert not any("/Merge" in cmd or "/Overwrite" in cmd for cmd in commands)
        assert "기본 컬러" in event["text"] and "디머 레벨" in event["text"]

    # 계열 하나가 거부돼도(풀 미상) 나머지는 계속 저장한다 — 실행 순서는
    # 등록 순서이므로 거부가 앞 계열에서 나도 뒤 계열이 살아난다.
    def test_a_refused_family_does_not_take_the_other_down(self, tmp_path):
        # Color 풀이 목록에 없다 → 기본 컬러는 풀 미상으로 거부된다.
        session, calls, _question = self._real_rig(
            tmp_path,
            pool_index={1: "Dimmer", 2: "Position"},
            answers=["기본 컬러, 기본 디머", "41"],
        )

        event = session.run_instruction("기본 컬러 프리셋과 기본 디머 프리셋을 저장해줘")

        commands = _all_commands(calls)
        assert "Color 풀을 찾지 못했습니다" in event["text"]
        assert "Store Preset 1.41" in commands  # 디머는 그대로 저장됐다
        assert not any(cmd.startswith("Store Preset 4.") for cmd in commands)

    # 2026-08-19 실측 회귀: 카드에서 일곱 계열을 다 골랐는데 **둘만** 저장되고
    # 다섯이 "저장 조건을 확정하지 못해 건너뛰었습니다"로 돌아왔다. 계열
    # 핸들러가 자기 트리거를 다시 검사했기 때문이다 — 트리거는 「수식어 → 축
    # → 동사」 어순을 요구하는 단일 요청용 그물이라 열거형 문장을 받지 않는다.
    # 계열은 레지스트리가 판정하고 사용자가 카드에서 확정했으므로, 그 뒤에
    # 트리거를 다시 묻는 것은 확정을 뒤집는 일이다.
    def test_an_enumerating_sentence_still_stores_every_chosen_family(self, tmp_path):
        session, calls, question = self._real_rig(
            tmp_path,
            pool_index=_M0_POOL_INDEX,
            answers=["기본 컬러, 기본 디머", "21", "41"],
        )

        # 이 문장은 기본 컬러·기본 디머 **트리거를 둘 다 매치하지 않는다**.
        assert _BASIC_COLORS_REQUEST.search(COMPOUND_TEXT) is None
        assert _BASIC_DIMMER_REQUEST.search(COMPOUND_TEXT) is None

        event = session.run_instruction(COMPOUND_TEXT)

        commands = _all_commands(calls)
        assert "Store Preset 4.21" in commands  # 기본 컬러 10종
        assert "Store Preset 4.30" in commands
        assert "Store Preset 1.41" in commands  # 디머 레벨 10종
        assert "Store Preset 1.50" in commands
        assert len(_writes(calls)) == 20
        # 건너뛰었다는 보고가 없어야 한다 — 고른 계열은 실제로 저장된다.
        assert "저장 조건을 확정하지 못해" not in event["text"]
        # 계열마다 자기 시작 번호 카드는 그대로 뜬다(선택 1 + 번호 2).
        assert len(question.asked) == 3


class TestOneFamilyFailingKeepsTheRest:
    """look 하나가 거부돼도 나머지를 살리는 기존 번들 규율과 같은 형상."""

    def test_a_raising_family_does_not_stop_the_others(self, tmp_path):
        labels = ", ".join(family.label for family in DETECTED_FAMILIES)
        session, calls, _question = _build(tmp_path, answers=[labels], raising={"basic_color"})

        event = session.run_instruction(COMPOUND_TEXT)

        assert [key for key, _text, _forced in calls] == [
            family.key for family in DETECTED_FAMILIES
        ]
        assert "기본 디머" in event["text"]  # 실패한 계열 뒤도 계속 진행했다
        assert "미저장" in event["text"] and "기본 컬러" in event["text"]

    # REQ-MVP-044 — 예외 원문은 표면에 나오지 않고 감사 로그로만 간다.
    def test_the_raw_failure_detail_never_reaches_the_surface(self, tmp_path):
        labels = ", ".join(family.label for family in DETECTED_FAMILIES)
        session, _calls, _question = _build(tmp_path, answers=[labels], raising={"basic_color"})

        event = session.run_instruction(COMPOUND_TEXT)

        assert "RuntimeError" not in event["text"]
        assert "콘솔 왕복 실패" not in event["text"]

    def test_a_family_that_declines_the_sentence_is_disclosed_not_silent(self, tmp_path):
        labels = ", ".join(family.label for family in DETECTED_FAMILIES)
        session, calls, _question = _build(tmp_path, answers=[labels], declining={"combo_phaser"})

        event = session.run_instruction(COMPOUND_TEXT)

        assert [key for key, _text, _forced in calls] == [
            family.key for family in DETECTED_FAMILIES
        ]
        assert "건너뛰었습니다" in event["text"]
        assert "미저장" in event["text"] and "콤보 페이저" in event["text"]

    # 실행된 계열들의 명령 결과는 하나의 요약에 모여 표면에 도달한다.
    def test_the_summary_collects_every_family_outcome(self, tmp_path):
        labels = ", ".join(family.label for family in DETECTED_FAMILIES)
        session, _calls, _question = _build(tmp_path, answers=[labels])

        event = session.run_instruction(COMPOUND_TEXT)

        commands = [view["command"] for view in event["commands"]]
        assert commands == [f"Store Preset {family.key}" for family in DETECTED_FAMILIES]
