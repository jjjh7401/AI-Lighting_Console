"""t365 — 대량 포지션 생성 **앞에** 서는 두 검사.

리서치 두 편이 같은 전제를 말한다. 18번 문서(``docs/research/ma3-effects/
18-addondesk-position-preset-research.md``) §9 항목 2 는 "몇 개 만들까요?"
보다 먼저 "같은 방향으로 설치된 장비끼리 묶었나요?" 를 물으라 하고, 19번
문서 §6 의 pan/tilt 자동화 대표 실패 다섯 중 둘이 그 질문으로 잡힌다 —
체인 순서가 뒤집힌 것과, 기구 수가 블록에 안 나눠떨어지는 것.

**이 파일이 지키는 것은 셋이다.**

1. 결함을 찾는가(양성 대조) — 뒤집힌 체인은 뒤집혔다고 말하고, 어긋난 자리를
   짚고, 10대를 3갈래로 나누면 안 떨어진다고 말한다.
2. **멀쩡한 것을 결함이라 하지 않는가**(음성 대조) — 맞는 체인은 네 정렬
   전부에서 깨끗하게 나오고, 나눗셈 검사는 전부 통과시키지 않는다. 안 쏴 본
   가드는 잰 가드가 아니고, 한쪽 팔만 쏜 가드는 절반만 잰 가드다.
3. **권고로 남는가** — 체인을 고쳐 쓰지 않고, 결함을 만나도 던지지 않는다.

20번 문서 §6.2 의 실례(폭 10 / three fan)는 **주장으로 옮겨 적지 않고 여기서
직접 계산해 대조한다**. 문서는 리서치 노트지 사양이 아니다.
"""

from __future__ import annotations

import pytest

from server.spatial import SPATIAL_SORTS, analyze_spatial_records, spatial_sorted_fids
from server.spatial.preflight import (
    CHAIN_ORDER_VERDICTS,
    SPLIT_MODES,
    SPLIT_VERDICTS,
    check_chain_order,
    check_split,
)
from server.spatial.schema import SpatialAnalysisError


def _rec(fid: int, x: float, y: float, z: float = 3.0) -> dict:
    return {"fid": fid, "name": f"MOVER {fid}", "x": x, "y": y, "z": z}


def _bar_8() -> list[dict]:
    """무버 8대가 한 바에. fid 1..8 이 무대 왼쪽에서 오른쪽 순서 그대로다."""
    return [_rec(i + 1, -3.5 + i, 0.0) for i in range(8)]


def _grid_3x4() -> list[dict]:
    """3행 4열. 행은 y = -3 / 0 / 3, fid 는 행 우선으로 1..12."""
    return [
        _rec(row * 4 + column + 1, -1.5 + column, -3.0 + 3.0 * row)
        for row in range(3)
        for column in range(4)
    ]


def _unpositioned_8() -> list[dict]:
    """패치는 됐는데 좌표가 전부 0 인 리그 — 참 순서가 확립되지 않는다."""
    return [
        {"fid": i + 1, "name": f"MOVER {i + 1}", "x": 0.0, "y": 0.0, "z": 0.0} for i in range(8)
    ]


BAR = analyze_spatial_records(_bar_8())
GRID = analyze_spatial_records(_grid_3x4())
TRUE_ORDER = (1, 2, 3, 4, 5, 6, 7, 8)


# -- 양성 대조: 결함을 찾는가 -----------------------------------------------------


