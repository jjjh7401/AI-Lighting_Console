"""`candidate_names` — "없다"고 말하기 전에 토큰까지 본다.

실기 2026-08-18: «robe esprite» 요청에 라이브러리의 «Robin Esprite»가 걸리지 않아
필요 없는 GUI 절차를 사용자에게 안내했다. 제조사(Robe)와 제품군(Robin) 표기가
다른 것은 실물에서 흔하다.
"""

from __future__ import annotations

from server.vwx.librarywatch import MIN_DISTINCTIVE_TOKEN, candidate_names

LIBRARY = (
    "Robin Esprite",
    "Robin Forte HP",
    "Robin LEDBeam 350",
    "Robin Spiider",
    "Xtylos",
    "Sharpy Plus",
)


class TestTheRealMiss:
    def test_robe_esprite_finds_robin_esprite(self):
        # [HARD] 이 한 줄이 그 사고다 — 부분문자열만 보면 후보가 0건이다.
        assert candidate_names("robe esprite", LIBRARY) == ("Robin Esprite",)

    def test_the_substring_path_still_works(self):
        assert candidate_names("esprite", LIBRARY) == ("Robin Esprite",)

    def test_an_exact_name_comes_first(self):
        assert candidate_names("Sharpy Plus", LIBRARY)[0] == "Sharpy Plus"


class TestItNeverGuessesWhenItCannot:
    def test_an_unrelated_name_yields_no_candidate(self):
        assert candidate_names("Martin Mac Aura XB", LIBRARY) == ()

    def test_an_empty_or_symbol_only_request_matches_nothing(self):
        # 공허한 이름으로 "일치"를 주장하면 라이브러리 전 항목이 후보가 된다.
        for value in ("", "   ", "---", "///"):
            assert candidate_names(value, LIBRARY) == (), repr(value)

    def test_a_short_token_does_not_sweep_the_library(self):
        # 'led'(3자)만 겹치는 요청이 LEDBeam을 끌어오면 3자 토큰이 기준이 된 것이다.
        assert candidate_names("led", LIBRARY) == ()

    def test_a_family_token_returns_every_member_so_the_user_chooses(self):
        # 'robin'은 네 제품에 공통이다 — 하나로 좁히지 않고 전부 후보로 낸다.
        assert candidate_names("robin 600", LIBRARY) == (
            "Robin Esprite",
            "Robin Forte HP",
            "Robin LEDBeam 350",
            "Robin Spiider",
        )


class TestTheMinimumTokenBoundaryIsTwoSided:
    """`MIN_DISTINCTIVE_TOKEN` 경계 — 등기부(`test_vwx_address.py`)의 대조군.

    `>= 3`으로 밀면 3자 조각이 라이브러리를 훑고, `>= 5`로 밀면 4자 제조사명
    ('robe')이 빠져 실기 사고가 그대로 재현된다. 두 방향을 각각 못박는다.
    """

    def test_a_four_letter_token_is_distinctive_enough(self):
        # 'robe'(정확히 4자)가 빠지면 «robe esprite» 사고가 재현된다.
        assert MIN_DISTINCTIVE_TOKEN == 4
        assert candidate_names("robe esprite", LIBRARY) == ("Robin Esprite",)

    def test_a_three_letter_token_is_not(self):
        # 'led'(3자)는 제품군을 가리지 못한다 — 후보 0건이어야 한다.
        assert candidate_names("led", LIBRARY) == ()
        assert candidate_names("hp 무빙", LIBRARY) == ()

    def test_the_substring_axis_uses_the_same_bound(self):
        # 4자 부분문자열은 통과, 3자는 불통 — 토큰 축과 같은 상수여야 한다.
        assert candidate_names("beam", ("Robin LEDBeam 350",)) == ("Robin LEDBeam 350",)
        assert candidate_names("bea", ("Robin LEDBeam 350",)) == ()
