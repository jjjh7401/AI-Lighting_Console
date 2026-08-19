"""프리셋 요청 어휘 — 트리거 정규식과 계열 레지스트리의 판정.

여기는 실행 경로가 아니라 **판정**을 고정한다. 합성 문장이 실제로 카드를 세우고
계열을 순차 실행하는지는 ``test_preset_compound.py``가 본다.

두 층을 따로 본다.

* ``_*_REQUEST`` 트리거 — 계열 **하나**를 겨냥한 문장을 잡는 사전 핸들러의 진입
  조건. 어순(수식어 → 축 → 동사)을 요구한다.
* ``PRESET_FAMILIES[*].matches`` — 한 문장이 어느 계열들을 지정했나를 어순과
  무관하게 판정한다. 합성 핸들러가 선택 카드를 세울 근거다.

두 층이 필요한 이유가 이 파일의 회귀 방어 대상이다: 2026-08-19 실측에서
«포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을 설정하고 …» 문장이 사전
핸들러 22개 중 **하나도** 매치하지 못해 LLM으로 빠졌고(동사 '설정', 표기 '딤머',
일반 표현 '페이저', 어휘 '복합'이 모두 미인식), 반대로 «기본 딤머 프리셋
저장해줘»는 포지션 트리거의 일반 명사 '프리셋'에 걸려 **포지션** 프리셋 10종을
만들었다. 표기 오타 하나가 축을 바꿔 요청한 적 없는 풀을 덮어쓴 것이다.
"""

from __future__ import annotations

import pytest

from server.web.session import (
    _BASIC_COLORS_REQUEST,
    _BASIC_DIMMER_REQUEST,
    _BASIC_POSITIONS_REQUEST,
    _COLOR_PHASER_REQUEST,
    _COMBO_PHASER_REQUEST,
    _DIMMER_PHASER_REQUEST,
    _REGENERATE_DIMMER_PHASER_REQUEST,
    _REGENERATE_DIMMER_REQUEST,
    PRESET_FAMILIES,
)

#: 저장 트리거 여섯 — 계열 키로 찾는다.
_STORE_TRIGGERS = {
    "basic_position": _BASIC_POSITIONS_REQUEST,
    "basic_color": _BASIC_COLORS_REQUEST,
    "basic_dimmer": _BASIC_DIMMER_REQUEST,
    "color_phaser": _COLOR_PHASER_REQUEST,
    "dimmer_phaser": _DIMMER_PHASER_REQUEST,
    "combo_phaser": _COMBO_PHASER_REQUEST,
}


def _families(text: str) -> list[str]:
    """등록 순서대로 나열된, 이 문장이 지정한 계열 키들."""
    return [family.key for family in PRESET_FAMILIES if family.matches(text)]


class TestStoreVerbVocabulary:
    """'설정'·'세팅'은 저장 동사다 — 여섯 계열 전부에서."""

    @pytest.mark.parametrize(
        ("key", "text"),
        [
            ("basic_position", "기본 포지션 프리셋 {verb}해줘"),
            ("basic_color", "기본 컬러 프리셋 {verb}해줘"),
            ("basic_dimmer", "기본 디머 프리셋 {verb}해줘"),
            ("color_phaser", "멀티컬러 페이저 {verb}해줘"),
            ("dimmer_phaser", "디머 페이저 {verb}해줘"),
            ("combo_phaser", "콤보 페이저 {verb}해줘"),
        ],
    )
    @pytest.mark.parametrize("verb", ["저장", "만들", "생성", "설정", "세팅"])
    def test_every_family_accepts_the_new_verbs_alongside_the_shipped_ones(self, key, text, verb):
        assert _STORE_TRIGGERS[key].search(text.format(verb=verb)) is not None

    def test_reconfigure_is_not_a_store_verb(self):
        # '재설정'은 재생성 의도다. 저장 동사로 받으면 신규 저장 경로가 재생성
        # 문장을 삼킨다 — 재생성 어휘 확장은 별 건이라, 오늘처럼 어느 트리거도
        # 잡지 않고 모델 경로에 남는 쪽이 정직하다.
        text = "기본 포지션 프리셋 재설정해줘"
        assert [key for key, trigger in _STORE_TRIGGERS.items() if trigger.search(text)] == []
        assert _families(text) == []


