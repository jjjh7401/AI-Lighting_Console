"""server/vwx/address.py 주소 처리 테스트 (M3 — AC-VWX-009~012). 문서 근거 · 실물 미검증."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

import pytest

from server.prechk.patch import normalize_address
from server.tests.test_autopatch_contract import iter_vwx_modules, vwx_module_label
from server.vwx.address import (
    _UNIVERSE_ADDRESS_SPLIT,
    _UNIVERSE_WIDTH,
    ADDRESS_BASIS_ABS_BACK_CALCULATED,
    ADDRESS_BASIS_ABS_CONFIRMED,
    ADDRESS_BASIS_DIRECT,
    PATCHED,
    READ_FAILURE_ADDRESS_TRIPLE_MISMATCH,
    READ_FAILURE_ADDRESS_UNPARSEABLE,
    READ_FAILURE_MULTI_SYSTEM,
    READ_FAILURE_NO_ADDRESS_DATA,
    UNPATCHED_DESIGNED,
    classify_and_resolve,
    resolve_all,
    split_universe_address,
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


# --- round17 주소 산술·파싱 경계 전수 (AddressGates) ---
#
# round17 치명 #4(절대주소 역산 나눗셈 경계 무대조군) · 치명 #5(조합 주소 파싱
# fail-open) · minor #12(문서-코드 모순)을 닫는다. 일곱 라운드 반복된 실패 양식은
# **"게이트가 자기 모듈·자기 형제 한 칸에서 멈춘다"**였다 — round16이 만든 "구간 경계
# 전수 22행"은 `apply.py`·`patchplan.py`의 **구간 관계**에 한정되어 `address.py`의
# **나눗셈/나머지 경계**가 표 밖이었고, 그 자리 한 칸 변조가 5,690건을 통과했다.
# 그래서 여기서는 경계를 값 하나가 아니라 **표**로 잡는다.
#
# 게이트 설계 원칙(round16 `_ROUND16_FORBIDDEN_NORMALISATIONS` 항진식 실패 재발 방지):
#   · 기대값은 프로덕션 상수(`_UNIVERSE_WIDTH`)가 아니라 **독립 리터럴 512**에서 파생한다.
#     프로덕션 상수와 독립 리터럴의 일치 자체는 별도 단정으로 검사한다(자기 비교 금지).
#   · 모든 표에 **명시 리터럴 행수 단정**을 건다 — 행 하나를 지우면 그 단정이 깨진다.
#   · 커버리지 집합(경계값 · 토큰 수 · 구분자)은 표에서 파생하지 않고 **독립 선언** 후
#     표와 등호 비교한다. 표 자신에서 파생한 집합과 비교하면 항진식이다.

#: 콘솔 유니버스 폭 — 프로덕션 상수를 참조하지 않는 독립 리터럴(research.md §4).
_R17_WIDTH_LITERAL = 512

#: `split_universe_address`가 쓰는 구분자 — 독립 리터럴(research.md §4).
_R17_SEPARATOR_PATTERN = r"[/:\-.]"
_R17_SEPARATORS = ("/", ":", "-", ".")


def test_r17_production_universe_width_matches_the_independent_literal():
    """[round17 #4] `_UNIVERSE_WIDTH`를 512에서 한 칸이라도 옮기면 실패한다.

    아래 경계표들이 `_R17_WIDTH_LITERAL`에서 기대값을 파생하므로, 이 한 줄이
    프로덕션 상수와 독립 리터럴을 잇는 유일한 다리다(표가 프로덕션 상수를 직접
    참조하면 자기 비교가 되어 아무 것도 검증하지 못한다).
    """
    assert _UNIVERSE_WIDTH == _R17_WIDTH_LITERAL


def test_r17_production_separator_set_matches_the_independent_literal():
    """[round17 #5] `_UNIVERSE_ADDRESS_SPLIT`의 구분자 집합을 바꾸면 실패한다."""
    assert _UNIVERSE_ADDRESS_SPLIT.pattern == _R17_SEPARATOR_PATTERN


class _AbsRow(NamedTuple):
    """Absolute Address 단독 역산 경계 한 칸."""

    value: int
    kind: str
    classification: str
    universe: int | None
    address: int | None
    basis: str | None
    status: str


_R17_STATUS_SPEC = "규약 산출 — 이 값이 옳다"
#: **현행 동작 기록일 뿐 "옳다"는 판정이 아니다.** round17 결함 R17-A 참조 — 이 값들이
#: 1단계 리포트를 지나 Lua 전달물(`patch = { "0.507" }`)까지 도달했다. 패치 계층
#: (`patchplan.plan_addresses`)이 `address_below_minimum`으로 배제하도록 round17에서
#: 막았고(`test_autopatch_verify.py`의 R17-A 섹션), 1단계 자체의 분류는 이 SPEC의
#: §D Out of Scope(AC-AUTOPATCH-025 — 1단계 공개 계약 무변경)로 남겼다. 여기 적힌
#: 값은 그 **도달성 판정의 근거 기록**이지 정합성 승인이 아니다.
_R17_STATUS_DEFECT_R17A = "현행 동작 기록 · 정합성 판정 아님 · 결함 R17-A"

#: 절대주소 → (universe, address) 역산의 경계 전수. 512의 배수 앞뒤 한 칸씩(0~3블록)에
#: 0·음수를 더했다. 기대값은 전부 `_R17_WIDTH_LITERAL`에서 손으로 파생했다.
_R17_ABS_INVERSION_ROWS: tuple[_AbsRow, ...] = (
    _AbsRow(
        -513,
        "resolved",
        PATCHED,
        -1,
        511,
        ADDRESS_BASIS_ABS_BACK_CALCULATED,
        _R17_STATUS_DEFECT_R17A,
    ),
    _AbsRow(
        -512,
        "resolved",
        PATCHED,
        -1,
        512,
        ADDRESS_BASIS_ABS_BACK_CALCULATED,
        _R17_STATUS_DEFECT_R17A,
    ),
    _AbsRow(
        -5, "resolved", PATCHED, 0, 507, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_DEFECT_R17A
    ),
    _AbsRow(
        -1, "resolved", PATCHED, 0, 511, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_DEFECT_R17A
    ),
    _AbsRow(0, "resolved", UNPATCHED_DESIGNED, None, 0, None, _R17_STATUS_SPEC),
    _AbsRow(1, "resolved", PATCHED, 1, 1, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(2, "resolved", PATCHED, 1, 2, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(511, "resolved", PATCHED, 1, 511, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(512, "resolved", PATCHED, 1, 512, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(513, "resolved", PATCHED, 2, 1, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(514, "resolved", PATCHED, 2, 2, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1023, "resolved", PATCHED, 2, 511, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1024, "resolved", PATCHED, 2, 512, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1025, "resolved", PATCHED, 3, 1, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1535, "resolved", PATCHED, 3, 511, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1536, "resolved", PATCHED, 3, 512, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
    _AbsRow(1537, "resolved", PATCHED, 4, 1, ADDRESS_BASIS_ABS_BACK_CALCULATED, _R17_STATUS_SPEC),
)

#: 표에서 파생하지 **않은** 독립 커버리지 요구 — 블록 경계 앞뒤 한 칸(0~3블록) 전부와
#: 0·음수 표본. 행을 하나 지우면 아래 등호 단정이 깨진다.
_R17_REQUIRED_ABS_VALUES = frozenset(
    {block * _R17_WIDTH_LITERAL + delta for block in (0, 1, 2, 3) for delta in (-1, 0, 1)}
    | {2, 514, -5, -512, -513}
)


class TestR17AbsoluteInversionBoundaryTable:
    """[round17 #4] `address.py`의 절대주소 역산(`//`·`%`) 경계 전수."""

    def test_the_table_covers_exactly_the_required_boundary_values(self):
        """[round17 표 전수] 행을 지우거나 중복시키면 실패한다."""
        values = tuple(row.value for row in _R17_ABS_INVERSION_ROWS)
        assert len(values) == 17, "행수 리터럴 — 행 삭제/추가 감지"
        assert len(set(values)) == len(values), "같은 절대주소가 두 번 들어갔다"
        assert set(values) == _R17_REQUIRED_ABS_VALUES
        # 비공허성 — 두 분류가 모두 표에 있다(한쪽만 남기면 갈래 하나가 무검증이 된다).
        assert {row.classification for row in _R17_ABS_INVERSION_ROWS} == {
            PATCHED,
            UNPATCHED_DESIGNED,
        }

    @pytest.mark.parametrize("row", _R17_ABS_INVERSION_ROWS, ids=lambda r: f"abs{r.value}")
    def test_each_boundary_value_inverts_to_the_declared_universe_and_address(self, row):
        """[round17 #4] `address.py`의 `universe = ((value - 1) // _UNIVERSE_WIDTH) + 1`을
        `(value // _UNIVERSE_WIDTH) + 1`로 바꾸면 abs=512 행이 u=2를 내며 실패한다.
        형제 줄 `address = ((value - 1) % _UNIVERSE_WIDTH) + 1`을 같은 형태로 한 칸
        (`(value % _UNIVERSE_WIDTH) + 1`) 바꾸면 abs=512 행이 a=1을 내며 실패한다.
        `_UNIVERSE_WIDTH`를 513으로 바꾸면 abs=513 행이 u=1을 내며 실패한다.
        `if value == 0:`을 `<= 0`으로 바꾸면 abs=-1 행이 unpatched_designed로 뒤집힌다.

        음수 행의 기대값은 **현행 동작 기록**이며 옳다는 판정이 아니다 —
        `_R17_STATUS_DEFECT_R17A` 주석과 결함 R17-A 참조.
        """
        outcome = classify_and_resolve({"absolute_address": str(row.value)})
        assert outcome.kind == row.kind
        assert outcome.classification == row.classification
        assert outcome.universe == row.universe
        assert outcome.address == row.address
        assert outcome.address_basis == row.basis

    @pytest.mark.parametrize("row", _R17_ABS_INVERSION_ROWS, ids=lambda r: f"abs{r.value}")
    def test_confirmed_premise_only_upgrades_the_basis_never_the_numbers(self, row):
        """[round17 #12] 전제 확인 플래그가 **역산 여부가 아니라 등급만** 가른다는
        v0.1.7 규약을 경계 전수로 고정한다 — 누가 구 독스트링("절대 수행하지 않는다")을
        근거로 `contiguous_512_confirmed=False`에서 역산을 막으면 전 행이 실패한다."""
        confirmed = classify_and_resolve(
            {"absolute_address": str(row.value)}, contiguous_512_confirmed=True
        )
        assert (confirmed.kind, confirmed.universe, confirmed.address) == (
            row.kind,
            row.universe,
            row.address,
        )
        expected = ADDRESS_BASIS_ABS_CONFIRMED if row.basis is not None else None
        assert confirmed.address_basis == expected


#: 정방향 `(u-1)*512+a`와 왕복 일치를 확인할 좌표 — 유니버스 4개 × 주소 4칸
#: (바닥 · 바닥+1 · 폭-1 · 폭)의 전조합.
_R17_ROUNDTRIP_UNIVERSES = (1, 2, 3, 4)
_R17_ROUNDTRIP_ADDRESSES = (1, 2, _R17_WIDTH_LITERAL - 1, _R17_WIDTH_LITERAL)
_R17_ROUNDTRIP_PAIRS = tuple(
    (universe, address)
    for universe in _R17_ROUNDTRIP_UNIVERSES
    for address in _R17_ROUNDTRIP_ADDRESSES
)


class TestR17ForwardAndRoundTripAtEveryBoundary:
    """[round17 #4] 정방향 `(u-1)*512+a`와 역방향 `//`·`%`가 경계 전 좌표에서 **서로의
    역함수**임을 고정한다. 정방향 식의 기존 대조군은 u=1·u=2 표본 둘뿐이라
    `(universe - 1)`을 `universe`로 바꿔도 큰 u에서만 어긋나 놓칠 수 있었다."""

    def test_the_pair_table_covers_exactly_the_declared_axes(self):
        """[round17 표 전수] 축에서 값을 하나 빼면 실패한다."""
        assert len(_R17_ROUNDTRIP_PAIRS) == 16, "행수 리터럴 — 행 삭제/추가 감지"
        assert {u for u, _ in _R17_ROUNDTRIP_PAIRS} == {1, 2, 3, 4}
        assert {a for _, a in _R17_ROUNDTRIP_PAIRS} == {1, 2, 511, 512}

    @pytest.mark.parametrize("pair", _R17_ROUNDTRIP_PAIRS, ids=lambda p: f"u{p[0]}a{p[1]}")
    def test_absolute_round_trips_back_to_the_same_universe_and_address(self, pair):
        """[round17 #4] 역산 두 줄 중 어느 쪽이든 한 칸 옮기면 폭 경계 좌표
        (a=512 · a=1)에서 왕복이 깨져 실패한다."""
        universe, address = pair
        absolute = (universe - 1) * _R17_WIDTH_LITERAL + address
        outcome = classify_and_resolve({"absolute_address": str(absolute)})
        assert (outcome.universe, outcome.address) == (universe, address)

    @pytest.mark.parametrize("pair", _R17_ROUNDTRIP_PAIRS, ids=lambda p: f"u{p[0]}a{p[1]}")
    def test_a_consistent_triple_never_raises_the_mismatch_warning(self, pair):
        """[round17 #4 형제] 교차검증 기댓값 `(universe - 1) * _UNIVERSE_WIDTH + address`를
        `universe * _UNIVERSE_WIDTH + address`로 바꾸면 **일치하는** 3중 표현이 전부
        불일치 경고를 달며 실패한다."""
        universe, address = pair
        absolute = (universe - 1) * _R17_WIDTH_LITERAL + address
        outcome = classify_and_resolve(
            {
                "universe": str(universe),
                "address": str(address),
                "absolute_address": str(absolute),
            }
        )
        assert outcome.warning_kind is None
        assert (outcome.universe, outcome.address) == (universe, address)
        assert outcome.address_basis == ADDRESS_BASIS_DIRECT

    @pytest.mark.parametrize("pair", _R17_ROUNDTRIP_PAIRS, ids=lambda p: f"u{p[0]}a{p[1]}")
    def test_an_absolute_off_by_one_always_raises_the_mismatch_warning(self, pair):
        """[round17 #4 형제 · 비공허성] 위 단정이 "경고는 절대 안 난다"는 공허한 검사가
        아님을 같은 좌표에서 보인다 — 절대주소를 한 칸만 어긋내면 전 좌표에서 경고가
        난다. 교차검증 비교를 상수 False로 바꾸면 여기서 실패한다."""
        universe, address = pair
        absolute = (universe - 1) * _R17_WIDTH_LITERAL + address + 1
        outcome = classify_and_resolve(
            {
                "universe": str(universe),
                "address": str(address),
                "absolute_address": str(absolute),
            }
        )
        assert outcome.warning_kind == READ_FAILURE_ADDRESS_TRIPLE_MISMATCH
        # 값은 여전히 쌍을 그대로 신뢰한다 — 경고가 값을 바꾸지 않는다.
        assert (outcome.universe, outcome.address) == (universe, address)

    @pytest.mark.parametrize("pair", _R17_ROUNDTRIP_PAIRS, ids=lambda p: f"u{p[0]}a{p[1]}")
    def test_console_form_agrees_with_normalize_address_at_every_boundary(self, pair):
        """[round17 AC-VWX-012 경계] `to_console_form`이 경계 좌표에서도
        `normalize_address`와 같은 정수쌍을 낸다(기존 대조군은 (1, 1) 한 점뿐이었다)."""
        universe, address = pair
        parse = to_console_form(universe, address)
        console = normalize_address(f"{universe}.{address}")
        assert (parse.universe, parse.address) == (universe, address)
        assert (parse.universe, parse.address) == (console.universe, console.address)


class _SplitRow(NamedTuple):
    """`Universe/Address` 조합값 파싱 한 칸."""

    raw: str
    tokens: int
    universe: int | None
    address: int | None
    kind: str
    reason: str | None
    classification: str | None
    basis: str | None


_RESOLVED = "resolved"
_READ_FAILURE = "read_failure"

#: 조합값 파싱의 **토큰 수 전수**(0·1·2·3·4) × 구분자 전수(`/` `:` `-` `.`) × 잡음
#: (빈 토큰 · 공백 · 비숫자 · 선행 0). `tokens`는 프로덕션 정규식이 아니라 아래
#: `_R17_SEPARATOR_PATTERN`(독립 리터럴)로 손계산한 값이다.
_R17_SPLIT_ROWS: tuple[_SplitRow, ...] = (
    _SplitRow("", 0, None, None, _READ_FAILURE, READ_FAILURE_NO_ADDRESS_DATA, None, None),
    _SplitRow("   ", 0, None, None, _READ_FAILURE, READ_FAILURE_NO_ADDRESS_DATA, None, None),
    _SplitRow("5", 1, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow("1.", 1, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow(".5", 1, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow("1.5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1/5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1:5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1-5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1..5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow(" 1 . 5 ", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("01.05", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("-1.5", 2, 1, 5, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1.512", 2, 1, 512, _RESOLVED, None, PATCHED, ADDRESS_BASIS_DIRECT),
    _SplitRow("1.0", 2, 1, 0, _RESOLVED, None, UNPATCHED_DESIGNED, None),
    _SplitRow("1.x", 2, 1, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow("x.5", 2, None, 5, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow("1.5.7", 3, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None),
    _SplitRow(
        "12.300.9", 3, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None
    ),
    _SplitRow(
        "1.5.7.9", 4, None, None, _READ_FAILURE, READ_FAILURE_ADDRESS_UNPARSEABLE, None, None
    ),
)


def _r17_independent_token_count(raw: str) -> int:
    """프로덕션을 부르지 않고 토큰 수를 센다 — 표의 `tokens` 열을 검증하는 독립 계산."""
    return len([part for part in re.split(_R17_SEPARATOR_PATTERN, raw.strip()) if part])


class TestR17CombinedAddressTokenTable:
    """[round17 #5] `split_universe_address`의 토큰 수 전수.

    치명 #5의 기제: `if len(parts) != 2`를 `< 2`로 한 칸 넓히면 `"1.5.7"`이 **거부되지
    않고** 앞 두 토큰만 취해 `u=1 a=5`로 **확신 있는 주소**가 되어 나간다. 판독 불가를
    판독 성공으로 바꾸는 fail-open이고, 그 값이 그대로 생성 대상 주소가 된다.
    round16까지 이 함수의 대조군은 2토큰 성공 사례뿐이라 3토큰·1토큰 갈래가 무검증이었다.
    """

    def test_the_table_covers_every_token_count_and_every_separator(self):
        """[round17 표 전수] 행을 지우면 행수·토큰수 집합·구분자 커버리지 중 하나가 깨진다."""
        assert len(_R17_SPLIT_ROWS) == 20, "행수 리터럴 — 행 삭제/추가 감지"
        assert len({row.raw for row in _R17_SPLIT_ROWS}) == 20, "같은 입력이 두 번 들어갔다"
        # 독립 선언한 토큰 수 전수 — 표에서 파생하지 않는다.
        assert {row.tokens for row in _R17_SPLIT_ROWS} == {0, 1, 2, 3, 4}
        for separator in _R17_SEPARATORS:
            assert any(separator in row.raw for row in _R17_SPLIT_ROWS), separator
        # 비공허성 — 성공·실패 두 결론이 모두 표에 있다.
        assert {row.kind for row in _R17_SPLIT_ROWS} == {_RESOLVED, _READ_FAILURE}

    @pytest.mark.parametrize("row", _R17_SPLIT_ROWS, ids=lambda r: repr(r.raw))
    def test_the_declared_token_count_matches_an_independent_split(self, row):
        """[round17 표 자기검증] 표의 `tokens` 열이 프로덕션과 무관하게 손계산과 맞는지
        확인한다 — 열이 틀리면 위 커버리지 게이트가 거짓 안심을 준다."""
        assert _r17_independent_token_count(row.raw) == row.tokens

    @pytest.mark.parametrize("row", _R17_SPLIT_ROWS, ids=lambda r: repr(r.raw))
    def test_split_universe_address_returns_the_declared_pair(self, row):
        """[round17 #5] `if len(parts) != 2:`를 `< 2`로 바꾸면 3·4토큰 행이 `(1, 5)`
        (또는 `(12, 300)`)를 내며 실패한다. `> 2`로 바꾸면 0·1토큰 행이 `IndexError`로
        터지며 실패한다. `!= 3`으로 바꾸면 2토큰 행 전부가 `(None, None)`이 되며 실패한다.
        """
        assert split_universe_address(row.raw) == (row.universe, row.address)

    @pytest.mark.parametrize("row", _R17_SPLIT_ROWS, ids=lambda r: repr(r.raw))
    def test_classify_and_resolve_agrees_with_the_declared_verdict(self, row):
        """[round17 #5 종단] 같은 입력이 **공개 진입점**을 지나서도 같은 판정을 내는지
        확인한다 — 조합값 갈래가 판독 실패를 판독 성공으로 바꾸지 않는다."""
        outcome = classify_and_resolve({"universe_address": row.raw})
        assert outcome.kind == row.kind
        assert outcome.reason_code == row.reason
        assert outcome.classification == row.classification
        assert outcome.address_basis == row.basis
        if row.kind == _RESOLVED:
            assert (outcome.universe, outcome.address) == (row.universe, row.address)

    def test_the_split_address_can_never_be_negative_so_the_zero_check_needs_no_lower_arm(self):
        """[round17 #5 형제 · 등가 뮤턴트 증명] 조합값 갈래의 `if address == 0:`을
        `<= 0`으로 바꿔도 행동이 같은 **이유**를 고정한다.

        `-`가 구분자 집합에 있으므로 부호는 토큰 분리 단계에서 먹힌다 — 조합값에서
        음수 주소는 **구성 자체가 불가능**하다. 구분자에서 `-`를 빼면(그 순간
        `"1-5"`가 2토큰이 아니게 되어) 위 구분자 커버리지 게이트가 먼저 실패하고,
        이 단정이 등가성의 전제를 지킨다. 등가 뮤턴트를 "무대조군"으로 오분류하지
        않도록 근거를 코드로 남긴다.
        """
        assert "-" in _R17_SEPARATOR_PATTERN
        for row in _R17_SPLIT_ROWS:
            _universe, address = split_universe_address(row.raw)
            assert address is None or address >= 0, row.raw
        # 직접 구성한 적대적 입력에서도 마찬가지다.
        for raw in ("-1.-5", "--1--5", "1.-0005", "-0.-0"):
            _universe, address = split_universe_address(raw)
            assert address is None or address >= 0, raw


# ==========================================================================
# [round17 HARD 규율 1] `server/vwx/` **전 모듈** 수치 경계 자리 레지스트리
# ==========================================================================
#
# round17의 교훈은 **"게이트가 모듈 경계에서 멈춘다"**이다 — 치명 5건 전부가 round15·16이
# 한 번도 뮤테이션하지 않은 모듈(`luagen.py`·`address.py`·`typemap.py`)에 있었고, round16
# 게이트는 자기 도달 범위 안에서는 견고했다. 그래서 이 레지스트리는 **손으로 모듈 이름을
# 적지 않고** `server/vwx` 디렉터리를 훑어 자리를 뽑는다 — 모듈이 늘어도 범위가 따라 늘고,
# 새 경계 자리를 등록 없이 넣으면 아래 전단사 게이트가 실패한다.
#
# 키는 **줄번호가 아니라 `(모듈, 축, ast.unparse 표현식)`**이다. 줄번호로 잡으면 다른
# 작업의 무관한 편집에도 표가 밀려 게이트가 유지 불가능해진다(round17에서 실측: 한 세션
# 안에 `apply.py` 510→515, `typemap.py` 370→388, `patchplan.py` 273→343으로 밀렸다).
#
# `status` 열의 뜻:
#   "gated"      — 이 자리를 한 칸 변조하면 스위트가 깨진다(격리 사본 뮤테이션으로 실측).
#   "equivalent" — 한 칸 변조가 **행동을 바꾸지 않는다**(도달 불가·부호 불가 등). 근거를
#                  `note`에 적는다. 등가 뮤턴트를 "무대조군"으로 오분류하지 않기 위한 칸이다.
# 이 열은 문서다 — 강제하는 것은 **자리의 등록 여부**이지 status 값이 아니다. status를
# 강제하면 표가 스스로를 증명하는 항진식이 된다.

#: 수치 경계로 세는 다섯 축. 이름을 바꾸면 아래 스캐너와 표가 함께 깨진다.
_R17_BOUNDARY_AXES = ("arith", "lencmp", "numcmp", "offby", "slice")


class _Site(NamedTuple):
    module: str
    axis: str
    expression: str


def _r17_plain_int(value: object) -> bool:
    """`bool`을 제외한 진짜 정수 리터럴인가 — `True`는 `int`의 부분형이라 걸러낸다."""
    return isinstance(value, int) and not isinstance(value, bool)


def _r17_boundary_axis(node: ast.AST) -> str | None:
    """AST 노드 하나가 어느 수치 경계 축인지 — 아니면 ``None``."""
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.FloorDiv, ast.Mod, ast.Div, ast.Mult)
    ):
        return "arith"
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        for side in (node.left, node.right):
            if isinstance(side, ast.Constant) and _r17_plain_int(side.value):
                return "offby"
    if isinstance(node, ast.Compare):
        text = ast.unparse(node)
        if "len(" in text:
            return "lencmp"
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and _r17_plain_int(comparator.value):
                return "numcmp"
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
        return "slice"
    return None


def _r17_scan_vwx_boundary_sites() -> set[_Site]:
    """`server/vwx` 디렉터리의 **모든** ``*.py``에서 수치 경계 자리를 전수로 뽑는다.

    읽는 범위는 `server/vwx` 전 모듈이며 모듈 이름을 손으로 적지 않는다 — 모듈이
    추가되면 범위가 자동으로 따라 늘어난다.
    """
    package = Path(__file__).resolve().parents[1] / "vwx"
    found: set[_Site] = set()
    for path in iter_vwx_modules(package):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            axis = _r17_boundary_axis(node)
            if axis is not None:
                found.add(_Site(vwx_module_label(path), axis, ast.unparse(node)))
    return found


#: `server/vwx` 전 모듈의 수치 경계 자리 등기부. 새 자리를 넣으면 아래 전단사 게이트가
#: **등록할 정확한 튜플을 찍어주며** 실패한다.
_R17_VWX_BOUNDARY_SITES: tuple[_Site, ...] = (
    _Site("address.py", "arith", "(universe - 1) * _UNIVERSE_WIDTH"),
    _Site("address.py", "arith", "(value - 1) % _UNIVERSE_WIDTH"),
    _Site("address.py", "arith", "(value - 1) // _UNIVERSE_WIDTH"),
    _Site("address.py", "lencmp", "len(parts) != 2"),
    _Site("address.py", "numcmp", "_to_int(dmx_raw) == 0"),
    _Site("address.py", "numcmp", "address == 0"),
    _Site("address.py", "numcmp", "value == 0"),
    _Site("address.py", "offby", "(value - 1) % _UNIVERSE_WIDTH + 1"),
    _Site("address.py", "offby", "(value - 1) // _UNIVERSE_WIDTH + 1"),
    _Site("address.py", "offby", "universe - 1"),
    _Site("address.py", "offby", "value - 1"),
    _Site("address.py", "slice", "system.strip().upper()[:1]"),
    _Site("apply.py", "lencmp", "len(by_index) != 1"),
    _Site("apply.py", "lencmp", "len(by_name) != 1"),
    _Site("apply.py", "lencmp", "len(candidates) == 1"),
    _Site("apply.py", "lencmp", "len(found) == 1"),
    _Site("apply.py", "lencmp", "len(found) > 1"),
    _Site("apply.py", "lencmp", "len(occupants) > 1"),
    _Site("apply.py", "numcmp", "unread > 0"),
    _Site("apply.py", "numcmp", "verification.created_count == 0"),
    # --- 실물 워크시트 계수 요약행 판별 (columns.py `_column_count_row_indices`) —
    # Vectorworks `Create Report` 워크시트는 헤더 아래에 컬럼별 레코드 수 행을 둔다.
    # 그 행은 헤더와 **폭이 같아** reader의 소계 감지를 통과하고 값이 전부 정수라
    # 최소 레코드 조건도 통과했다(실물 화면 근거로 재현 — 조명 11대가 12대로 읽혔다).
    # 판별은 휴리스틱이 아니라 **등식**이다: 후보행의 각 값 == 그 컬럼 아래 비어있지
    # 않은 셀 수. 아래 네 자리가 그 등식의 경계다.
    #   `>= 2`를 `>= 1`로 밀면 한 칸짜리 정수 행(합계 하나만 남은 꼬리행)이 후보가 되고,
    #   `>= 3`으로 밀면 두 컬럼짜리 워크시트에서 요약행을 놓쳐 유령이 되살아난다.
    #   `counts.get(header, 0) + 1`은 계수 그 자체라 ±1이 곧 오판이다.
    #   `index + 1`(블록 시작)과 슬라이스 끝을 밀면 요약행 자신이 자기 계수에 포함되거나
    #   다음 블록 첫 행을 잃는다 — 어느 쪽이든 등식이 깨져 요약행이 데이터로 산다.
    # 양방향 대조군은 `test_vwx_worksheet_grid.py`.
    _Site("columns.py", "lencmp", "len(nonempty) >= 2"),
    _Site("columns.py", "offby", "counts.get(header, 0) + 1"),
    _Site("columns.py", "offby", "index + 1"),
    _Site("columns.py", "slice", "raw_records[index + 1:end]"),
    # --- 타입 조달 안내 (typesource.py) — 콘솔 라이브러리 경로를 만드는 자리.
    # 수치 경계가 아니라 **경로 조립**이지만 스캐너가 `/` 연산을 산술로 센다.
    # 실물 디스크로 확인한 값이다: `~/MALightingTechnology/gma3_library/` 아래
    # `fixturetypes`(GDTF)와 `mvr`(MVR — `patch_mvr.html`이 명시). 어긋나면 조작자가
    # 파일을 **없는 자리에 놓고** 콘솔 Library 탭에서 못 찾는다.
    # 문자열은 `FIXTURE_TYPE_HINT`/`MVR_HINT` 두 상수가 한 번만 만든다 — 문장마다
    # 다시 조립하면 한 곳만 고쳤을 때 안내가 갈라진다.
    _Site("typesource.py", "arith", "LIBRARY_ROOT / 'fixturetypes'"),
    _Site("typesource.py", "arith", "LIBRARY_ROOT / 'mvr'"),
    _Site("typesource.py", "arith", "Path('MALightingTechnology') / 'gma3_library'"),
    _Site("typesource.py", "arith", "Path('~') / FIXTURE_TYPE_DIR"),
    _Site("typesource.py", "arith", "Path('~') / MVR_DIR"),
    # --- 인테이크 (intake.py) — 부분 정보를 질문으로 바꾸는 자리. 수치 경계는 셋뿐이다:
    #   `len(exact)/len(near) == 1`  이름이 **하나로 좁혀질 때만** 확정한다. 밀면
    #      후보 여럿에서 첫 것을 집어 엉뚱한 타입으로 패치된다 — R22-C와 같은 붕괴다.
    #   `len(modes) == 1`            모드가 하나뿐일 때만 자동 선택.
    #      밀면 둘 중 하나를 조용히 고른다.
    #   `quantity < 1`               0대·음수는 질문으로 되돌린다.
    #   `len(starts)/len(out) < count`  자동 배정 루프의 종료 조건. 어긋나면 요청한 수와
    #      만든 행 수가 갈라진다(모자라거나 남는다).
    #   `starts[:_PREVIEW_LIMIT]` / `len(starts) > len(preview)`  사용자에게 보여 줄 미리보기.
    #      값이 아니라 **표시**라 판정에 영향이 없다 — 그래서 여기 등기하고 대조군은 얕다.
    #   `index * (footprint or 1)`   수동 지정 시 다음 픽스처까지의 간격. MA3가 첫 주소를
    #      받아 채널 수만큼 띄우는 것과 같다.
    # 양방향 대조군은 `test_vwx_intake.py`.
    _Site("intake.py", "arith", "index * (footprint or 1)"),
    _Site("intake.py", "lencmp", "len(exact) == 1"),
    _Site("intake.py", "lencmp", "len(modes) == 1"),
    _Site("intake.py", "lencmp", "len(near) == 1"),
    _Site("intake.py", "lencmp", "len(out) < count"),
    _Site("intake.py", "lencmp", "len(starts) < count"),
    _Site("intake.py", "lencmp", "len(starts) > len(preview)"),
    _Site("intake.py", "numcmp", "quantity < 1"),
    _Site("intake.py", "slice", "starts[:_PREVIEW_LIMIT]"),
    # --- DMX 절대주소 산술 (mvr.py) — **저장소에 이 한 자리뿐이다.**
    # MVR `Address`는 break 기준 절대 DMX(실물 실측 1~1834)이고 MA3 Patch 표기는
    # `universe.address`다(`patch_add_fixtures.html`). 이 SPEC에서 가장 고전적인
    # off-by-one 지대라, 512/513이 어긋나면 **유니버스 하나가 통째로** 밀려 176대가
    # 전부 엉뚱한 주소에 선다.
    #   `absolute - 1` / `// + 1` / `% + 1`  split_absolute — 512가 유니버스 2로 넘어가거나
    #      유니버스가 0부터 세어지거나 각 유니버스 첫 칸이 사라진다.
    #   `(universe - 1) * UNIVERSE_WIDTH`    join_absolute — split의 역. 왕복이 깨진다.
    #   `absolute + max(width, 1) - 1`       fits_in_one_universe — 마지막 채널. `-1`을 빼면
    #      경계에 딱 맞는 픽스처를 걸친다고 오판해 유니버스 하나를 통째로 버린다.
    #   `universe + 1`                       next_universe_start — 안 밀면 무한 루프다.
    # **처음엔 이 산술이 intake.py에도 있었다.** 형제 표면이 되기 전에 여기로 모았고,
    # 그 결과 intake의 경계 자리가 23 -> 8로 줄었다(round24 교훈 ⓐ: 복사가 아니라 분해).
    # 양방향 대조군은 `test_vwx_mvr.py`의 경계 파라미터 6행(1·512·513·1024·1025·1834).
    _Site("mvr.py", "arith", "zero_based % UNIVERSE_WIDTH"),
    _Site("mvr.py", "arith", "zero_based // UNIVERSE_WIDTH"),
    _Site("mvr.py", "arith", "(universe - 1) * UNIVERSE_WIDTH"),
    _Site("mvr.py", "offby", "absolute - 1"),
    _Site("mvr.py", "offby", "absolute + max(width, 1) - 1"),
    _Site("mvr.py", "offby", "universe + 1"),
    _Site("mvr.py", "offby", "universe - 1"),
    _Site("mvr.py", "offby", "zero_based % UNIVERSE_WIDTH + 1"),
    _Site("mvr.py", "offby", "zero_based // UNIVERSE_WIDTH + 1"),
    # GDTF에서 읽은 채널 수를 실을지 판정하는 자리. `> 0`을 `>= 0`으로 밀면 채널 수를
    # 못 읽은 모드가 `"0"`을 싣고, 그 0이 하류에서 「0채널 픽스처」로 읽힌다.
    # 못 읽었으면 **비운다** — 추측한 숫자를 싣지 않는다.
    _Site("mvr.py", "numcmp", "entry.modes[mode] > 0"),
    # `.gdtf` 확장자를 벗겨 `GDTFSpec` 키를 만드는 자리. 길이가 어긋나면 컨테이너의
    # 타입 파일과 장면 XML의 참조가 안 맞아 채널 수를 통째로 잃는다.
    _Site("mvr.py", "slice", "name[:-len('.gdtf')]"),
    _Site("diff.py", "lencmp", "len(designed_rig.observed_systems) >= 2"),
    _Site("diff.py", "offby", "console_counts.get(fixture_type, 0) + 1"),
    _Site("diff.py", "offby", "designed_counts.get(itype, 0) + 1"),
    _Site("luagen.py", "numcmp", "ord(char) < 32"),
    _Site("luagen.py", "numcmp", "ord(char) == 127"),
    _Site("patchplan.py", "lencmp", "len(read_slots) > child_count"),
    _Site("patchplan.py", "numcmp", "footprint <= 0"),
    _Site("patchplan.py", "numcmp", "self.unparsable_rows > 0"),
    _Site("patchplan.py", "numcmp", "self.unreadable_fids > 0"),
    _Site("patchplan.py", "numcmp", "self.unseen > 0"),
    _Site("patchplan.py", "numcmp", "self.unusable_rows > 0"),
    # --- round19 절단 복구 스윕 (TruncationSweep) — 스윕 상한. `range(1, boundary + 1)`의
    # `+ 1`을 지우면 마지막 슬롯을 프로브하지 않아 `unseen`이 1 남고 배정이 상시 거부된다.
    # 반대로 `+ 2`면 선언 총계 밖을 프로브한다. 양방향 대조군은
    # `test_autopatch_fid.py`의 `test_r19_the_sweep_probes_exactly_the_declared_range`.
    _Site("patchplan.py", "offby", "recovery_boundary + 1"),
    _Site("patchplan.py", "offby", "target.address + footprint - 1"),
    _Site("patchplan.py", "slice", "sha256(encoded.encode('utf-8')).hexdigest()[:16]"),
    _Site("reader.py", "arith", "control / len(text)"),
    _Site("reader.py", "lencmp", "control / len(text) > 0.1"),
    _Site("reader.py", "lencmp", "len(row) == width"),
    _Site("reader.py", "lencmp", "len(widths) == 1"),
    _Site("reader.py", "numcmp", "byte == 0"),
    _Site("reader.py", "numcmp", "header_index < 0"),
    _Site("reader.py", "numcmp", "header_index == 0"),
    _Site("reader.py", "numcmp", "ord(ch) < 32"),
    _Site("reader.py", "offby", "header_index + 1"),
    _Site("reader.py", "offby", "widths.get(len(row), 0) + 1"),
    _Site("reader.py", "slice", "data[:2]"),
    _Site("reader.py", "slice", "rows[:_HEADER_SCAN_LIMIT]"),
    _Site("reader.py", "slice", "rows[header_index + 1:]"),
    _Site("report.py", "arith", "rig.dropped_row_count / rig.candidate_row_count"),
    _Site("report.py", "lencmp", "len(join_conflicts) > 3"),
    _Site("report.py", "lencmp", "len(self.diff.designed_rig.fixtures) > 0"),
    _Site("report.py", "lencmp", "len(self.diff.designed_rig.observed_systems) <= 1"),
    _Site("report.py", "numcmp", "rig.candidate_row_count <= 0"),
    _Site("report.py", "offby", "counts.get(entry.kind, 0) + 1"),
    _Site("report.py", "offby", "len(join_conflicts) - 3"),
    _Site("report.py", "slice", "join_conflicts[:3]"),
    _Site("rig.py", "lencmp", "len(channels) == 1"),
    _Site("rig.py", "lencmp", "len(channels) > 1"),
    _Site("rig.py", "lencmp", "len(members) < 2"),
    _Site("rig.py", "lencmp", "len(members) > 1"),
    _Site("rig.py", "numcmp", "dropped_row_count > 0"),
    _Site("rig.py", "numcmp", "value > 0"),
    _Site("rig.py", "offby", "fixture.address + fixture.footprint - 1"),
    _Site("rig.py", "offby", "i + 1"),
    _Site("rig.py", "slice", "intervals[i + 1:]"),
    _Site("rig.py", "slice", "raw.strip().upper()[:1]"),
    # --- round23 R23-2 · round24 R24-5 (CostBasis · EquivDisclosure) — 회수 비용 고지의
    # `c·m` 항. 비용표 `U + k(1 + c·m)`에서 `c`는 모드 한 종당 왕복 수다. round23은
    # 이 자리에 **상한 상수**를 곱했고(호출 인자를 사후에 못 읽는다는 이유), 그래서
    # 기각선 3,872(= `c=1` negative 단가로 유도된 수)와 **단위가 어긋났다** — negative
    # 분기가 약 1.9배 엄하게 판정됐다(R24-5). 이제 스윕이 자기 단가를 기록하고
    # (`FixtureTypeLibrary.recovery_mode_roundtrips`) 이 자리는 그 값을 곱한다.
    # `*`를 `+`로 밀거나 단가를 낮추면 고지가 **과소보고**로 돌아가 `False`(= "쟀는데
    # 범위 안"이라는 긍정 주장)가 거짓이 된다. 반대로 단가를 키우면 negative 분기가
    # 다시 과다 고지로 돌아간다. **양방향 대조군**은 `test_autopatch_types.py`의
    # round23 비용 절(상한·불변식·단조성·경계 등식)과 round24 단위 절(분기 간 판정
    # 일관성 · 감사 오탐 입력).
    _Site("typemap.py", "arith", "mode_roundtrips * len(entry.modes)"),
    _Site("typemap.py", "lencmp", "len(mode_candidates) == 1"),
    _Site("typemap.py", "lencmp", "len(type_candidates) == 1"),
    # --- round23 R22-B 초과 열거 (CompletenessGate) — 계수 대조의 **반대 방향**을
    # **루트 축과 모드 축 둘 다**에서 본다(한쪽만 고치면 "형제 절반만 고침"이 남는다).
    # `>`를 `>=`로 밀면 선언과 정확히 같은 관측이 초과로 읽혀 깨끗한 스냅샷이 상시
    # 불완전이 되고, `<`로 밀면 초과 열거가 영영 안 걸린다. 대조군은
    # `test_autopatch_types.py`의 round23 완전성 게이트 절.
    _Site("typemap.py", "lencmp", "len(self.types) > self.child_count"),
    _Site("typemap.py", "lencmp", "len(self.modes) > self.mode_child_count"),
    # --- round21 폐기 축 (SlotDiscard) — 목록 완전성 union의 세 번째 갈래. `> 0`을
    # `> 1`로 밀면 폐기 행 **한 개**가 union에 걸리지 않아 부분 목록이 전수로 읽히고,
    # `>= 0`(항상 참)으로 밀면 깨끗한 스냅샷도 상시 불완전이 된다. 양방향 대조군은
    # `test_autopatch_types.py`의 round21 절(`_R21_ROW_SHAPES` 계수 대조 + 폐기 0건
    # 스냅샷이 `enumeration_incomplete`를 세우지 않음).
    _Site("typemap.py", "numcmp", "self.mode_rows_discarded > 0"),
    _Site("typemap.py", "numcmp", "self.rows_discarded > 0"),
    # --- round21 표적 회수 스윕 (LibraryTruncation) — `recover_requested_types`.
    # `child_count + 1`은 `range(1, child_count + 1)`의 상한이라 **경계 그 자체**다:
    # `+2`로 밀면 선언 총계를 넘는 인덱스를 프로브하고(존재하지 않는 슬롯을 물어본다),
    # `+0`으로 밀면 마지막 슬롯을 영영 회수하지 못한다. 양방향 대조군은
    # `test_r21_the_sweep_boundary_is_exactly_one_to_child_count`가 프로브된 인덱스
    # 목록을 값으로 고정해 잡는다.
    _Site("typemap.py", "offby", "child_count + 1"),
    # --- round23 R22-C (SweepCorrectness) — **`len(remaining) == len(pending)` 자리를
    # 지웠다.** 그 표현식은 "요청 키가 걸렸으면 그 슬롯에서 멈춘다"는 조기 종료의
    # 코드 형태였고, 포함관계 퍼지 매칭에서 **엉뚱한 타입을 확정**시켰다(R22-C). 이제
    # 스윕은 전 미열거 슬롯의 이름을 프로브해 일치를 전수로 모으고, 걸렸는지 여부만
    # 묻는 `any(...)`는 수치 경계가 아니라 등기 대상이 아니다. 모호성 확정 규율은
    # 열거 경로의 `len(type_candidates) == 1`(위 행)이 단독으로 진다 — 같은 판단을
    # 두 자리가 나눠 갖던 것이 결함의 기제였다.
)

#: 자리별 판정 메모 — 등가 뮤턴트임을 근거와 함께 남긴다(무대조군 오분류 방지).
#: 강제 대상이 아니라 기록이다. 키가 레지스트리에 없으면 아래 게이트가 잡는다.
_R17_BOUNDARY_EQUIVALENTS: dict[_Site, str] = {
    _Site("address.py", "numcmp", "address == 0"): (
        "조합값 갈래의 주소는 음수가 될 수 없다 — `-`가 구분자라 부호가 토큰 분리에서 먹힌다"
        "(TestR17CombinedAddressTokenTable의 등가 증명 테스트 참조)."
    ),
    _Site("reader.py", "numcmp", "header_index == 0"): (
        "바로 위 `if header_index < 0:`가 음수를 먼저 돌려보내므로 `<= 0`은 `== 0`과 같다."
    ),
    _Site("apply.py", "numcmp", "verification.created_count == 0"): (
        "`created_count`는 결과 목록을 세어 만든 값이라 음수가 될 수 없어 `<= 0`이 등가다 "
        "— 대신 `>= 0`(항상 참) 변조는 대조군이 잡는다."
    ),
}


def test_r17_the_boundary_registry_is_a_bijection_onto_server_vwx():
    """[round17 HARD 규율 1] `server/vwx` **전 모듈**의 수치 경계 자리가 모두 등기부에
    있고, 등기부에 유령 행이 없다.

    이 게이트가 요구하는 것은 "그 자리에 대조군이 있다"가 아니라 **"그 자리가 보인다"**이다.
    round15~17이 반복해서 놓친 것은 나쁜 판정이 아니라 **표 밖에 있던 자리**였다.
    """
    scanned = _r17_scan_vwx_boundary_sites()
    registered = set(_R17_VWX_BOUNDARY_SITES)
    missing = sorted(scanned - registered)
    ghost = sorted(registered - scanned)
    message = []
    if missing:
        message.append(
            "등록되지 않은 경계 자리 — 아래 행을 `_R17_VWX_BOUNDARY_SITES`에 추가하라:\n"
            + "\n".join(f"    _Site({s.module!r}, {s.axis!r}, {s.expression!r})," for s in missing)
        )
    if ghost:
        message.append(
            "프로덕션에 더는 없는 등기 행 — 삭제하라:\n"
            + "\n".join(f"    _Site({s.module!r}, {s.axis!r}, {s.expression!r})," for s in ghost)
        )
    assert not message, "\n\n".join(message)


def test_r17_the_boundary_registry_has_no_duplicate_rows():
    """[round17 표 전수] 등기부에서 행을 지우면 위 전단사 게이트가 잡고, 행을 중복시키면
    여기서 잡는다 — 중복 행은 커버리지 착시를 만든다."""
    assert len(_R17_VWX_BOUNDARY_SITES) == len(set(_R17_VWX_BOUNDARY_SITES))
    assert {site.axis for site in _R17_VWX_BOUNDARY_SITES} <= set(_R17_BOUNDARY_AXES)


def test_r17_the_boundary_scanner_is_not_vacuous():
    """[round17 비공허성] 스캐너가 "아무 것도 못 찾는 함수"가 아님을 다섯 축 각각에서
    보인다 — 축 하나라도 못 뽑으면 그 축 전체가 조용히 무검증이 된다."""
    scanned = _r17_scan_vwx_boundary_sites()
    assert scanned, "server/vwx에서 경계 자리를 하나도 못 뽑았다"
    for axis in _R17_BOUNDARY_AXES:
        assert any(site.axis == axis for site in scanned), axis
    # 축 판정기 자체를 합성 소스로 확인한다(프로덕션이 바뀌어도 축 정의가 유지되게).
    probes = {
        "arith": "a // b",
        "lencmp": "len(a) == 1",
        "numcmp": "a > 3",
        "offby": "a - 1",
        "slice": "a[:3]",
    }
    assert set(probes) == set(_R17_BOUNDARY_AXES), "축 프로브가 축 전수를 덮지 않는다"
    for axis, source in probes.items():
        node = ast.parse(source, mode="eval").body
        assert _r17_boundary_axis(node) == axis, source


def test_r17_every_equivalence_note_names_a_registered_site():
    """[round17] 등가 판정 메모가 **실재하는 자리**를 가리키는지 확인한다 — 프로덕션이
    바뀌어 그 자리가 사라지면 메모도 함께 정리되어야 한다(유령 근거 금지)."""
    registered = set(_R17_VWX_BOUNDARY_SITES)
    orphan = sorted(site for site in _R17_BOUNDARY_EQUIVALENTS if site not in registered)
    assert not orphan, f"등기부에 없는 자리에 등가 메모가 남아 있다: {orphan}"
    for site, note in _R17_BOUNDARY_EQUIVALENTS.items():
        assert note.strip(), site


# ==========================================================================
# [round17 #12] 문서-코드 모순 — 독스트링이 안전 속성에 대해 코드와 정반대였다
# ==========================================================================
#
# round17 이전 `classify_and_resolve` 독스트링은 *"검증되지 않은 한 Absolute Address
# 역산을 절대 수행하지 않는다(추측 금지, REQ-VWX-009)"*라고 적었는데, 코드는
# `contiguous_512_confirmed=False`에서도 **역산을 수행하고 등급만 낮춘다**(v0.1.7
# 재설계, ASSUMPTION-69 재정의). 안전 속성("절대 하지 않는다")에 대한 정반대 서술은
# 그 자체로 위험하다 — 다음 사람이 독스트링을 근거로 "그럼 이 역산은 버그"라며 되돌리면
# 설계 측 리그가 다시 무너진다(그게 v0.1.5→v0.1.6에서 실제로 일어난 결함 1, P0다).
#
# 그래서 문서를 고치고(동작은 손대지 않았다) **문서와 동작을 함께 못박는다**. 문서만
# 검사하면 리터럴 자기확인이고, 동작만 검사하면 문서가 다시 어긋난다 — 둘을 한
# 테스트에서 잇는다.

#: 되돌아오면 안 되는 구 문구 — 안전 속성을 정반대로 서술한다.
_R17_RETIRED_DOC_CLAIM = "절대 수행하지 않는다"


def test_r17_the_docstring_and_the_behaviour_agree_about_unconfirmed_back_calculation():
    """[round17 #12] `classify_and_resolve` 독스트링을 구 문구로 되돌리면 실패한다.

    두 방향을 한 자리에서 잇는다:
      1. **동작** — 전제 미확인에서도 역산이 수행되고 등급만 내려간다.
      2. **문서** — 그 동작을 서술한다. "절대 수행하지 않는다"는 되돌아올 수 없다.

    문서 단정만 있으면 리터럴 자기확인이므로, 같은 테스트가 프로덕션 함수를 실제로
    호출해 동작을 먼저 확인하고 그 관측과 문서가 같은 말을 하는지 본다.
    """
    unconfirmed = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=False)
    confirmed = classify_and_resolve({"absolute_address": "600"}, contiguous_512_confirmed=True)

    # 1. 관측 — 미확인에서도 역산이 **수행된다**.
    assert unconfirmed.kind == "resolved"
    assert (unconfirmed.universe, unconfirmed.address) == (2, 88)
    assert unconfirmed.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED
    assert "등급 하향" in unconfirmed.detail
    # 플래그가 가르는 것은 **등급뿐** — 숫자는 같다.
    assert (confirmed.universe, confirmed.address) == (unconfirmed.universe, unconfirmed.address)
    assert confirmed.address_basis == ADDRESS_BASIS_ABS_CONFIRMED
    assert confirmed.address_basis != unconfirmed.address_basis

    # 2. 문서 — 위 관측과 같은 말을 해야 한다.
    doc = classify_and_resolve.__doc__ or ""
    assert _R17_RETIRED_DOC_CLAIM not in doc, (
        "독스트링이 다시 '역산을 절대 수행하지 않는다'고 말한다 — 코드는 수행한다"
    )
    assert "역산은 수행한다" in doc, "미확인에서도 역산한다는 사실이 문서에 없다"
    assert "등급" in doc, "플래그가 가르는 것이 등급이라는 사실이 문서에 없다"
    assert "ABS_BACK_CALCULATED" in doc.upper(), "약한 등급의 이름이 문서에 없다"


def test_r17_the_retired_doc_claim_probe_is_not_vacuous():
    """[round17 #12 비공허성] 위 부재 단정이 "어떤 문자열이든 없다"는 공허한 검사가
    아님을 보인다 — 같은 부분문자열 검사를 구 문구가 실제로 들어 있는 문자열에 걸면
    잡힌다."""
    planted = "검증되지 않은 한 Absolute Address 역산을 절대 수행하지 않는다(추측 금지)."
    assert _R17_RETIRED_DOC_CLAIM in planted
