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
        records_a, failures_a, _excluded_a = resolve_columns(forward)
        records_b, failures_b, _excluded_b = resolve_columns(reversed_order)
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
        records, failures, _excluded = resolve_columns(raw)
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
        records, _failures, _excluded = resolve_columns(raw)
        assert records[0].extra  # non-empty
        assert set(records[0].extra) == {"Weight", "Wattage"}


class TestMinimumValidRecord:
    """AC-VWX-008 — 최소 유효 레코드 판정."""

    def test_missing_instrument_type_is_a_structured_failure_not_an_exception(self):
        raw = [{"Universe": "1", "DMX Address": "1"}]
        records, failures, _excluded = resolve_columns(raw)  # must not raise
        assert records == []
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_MIN_RECORD

    def test_missing_address_family_is_also_a_structured_failure(self):
        raw = [{"Instrument Type": "MMX", "Symbol Name": "MMX_SYM"}]
        records, failures, _excluded = resolve_columns(raw)
        assert records == []
        assert len(failures) == 1
        assert failures[0].kind == READ_FAILURE_MIN_RECORD

    def test_a_normal_record_is_never_misclassified_as_a_failure(self):
        """비공허성 — 정상 레코드가 판독 실패로 오분류되지 않는다."""
        raw = [{"Instrument Type": "MMX", "Universe": "1", "DMX Address": "1"}]
        records, failures, _excluded = resolve_columns(raw)
        assert not failures
        assert len(records) == 1


class TestFixtureNameAndGdtfFixtureAliases:
    """M0 실물 샘플(2026-08-05) 반영 — ASSUMPTION-68 NEGATIVE로 별칭표 확장."""

    def test_fixture_name_header_resolves_to_the_new_canonical_field(self):
        assert resolve_header("Fixture Name") == "fixture_name"
        assert resolve_header("FixtureName") == "fixture_name"

    def test_gdtf_fixture_header_resolves_to_the_new_canonical_field(self):
        assert resolve_header("GDTF Fixture") == "gdtf_fixture"
        assert resolve_header("GDTFFixture") == "gdtf_fixture"

    def test_fixture_name_never_collides_with_symbol_name(self):
        """요구사항 명시 — 이 둘은 다른 필드다, 합치지 않는다."""
        assert resolve_header("Fixture Name") != resolve_header("Symbol Name")
        assert resolve_header("Symbol Name") == "symbol_name"

    def test_gdtf_fixture_never_collides_with_gdtf_fixture_mode(self):
        """정규화 키가 다름을 테스트로 못박는다 — gdtffixture vs gdtffixturemode."""
        assert resolve_header("GDTF Fixture") == "gdtf_fixture"
        assert resolve_header("GDTF Fixture Mode") == "mode"
        assert resolve_header("GDTF Fixture") != resolve_header("GDTF Fixture Mode")

    def test_real_sample_row_resolves_both_new_fields_out_of_extra(self):
        """비공허성 종단 — 실물 헤더 전체를 넣으면 두 필드 다 extra가 아니라 정규 필드로 간다."""
        raw = [
            {
                "Instrument Type": "Martin MAC Encore Performance CLD",
                "Fixture Name": "Encore 1",
                "GDTF Fixture": "Martin Professional@MAC Encore Performance CLD",
                "Universe": "1",
                "DMX Address": "1",
                "Gobo": "",  # 범위 밖 필드 — extra로 남아야 한다.
            }
        ]
        records, failures, _excluded = resolve_columns(raw)
        assert not failures
        assert len(records) == 1
        assert records[0].fields["fixture_name"] == "Encore 1"
        assert records[0].fields["gdtf_fixture"] == "Martin Professional@MAC Encore Performance CLD"
        assert "fixture_name" not in records[0].extra
        assert "gdtf_fixture" not in records[0].extra
        assert "Gobo" in records[0].extra  # 범위 밖 필드는 여전히 extra 보존.