class TestTheCheckFindsTheFault:
    def test_the_true_order_comes_from_the_coordinates_not_from_the_fid_numbers(self):
        # 이 파일의 전제. fid 순서와 좌표 순서가 같은 리그를 골랐으므로, 아래
        # 판정들이 좌표를 보고 있다는 것을 여기서 한 번 못 박는다.
        assert check_chain_order(TRUE_ORDER, BAR, "left_to_right").expected == TRUE_ORDER
        assert check_chain_order(TRUE_ORDER, BAR, "right_to_left").expected == TRUE_ORDER[::-1]

    def test_a_reversed_chain_is_reported_as_reversed(self):
        result = check_chain_order(TRUE_ORDER[::-1], BAR, "left_to_right")
        assert result.verdict == "reversed"
        assert not result.clean

    def test_the_reversed_chain_says_where_it_diverges_not_merely_that_it_differs(self):
        result = check_chain_order(TRUE_ORDER[::-1], BAR, "left_to_right")
        # 짝수 길이라 고정점이 없다: 여덟 자리가 전부 어긋나고, 각 자리가
        # "무엇 대신 무엇이" 까지 말한다.
        assert [d.index for d in result.divergences] == list(range(8))
        assert (result.divergences[0].proposed_fid, result.divergences[0].expected_fid) == (8, 1)

    def test_a_reversed_chain_names_no_swapped_pair_because_the_fix_is_the_direction(self):
        # 뒤집힘과 자리 맞바꿈을 가르는 것이 이 검사의 존재 이유다. 뒤집힌
        # 체인에 "이 두 대를 바꾸세요"를 붙이면 틀린 수선을 지시하는 셈이다.
        assert check_chain_order(TRUE_ORDER[::-1], BAR, "left_to_right").swapped_positions == ()

    def test_two_adjacent_fixtures_swapped_is_a_different_verdict_from_reversed(self):
        result = check_chain_order((1, 2, 3, 5, 4, 6, 7, 8), BAR, "left_to_right")
        assert result.verdict == "transposed"
        assert result.swapped_positions == ((3, 4),)
        assert [d.index for d in result.divergences] == [3, 4]

    def test_a_non_adjacent_swap_is_located_too(self):
        result = check_chain_order((8, 2, 3, 4, 5, 6, 7, 1), BAR, "left_to_right")
        assert (result.verdict, result.swapped_positions) == ("transposed", ((0, 7),))

    def test_two_independent_swaps_are_both_named(self):
        result = check_chain_order((2, 1, 3, 4, 6, 5, 7, 8), BAR, "left_to_right")
        assert result.swapped_positions == ((0, 1), (4, 5))

    def test_a_chain_that_is_neither_reversed_nor_a_set_of_swaps_is_reordered(self):
        # 한 칸 회전. 자리가 전부 어긋나지만 교환 쌍으로 덮이지 않는다 —
        # 한 번의 수선으로 설명되지 않는 어긋남이고, 그렇게 말해야 한다.
        result = check_chain_order((2, 3, 4, 5, 6, 7, 8, 1), BAR, "left_to_right")
        assert result.verdict == "reordered"
        assert result.swapped_positions == ()
        assert len(result.divergences) == 8

    def test_the_expected_order_rides_along_so_the_caller_need_not_sort_again(self):
        assert check_chain_order((2, 1, 3, 4, 5, 6, 7, 8), BAR, "left_to_right").expected == (
            TRUE_ORDER
        )


class TestMembershipIsCheckedBeforeOrder:
    def test_a_fid_this_rig_does_not_hold_is_named(self):
        result = check_chain_order((1, 2, 3, 4, 5, 6, 7, 99), BAR, "left_to_right")
        assert result.verdict == "membership_mismatch"
        assert result.unknown_fids == (99,)
        assert result.missing_fids == (8,)

    def test_a_fid_named_twice_is_named(self):
        result = check_chain_order((1, 2, 3, 4, 5, 6, 7, 7), BAR, "left_to_right")
        assert (result.verdict, result.duplicate_fids) == ("membership_mismatch", (7,))

    def test_a_subset_chain_is_a_scope_signal_not_a_transposition(self):
        # 37대 리그에서 무버 8대만 부채로 펴는 흔한 경우. 여기서 전체 순서를
        # 조용히 부분집합으로 걸러내면 center_out 과 diagonal 이 틀려진다
        # (행 중심과 열 번호가 구성원에 따라 움직인다). 자리별 어긋남을 세는
        # 대신 집합이 다르다고 말한다.
        result = check_chain_order((1, 2, 3, 4), BAR, "left_to_right")
        assert result.verdict == "membership_mismatch"
        assert result.missing_fids == (5, 6, 7, 8)
        assert result.divergences == ()


# -- 음성 대조: 멀쩡한 것을 결함이라 하지 않는가 ------------------------------------


class TestTheCheckDoesNotCryWolf:
    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_the_coordinate_derived_chain_is_clean_in_every_sort(self, sort):
        # 날조 대조군. 검사가 "항상 결함 있음"으로 답하면 여기서 죽는다.
        result = check_chain_order(spatial_sorted_fids(GRID, sort), GRID, sort)
        assert result.verdict == "matches"
        assert result.clean

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_a_clean_chain_carries_no_divergence_and_no_swap(self, sort):
        result = check_chain_order(spatial_sorted_fids(GRID, sort), GRID, sort)
        assert (result.divergences, result.swapped_positions) == ((), ())
        assert (result.unknown_fids, result.missing_fids, result.duplicate_fids) == ((), (), ())

    def test_right_to_left_is_clean_for_the_right_to_left_chain(self):
        # 같은 체인이 한 정렬에서는 뒤집힘, 다른 정렬에서는 깨끗하다. 판정이
        # 체인만 보는 것이 아니라 **요청한 방향**을 함께 본다는 증거다.
        chain = TRUE_ORDER[::-1]
        assert check_chain_order(chain, BAR, "left_to_right").verdict == "reversed"
        assert check_chain_order(chain, BAR, "right_to_left").verdict == "matches"