class TestDimmerSpelling:
    """'딤머'·'딜머'는 실측된 사용자 표기다 — 저장·재생성 양쪽에 있어야 한다."""

    @pytest.mark.parametrize("word", ["디머", "딤머", "딜머", "dimmer"])
    def test_the_level_family_accepts_every_spelling(self, word):
        assert _BASIC_DIMMER_REQUEST.search(f"기본 {word} 프리셋 저장해줘") is not None

    @pytest.mark.parametrize("word", ["디머", "딤머", "딜머", "dimmer"])
    def test_the_phaser_family_accepts_every_spelling(self, word):
        assert _DIMMER_PHASER_REQUEST.search(f"{word} 페이저 만들어줘") is not None

    @pytest.mark.parametrize("word", ["디머", "딤머", "딜머", "dimmer"])
    def test_regeneration_accepts_every_spelling_too(self, word):
        # 표기 누락은 오타가 아니라 결함이다: 저장은 되는데 재생성은 안 되면
        # 운영자는 갱신됐다고 믿고 큐는 옛 값을 계속 가리킨다.
        assert _REGENERATE_DIMMER_REQUEST.search(f"기본 {word} 다시 잡아줘") is not None
        assert _REGENERATE_DIMMER_PHASER_REQUEST.search(f"{word} 페이저 다시 잡아줘") is not None


class TestPhaserAndCompoundNouns:
    """일반 표현 '페이저'와 사용자 어휘 '복합'."""

    def test_a_color_axis_plus_phaser_reaches_the_color_phaser_family(self):
        # 카탈로그 이름('멀티컬러')을 모르는 운영자의 어휘.
        assert _COLOR_PHASER_REQUEST.search("컬러 페이저 만들어줘") is not None

    def test_a_dimmer_axis_plus_phaser_reaches_the_dimmer_phaser_family(self):
        assert _DIMMER_PHASER_REQUEST.search("딤머 페이저 만들어줘") is not None

    def test_compound_is_another_name_for_the_combo_family(self):
        # 신규 프리셋 종류가 아니다 — 컬러+디머 혼합(All 1 풀) 그대로다.
        assert _COMBO_PHASER_REQUEST.search("복합 프리셋 저장해줘") is not None


class TestPositionMisroutingGuard:
    """포지션 트리거의 명사 대안 '프리셋'이 다른 축 문장을 삼키지 않는다."""

    @pytest.mark.parametrize(
        "text",
        [
            # 2026-08-19 실측 버그: 이 문장이 포지션 프리셋 10종을 만들었다.
            "기본 딤머 프리셋 저장해줘",
            "기본 딜머 프리셋 저장해줘",
            "기본 디머 프리셋 설정해줘",
            "기본 컬러 프리셋을 11번부터 저장해줘",
            "복합 프리셋 저장해줘",
            "드롭 프리셋 만들어줘",
        ],
    )
    def test_another_axis_without_a_position_noun_is_not_a_position_request(self, text):
        assert _BASIC_POSITIONS_REQUEST.search(text) is None

    @pytest.mark.parametrize(
        "text",
        [
            "기본 포지션 프리셋 저장해줘",
            "기본 포지션 프리셋 설정해줘",
            "기본 포지션 10개를 프리셋에 저장해줘",
            "기본 포지션 프리셋을 5번부터 만들어줘",
            "기본 포지션 프리셋을 41번부터 저장해줘",
            # 축 명사가 아예 없는 문장은 포지션이 기본값이다 — 출하된 동작.
            "기본 프리셋 저장해줘",
        ],
    )
    def test_position_and_bare_preset_sentences_still_land(self, text):
        assert _BASIC_POSITIONS_REQUEST.search(text) is not None


