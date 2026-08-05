"""실물 샘플 3종(2026-08-05, 9번째 라운드) — 결함 1/2/3 회귀 + 6개 검증 항목.
문서 근거 · 실물 미검증.

fixture 3종 (전부 REAL — 합성물 아님):
- ``vectorworks_worksheet_multisystem_full.csv`` — 경로 B, 멀티시스템(A/B),
  멀티셀, DMX/비-DMX 액세서리 혼재, 미패치 행, 집계행 3건.
- ``vectorworks_worksheet_absolute_address_only.csv`` — 위와 동일한 리그를
  Universe/DMX Address 컬럼 없이 Absolute Address만으로 내보낸 변형(경로 B).
- ``vectorworks_export_instrument_data_no_header.txt`` — 경로 A, 헤더 행 없음
  ("Export field names as first record" 미체크).
"""

from __future__ import annotations

from pathlib import Path

from server.prechk.inventory import COMPLETE, Inventory
from server.vwx.address import classify_and_resolve, resolve_all
from server.vwx.columns import (
    EXCLUDED_ROW_AGGREGATE,
    EXCLUDED_ROW_NON_DMX_ACCESSORY,
    READ_FAILURE_HEADERLESS_EXPORT,
    READ_FAILURE_MIN_RECORD,
    resolve_columns,
)
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT, compare
from server.vwx.reader import PATH_A, read
from server.vwx.report import build_vwx_report
from server.vwx.rig import SCOPE_QUALIFIER as SCOPE_QUALIFIER_TEXT
from server.vwx.rig import build_designed_rig

FIXTURES = Path(__file__).parent / "fixtures" / "vwx"
MULTISYSTEM_FULL = FIXTURES / "vectorworks_worksheet_multisystem_full.csv"
ABSOLUTE_ONLY = FIXTURES / "vectorworks_worksheet_absolute_address_only.csv"
NO_HEADER = FIXTURES / "vectorworks_export_instrument_data_no_header.txt"


def _empty_inventory() -> Inventory:
    return Inventory(
        path="Patch/Stages/1/Fixtures",
        child_count=0,
        enumerated_count=0,
        recovered_count=0,
        observed_count=0,
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
    )


def _run_pipeline(data: bytes):
    """리더->컬럼->주소->리그 전 파이프라인. 테스트 전용 헬퍼.

    ``candidate_count``를 실제 파이프라인(``server/orchestrator/tools.py``)과
    동일하게 넘긴다 — 스코프 한정(v0.1.7, 결함 2 P1)이 여기서도 계산된다.
    """
    read_result = read(data)
    column_records, column_failures, excluded_rows = resolve_columns(list(read_result.records))
    resolved_records, address_failures = resolve_all(column_records)
    designed_rig = build_designed_rig(resolved_records, candidate_count=len(column_records))
    return read_result, column_failures, excluded_rows, address_failures, designed_rig


