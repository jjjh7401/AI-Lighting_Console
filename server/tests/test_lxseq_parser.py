"""Tests for server.lxseq.parser — SPEC-COPILOT-LXSEQ-001 M1.

AC-LXSEQ-002: real CSV 86-row read, name-based columns (not positional).
AC-LXSEQ-003: 7-category row rejection, no raw exceptions escape.
AC-LXSEQ-004: FID never used as an address.
"""

from __future__ import annotations

import ast
import csv
import io
from pathlib import Path

import pytest

from server.lxseq.parser import (
    MissingColumnsError,
    parse_patch_csv,
)

FIXTURE_PATH = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")


def _load_fixture_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _rows_from_text(text: str) -> list[dict]:
    if text.startswith("﻿"):
        text = text[1:]
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# AC-LXSEQ-002 — real_csv / header
# ---------------------------------------------------------------------------


def test_real_csv_86_records_zero_rejected_zero_excluded():
    result = parse_patch_csv(_load_fixture_text())
    assert len(result.records) == 86
    assert result.rejected == ()
    assert result.excluded == ()

    first = result.records[0]
    assert first.fid == 101
    assert first.universe == 1
    assert first.address == 1
    assert first.channels == 12
    assert first.group == "KEY"

    last = result.records[-1]
    assert last.fid == 430
    assert last.universe == 5
    assert last.address == 322


def test_header_bom_absorbed_same_records():
    text = _load_fixture_text()
    assert text.startswith("﻿")
    without_bom = text[1:]
    with_bom_result = parse_patch_csv(text)
    without_bom_result = parse_patch_csv(without_bom)
    assert with_bom_result.records == without_bom_result.records


def test_header_column_order_scrambled_still_name_matched():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    scrambled = ["Position", *[f for f in fieldnames if f != "Position"]]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=scrambled)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    baseline = parse_patch_csv(_load_fixture_text())
    scrambled_result = parse_patch_csv(buf.getvalue())
    assert scrambled_result.records == baseline.records


