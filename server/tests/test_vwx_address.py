"""server/vwx/address.py 주소 처리 테스트 (M3 — AC-VWX-009~012). 문서 근거 · 실물 미검증."""

from __future__ import annotations

from server.prechk.patch import normalize_address
from server.vwx.address import (
    ADDRESS_BASIS_ABS_BACK_CALCULATED,
    ADDRESS_BASIS_ABS_CONFIRMED,
    ADDRESS_BASIS_DIRECT,
    PATCHED,
    READ_FAILURE_ADDRESS_TRIPLE_MISMATCH,
    READ_FAILURE_MULTI_SYSTEM,
    UNPATCHED_DESIGNED,
    classify_and_resolve,
    resolve_all,
    to_console_form,
)
from server.vwx.columns import resolve_columns


class TestUnpatchedSentinel:
    """AC-VWX-009 — 미패치 sentinel 분류."""

    def test_zero_dmx_address_is_unpatched_designed(self):
        outcome = classify_and_resolve({"universe": "1", "address": "0"})
        assert outcome.kind == "resolved"
        assert outcome.classification == UNPATCHED_DESIGNED

    def test_blank_dmx_address_is_also_unpatched_designed(self):
        outcome = classify_and_resolve({"universe": "1", "address": ""})
        assert outcome.kind == "resolved"
        assert outcome.classification == UNPATCHED_DESIGNED

    def test_unpatched_designed_is_a_distinct_code_from_the_console_absence_verdict(self):
        """비공허성 — 두 값이 실제로 다름을 직접 assert한다.

        "콘솔에 없음"(missing_in_console)은 diff.py(M5)의 대조 단계 산출물이다
        — 여기서는 코드값 상수 자체가 서로 다름만 검증한다(순환 의존 방지).
        """
        assert UNPATCHED_DESIGNED != "missing_in_console"


class TestAbsoluteAddressConditionalInversion:
    """AC-VWX-010 — Absolute Address 조건부 역산."""

    def test_universe_and_dmx_address_pair_is_preferred_over_absolute(self):
        outcome = classify_and_resolve(
            {"universe": "2", "address": "5", "absolute_address": "9999"}
        )
        assert outcome.kind == "resolved"
        assert outcome.classification == PATCHED
        assert (outcome.universe, outcome.address) == (2, 5)
        assert outcome.address_basis == ADDRESS_BASIS_DIRECT

    def test_absolute_only_without_confirmed_premise_derives_with_a_weak_basis(self):
        """v0.1.7 재설계(결함 1 P0, ASSUMPTION-69) — 전제 미확인은 더 이상 거부
        사유가 아니다. ``server/prechk/patch.py`` ``OverlapBasis``처럼 판정을
        거부하는 대신 가장 약한 근거로 역산하고 그 근거를 등급으로 남긴다."""
        # abs=600 -> universe=(600-1)//512+1=2, address=(600-1)%512+1=88
        outcome = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=False)
        assert outcome.kind == "resolved"
        assert (outcome.universe, outcome.address) == (2, 88)
        assert outcome.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED

    def test_absolute_only_with_confirmed_premise_inverts_with_a_stronger_basis(self):
        # abs=600 -> universe=(600-1)//512+1=2, address=(600-1)%512+1=88
        outcome = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=True)
        assert outcome.kind == "resolved"
        assert (outcome.universe, outcome.address) == (2, 88)
        assert outcome.address_basis == ADDRESS_BASIS_ABS_CONFIRMED

    def test_confirmed_and_unconfirmed_premises_derive_the_same_address_different_basis(self):
        """비공허성 — 근거 등급만 다르고 역산된 (universe, address)는 동일하다."""
        confirmed = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=True)
        unconfirmed = classify_and_resolve(
            {"absolute_address": "600"}, contiguous_512_confirmed=False
        )
        assert (confirmed.universe, confirmed.address) == (
            unconfirmed.universe,
            unconfirmed.address,
        )
        assert confirmed.address_basis != unconfirmed.address_basis


class TestMultiSystemAmbiguity:
    """AC-VWX-011 — 멀티시스템에서도 설계 측 주소 해석은 차단하지 않는다(결함 1, P0, v0.1.6).

    v0.1.5까지는 System 2개 이상이 관측되면 ``classify_and_resolve`` 자체가
    전 행을 차단(blocked)했다 — 실물 샘플 3종(SPEC-COPILOT-VWX-001 9번째
    라운드) 재현으로 이 차단이 설계 측 리그 전체를 0대로 무너뜨린다는 결함이
    드러났다. v0.1.6부터는 System 수와 무관하게 개별 레코드의 주소 해석은
    항상 정상 진행하고, 콘솔 대조만 별도로(``diff.py``) 미수행 처리한다.
    """

    def test_two_systems_sharing_universe_1_no_longer_blocks_resolution(self):
        """Defect-1 수정 — 이전에는 blocked였던 경로가 이제는 정상 resolved다."""
        outcome = classify_and_resolve(
            {"universe": "1", "address": "1"},
            system_letters=frozenset({"A", "B"}),
        )
        assert outcome.kind == "resolved"
        assert (outcome.universe, outcome.address) == (1, 1)

    def test_a_single_system_file_resolves_identically_to_multi_system(self):
        """비공허성 — 단일 System과 멀티시스템에서 개별 레코드 해석 결과가 같다."""
        single = classify_and_resolve(
            {"universe": "1", "address": "1"}, system_letters=frozenset({"A"})
        )
        multi = classify_and_resolve(
            {"universe": "1", "address": "1"}, system_letters=frozenset({"A", "B"})
        )
        assert single.kind == multi.kind == "resolved"
        assert (single.universe, single.address) == (multi.universe, multi.address)

    def test_multi_system_blocked_reason_code_is_retired_from_classify_and_resolve(self):
        """비공허성 — READ_FAILURE_MULTI_SYSTEM은 더 이상 이 함수에서 나오지 않는다."""
        outcome = classify_and_resolve(
            {"universe": "1", "address": "1"}, system_letters=frozenset({"A", "B", "C"})
        )
        assert outcome.reason_code != READ_FAILURE_MULTI_SYSTEM