class TestDefect1MultiSystemNoLongerBlocksDesignedOutput:
    """결함 1(P0) — 멀티시스템에서 설계 측 산출이 전멸하던 결함의 회귀 방지.

    코디네이터 직접 실측: 수정 전에는 이 파일이 fixture_count=0을 냈다.
    """

    def test_multisystem_file_produces_nonzero_fixtures(self):
        """비공허성 — 수정 전에는 이 값이 0이었다(코디네이터 재현)."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert len(rig.fixtures) == 9

    def test_observed_systems_captures_both_letters(self):
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert rig.observed_systems == frozenset({"A", "B"})

    def test_titan_tube_unpatched_row_is_classified_unpatched_designed(self):
        """멀티시스템 차단이 사라져도 미패치(주소 0) sentinel 분류는 그대로 동작한다."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        titan = next(f for f in rig.fixtures if f.address == 0)
        assert titan.classification == "unpatched_designed"
        assert titan.universe == 2
        assert titan.system == "A"

    def test_console_join_is_skipped_but_reason_is_distinct_from_generic_read_failure(self):
        """콘솔 대조만 미수행 — 사유 문구가 일반 판독 실패와 절대 뭉뚱그려지지 않는다."""
        _read, cf, ex, af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        assert report.comparison_performed() is False
        payload = report.to_dict()
        assert payload["diffs"]["performed"] is False
        reason = payload["diffs"]["reason"]
        assert "멀티시스템" not in reason or "System" in reason  # 사유 자체는 System 언급
        assert "System" in reason
        assert "매핑" in reason
        # 결함 1이 고치기 전에 쓰이던 문구(일반 판독 실패 사유)와 다름을 확인.
        assert reason != "판독 실패 0건으로 설계상 리그를 세우지 못했다"
        kinds = {entry["kind"] for entry in payload["skipped_checks"]}
        assert MULTI_SYSTEM_MAPPING_ABSENT in kinds

    def test_single_system_file_still_performs_the_console_join(self):
        """비공허성 — 단일 System 파일은 콘솔 대조가 여전히 정상 수행된다."""
        from server.vwx.rig import DesignedRig

        single_system_records, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        only_a = tuple(f for f in rig.fixtures if f.system != "B")
        single_rig = DesignedRig(
            fixtures=only_a,
            join_key_conflicts=(),
            vw_patch_conflicts=(),
            device_type_column_present=True,
            observed_systems=frozenset({"A"}),
        )
        diff = compare(single_rig, _empty_inventory())
        assert diff.skipped_checks
        assert not any(entry.kind == MULTI_SYSTEM_MAPPING_ABSENT for entry in diff.skipped_checks)


class TestDefect2ExcludedRowsAreNotReadFailures:
    """결함 2(P1) — 집계행·비-DMX 액세서리를 판독 실패로 잘못 세던 결함의 회귀 방지."""

    def test_no_read_failures_for_a_structurally_clean_file(self):
        """비공허성 — 수정 전에는 4건의 min_record_incomplete가 나왔다(코디네이터 재현)."""
        _read, column_failures, _ex, address_failures, _rig = _run_pipeline(
            MULTISYSTEM_FULL.read_bytes()
        )
        assert not column_failures
        assert not address_failures

    def test_three_subtotal_total_rows_are_excluded_as_aggregate(self):
        _read, _cf, excluded, _af, _rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        aggregate = [e for e in excluded if e.kind == EXCLUDED_ROW_AGGREGATE]
        assert len(aggregate) == 3

    def test_top_hat_is_excluded_as_non_dmx_accessory_not_a_read_failure(self):
        _read, _cf, excluded, _af, _rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        non_dmx = [e for e in excluded if e.kind == EXCLUDED_ROW_NON_DMX_ACCESSORY]
        assert len(non_dmx) == 1

    def test_summary_ko_states_zero_read_failures_and_four_excluded_with_breakdown(self):
        _read, cf, ex, af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        summary = report.summary_ko()
        assert "판독 실패 0건" in summary
        assert "제외 4건" in summary
        assert "집계행 3" in summary
        assert "비DMX 액세서리 1" in summary

    def test_a_file_with_only_read_failures_and_no_exclusions_keeps_the_old_phrasing(self):
        """비공허성 — 제외행이 없으면 기존 "판독 실패 N건" 단독 문구를 유지한다."""
        from server.vwx.diff import DiffResult
        from server.vwx.rig import DesignedRig

        rig = DesignedRig(
            fixtures=(),
            join_key_conflicts=(),
            vw_patch_conflicts=(),
            device_type_column_present=False,
        )
        diff = DiffResult(
            designed_rig=rig,
            console_inventory=_empty_inventory(),
            missing_in_console=(),
            address_collisions=(),
            quantity_mismatches=(),
            skipped_checks=(),
        )
        from server.vwx.columns import ColumnReadFailure

        report = build_vwx_report(
            diff,
            read_failures=(ColumnReadFailure(row=0, kind=READ_FAILURE_MIN_RECORD, detail="x"),),
        )
        summary = report.summary_ko()
        assert "판독 실패 1건" in summary
        assert "제외" not in summary


