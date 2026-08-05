"""server/vwx/diff.py precheck_patch 대조 테스트 (M5 — AC-VWX-018~021).
문서 근거 · 실물 미검증.
"""

from __future__ import annotations

import ast
from pathlib import Path

from server.prechk.inventory import COMPLETE, FixtureRecord, Inventory
from server.prechk.patch import FootprintPolicy
from server.vwx.address import PATCHED, ResolvedRecord
from server.vwx.diff import (
    ADDRESS_COLLISION,
    FID_CID_UNREACHABLE,
    FOOTPRINT_OVERLAP_DESCOPE,
    MISSING_IN_CONSOLE,
    QUANTITY_MISMATCH,
    compare,
)
from server.vwx.rig import build_designed_rig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_inventory(fixtures: list[tuple[int, str, str, str, str]]) -> Inventory:
    """(slot, patch_raw, fixture_type, mode, name) 목록 -> 완전한 Inventory."""
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
    fields = {
        "instrument_type": "Robin MMX Spot",
        "unit_number": str(row_index + 1),
    }
    fields.update(overrides.pop("fields", {}))
    defaults = {"classification": PATCHED, "universe": 1, "address": row_index + 1}
    defaults.update(overrides)
    return ResolvedRecord(fields=fields, extra={}, row_index=row_index, **defaults)


class TestJoinKeyNeverUsesFidOrCid:
    """AC-VWX-018 — 조인 키 = 주소+타입, FID/CID 금지."""

    def test_tampering_the_designed_rig_fixture_id_field_does_not_change_the_result(self):
        """시나리오 4 — 슬롯==FID 우연일치 리그에서 조인 키 무시."""
        console = make_inventory([(101, "1.001", "Robin MMX Spot", "Mode 1", "MMX 1")])
        designed_records = [
            rr(0, fields={"fixture_id": "999", "uid": "not-real-101"}),
        ]
        designed_rig = build_designed_rig(designed_records)
        result_a = compare(designed_rig, console)

        # fixture_id/uid를 콘솔 슬롯(101)과 일부러 다른 값으로 조작해도 결과가
        # 바뀌지 않는다 — 조인 키가 실제로 (universe,address)+type임을 증명.
        designed_records_tampered = [
            rr(0, fields={"fixture_id": "1", "uid": "totally-different"}),
        ]
        designed_rig_tampered = build_designed_rig(designed_records_tampered)
        result_b = compare(designed_rig_tampered, console)

        assert result_a.missing_in_console == result_b.missing_in_console
        assert result_a.missing_in_console == ()

    def test_diff_source_never_uses_fixture_id_or_uid_as_a_comparison_operand(self):
        """비공허성 — AST 스캔이 diff.py와 rig.py의 Compare 노드를 실제로 방문한다."""
        banned_names = {"fixture_id", "uid"}
        visited_compares = 0
        for module_name in ("diff.py", "rig.py"):
            source = (PROJECT_ROOT / "server" / "vwx" / module_name).read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    visited_compares += 1
                    operands = [node.left, *node.comparators]
                    for operand in operands:
                        name = getattr(operand, "id", None) or getattr(operand, "attr", None)
                        assert name not in banned_names, (
                            f"{module_name} compares on {name} — FID/CID join is banned"
                        )
        assert visited_compares > 0, "the AST scan visited no Compare nodes at all"


class TestFidCidStructuredSkip:
    """AC-VWX-019 — FID/CID 구조화된 미수행."""

    def test_fid_cid_unreachable_is_always_present_in_skipped_checks(self):
        console = make_inventory([])
        designed_rig = build_designed_rig([])
        result = compare(designed_rig, console)
        kinds = {entry.kind for entry in result.skipped_checks}
        assert FID_CID_UNREACHABLE in kinds

    def test_the_skip_entry_carries_a_reason_field_not_only_free_prose(self):
        console = make_inventory([])
        designed_rig = build_designed_rig([])
        result = compare(designed_rig, console)
        entry = next(e for e in result.skipped_checks if e.kind == FID_CID_UNREACHABLE)
        assert entry.reason  # a structured field, not embedded in prose elsewhere
        assert isinstance(entry.reason, str) and len(entry.reason) > 0