class TestConfidenceRidesAlong:
    def test_an_unestablished_layout_does_not_produce_a_confident_verdict(self):
        # 좌표가 전부 0 이면 참 순서 자체가 확립되지 않는다. 계산은 하되
        # (rows.py 의 관례) "당신 체인이 뒤집혔다"를 자신 있는 주장으로
        # 내보내지 않는다 — 깃발이 같이 나간다.
        unpositioned = analyze_spatial_records(_unpositioned_8())
        result = check_chain_order(TRUE_ORDER[::-1], unpositioned, "left_to_right")
        assert result.low_confidence is True
        assert result.confidence_reason == "no_spatial_spread"

    def test_a_regular_rig_carries_no_flag(self):
        result = check_chain_order(TRUE_ORDER, BAR, "left_to_right")
        assert (result.low_confidence, result.confidence_reason) == (False, None)


# -- 나눗셈: 20번 문서 §6.2 의 실례를 직접 계산해 대조 -------------------------------


class TestTheDocumentTwentyWorkedCase:
    """문서가 주장한 것 — 폭 10 / three fan — 을 산술로 확인한다."""

    def test_ten_into_three_fans_does_not_divide(self):
        result = check_split(10, fans=3)
        assert result.verdict == "uneven"
        assert not result.even

    def test_the_uneven_split_names_the_block_sizes_it_would_actually_produce(self):
        # "안 맞는다"만으로는 얼마나 안 맞는지가 안 보인다. 4+3+3 이다.
        result = check_split(10, fans=3)
        assert result.block_sizes == (4, 3, 3)
        assert result.remainder == 1

    def test_two_fans_divide_as_five_plus_five(self):
        result = check_split(10, fans=2)
        assert (result.verdict, result.block_sizes) == ("even", (5, 5))

    def test_five_fans_divide_in_twos(self):
        result = check_split(10, fans=5)
        assert (result.verdict, result.block_sizes) == ("even", (2, 2, 2, 2, 2))

    def test_the_clean_alternatives_are_named_on_both_axes(self):
        result = check_split(10, fans=3)
        # 요청을 바꾸는 축: 10 을 고르게 나누는 값 전부와 요청 양옆.
        assert result.clean_requests == (1, 2, 5, 10)
        assert (result.nearest_clean_request_below, result.nearest_clean_request_above) == (2, 5)
        # 기구를 바꾸는 축: three fan 을 그대로 쓰려면 9 나 12 여야 한다는
        # 문서의 두 번째 주장.
        assert (result.clean_fixture_count_below, result.clean_fixture_count_above) == (9, 12)

    @pytest.mark.parametrize("count", [9, 12])
    def test_the_fixture_counts_the_document_names_do_take_a_three_fan(self, count):
        assert check_split(count, fans=3).verdict == "even"


class TestTheSplitCheckDoesNotPassEverything:
    """날조 대조군 — 전부 통과시키는 검사는 여기서 죽는다."""

    def test_the_verdict_tracks_the_arithmetic_over_a_sweep(self):
        seen = set()
        for count in range(1, 25):
            for fans in range(1, 13):
                result = check_split(count, fans=fans)
                if fans > count:
                    assert result.verdict == "over_split"
                else:
                    assert result.even is (count % fans == 0), (count, fans)
                seen.add(result.verdict)
        # 세 판정이 전부 실제로 나오는지 — 한쪽으로만 답하는 구현을 배제한다.
        assert seen == {"even", "uneven", "over_split"}

    def test_the_block_sizes_always_account_for_every_fixture(self):
        for count in range(1, 25):
            for fans in range(1, count + 1):
                result = check_split(count, fans=fans)
                assert sum(result.block_sizes) == count
                assert len(result.block_sizes) == fans

    def test_more_fans_than_fixtures_is_not_merely_uneven(self):
        # 8대를 12갈래로 나눌 수는 없다. 기구를 재배치해도 해결되지 않으므로
        # "덜 고르다"와 같은 칸에 넣으면 호출자가 헛수고를 한다.
        result = check_split(8, fans=12)
        assert result.verdict == "over_split"
        assert result.block_sizes == ()
        assert result.clean_fixture_count_below is None
        assert result.clean_fixture_count_above == 12