class TestNormalizeAddressRepresentationParity:
    """AC-VWX-012 — normalize_address 표현 일치."""

    def test_same_logical_address_produces_the_same_integer_tuple(self):
        console_parse = normalize_address("1.001")
        vwx_parse = to_console_form(1, 1)
        assert (console_parse.universe, console_parse.address) == (
            vwx_parse.universe,
            vwx_parse.address,
        )

    def test_both_parsers_report_failure_as_a_structured_form_not_an_exception(self):
        console_parse = normalize_address("not-an-address")
        assert console_parse.ok is False
        outcome = classify_and_resolve({})  # no address data at all
        assert outcome.kind == "read_failure"
        # 둘 다 예외가 아니라 구조 자체가 실패 신호다.
        assert console_parse.error is not None
        assert outcome.reason_code is not None


class TestResolveAllPipeline:
    """address.resolve_all — columns.ColumnRecord 목록을 통째로 해석한다."""

    def test_multi_system_records_resolve_normally_through_the_full_pipeline(self):
        """Defect-1 수정 — 결함 1(P0) 이전에는 이 파이프라인이 2건 모두 blocked
        판독 실패로 만들었다; 이제는 둘 다 정상 resolved다(비공허성)."""
        from server.vwx.address import resolve_all

        raw = [
            {"Instrument Type": "MMX", "System": "A", "Universe": "1", "DMX Address": "1"},
            {"Instrument Type": "MMX", "System": "B", "Universe": "1", "DMX Address": "2"},
        ]
        records, _failures, _excluded = resolve_columns(raw)
        resolved, failures = resolve_all(records)
        assert not failures
        assert len(resolved) == 2
        assert {(r.universe, r.address) for r in resolved} == {(1, 1), (1, 2)}

    def test_a_normal_file_resolves_cleanly(self):
        from server.vwx.address import resolve_all

        raw = [{"Instrument Type": "MMX", "Universe": "1", "DMX Address": "1"}]
        records, _failures, _excluded = resolve_columns(raw)
        resolved, failures = resolve_all(records)
        assert not failures
        assert resolved[0].universe == 1
        assert resolved[0].address == 1
        assert resolved[0].classification == PATCHED


class TestTripleRepresentationCrossCheck:
    """M0 실물 샘플 반영 — Universe+DMX Address+Absolute Address 3중 표현 교차검증."""

    def test_consistent_absolute_address_resolves_with_no_warning(self):
        """음성 대조군 — M0 실물 샘플과 동일 형태(10/10 일치)."""
        outcome = classify_and_resolve({"universe": "1", "address": "39", "absolute_address": "39"})
        assert outcome.kind == "resolved"
        assert outcome.universe == 1
        assert outcome.address == 39
        assert outcome.warning_kind is None

    def test_universe_2_consistent_absolute_address_resolves_with_no_warning(self):
        """비공허성 — 유니버스 2 이상에서도 공식이 실제로 검증됨을 확인."""
        outcome = classify_and_resolve({"universe": "2", "address": "1", "absolute_address": "513"})
        assert outcome.kind == "resolved"
        assert outcome.warning_kind is None

    def test_mismatched_absolute_address_is_flagged_but_still_resolved_via_the_pair(self):
        """양성 케이스(합성) — Universes pane에 구멍이 있는 경우. Universe+DMX Address
        조합을 그대로 신뢰하고(값이 바뀌지 않는다), Absolute Address로 유니버스를
        역산하지 않는다 — 대신 구조화된 경고를 낸다."""
        outcome = classify_and_resolve(
            {"universe": "1", "address": "39", "absolute_address": "9999"}
        )
        assert outcome.kind == "resolved"
        assert outcome.universe == 1  # 역산되지 않았다 — Universe+DMX Address 그대로.
        assert outcome.address == 39
        assert outcome.warning_kind == READ_FAILURE_ADDRESS_TRIPLE_MISMATCH
        assert "불일치" in outcome.warning_detail

    def test_resolve_all_surfaces_the_mismatch_warning_without_dropping_the_record(self):
        """비공허성 종단 — resolve_all을 통과해도 레코드는 여전히 resolved에 남고,
        경고만 failures에 별도로 추가된다(레코드가 사라지지 않음)."""
        raw = [{"Instrument Type": "MMX", "Universe": "1", "Absolute Address": "9999"}]
        # Universe + Address(DMX) 쌍이 최우선이므로 DMX Address도 채운다.
        raw[0]["DMX Address"] = "39"
        records, _failures, _excluded = resolve_columns(raw)
        resolved, failures = resolve_all(records)
        assert len(resolved) == 1
        assert resolved[0].universe == 1
        assert resolved[0].address == 39
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_ADDRESS_TRIPLE_MISMATCH

    def test_absolute_address_alone_is_unaffected_by_the_cross_check(self):
        """교차검증은 Universe+DMX Address 쌍이 있을 때만 발동한다 — Absolute 단독
        경로(v0.1.7 재설계, ASSUMPTION-69)는 3중 표현 교차검증과 무관하게 자체
        분기(역산, 약한 근거)로만 처리된다(회귀 확인 — 교차검증 경고가 섞이지 않음)."""
        outcome = classify_and_resolve({"absolute_address": "39"})
        assert outcome.kind == "resolved"
        assert outcome.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED
        assert outcome.warning_kind is None
