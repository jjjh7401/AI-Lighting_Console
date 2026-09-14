"""카드 t405 — 같은 역할이 반복될 때 효과가 회차마다 달라진다.

고치기 전 실측(main@611ce34, ``src/Club Diver.mp3`` 를 앱 경로로 끝까지 태운
타임라인 39구간): 서로 다른 효과가 넷뿐이고 그중 **26구간이 바이트 동일한**
``('dimmer chase',)`` 였다. 역할 분포는 chorus 25 · verse 7 · bridge 5 ·
intro 1 · finale 1 — 역할 쏠림은 카드 t400 이 이미 풀었는데도 효과는 여전히
한 벌이었다. 원인이 레이어가 아니라 역할 표라는 것이 이 카드의 판정이다.

여기서 단언하는 것 셋:

1. 회차 1은 고치기 전과 **바이트 동일**하다 — 기존 룩을 안 흔든다.
2. 회차가 늘면 효과 묶음이 실제로 달라진다(색이 카드 t402 에서 한 것과 같은 축).
3. 감독 질감이 medium 이라 축이 하나로 깎여도 사다리가 살아 있다 — 예전에는
   이 자리에서 **항상 0번**을 집어 사다리가 통째로 지워졌다.

그리고 새로 쓰는 효과 이름이 지어낸 말이 아니라는 것 — 일곱 개 전부
``server/fx/library`` 의 실제 별칭이라 ``match_fx`` 가 fallback 없이 항목
하나로 건다. (기존 다섯 이름 ``dimmer chase``/``pan sweep``/``slow pan``/
``slow tilt``/``accent sweep`` 은 그러지 못한다 — 실측된 기존 간극이고 이
카드가 넓히지 않았다는 것만 아래에서 고정한다.)
"""

from __future__ import annotations

import pytest

from server.fx.loader import load_library_from_dir
from server.fx.matching import match_fx
from server.web.session import _ARC_FX, _ARC_FX_LADDER, _arc_fx_allowed

#: 이 카드가 새로 들여온 이름 → 걸려야 하는 라이브러리 항목.
NEW_LABEL_TO_FX_ID = {
    "horizontal chase": "chase-horizontal",
    "bounce chase": "chase-bounce-run",
    "v-shape swing": "sweep-vshape-swing",
    "soft wave": "wave-soft-rise",
    "cross diagonal": "diagonal-club-cross",
    "orbit": "circle-relative-orbit",
    "breathing": "pulse-breath",
}

#: 고치기 전부터 있던 이름 — 라이브러리에 안 걸린다(실측). 이 카드의 책임이
#: 아니지만, 목록이 조용히 늘어나면 알아채려고 여기 못박는다.
PRE_EXISTING_UNROUTED = ("dimmer chase", "pan sweep", "slow pan", "slow tilt", "accent sweep")

#: ``song_cue_composer._contains_any`` 가 효과 문자열을 이 토큰들로 되읽는다 —
#: 새 이름에 섞이면 구간이 통째로 블랙아웃/객석 조명으로 오판된다.
FORBIDDEN_TOKENS = (
    "blackout",
    "black out",
    "암전",
    "블랙아웃",
    "audience",
    "blinder",
    "blind",
    "객석",
    "블라인더",
)


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


class TestOccurrenceOneIsUnchanged:
    @pytest.mark.parametrize("role", sorted(_ARC_FX))
    def test_first_occurrence_matches_the_old_single_rung(self, role):
        assert _arc_fx_allowed(role, 1) == _ARC_FX[role][0]

    def test_occurrence_zero_and_negative_fold_to_the_first_rung(self):
        assert _arc_fx_allowed("chorus", 0) == _ARC_FX["chorus"][0]
        assert _arc_fx_allowed("chorus", -3) == _ARC_FX["chorus"][0]

    def test_an_unknown_role_has_no_ladder(self):
        assert _arc_fx_allowed("other", 1) is None


class TestTheLadderActuallyVaries:
    @pytest.mark.parametrize("role", ("chorus", "verse", "bridge"))
    def test_consecutive_occurrences_differ(self, role):
        assert _arc_fx_allowed(role, 1) != _arc_fx_allowed(role, 2)

    def test_chorus_shows_at_least_four_distinct_looks_over_its_measured_run(self):
        # 실측된 이 곡의 chorus 회차 수는 25.
        seen = {_arc_fx_allowed("chorus", n) for n in range(1, 26)}
        assert len(seen) >= 4

    def test_the_truncated_single_axis_still_varies(self):
        """감독 질감 medium → 축 하나. 예전 코드의 ``allowed[:1]`` 은 회차와
        무관하게 같은 값을 냈다. 사다리를 탄 뒤에도 첫 축이 회차마다 달라야
        고친 것이 실제로 보인다."""
        first_axis = [rung[0] for rung in _ARC_FX_LADDER["chorus"]]
        assert len(set(first_axis)) == len(first_axis), first_axis

    @pytest.mark.parametrize("role", sorted(_ARC_FX_LADDER))
    def test_every_rung_of_a_role_has_the_same_axis_count(self, role):
        """density 는 ``_ARC_FX`` 에서 오고 회차와 무관하다 — 칸 길이가 갈리면
        선언한 축 개수와 실제 묶음이 어긋난다."""
        widths = {len(rung) for rung in _ARC_FX_LADDER[role]}
        assert len(widths) == 1
        assert widths.pop() == len(_ARC_FX[role][0])


class TestTheNamesAreRealLibraryWords:
    @pytest.mark.parametrize(("label", "fx_id"), sorted(NEW_LABEL_TO_FX_ID.items()))
    def test_the_new_label_routes_to_its_entry(self, library, label, fx_id):
        result = match_fx(label, library).to_dict()
        assert result["selected"] == fx_id
        assert result["fallback"] is False

    @pytest.mark.parametrize("label", PRE_EXISTING_UNROUTED)
    def test_the_pre_existing_names_are_still_the_only_unrouted_ones(self, library, label):
        assert match_fx(label, library).to_dict()["fallback"] is True

    def test_no_ladder_label_outside_the_two_sets_above(self):
        used = {label for rungs in _ARC_FX_LADDER.values() for rung in rungs for label in rung}
        assert used == set(NEW_LABEL_TO_FX_ID) | set(PRE_EXISTING_UNROUTED)

    def test_no_label_carries_a_blackout_or_audience_token(self):
        used = {label for rungs in _ARC_FX_LADDER.values() for rung in rungs for label in rung}
        for label in used:
            folded = label.casefold()
            assert not any(token in folded for token in FORBIDDEN_TOKENS), label