class TestBlockMode:
    def test_a_block_size_that_divides_is_even(self):
        result = check_split(12, block=4)
        assert (result.verdict, result.block_sizes) == ("even", (4, 4, 4))

    def test_a_block_size_that_does_not_divide_shows_the_short_last_block(self):
        result = check_split(10, block=3)
        assert (result.verdict, result.block_sizes) == ("uneven", (3, 3, 3, 1))

    def test_a_block_wider_than_the_rig_is_uneven_not_over_split(self):
        # fan 과 달리 블록이 리그보다 넓은 것은 성립한다 — 짧은 블록 하나다.
        result = check_split(3, block=5)
        assert (result.verdict, result.block_sizes) == ("uneven", (3,))


# -- 권고로 남는가 ---------------------------------------------------------------


class TestBothChecksAreAdvisory:
    def test_the_chain_check_never_rewrites_the_chain_it_was_given(self):
        proposed = [8, 7, 6, 5, 4, 3, 2, 1]
        result = check_chain_order(proposed, BAR, "left_to_right")
        assert proposed == [8, 7, 6, 5, 4, 3, 2, 1]
        assert result.proposed == (8, 7, 6, 5, 4, 3, 2, 1)

    def test_the_chain_check_returns_a_fault_rather_than_raising_it(self):
        # 결함은 예외가 아니라 값이다. 예외였다면 호출자가 사용자에게 되묻는
        # 대신 흐름이 끊긴다.
        assert check_chain_order((), BAR, "left_to_right").verdict == "membership_mismatch"

    def test_the_split_check_returns_a_fault_rather_than_raising_it(self):
        assert check_split(10, fans=3).verdict == "uneven"

    def test_the_split_check_does_not_silently_round_the_request_to_a_divisor(self):
        # 안 떨어지는 분할도 콘솔에서는 실행되고, 그게 의도일 수도 있다.
        # 대안은 제시하되 요청값은 그대로 돌려준다.
        assert check_split(10, fans=3).requested == 3


class TestOnlyMalformedInputRaises:
    def test_a_sort_outside_the_closed_vocabulary_raises(self):
        # 정렬 어휘는 sorting.py 것을 그대로 쓴다 — 여기서 두 번째 어휘를
        # 만들지 않았다는 증거이자, 모르는 이름이 기본값으로 떨어지지
        # 않는다는 증거.
        with pytest.raises(SpatialAnalysisError):
            check_chain_order(TRUE_ORDER, BAR, "front_to_back")

    @pytest.mark.parametrize("count", [0, -1])
    def test_a_rig_of_no_fixtures_raises(self, count):
        with pytest.raises(SpatialAnalysisError):
            check_split(count, fans=2)

    def test_a_request_below_one_raises(self):
        with pytest.raises(SpatialAnalysisError):
            check_split(10, fans=0)

    def test_naming_neither_axis_raises(self):
        with pytest.raises(SpatialAnalysisError):
            check_split(10)

    def test_naming_both_axes_raises(self):
        with pytest.raises(SpatialAnalysisError):
            check_split(10, fans=2, block=5)


class TestTheVerdictVocabulariesAreClosed:
    def test_every_chain_verdict_emitted_belongs_to_the_closed_set(self):
        chains = [
            TRUE_ORDER,
            TRUE_ORDER[::-1],
            (1, 2, 3, 5, 4, 6, 7, 8),
            (2, 3, 4, 5, 6, 7, 8, 1),
            (1, 2, 3, 4, 5, 6, 7, 99),
        ]
        emitted = {check_chain_order(chain, BAR, "left_to_right").verdict for chain in chains}
        assert emitted <= CHAIN_ORDER_VERDICTS
        # 공허하지 않은지 — 다섯 입력이 실제로 다섯 판정을 낸다.
        assert len(emitted) == 5

    def test_every_split_verdict_emitted_belongs_to_the_closed_set(self):
        emitted = {
            check_split(count, fans=fans).verdict for count in range(1, 13) for fans in range(1, 13)
        }
        assert emitted <= SPLIT_VERDICTS

    def test_the_split_modes_are_the_two_the_functions_accept(self):
        assert SPLIT_MODES == ("fans", "block")
        assert {check_split(10, fans=2).mode, check_split(10, block=2).mode} == set(SPLIT_MODES)