class TestFamilyRegistryVerdicts:
    """``matches``는 어순과 무관하게 "이 문장이 지정한 계열들"을 낸다."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # ── 계열 하나 — 오라우팅 없이 그 계열만 ────────────────────────
            ("기본 딤머 프리셋 설정해줘", ["basic_dimmer"]),
            ("기본 딜머 프리셋 설정해줘", ["basic_dimmer"]),
            ("기본 컬러 프리셋 세팅해줘", ["basic_color"]),
            ("기본 포지션 프리셋 설정해줘", ["basic_position"]),
            ("복합 프리셋 저장해줘", ["combo_phaser"]),
            ("딤머 페이저 만들어줘", ["dimmer_phaser"]),
            ("컬러 페이저 만들어줘", ["color_phaser"]),
            # '기본'은 수식어일 뿐 — 페이저 복합어가 있으면 계열은 여전히 하나다.
            ("기본 디머 페이저 저장해줘", ["dimmer_phaser"]),
            ("기본 멀티컬러 페이저 저장해줘", ["color_phaser"]),
            # 콤보 토큰이 컬러·디머 어휘를 품고 있어도 행선지는 콤보 하나다.
            ("컬러 디머 페이저 저장해줘", ["combo_phaser"]),
            ("콤보 페이저 저장해줘", ["combo_phaser"]),
            # ── 계열 여럿 — 카드로 물어야 하는 문장 ───────────────────────
            (
                "포지션, 컬러, 딤머의 기본 프리셋과 페이저 프리셋을 설정하고 "
                "복합 프리셋도 All에 설정해줘",
                [
                    "basic_position",
                    "basic_color",
                    "basic_dimmer",
                    "color_phaser",
                    "dimmer_phaser",
                    "combo_phaser",
                ],
            ),
            ("기본 컬러랑 기본 딤머 프리셋 설정해줘", ["basic_color", "basic_dimmer"]),
            # 운영자는 계열 이름('기본 포지션')이 아니라 축 + '프리셋'으로 말한다.
            # 열거형은 명사 하나를 축들이 나눠 쓴다.
            (
                "포지션 프리셋과 컬러 프리셋 저장해줘",
                ["basic_position", "fx_position", "basic_color", "color_phaser"],
            ),
            (
                "포지션, 컬러 프리셋 저장해줘",
                ["basic_position", "fx_position", "basic_color", "color_phaser"],
            ),
            (
                "컬러 페이저 프리셋과 디머 페이저 프리셋 저장해줘",
                ["color_phaser", "dimmer_phaser"],
            ),
            # ── 프리셋 저장 문장이 아닌 것들 ──────────────────────────────
            ("무빙 이펙트 적용해줘", []),
            ("무빙 이펙트 만들어줘", []),
            ("좌우 스윕 시퀀스 만들어줘", []),
            # 축 명사만으로는 부족하다 — '기본'도 '프리셋'도 없다.
            ("포지션 큐 만들어줘", []),
            ("포지션 시퀀스 저장해줘", []),
            # '이펙트 포지션'은 기하 골격 계열 — 기본 포지션과 다른 10종이다.
            ("이펙트 포지션 프리셋을 41번부터 저장해줘", ["fx_position"]),
            # 2026-08-17 리뷰가 등록 순서로 단일 행선지에 못박은 합성 어휘 —
            # 어휘가 여럿이어도 요청은 하나다.
            ("기본 멀티컬러 페이저 프리셋을 31번부터 저장해줘", ["color_phaser"]),
            ("기본 디머 이펙트 프리셋을 21번부터 저장해줘", ["dimmer_phaser"]),
            ("컬러 디머 페이저 프리셋을 51번부터 저장해줘", ["combo_phaser"]),
        ],
    )
    def test_the_registry_names_exactly_the_families_the_sentence_asked_for(self, text, expected):
        assert _families(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "페이저 프리셋 설정해줘",
            "페이저 프리셋 만들어줘",
        ],
    )
    def test_a_bare_phaser_request_is_ambiguous_across_all_three_phaser_families(self, text):
        # 축이 없으면 어느 한 계열로 **짐작하지 않는다** — 세 후보를 모두 올려
        # 합성 핸들러가 카드로 묻게 한다. 단일 트리거는 일부러 잡지 않는다.
        assert _families(text) == ["color_phaser", "dimmer_phaser", "combo_phaser"]
        assert [key for key, trigger in _STORE_TRIGGERS.items() if trigger.search(text)] == []

    @pytest.mark.parametrize(
        "text",
        [
            "기본 컬러 다시 잡아줘",
            "기본 포지션 다시 잡아줘",
            "이펙트 포지션 다시 잡아줘",
            "기본 딤머 다시 잡아줘",
            "콤보 페이저 재생성해줘",
            # 다축 재생성 — 재생성 어휘가 저장 동사('잡아')를 공유한다.
            "기본 컬러랑 포지션 다시 잡아줘",
        ],
    )
    def test_regeneration_sentences_name_no_store_family(self, text):
        # 레지스트리는 신규 저장 문장을 계열로 쪼개는 장치다. 재생성 문장을
        # 후보로 올리면 합성 경로가 재생성 요청을 저장 카드로 바꿔버린다.
        assert _families(text) == []


class TestDirectorVocabulary:
    """조명감독이 실제로 쓰는 말로 계열이 불려야 한다.

    2026-08-19 확장: 저장 동사는 「저장」만이 아니고(깔아·구성·준비·등록·채워),
    축도 콘솔 용어만 쓰지 않는다(포커스·팔레트·밝기·인텐시티·체이스).
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # 저장 동사 — 계열은 그대로, 부르는 말만 다르다.
            ("기본 포지션 프리셋 깔아줘", ["basic_position"]),
            ("기본 컬러 프리셋 구성해줘", ["basic_color"]),
            ("기본 디머 프리셋 준비해줘", ["basic_dimmer"]),
            ("기본 컬러 프리셋 등록해줘", ["basic_color"]),
            ("기본 포지션 프리셋 채워줘", ["basic_position"]),
            # 축 동의어 — 같은 계열을 다른 이름으로 부른다.
            ("포커스 프리셋 저장해줘", ["basic_position", "fx_position"]),
            ("위치 프리셋 저장해줘", ["basic_position", "fx_position"]),
            ("팔레트 프리셋 저장해줘", ["basic_color", "color_phaser"]),
            ("밝기 프리셋 저장해줘", ["basic_dimmer", "dimmer_phaser"]),
            ("인텐시티 프리셋 저장해줘", ["basic_dimmer", "dimmer_phaser"]),
            ("광량 프리셋 저장해줘", ["basic_dimmer", "dimmer_phaser"]),
            # 체이스는 페이저 어휘다 — 기본 계열까지 끌고 오면 카드에 두 줄이 뜬다.
            ("컬러 체이스 프리셋 저장해줘", ["color_phaser"]),
            ("디머 체이스 프리셋 저장해줘", ["dimmer_phaser"]),
            ("밝기 페이저 프리셋 만들어줘", ["dimmer_phaser"]),
        ],
    )
    def test_the_field_word_reaches_the_same_family(self, text, expected):
        assert _families(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["프리셋 재구성해줘", "기본 컬러 프리셋 재설정해줘", "포지션 프리셋 재등록해줘"],
    )
    def test_the_re_prefixed_verbs_are_not_a_store_request(self, text):
        # 재-접두 동사는 재생성 의도다. 저장 동사를 공유하므로 룩비하인드가
        # 없으면 신규 저장 카드로 끌려간다.
        assert _families(text) == []