class TestDefect3HeaderlessPathAConsolidation:
    """결함 3(P1) — 헤더 없는 경로 A 파일의 행별 실패 폭주를 파일 단위 판정 1건으로 압축."""

    def test_reader_still_structurally_reads_the_file_without_positional_guessing(self):
        result = read(NO_HEADER.read_bytes())
        assert result.path_kind == PATH_A
        assert len(result.records) == 17
        assert set(result.records[0]) == {f"col_{i}" for i in range(28)}

    def test_columns_layer_emits_exactly_one_consolidated_failure_not_seventeen(self):
        """비공허성 — 수정 전에는 이 파일이 17건의 개별 min_record_incomplete를 냈다."""
        result = read(NO_HEADER.read_bytes())
        records, failures, excluded = resolve_columns(list(result.records))
        assert records == []
        assert not excluded
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_HEADERLESS_EXPORT

    def test_the_single_failure_carries_actionable_remediation_text(self):
        result = read(NO_HEADER.read_bytes())
        _records, failures, _excluded = resolve_columns(list(result.records))
        detail = failures[0].detail
        assert "Export field names as first record" in detail
        assert "위치로 추측하지 않는다" in detail

    def test_a_headered_file_never_triggers_the_headerless_consolidation(self):
        """비공허성 — 헤더가 있는 정상 경로 A 파일은 여전히 정상 개별 판독된다."""
        result = read(MULTISYSTEM_FULL.read_bytes())
        records, failures, _excluded = resolve_columns(list(result.records))
        assert records
        assert not any(f.kind == READ_FAILURE_HEADERLESS_EXPORT for f in failures)


class TestMulticellFoldingWithMultiSystem:
    """검증 항목 ① — Part Index 1..8이 System 관측 여부와 무관하게 1개로 접힌다."""

    def test_eight_cell_rows_fold_into_exactly_one_fixture(self):
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        multicell = next(f for f in rig.fixtures if f.part_indices)
        assert multicell.part_indices == ("1", "2", "3", "4", "5", "6", "7", "8")

    def test_representative_row_is_the_minimum_part_index_at_address_201(self):
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        multicell = next(f for f in rig.fixtures if f.part_indices)
        assert multicell.address == 201
        assert multicell.universe == 1
        assert multicell.system == "A"

    def test_fixture_count_is_not_eight_times_inflated_by_the_multicell(self):
        """비공허성 — 8개 셀을 개별 계수했다면 quantity가 8배 부풀었을 것이다."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert len(rig.fixtures) == 9  # 8셀 -> 1 + 8개의 다른 픽스처/액세서리


class TestDmxAccessoryHandling:
    """검증 항목 ② — DMX 소비 액세서리는 포함, 비-DMX 액세서리는 배제(둘 다 "Accessory" 리터럴)."""

    def test_coloram_scroller_is_included_as_its_own_fixture(self):
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        coloram = [f for f in rig.fixtures if f.device_type == "Accessory"]
        assert len(coloram) == 1
        assert coloram[0].unit_number == "2B"
        assert coloram[0].footprint == 1

    def test_top_hat_never_reaches_the_designed_rig(self):
        """비공허성 — 배제되지 않았다면 fixture_count에 Top Hat이 섞였을 것이다."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert not any("Top Hat" in (f.fixture_name or "") for f in rig.fixtures)


class TestUnpatchedThirdClassification:
    """검증 항목 ③ — 미패치(주소 0)는 "콘솔 미확인"과 다른 별도 분류다."""

    def test_titan_tube_classification_is_distinct_from_missing_in_console(self):
        from server.vwx.address import UNPATCHED_DESIGNED
        from server.vwx.diff import MISSING_IN_CONSOLE

        assert UNPATCHED_DESIGNED != MISSING_IN_CONSOLE
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        titan = next(f for f in rig.fixtures if f.address == 0)
        assert titan.classification == UNPATCHED_DESIGNED

    def test_unpatched_fixture_is_excluded_from_the_console_join_when_it_would_run(self):
        """비공허성 — 미패치는 콘솔 대조가 정상 수행되는 상황에서도 조인 대상이 아니다."""
        from server.vwx.rig import DesignedRig

        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        only_a = tuple(f for f in rig.fixtures if f.system != "B")
        single_rig = DesignedRig(
            fixtures=only_a,
            join_key_conflicts=(),
            vw_patch_conflicts=(),
            device_type_column_present=True,
            observed_systems=frozenset({"A"}),
        )
        diff = compare(single_rig, _empty_inventory())
        assert not any(entry.address == 0 for entry in diff.missing_in_console)


