"""server/vwx/address.py 주소 처리 테스트 (M3 — AC-VWX-009~012). 문서 근거 · 실물 미검증."""

from __future__ import annotations

from server.prechk.patch import normalize_address
from server.vwx.address import (
    PATCHED,
    READ_FAILURE_ABS_UNVERIFIED,
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

    def test_absolute_only_without_confirmed_premise_never_guesses(self):
        outcome = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=False)
        assert outcome.kind == "read_failure"
        assert outcome.reason_code == READ_FAILURE_ABS_UNVERIFIED
        assert outcome.universe is None and outcome.address is None

    def test_absolute_only_with_confirmed_premise_inverts_correctly(self):
        # abs=600 -> universe=(600-1)//512+1=2, address=(600-1)%512+1=88
        outcome = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=True)
        assert outcome.kind == "resolved"
        assert (outcome.universe, outcome.address) == (2, 88)


class TestMultiSystemAmbiguity:
    """AC-VWX-011 — 멀티시스템 모호 차단."""

    def test_two_systems_sharing_universe_1_are_blocked_not_merged(self):
        outcome = classify_and_resolve(
            {"universe": "1", "address": "1"},
            system_letters=frozenset({"A", "B"}),
        )
        assert outcome.kind == "blocked"
        assert outcome.reason_code == READ_FAILURE_MULTI_SYSTEM
        assert "멀티시스템" in outcome.detail

    def test_a_single_system_file_never_triggers_the_block(self):
        """비공허성 — 단일 System 파일에서 오발동하지 않는다."""
        outcome = classify_and_resolve(
            {"universe": "1", "address": "1"},
            system_letters=frozenset({"A"}),
        )
        assert outcome.kind == "resolved"


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

    def test_system_letters_are_computed_across_the_whole_file(self):
        from server.vwx.address import resolve_all

        raw = [
            {"Instrument Type": "MMX", "System": "A", "Universe": "1", "DMX Address": "1"},
            {"Instrument Type": "MMX", "System": "B", "Universe": "1", "DMX Address": "2"},
        ]
        records, _failures = resolve_columns(raw)
        resolved, failures = resolve_all(records)
        assert resolved == []
        assert len(failures) == 2

    def test_a_normal_file_resolves_cleanly(self):
        from server.vwx.address import resolve_all

        raw = [{"Instrument Type": "MMX", "Universe": "1", "DMX Address": "1"}]
        records, _failures = resolve_columns(raw)
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
        records, _failures = resolve_columns(raw)
        resolved, failures = resolve_all(records)
        assert len(resolved) == 1
        assert resolved[0].universe == 1
        assert resolved[0].address == 39
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_ADDRESS_TRIPLE_MISMATCH

    def test_absolute_address_alone_is_unaffected_by_the_cross_check(self):
        """교차검증은 Universe+DMX Address 쌍이 있을 때만 발동한다 — Absolute 단독
        경로(ASSUMPTION-69)는 이 변경으로 바뀌지 않는다(회귀 확인)."""
        outcome = classify_and_resolve({"absolute_address": "39"})
        assert outcome.kind == "read_failure"
        assert outcome.reason_code == READ_FAILURE_ABS_UNVERIFIED