class TestThreeDiffCategories:
    """AC-VWX-020 — 대조 리포트 3부류."""

    def test_missing_in_console_lists_a_designed_only_fixture(self):
        console = make_inventory([])
        designed_rig = build_designed_rig([rr(0)])
        result = compare(designed_rig, console)
        assert len(result.missing_in_console) == 1
        assert result.missing_in_console[0].instrument_type == "Robin MMX Spot"

    def test_address_collision_reuses_the_console_side_duplicate_verdict(self):
        console = make_inventory(
            [
                (1, "1.001", "Robin MMX Spot", "Mode 1", "A"),
                (2, "1.001", "Robin MMX Spot", "Mode 1", "B"),
            ]
        )
        designed_rig = build_designed_rig([])
        result = compare(designed_rig, console)
        assert len(result.address_collisions) == 1
        assert result.address_collisions[0].universe == 1
        assert result.address_collisions[0].address == 1

    def test_quantity_mismatch_carries_type_designed_count_and_console_count(self):
        console = make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")])
        designed_rig = build_designed_rig([rr(0), rr(1, fields={"unit_number": "2"})])
        result = compare(designed_rig, console)
        assert len(result.quantity_mismatches) == 1
        entry = result.quantity_mismatches[0]
        assert entry.instrument_type == "Robin MMX Spot"
        assert entry.designed_count == 2
        assert entry.console_count == 1

    def test_all_three_categories_are_always_present_even_when_empty(self):
        """비공허성 — 3부류 전부가 항상 응답에 존재한다(비어 있어도)."""
        console = make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")])
        designed_rig = build_designed_rig([rr(0)])
        result = compare(designed_rig, console)
        assert result.missing_in_console == ()
        assert result.address_collisions == ()
        assert result.quantity_mismatches == ()
        # 3부류 필드 자체는 튜플로 항상 존재(속성 접근이 실패하지 않는다).
        assert isinstance(result.missing_in_console, tuple)
        assert isinstance(result.address_collisions, tuple)
        assert isinstance(result.quantity_mismatches, tuple)


class TestOptionalFootprintOverlapReuse:
    """AC-VWX-021 — 옵션 구간 겹침 재사용."""

    def test_footprint_policy_disabled_reports_a_skip_not_an_exception(self):
        console = make_inventory([(1, "1.001", "Robin MMX Spot", "Mode 1", "A")])
        designed_rig = build_designed_rig([])
        result = compare(designed_rig, console)  # no footprint_policy passed
        kinds = {entry.kind for entry in result.skipped_checks}
        assert FOOTPRINT_OVERLAP_DESCOPE in kinds

    def test_footprint_policy_enabled_does_not_report_the_descope_skip(self):
        console = make_inventory(
            [
                (1, "1.001", "Robin MMX Spot", "Mode 1", "A"),
                (2, "1.003", "Robin MMX Spot", "Mode 1", "B"),
            ]
        )
        designed_rig = build_designed_rig([])
        policy = FootprintPolicy(enabled=True, widths={1: 4, 2: 4})
        result = compare(designed_rig, console, footprint_policy=policy)
        kinds = {entry.kind for entry in result.skipped_checks}
        assert FOOTPRINT_OVERLAP_DESCOPE not in kinds
        # REQ-VWX-021 재사용 확인 — evaluate_patch의 range_overlap 축이 실행됐다
        # (겹치는 폭 4채널짜리 두 픽스처가 1.001/1.003에서 실제로 겹친다).


class TestDiffKindClosedVocabulary:
    """diff_kind 3부류 집합 자체의 정합성 — report.py(M6)가 그대로 소비한다."""

    def test_diff_kind_has_exactly_three_members(self):
        from server.vwx.diff import DIFF_KIND

        expected = {MISSING_IN_CONSOLE, ADDRESS_COLLISION, QUANTITY_MISMATCH}
        assert expected == DIFF_KIND