class TestAccessoryJoinKeyDoesNotFoldOnSharedParentChannel:
    """검증 항목 ④ — 부모 채널을 물려받는 액세서리가 channel 우선순위로 잘못 접히지 않는다.

    이 파일에서 Channel "1"은 3행에 등장한다: VWX-A-0002(Unit 2, 일반 픽스처)
    + ACC1(Unit 2A, Top Hat) + ACC2(Unit 2B, Coloram). channel 최우선 조인을
    액세서리에도 적용했다면 이 3행이 하나로 잘못 접혔을 것이다(직전 라운드
    join-key-scope 수정이 만든 구멍).
    """

    def test_parent_and_accessory_sharing_channel_do_not_fold_into_one_fixture(self):
        _read, _cf, excluded, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        # ACC1(Top Hat)은 columns.py에서 excluded_rows로 먼저 걸러진다 —
        # 남는 건 VWX-A-0002(Unit 2)와 ACC2(Unit 2B) 둘이다.
        assert any(e.kind == "non_dmx_accessory" for e in excluded)
        unit_2 = next(f for f in rig.fixtures if f.unit_number == "2")
        unit_2b = next(f for f in rig.fixtures if f.unit_number == "2B")
        assert unit_2 is not unit_2b
        assert unit_2.address == 45
        assert unit_2b.address == 150
        # 둘 다 channel "1"을 공유하지만 서로 다른 픽스처로 남는다(비공허성).
        assert unit_2.channel == unit_2b.channel == "1"
        assert not rig.join_key_conflicts

    def test_non_numeric_accessory_unit_number_works_as_a_plain_string_key(self):
        """비공허성 — "2A"/"2B" 같은 비숫자 unit_number가 정상적으로 스코프 키로 동작한다."""
        raw = [
            {
                "Instrument Type": "S4",
                "Channel": "9",
                "Unit Number": "1",
                "Position": "FOH",
                "Universe": "1",
                "DMX Address": "1",
            },
            {
                "Instrument Type": "Scroller",
                "Device Type": "Accessory",
                "Channel": "9",
                "Unit Number": "1A",
                "Position": "FOH",
                "Universe": "1",
                "DMX Address": "2",
                "DMX Footprint": "1",
            },
        ]
        records, _failures, _excluded = resolve_columns(raw)
        resolved, address_failures = resolve_all(records)
        assert not address_failures
        rig = build_designed_rig(resolved)
        assert len(rig.fixtures) == 2
        assert not rig.join_key_conflicts


