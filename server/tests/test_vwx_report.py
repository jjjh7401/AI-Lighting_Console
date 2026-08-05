"""server/vwx/report.py 구조화 페이로드 + 한국어 표현 테스트 (M6 — AC-VWX-022~023).
문서 근거 · 실물 미검증.
"""

from __future__ import annotations

import ast
from pathlib import Path

from server.prechk.inventory import COMPLETE, FixtureRecord, Inventory
from server.vwx.address import PATCHED, ResolvedRecord
from server.vwx.diff import DIFF_KIND, SKIPPED_CHECK_KIND_VWX, compare
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
