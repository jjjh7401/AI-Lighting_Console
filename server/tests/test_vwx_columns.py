"""server/vwx/columns.py 컬럼 해석 테스트 (M2 — AC-VWX-006~008). 문서 근거 · 실물 미검증."""

from __future__ import annotations

from server.vwx.columns import (
    READ_FAILURE_MIN_RECORD,
    match_count,
    resolve_columns,
    resolve_header,
)


class TestAliasTableColumnMatching:
    """AC-VWX-006 — 별칭 테이블 컬럼 매칭(비위치)."""

    def test_case_space_and_punctuation_variants_all_resolve_to_the_same_field(self):
        variants = ["DMX Address", "dmx address", "DMX  Address", "DMX-Address"]
        resolved = {resolve_header(variant) for variant in variants}
        assert resolved == {"address"}

    def test_column_order_does_not_matter(self):
        """위치 무관성 — 순서가 뒤섞여도 같은 필드가 같게 해석된다(비공허성)."""
        forward = [
            {"Instrument Type": "MMX", "Universe": "1", "DMX Address": "1"},
        ]
        reversed_order = [
            {"DMX Address": "1", "Universe": "1", "Instrument Type": "MMX"},
        ]
        records_a, failures_a = resolve_columns(forward)
        records_b, failures_b = resolve_columns(reversed_order)
        assert not failures_a and not failures_b
        assert records_a[0].fields == records_b[0].fields

    def test_match_count_counts_only_alias_hits(self):
        assert match_count(["Instrument Type", "Universe", "Random Junk"]) == 2
        assert match_count(["nonsense", "more nonsense"]) == 0


class TestExtraColumnPreservation:
    """AC-VWX-007 — 미지 컬럼 보존(extra)."""

    def test_unknown_column_survives_verbatim_in_extra(self):
        raw = [
            {
                "Instrument Type": "MMX",
                "Universe": "1",
                "DMX Address": "1",
                "Custom Field 1": "hello",
            }
        ]
        records, failures = resolve_columns(raw)
        assert not failures
        assert records[0].extra["Custom Field 1"] == "hello"

    def test_extra_is_never_discarded(self):
        """비공허성 — extra 딕셔너리가 실제로 비어 있지 않다."""
        raw = [
            {
                "Instrument Type": "MMX",
                "Universe": "1",
                "DMX Address": "1",
                "Weight": "12kg",
                "Wattage": "575W",
            }
        ]
        records, _failures = resolve_columns(raw)
        assert records[0].extra  # non-empty
        assert set(records[0].extra) == {"Weight", "Wattage"}


class TestMinimumValidRecord:
    """AC-VWX-008 — 최소 유효 레코드 판정."""

    def test_missing_instrument_type_is_a_structured_failure_not_an_exception(self):
        raw = [{"Universe": "1", "DMX Address": "1"}]
        records, failures = resolve_columns(raw)  # must not raise
        assert records == []
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_MIN_RECORD

    def test_missing_address_family_is_also_a_structured_failure(self):
        raw = [{"Instrument Type": "MMX", "Symbol Name": "MMX_SYM"}]
        records, failures = resolve_columns(raw)
        assert records == []
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_MIN_RECORD

    def test_a_normal_record_is_never_misclassified_as_a_failure(self):
        """비공허성 — 정상 레코드가 판독 실패로 오분류되지 않는다."""
        raw = [{"Instrument Type": "MMX", "Universe": "1", "DMX Address": "1"}]
        records, failures = resolve_columns(raw)
        assert not failures
        assert len(records) == 1