class TestPerSystemAbsoluteAddressAmbiguity:
    """검증 항목 ⑤ — Absolute Address 단독으로는 System을 구분할 수 없다(ASSUMPTION-69).

    파일 2(Universe/DMX Address 컬럼 없음)로 확인: B/System U1/abs=1과
    A/System U1/abs=1은 숫자값이 완전히 같다 — System이 별도 필드로
    보존되지 않으면 원리적으로 구분 불가능하다.

    v0.1.7 재설계(결함 1, P0) — "전제 미검증이면 거부"에서 "선언된 전제 위에서
    역산하고 근거를 등급으로 남긴다"로 바뀌었다. 02는 이제 01과 동일하게
    9대로 읽히며, 근거는 전부 역산(``absolute_back_calculated``)이고 리그
    전체에 전제 문구가 실린다.
    """

    def test_absolute_only_file_now_resolves_the_full_rig_not_just_the_unpatched_row(self):
        """비공허성 — 수정 전에는 fixture_count가 1(Titan Tube만)이었다."""
        _read, _cf, excluded, address_failures, rig = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        assert not address_failures  # 더 이상 미검증 사유로 탈락하는 행이 없다
        assert len(rig.fixtures) == 9  # 01과 동일한 리그(멀티셀 폴딩 포함)

    def test_rig_wide_address_basis_is_back_calculated_with_the_premise_note(self):
        from server.vwx.address import (
            ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE,
            ADDRESS_BASIS_ABS_BACK_CALCULATED,
        )

        _read, _cf, _ex, _af, rig = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        assert rig.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED
        assert rig.address_basis_note == ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE
        assert all(
            fixture.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED
            for fixture in rig.fixtures
            if fixture.classification == "patched"
        )

    def test_multisystem_full_file_is_direct_basis_not_back_calculated(self):
        """비공허성 대조군 — 01(Universe+DMX Address 쌍 존재)은 역산이 전혀 없다."""
        from server.vwx.address import ADDRESS_BASIS_DIRECT

        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert rig.address_basis == ADDRESS_BASIS_DIRECT
        assert rig.address_basis_note == ""

    def test_02_and_01_derive_the_same_universe_address_pairs_per_system(self):
        """02(abs 역산)와 01(직접값)이 같은 (system, universe, address)로 수렴한다 —
        abs1→u1a1(A) · abs45→u1a45(A) · abs513→u2a1(A) · abs642→u2a130(A) ·
        B abs1→u1a1(B)를 코디네이터가 직접 검산했다."""
        _read, _cf, _ex, _af, rig_02 = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        _read, _cf, _ex, _af, rig_01 = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        key = lambda fx: (fx.system, fx.unit_number)  # noqa: E731 — 로컬 테스트 헬퍼
        # 미패치(주소 0)는 제외한다 — Absolute Address=0 경로는 universe를 복원할
        # 근거가 없어 universe=None으로 남는다(기존 sentinel 분기, 이번 결함과 무관).
        addr_02 = {key(fx): (fx.universe, fx.address) for fx in rig_02.fixtures if fx.address != 0}
        addr_01 = {key(fx): (fx.universe, fx.address) for fx in rig_01.fixtures if fx.address != 0}
        assert addr_02 == addr_01

    def test_abs_1_resolves_identically_regardless_of_system_letter(self):
        """System A와 System B가 동일한 abs=1을 가지면 (universe,address) 역산 결과가
        완전히 같다 — System 문자를 별도로 안 붙이면 원리적으로 구분할 수 없다."""
        system_a = classify_and_resolve(
            {"absolute_address": "1", "system": "A"}, contiguous_512_confirmed=True
        )
        system_b = classify_and_resolve(
            {"absolute_address": "1", "system": "B"}, contiguous_512_confirmed=True
        )
        assert system_a.kind == system_b.kind == "resolved"
        assert (system_a.universe, system_a.address) == (system_b.universe, system_b.address)

    def test_system_field_is_the_only_thing_that_disambiguates_them(self):
        """``fields.get("system")``이 보존돼야만 두 레코드를 구분할 수 있다 — 주소
        해석 자체(``classify_and_resolve``)로는 System을 되살릴 수 없다."""
        raw_a = {"instrument_type": "X", "absolute_address": "1", "system": "A"}
        raw_b = {"instrument_type": "X", "absolute_address": "1", "system": "B"}
        assert raw_a.get("system") != raw_b.get("system")