def test_header_missing_required_column_is_file_level_failure():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = [f for f in rows[0] if f != "Position"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    with pytest.raises(MissingColumnsError) as exc_info:
        parse_patch_csv(buf.getvalue())
    assert "Position" in exc_info.value.missing


def test_header_extra_columns_preserved_in_extra_dict():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = [*rows[0].keys(), "Notes"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        row = dict(row)
        row["Notes"] = "spare"
        writer.writerow(row)

    result = parse_patch_csv(buf.getvalue())
    assert len(result.records) == 86
    assert result.records[0].extra.get("Notes") == "spare"


# ---------------------------------------------------------------------------
# AC-LXSEQ-003 — reject / overflow / duplicate / overlap
# ---------------------------------------------------------------------------


def _rewrite_row(rows: list[dict], fid: str, **changes: str) -> list[dict]:
    out = []
    for row in rows:
        if row["FID"] == fid:
            row = dict(row)
            row.update(changes)
        out.append(row)
    return out


def _to_csv_text(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def test_reject_universe_overflow_on_address_502_pass_on_address_500():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())

    passing_rows = _rewrite_row(rows, "101", Address="500", AddrRange="1.500–511")
    passing = parse_patch_csv(_to_csv_text(passing_rows, fieldnames))
    assert passing.rejected == ()
    assert len(passing.records) == 86

    overflow_rows = _rewrite_row(rows, "101", Address="502", AddrRange="1.502–513")
    overflow = parse_patch_csv(_to_csv_text(overflow_rows, fieldnames))
    assert len(overflow.rejected) == 1
    assert overflow.rejected[0].kind == "universe_overflow"
    assert len(overflow.records) == 85


def test_reject_addr_range_mismatch_wrong_digits():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    mismatched = _rewrite_row(rows, "102", AddrRange="1.013–023")
    result = parse_patch_csv(_to_csv_text(mismatched, fieldnames))
    assert len(result.rejected) == 1
    assert result.rejected[0].kind == "addr_range_mismatch"


@pytest.mark.parametrize("dash", ["-", "—"])
def test_addr_range_dash_variants_are_accepted(dash: str):
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    variant = _rewrite_row(rows, "102", AddrRange=f"1.013{dash}024")
    result = parse_patch_csv(_to_csv_text(variant, fieldnames))
    assert result.rejected == ()
    assert len(result.records) == 86


def test_reject_duplicate_fid_both_rows_rejected():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    rows = [dict(r) for r in rows]
    for row in rows:
        if row["FID"] == "102":
            row["FID"] = "101"
    result = parse_patch_csv(_to_csv_text(rows, fieldnames))
    dup_rejections = [r for r in result.rejected if r.kind == "duplicate_fid"]
    assert len(dup_rejections) == 2
    assert len(result.records) == 84


def test_reject_address_overlap_in_same_universe():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    overlapped = _rewrite_row(rows, "102", Address="1", AddrRange="1.001–012")
    result = parse_patch_csv(_to_csv_text(overlapped, fieldnames))
    overlap_rejections = [r for r in result.rejected if r.kind == "address_overlap_in_file"]
    assert len(overlap_rejections) == 2
    assert len(result.records) == 84


def test_zero_channels_row_is_excluded_not_rejected():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    zeroed = _rewrite_row(rows, "101", Ch="0")
    result = parse_patch_csv(_to_csv_text(zeroed, fieldnames))
    assert result.rejected == ()
    assert len(result.excluded) == 1
    assert result.excluded[0].fid_raw == "101"
    assert len(result.records) == 85


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [("Address", "0"), ("Address", "-3"), ("Universe", "0")],
)
def test_reject_address_out_of_range(field_name: str, bad_value: str):
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    bad = _rewrite_row(rows, "101", **{field_name: bad_value})
    result = parse_patch_csv(_to_csv_text(bad, fieldnames))
    out_of_range = [r for r in result.rejected if r.kind == "address_out_of_range"]
    assert len(out_of_range) == 1
    assert out_of_range[0].fid_raw == "101"
    assert len(result.records) == 85


def test_non_integer_field_rejected_without_raising():
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    bad = _rewrite_row(rows, "101", Address="not-a-number")
    result = parse_patch_csv(_to_csv_text(bad, fieldnames))
    assert len(result.rejected) == 1
    assert result.rejected[0].kind == "non_integer_field"
    assert len(result.records) == 85


# ---------------------------------------------------------------------------
# AC-LXSEQ-004 — fid_is_not_an_address
# ---------------------------------------------------------------------------


# AC-LXSEQ-004 ①은 +1000만 명시하지만, 짝수 오프셋은 `fid % 2` 같은 홀짝 의존을
# 통과시킨다(뮤테이션 3에서 실제로 통과했다). 홀수 오프셋과 FID별로 다른 오프셋을
# 함께 걸어 "FID 값이 어떻게 변하든 자리는 그대로"를 실제로 검사한다.
@pytest.mark.parametrize("offset_kind", ["even_1000", "odd_1001", "per_row_varying"])
def test_fid_is_not_an_address_addresses_stable_under_fid_offset(offset_kind: str):
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())

    if offset_kind == "even_1000":
        shifted = [dict(r, FID=str(int(r["FID"]) + 1000)) for r in rows]
    elif offset_kind == "odd_1001":
        shifted = [dict(r, FID=str(int(r["FID"]) + 1001)) for r in rows]
    else:
        shifted = [dict(r, FID=str(int(r["FID"]) + 1000 + i)) for i, r in enumerate(rows)]

    baseline = parse_patch_csv(_to_csv_text(rows, fieldnames))
    shifted_result = parse_patch_csv(_to_csv_text(shifted, fieldnames))

    baseline_addrs = {(r.universe, r.address) for r in baseline.records}
    shifted_addrs = {(r.universe, r.address) for r in shifted_result.records}
    assert baseline_addrs  # 비공허성 — 빈 집합끼리 같다고 통과하지 않게
    assert baseline_addrs == shifted_addrs


def test_fid_is_not_an_address_group_and_position_do_not_move_addresses():
    """Group·Position을 바꿔도 자리는 변하지 않는다 (REQ-LXSEQ-003)."""
    rows = _rows_from_text(_load_fixture_text())
    fieldnames = list(rows[0].keys())
    relabeled = [dict(r, Group="ZZZ", Position="어딘가") for r in rows]

    baseline = parse_patch_csv(_to_csv_text(rows, fieldnames))
    relabeled_result = parse_patch_csv(_to_csv_text(relabeled, fieldnames))

    baseline_addrs = {(r.universe, r.address) for r in baseline.records}
    relabeled_addrs = {(r.universe, r.address) for r in relabeled_result.records}
    assert baseline_addrs
    assert baseline_addrs == relabeled_addrs


def test_fid_identifier_not_used_in_address_arithmetic_ast_scan():
    parser_src = Path("server/lxseq/parser.py").read_text(encoding="utf-8")
    tree = ast.parse(parser_src)

    scanned_functions = 0
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            scanned_functions += 1
            for sub in ast.walk(node):
                if isinstance(sub, ast.BinOp):
                    for operand in (sub.left, sub.right):
                        if isinstance(operand, ast.Name) and operand.id == "fid":
                            violations.append(f"{node.name}: fid used in BinOp")
                if isinstance(sub, ast.Call):
                    func_name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                    if func_name == "normalize_address":
                        for arg in sub.args:
                            if isinstance(arg, ast.Name) and arg.id == "fid":
                                violations.append(f"{node.name}: fid passed to normalize_address")

    assert scanned_functions >= 3
    assert violations == []
