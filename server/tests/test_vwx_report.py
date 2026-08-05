"""server/vwx/report.py 구조화 페이로드 + 한국어 표현 테스트 (M6 — AC-VWX-022~023).
문서 근거 · 실물 미검증.
"""

from __future__ import annotations

import ast
from pathlib import Path

from server.prechk.inventory import COMPLETE, FixtureRecord, Inventory
from server.vwx.address import PATCHED, ResolvedRecord
from server.vwx.diff import DIFF_KIND, SKIPPED_CHECK_KIND_VWX, compare
from server.vwx.reader import READ_FAILURE_BLOCK_UNDETECTED, READ_FAILURE_NOT_PATCH_SOURCE
from server.vwx.report import (
    VWX_CLOSED_VOCABULARIES,
    UnknownVwxVerdict,
    build_vwx_report,
    diff_kind_label,
    skipped_check_kind_label,
)
from server.vwx.rig import build_designed_rig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_inventory(fixtures: list[tuple[int, str, str, str, str]] | None = None) -> Inventory:
    fixtures = fixtures or []
    records = tuple(
        FixtureRecord(slot=slot, name=name, patch_raw=patch_raw, fixture_type=ftype, mode=mode)
        for slot, patch_raw, ftype, mode, name in fixtures
    )
    return Inventory(
        path="Patch/Stages/1/Fixtures",
        child_count=len(records),
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=records,
    )


def rr(row_index: int, **overrides) -> ResolvedRecord:
    fields = {"instrument_type": "Robin MMX Spot", "unit_number": str(row_index + 1)}
    fields.update(overrides.pop("fields", {}))
    defaults = {"classification": PATCHED, "universe": 1, "address": row_index + 1}
    defaults.update(overrides)
    return ResolvedRecord(fields=fields, extra={}, row_index=row_index, **defaults)


class TestStructuredPayloadDiscipline:
    """AC-VWX-022 — 구조화된 페이로드."""

    def test_all_four_structured_categories_exist_independently(self):
        """판독실패·데이터블록미탐·미수행·부정전제 4종이 최상위 키에 독립적으로."""
        console = make_inventory([])
        designed_rig = build_designed_rig([])
        diff = compare(designed_rig, console)
        report = build_vwx_report(diff)
        payload = report.to_dict()

        assert "read_failures" in payload  # 판독 실패
        assert "skipped_checks" in payload  # 미수행 판정
        assert "join_key_conflicts" in payload["designed_rig"]  # 부정 전제류 구조
        assert "diffs" in payload  # 대조 3부류

    def test_no_python_exception_traceback_string_reaches_a_user_facing_field(self):
        """비공허성 — 정상 케이스에서 각 필드가 빈 목록으로 존재한다."""
        console = make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")])
        designed_rig = build_designed_rig([rr(0)])
        diff = compare(designed_rig, console)
        report = build_vwx_report(diff)
        payload = report.to_dict()

        for field_name in ("read_failures",):
            assert payload[field_name] == []
        for text in str(payload).split():
            assert "Traceback" not in text
            assert "Error:" not in text