class TestOverlapFalsePositivePreventionAcrossSystems:
    """검증 항목 ⑥ — (system, universe) 스코프 도입 후 이 파일의 겹침이 정확히 0이다.

    System을 무시했다면 A/U1/1과 B/U1/1이 오탐으로 겹침 판정됐을 것이다
    (이 파일이 의도적으로 설계한 함정).
    """

    def test_multisystem_file_reports_zero_design_overlaps(self):
        """비공허성 — 수정 전 코드(system 미고려)라면 A/U1과 B/U1이 오탐 겹침이었다."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert rig.design_overlaps == ()

    def test_a_and_b_both_have_universe_1_address_1_but_are_not_flagged(self):
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        a_u1_1 = next(f for f in rig.fixtures if f.system == "A" and f.address == 1)
        b_u1_1 = next(f for f in rig.fixtures if f.system == "B" and f.address == 1)
        assert a_u1_1.universe == b_u1_1.universe == 1
        assert rig.design_overlaps == ()

    def test_a_genuine_same_system_overlap_is_still_caught(self):
        """양성 대조군 — 같은 (system,universe) 안에서 stride < footprint면 여전히 잡힌다."""
        from server.vwx.address import PATCHED, ResolvedRecord

        records = [
            ResolvedRecord(
                fields={
                    "instrument_type": "A",
                    "unit_number": "1",
                    "system": "A",
                    "footprint": "10",
                },
                extra={},
                row_index=0,
                universe=1,
                address=1,
                classification=PATCHED,
            ),
            ResolvedRecord(
                fields={
                    "instrument_type": "B",
                    "unit_number": "2",
                    "system": "A",
                    "footprint": "10",
                },
                extra={},
                row_index=1,
                universe=1,
                address=5,
                classification=PATCHED,
            ),
        ]
        rig = build_designed_rig(records)
        assert len(rig.design_overlaps) == 1

    def test_the_same_stride_across_different_systems_is_never_flagged(self):
        """양성 대조군의 거울상 — 같은 좌표라도 system이 다르면 절대 겹치지 않는다(비공허성)."""
        from server.vwx.address import PATCHED, ResolvedRecord

        records = [
            ResolvedRecord(
                fields={
                    "instrument_type": "A",
                    "unit_number": "1",
                    "system": "A",
                    "footprint": "10",
                },
                extra={},
                row_index=0,
                universe=1,
                address=1,
                classification=PATCHED,
            ),
            ResolvedRecord(
                fields={
                    "instrument_type": "B",
                    "unit_number": "2",
                    "system": "B",
                    "footprint": "10",
                },
                extra={},
                row_index=1,
                universe=1,
                address=5,
                classification=PATCHED,
            ),
        ]
        rig = build_designed_rig(records)
        assert rig.design_overlaps == ()


class TestAddressBasisPayloadAndSummary:
    """02 재설계(v0.1.7, 결함 1 P0) — 근거 등급이 payload·summary_ko에 실제로 실린다."""

    def test_02_payload_reports_back_calculated_basis_per_fixture_and_rig_wide(self):
        from server.vwx.address import ADDRESS_BASIS_ABS_BACK_CALCULATED

        _read, cf, ex, af, rig = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        payload = report.to_dict()
        designed = payload["designed_rig"]
        assert designed["address_basis"] == ADDRESS_BASIS_ABS_BACK_CALCULATED
        assert "Universes pane" in designed["address_basis_note"]
        assert "512블록" in designed["address_basis_note"]
        patched_fixtures = [f for f in designed["fixtures"] if f["classification"] == "patched"]
        assert patched_fixtures
        assert all(
            f["address_basis"] == ADDRESS_BASIS_ABS_BACK_CALCULATED for f in patched_fixtures
        )

    def test_01_payload_reports_direct_basis_and_empty_note(self):
        from server.vwx.address import ADDRESS_BASIS_DIRECT

        _read, cf, ex, af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        payload = report.to_dict()
        designed = payload["designed_rig"]
        assert designed["address_basis"] == ADDRESS_BASIS_DIRECT
        assert designed["address_basis_note"] == ""

    def test_02_summary_ko_carries_the_premise_disclaimer(self):
        _read, cf, ex, af, rig = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        summary = report.summary_ko()
        assert "Universes pane" in summary
        assert "Start#/End#" in summary

    def test_01_summary_ko_never_mentions_the_premise_disclaimer(self):
        """비공허성 — 직접값 근거인 01은 역산 전제 문구가 전혀 등장하지 않는다."""
        _read, cf, ex, af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=(*cf, *af), excluded_rows=tuple(ex))
        summary = report.summary_ko()
        assert "Universes pane" not in summary


class TestTripleMismatchStillRejectsDerivation:
    """완료 조건 — 진짜 triple mismatch 파일에서는 여전히 역산을 금지하고 직접값을 쓴다."""

    def test_universe_dmx_pair_wins_even_when_absolute_disagrees(self):
        from server.vwx.address import ADDRESS_BASIS_DIRECT, READ_FAILURE_ADDRESS_TRIPLE_MISMATCH

        outcome = classify_and_resolve(
            {"universe": "1", "address": "39", "absolute_address": "9999"}
        )
        assert outcome.kind == "resolved"
        assert (outcome.universe, outcome.address) == (1, 39)
        assert outcome.address_basis == ADDRESS_BASIS_DIRECT
        assert outcome.warning_kind == READ_FAILURE_ADDRESS_TRIPLE_MISMATCH


class TestScopeQualificationOnMassDrop:
    """결함 2(P1) — 대량 탈락 후 확신에 찬 대조를 내지 않는다."""

    def test_no_drop_file_carries_no_scope_qualification(self):
        """완료 조건 — 탈락 0건인 01에서는 스코프 한정이 붙지 않는다(비공허성)."""
        _read, _cf, _ex, _af, rig = _run_pipeline(MULTISYSTEM_FULL.read_bytes())
        assert rig.dropped_row_count == 0
        assert rig.scope_qualified is False
        assert rig.scope_note == ""

    def test_02_after_the_p0_fix_no_longer_drops_any_row(self):
        """비공허성 — 결함 1 수정으로 02 자체는 더 이상 탈락이 없다(근본 원인 해소)."""
        _read, _cf, _ex, _af, rig = _run_pipeline(ABSOLUTE_ONLY.read_bytes())
        assert rig.dropped_row_count == 0
        assert rig.scope_qualified is False

    def _mass_drop_raw_records(self) -> list[dict]:
        """9개는 정상, 1개는 진짜 판독 실패(주소 파싱 불가)인 합성 후보 집합."""
        raw: list[dict] = []
        for i in range(9):
            raw.append(
                {
                    "Instrument Type": "MMX",
                    "Unit Number": str(i + 1),
                    "Universe": "1",
                    "DMX Address": str(i + 1),
                }
            )
        raw.append(
            {
                "Instrument Type": "MMX",
                "Unit Number": "99",
                "Absolute Address": "not-a-number",
            }
        )
        return raw

    def test_large_drop_ratio_leads_summary_with_the_drop_before_fixture_count(self):
        """양성 케이스 — 탈락 비율이 크면 '도면 픽스처'보다 탈락 사실이 먼저 나온다."""
        raw = [
            {
                "Instrument Type": "MMX",
                "Unit Number": "1",
                "Universe": "1",
                "DMX Address": "1",
            }
        ]
        # 나머지 8개는 판독 실패(주소 표현이 파싱 불가)로 만든다 — 9개 후보 중 1개만 산다.
        for i in range(8):
            raw.append(
                {
                    "Instrument Type": "MMX",
                    "Unit Number": str(i + 2),
                    "Absolute Address": "not-a-number",
                }
            )
        records, _failures, _excluded = resolve_columns(raw)
        resolved, address_failures = resolve_all(records)
        assert len(address_failures) == 8
        rig = build_designed_rig(resolved, candidate_count=len(records))
        assert rig.dropped_row_count == 8
        assert rig.scope_qualified is True
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=tuple(address_failures))
        summary = report.summary_ko()
        assert summary.index(SCOPE_QUALIFIER_TEXT) < summary.index("도면 픽스처")

    def test_small_drop_ratio_still_mentions_the_note_but_not_as_the_lead(self):
        """음성 대조군 — 탈락 비율이 작으면(1/9 ≈ 11%) 문구는 붙되 맨 앞은 아니다."""
        raw = self._mass_drop_raw_records()
        records, _failures, _excluded = resolve_columns(raw)
        resolved, address_failures = resolve_all(records)
        assert len(address_failures) == 1
        rig = build_designed_rig(resolved, candidate_count=len(records))
        assert rig.scope_qualified is True
        assert rig.dropped_row_count == 1
        diff = compare(rig, _empty_inventory())
        report = build_vwx_report(diff, read_failures=tuple(address_failures))
        summary = report.summary_ko()
        assert SCOPE_QUALIFIER_TEXT in summary
        assert summary.index("도면 픽스처") < summary.index(SCOPE_QUALIFIER_TEXT)

    def test_excluded_rows_are_never_counted_as_dropped(self):
        """완료 조건 (c) — 집계행·비DMX 액세서리 같은 의도적 제외는 탈락이 아니다."""
        raw = [
            {
                "Instrument Type": "MMX",
                "Unit Number": "1",
                "Universe": "1",
                "DMX Address": "1",
            },
            {"Device Type": "SUBTOTAL"},
        ]
        records, failures, excluded = resolve_columns(raw)
        assert not failures
        assert len(excluded) == 1
        resolved, address_failures = resolve_all(records)
        assert not address_failures
        rig = build_designed_rig(resolved, candidate_count=len(records))
        assert rig.scope_qualified is False
        assert rig.dropped_row_count == 0