class TestAllFamiliesVocabulary:
    """「전부/모두」는 일곱 계열을 한 번에 부른다."""

    @pytest.mark.parametrize(
        "text",
        [
            "프리셋 전부 저장해줘",
            "프리셋 모두 깔아줘",
            "프리셋 전체 등록해줘",
            "프리셋 7계열 전부 구성해줘",
            "70종 프리셋 풀세트 준비해줘",
            "프리셋 싹 만들어줘",
        ],
    )
    def test_it_names_every_family(self, text):
        assert _families(text) == [
            "basic_position",
            "fx_position",
            "basic_color",
            "basic_dimmer",
            "color_phaser",
            "dimmer_phaser",
            "combo_phaser",
        ]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("컬러 프리셋 전부 저장해줘", ["basic_color", "color_phaser"]),
            ("포지션 프리셋 모두 만들어줘", ["basic_position", "fx_position"]),
            ("디머 프리셋 전체 저장해줘", ["basic_dimmer", "dimmer_phaser"]),
        ],
    )
    def test_an_axis_narrows_it_back_to_that_axis(self, text, expected):
        # 축이 있으면 '전부'는 계열이 아니라 그 축의 10종을 가리킨다 —
        # 일곱 계열을 덮어쓸 후보로 올리면 묻지 않은 60칸이 위험해진다.
        assert _families(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["프리셋 전부 지워줘", "프리셋 전부 다시 잡아줘", "프리셋 전부 보여줘"],
    )
    def test_it_needs_a_store_verb(self, text):
        assert _families(text) == []