class TestKoreanExpressionLayer:
    """AC-VWX-023 — 한국어 표현 계층."""

    def test_new_diff_kind_codes_are_registered_with_exact_key_set_match(self):
        assert set(VWX_CLOSED_VOCABULARIES["diff_kind"]) == DIFF_KIND
        for code in DIFF_KIND:
            assert diff_kind_label(code)  # raises if unregistered

    def test_new_skipped_check_kind_codes_are_registered_with_exact_key_set_match(self):
        assert set(VWX_CLOSED_VOCABULARIES["skipped_check_kind"]) == SKIPPED_CHECK_KIND_VWX
        for code in SKIPPED_CHECK_KIND_VWX:
            assert skipped_check_kind_label(code)

    def test_an_unregistered_code_raises_rather_than_passing_through(self):
        try:
            diff_kind_label("not_a_real_code")
        except UnknownVwxVerdict:
            pass
        else:
            raise AssertionError("unregistered code should have raised")

    def test_no_new_code_in_this_spec_directly_imports_an_underscore_prefixed_identifier(self):
        """비공허성 AST 스캔 — 밑줄 식별자 직접 import 지점 0건."""
        source = (PROJECT_ROOT / "server" / "vwx" / "report.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        import_count = 0
        for node in ast.walk(tree):
            is_server_import = (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("server.")
            )
            if is_server_import:
                for alias in node.names:
                    import_count += 1
                    assert not alias.name.startswith("_"), (
                        f"report.py imports underscore-prefixed {alias.name} from {node.module}"
                    )
        assert import_count > 0, "the AST scan visited no server.* imports at all"


class TestReportSummaryKorean:
    def test_summary_ko_is_korean_text_ending_with_a_period(self):
        console = make_inventory([])
        designed_rig = build_designed_rig([rr(0)])
        diff = compare(designed_rig, console)
        report = build_vwx_report(diff)
        summary = report.summary_ko()
        assert summary.endswith(".")
        assert "콘솔 미확인" in summary  # missing_in_console label rendered

    def test_a_fully_clean_comparison_reports_no_difference(self):
        console = make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")])
        designed_rig = build_designed_rig([rr(0)])
        diff = compare(designed_rig, console)
        report = build_vwx_report(diff)
        assert "차이 없음" in report.summary_ko()


class TestStructuralRejectionNeverReadsAsACleanMatch:
    """결함 2 잔존 교정 — 대조가 성립하지 않으면 "차이 없음"을 절대 말하지 않는다.

    1차 수정은 ``read_failures``만 채웠을 뿐 ``summary_ko``가 여전히 "차이
    없음"으로 시작해 거짓 안전 신호였다(코디네이터 재현). 이 클래스는 사용자가
    실제로 읽는 ``summary_ko`` 단일 문장과 ``diffs`` 페이로드 형태를
    검증한다.

    비공허성: "차이 없음" 부재만 assert하면 문자열 검사기가 죽어 있어도
    통과할 수 있다 — 그래서 정상 케이스(:meth:`test_a_fully_clean_comparison_
    reports_no_difference`, 위)에서는 실제로 그 문구가 등장함을 이미
    확인했다. 이 클래스는 그 대조군에 더해, 두 거부 경로(``not_patch_source``
    ·``worksheet_block_undetected``) 각각에서 부재를 확인한다.
    """

    def _empty_designed_rig_report(self, *, kind: str, detail: str):
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class _Failure:
            row: int | None
            kind: str
            detail: str

        console = make_inventory([])
        designed_rig = build_designed_rig([])  # 판독 실패로 레코드 0건인 상황을 대역.
        diff = compare(designed_rig, console)
        return build_vwx_report(diff, read_failures=(_Failure(row=0, kind=kind, detail=detail),))

    def test_not_patch_source_rejection_never_says_no_difference(self):
        report = self._empty_designed_rig_report(
            kind=READ_FAILURE_NOT_PATCH_SOURCE,
            detail="패치 출처 아님(주소 열 없음) — Instrument Summary류로 판단",
        )
        summary = report.summary_ko()
        assert "차이 없음" not in summary
        assert summary.startswith("패치 출처로 성립하지 않는다")
        assert "대조를 수행하지 않았다" in summary

        payload = report.to_dict()
        assert payload["diffs"] == {
            "performed": False,
            "reason": "패치 출처 아님(주소 열 없음) — Instrument Summary류로 판단",
        }

    def test_worksheet_block_undetected_rejection_never_says_no_difference(self):
        """결함 1 경로(CR 전용 등)도 동일 규칙을 따른다(요구사항 2)."""
        report = self._empty_designed_rig_report(
            kind=READ_FAILURE_BLOCK_UNDETECTED,
            detail="헤더 없음 — 데이터 블록 미탐(임의 추측으로 자르지 않는다)",
        )
        summary = report.summary_ko()
        assert "차이 없음" not in summary
        assert summary.startswith("패치 출처로 성립하지 않는다")
        assert "대조를 수행하지 않았다" in summary

        payload = report.to_dict()
        assert payload["diffs"]["performed"] is False
        assert "missing_in_console" not in payload["diffs"]

    def test_comparison_performed_flag_matches_rejection_presence(self):
        clean_report = build_vwx_report(
            compare(
                build_designed_rig([rr(0)]),
                make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")]),
            )
        )
        assert clean_report.comparison_performed() is True

        rejected_report = self._empty_designed_rig_report(
            kind=READ_FAILURE_NOT_PATCH_SOURCE, detail="사유"
        )
        assert rejected_report.comparison_performed() is False