class TestForeignIntentsKeepTheirSentences:
    """프리셋 어휘를 지나가며 쓰는 남의 의도는 계열로 세지 않는다."""

    def test_a_song_design_brief_is_not_a_preset_store_request(self):
        # 곡 브리프는 시작 슬롯을 프리셋 번호로 적고 무드를 색·밝기로 쓴다.
        # 어순 무관 판정에는 컬러·디머로 보이지만 저장 요청이 아니다 —
        # 합성 카드가 체인 앞자리에서 이 문장을 가로채면 곡 설계가 멎는다.
        text = (
            "90초 록 곡 조명 설계를 만들어줘. 시퀀스 110, 프리셋 21번부터, 수동 Go. "
            "0:00 인트로는 파란색과 낮은 밝기로 시작하고, "
            "0:48 후렴에서 마젠타와 화이트로 가장 크게 터뜨려줘."
        )
        assert _families(text) == []

    def test_a_position_cue_sheet_is_not_a_preset_store_request(self):
        text = "포지션 큐 시트 만들어줘. 프리셋 21번부터, 인트로 0:00 잔잔"
        assert _families(text) == []

    def test_storing_a_preset_as_a_cue_is_not_a_preset_store_request(self):
        # «프리셋 28번 포지션을 큐로 저장» 은 프리셋을 **참조**해 큐를 만드는
        # 요청이다. 축만 말한 문장이 그 축의 계열을 전부 올리게 되면서 이
        # 문장이 두 계열로 보여 카드에 끌려갔다(2026-08-19 회귀).
        assert _families("프리셋 28번 포지션을 큐로 저장해줘, 페이드 3초") == []


class TestBareAxisOffersTheWholeAxis:
    """수식어 없이 축만 말하면 그 축의 계열을 **전부** 올린다.

    운영자는 축으로 말하지 계열 이름으로 말하지 않는다 — «딤머, 포지션,
    컬러, 콤보 프리셋을 설정해줘». 그 축에 기본·연출·페이저가 몇 벌 있는지는
    앱이 아는 사정이다. 좁혀서 올리면 있는 줄도 모르고 지나가고, 넓혀 올리면
    카드에서 체크를 풀면 그만이다(미체크는 아무것도 저장하지 않는다).
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("포지션 프리셋 저장해줘", ["basic_position", "fx_position"]),
            ("컬러 프리셋 저장해줘", ["basic_color", "color_phaser"]),
            ("딤머 프리셋 저장해줘", ["basic_dimmer", "dimmer_phaser"]),
            # 콤보 축에는 계열이 하나뿐이다 — 넓힐 것이 없다.
            ("콤보 프리셋 저장해줘", ["combo_phaser"]),
        ],
    )
    def test_an_axis_alone_brings_its_whole_axis(self, text, expected):
        assert _families(text) == expected

    def test_the_reported_sentence_brings_all_seven(self):
        assert _families("딤머, 포지션, 컬러, 콤보 프리셋을 설정해줘") == [
            "basic_position",
            "fx_position",
            "basic_color",
            "basic_dimmer",
            "color_phaser",
            "dimmer_phaser",
            "combo_phaser",
        ]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # 수식어가 하나라도 있으면 그 문장은 계열을 특정한 것이다.
            ("기본 포지션 프리셋 저장해줘", ["basic_position"]),
            ("기본 컬러 프리셋 저장해줘", ["basic_color"]),
            ("기본 딤머 프리셋 저장해줘", ["basic_dimmer"]),
            ("컬러 페이저 프리셋 저장해줘", ["color_phaser"]),
            ("딤머 페이저 프리셋 저장해줘", ["dimmer_phaser"]),
            ("이펙트 포지션 프리셋 저장해줘", ["fx_position"]),
        ],
    )
    def test_a_qualifier_keeps_it_narrow(self, text, expected):
        assert _families(text) == expected
