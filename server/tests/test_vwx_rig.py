"""server/vwx/rig.py 설계상 리그 모델 테스트 (M4 — AC-VWX-013~017). 문서 근거 · 실물 미검증."""

from __future__ import annotations

from server.vwx.address import PATCHED, UNPATCHED_DESIGNED, ResolvedRecord
from server.vwx.rig import (
    STATIC_ACCESSORY,
    VW_IDENTICAL_PATCH,
    VW_PATCH_CONFLICT,
    VW_PATCH_OVERLAP,
    build_designed_rig,
    fuzzy_type_equal,
)


def rr(
    row_index: int,
    *,
    unit_number: str | None = None,
    instrument_type: str = "MMX",
    mode: str | None = None,
    channel: str | None = None,
    universe: int | None = 1,
    address: int | None = 1,
    classification: str = PATCHED,
    part_index: str | None = None,
    device_type: str | None = None,
    fixture_name: str | None = None,
    gdtf_fixture: str | None = None,
    footprint: str | None = None,
    extra: dict | None = None,
) -> ResolvedRecord:
    fields: dict[str, str] = {"instrument_type": instrument_type}
    if unit_number is not None:
        fields["unit_number"] = unit_number
    if mode is not None:
        fields["mode"] = mode
    if channel is not None:
        fields["channel"] = channel
    if part_index is not None:
        fields["part_index"] = part_index
    if device_type is not None:
        fields["device_type"] = device_type
    if fixture_name is not None:
        fields["fixture_name"] = fixture_name
    if gdtf_fixture is not None:
        fields["gdtf_fixture"] = gdtf_fixture
    if footprint is not None:
        fields["footprint"] = footprint
    return ResolvedRecord(
        fields=fields,
        extra=extra or {},
        row_index=row_index,
        universe=universe,
        address=address,
        classification=classification,
    )


class TestPartIndexMultiCellFolding:
    """AC-VWX-013 — 설계상 리그 모델 + 멀티셀 폴딩."""

    def test_three_part_index_rows_fold_into_one_logical_fixture(self):
        records = [
            rr(0, unit_number="1", part_index="1", instrument_type="MMX Head"),
            rr(1, unit_number="1", part_index="2", instrument_type="MMX Head"),
            rr(2, unit_number="1", part_index="3", instrument_type="MMX Head"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 1
        assert not rig.join_key_conflicts
        assert rig.fixtures[0].part_indices == ("1", "2", "3")

    def test_representative_fields_come_from_the_minimum_part_index_row(self):
        """대표 규칙은 Part Index 최솟값 행이다 — 임의 값이 아니다(닫힌 결정)."""
        records = [
            rr(0, unit_number="1", part_index="2", instrument_type="from-part-2"),
            rr(1, unit_number="1", part_index="1", instrument_type="from-part-1"),
            rr(2, unit_number="1", part_index="3", instrument_type="from-part-3"),
        ]
        rig = build_designed_rig(records)
        assert rig.fixtures[0].instrument_type == "from-part-1"

    def test_a_fixture_with_no_part_index_is_reflected_one_to_one(self):
        """비공허성 — Part Index 없는 일반 픽스처는 접힘 없이 1:1이다."""
        records = [
            rr(0, unit_number="1", instrument_type="A"),
            rr(1, unit_number="2", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2
        assert {f.instrument_type for f in rig.fixtures} == {"A", "B"}


class TestAccessoryFiltering:
    """AC-VWX-014 — 액세서리 필터링."""

    def test_static_accessory_is_excluded_from_the_designed_rig(self):
        records = [
            rr(0, unit_number="1", device_type=STATIC_ACCESSORY),
            rr(1, unit_number="2", device_type="Light Fixture"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 1
        assert rig.fixtures[0].unit_number == "2"

    def test_dmx_consuming_accessory_is_included(self):
        records = [rr(0, unit_number="1", device_type="Accessory")]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 1

    def test_without_a_device_type_column_at_all_no_filtering_happens(self):
        """비공허성 — Device Type 컬럼이 아예 없으면 임의 배제하지 않는다."""
        records = [rr(0, unit_number="1"), rr(1, unit_number="2")]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2
        assert rig.device_type_column_present is False


class TestFuzzyTypeMatching:
    """AC-VWX-015 — 타입·모드 퍼지 매칭(동등 비교 금지)."""

    def test_a_vw_name_and_a_console_name_that_partially_overlap_match(self):
        assert fuzzy_type_equal("Robe Robin MMX Spot", "Robin MMX Spot") is True

    def test_unrelated_strings_are_unresolved_not_forced_equal(self):
        assert fuzzy_type_equal("Robe Robin MMX Spot", "Martin MAC Aura") is False

    def test_blank_values_never_match_each_other(self):
        assert fuzzy_type_equal("", "") is False
        assert fuzzy_type_equal(None, "Robin MMX Spot") is False


class TestJoinKeyConflictRejection:
    """AC-VWX-016 — 파일 내부 조인키 충돌 거부."""

    def test_duplicate_unit_number_without_part_index_is_never_silently_merged(self):
        records = [
            rr(0, unit_number="5", instrument_type="A"),
            rr(1, unit_number="5", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert rig.fixtures == ()
        assert len(rig.join_key_conflicts) == 1
        assert rig.join_key_conflicts[0].rows == (0, 1)

    def test_blank_unit_number_falls_back_to_channel_then_conflicts_too(self):
        records = [
            rr(0, unit_number=None, channel="CH1", instrument_type="A"),
            rr(1, unit_number=None, channel="CH1", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert rig.fixtures == ()
        assert len(rig.join_key_conflicts) == 1

    def test_both_keys_blank_is_reported_as_unjoinable(self):
        records = [rr(0, unit_number=None, channel=None)]
        rig = build_designed_rig(records)
        assert len(rig.join_key_conflicts) == 1
        assert rig.join_key_conflicts[0].rows == (0,)


class TestVectorworksNativeConflictPassthrough:
    """AC-VWX-017 — VW 자체 충돌 분류 통과(예외 없음)."""

    def test_identical_patch_same_universe_address_and_channel(self):
        records = [
            rr(0, unit_number="1", universe=1, address=1, channel="1"),
            rr(1, unit_number="2", universe=1, address=1, channel="1"),
        ]
        rig = build_designed_rig(records)  # must not raise
        kinds = {c.kind for c in rig.vw_patch_conflicts}
        assert VW_IDENTICAL_PATCH in kinds

    def test_patch_conflict_same_universe_address_different_channel(self):
        records = [
            rr(0, unit_number="1", universe=1, address=1, channel="1"),
            rr(1, unit_number="2", universe=1, address=1, channel="2"),
        ]
        rig = build_designed_rig(records)
        kinds = {c.kind for c in rig.vw_patch_conflicts}
        assert VW_PATCH_CONFLICT in kinds

    def test_patch_overlap_when_channel_is_unresolved(self):
        records = [
            rr(0, unit_number="1", universe=1, address=1),
            rr(1, unit_number="2", universe=1, address=1),
        ]
        rig = build_designed_rig(records)
        kinds = {c.kind for c in rig.vw_patch_conflicts}
        assert VW_PATCH_OVERLAP in kinds

    def test_a_clean_file_reports_an_empty_list_not_an_omission(self):
        """비공허성 — 충돌 0건인 정상 파일에서 필드가 빈 목록으로 존재한다."""
        records = [
            rr(0, unit_number="1", universe=1, address=1),
            rr(1, unit_number="2", universe=1, address=2),
        ]
        rig = build_designed_rig(records)
        assert rig.vw_patch_conflicts == ()

    def test_unpatched_designed_fixtures_never_enter_vw_conflict_detection(self):
        records = [
            rr(0, unit_number="1", classification=UNPATCHED_DESIGNED, universe=None, address=0),
            rr(1, unit_number="2", classification=UNPATCHED_DESIGNED, universe=None, address=0),
        ]
        rig = build_designed_rig(records)
        assert rig.vw_patch_conflicts == ()


class TestFixtureNameAndGdtfFixtureFields:
    """M0 실물 샘플 반영 — fixture_name·gdtf_fixture가 extra가 아닌 정규 필드로 해석된다."""

    def test_fixture_name_and_gdtf_fixture_are_carried_onto_the_designed_fixture(self):
        records = [
            rr(
                0,
                unit_number="1",
                instrument_type="Martin MAC Encore Performance CLD",
                fixture_name="Encore 1",
                gdtf_fixture="Martin Professional@MAC Encore Performance CLD",
            )
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 1
        fixture = rig.fixtures[0]
        assert fixture.fixture_name == "Encore 1"
        assert fixture.gdtf_fixture == "Martin Professional@MAC Encore Performance CLD"

    def test_match_type_prefers_gdtf_fixture_over_instrument_type(self):
        records = [
            rr(
                0,
                unit_number="1",
                instrument_type="Martin MAC Encore Performance CLD",
                gdtf_fixture="Martin Professional@MAC Encore Performance CLD",
            )
        ]
        rig = build_designed_rig(records)
        assert rig.fixtures[0].match_type == "Martin Professional@MAC Encore Performance CLD"

    def test_match_type_falls_back_to_instrument_type_when_gdtf_fixture_absent(self):
        """비공허성 대조군 — gdtf_fixture가 없는 정상 경로가 그대로 동작한다."""
        records = [rr(0, unit_number="1", instrument_type="Robin MMX Spot")]
        rig = build_designed_rig(records)
        assert rig.fixtures[0].gdtf_fixture is None
        assert rig.fixtures[0].match_type == "Robin MMX Spot"


class TestDesignSideOverlapDetection:
    """M0 실물 샘플이 준 DMX Footprint 폭 출처로 설계 측 구간 겹침을 직접 판정한다."""

    def test_stride_equal_to_footprint_reports_zero_overlaps(self):
        """음성 대조군 — M0 실물 샘플과 동일한 형태(stride==footprint, 완벽 패킹)."""
        records = [
            rr(0, unit_number="1", universe=1, address=1, footprint="38"),
            rr(1, unit_number="2", universe=1, address=39, footprint="38"),
            rr(2, unit_number="3", universe=1, address=77, footprint="38"),
        ]
        rig = build_designed_rig(records)
        assert rig.footprint_data_present is True
        assert rig.design_overlaps == ()

    def test_stride_smaller_than_footprint_is_caught_as_an_overlap(self):
        """양성 케이스(합성) — stride(20) < footprint(38)면 실제로 겹친다.

        비공허성 핵심 — 이 assert가 없으면 겹침 판정 기능이 항상 빈 목록만
        내도 테스트가 통과해버린다.
        """
        records = [
            rr(0, unit_number="1", universe=1, address=1, footprint="38"),
            rr(1, unit_number="2", universe=1, address=21, footprint="38"),  # 1~38 vs 21~58 겹침
        ]
        rig = build_designed_rig(records)
        assert len(rig.design_overlaps) == 1
        entry = rig.design_overlaps[0]
        assert entry.universe == 1
        assert "1" in entry.members and "2" in entry.members

    def test_different_universes_never_report_a_false_overlap(self):
        records = [
            rr(0, unit_number="1", universe=1, address=1, footprint="38"),
            rr(1, unit_number="2", universe=2, address=1, footprint="38"),
        ]
        rig = build_designed_rig(records)
        assert rig.design_overlaps == ()

    def test_no_footprint_column_leaves_footprint_data_present_false(self):
        """footprint 컬럼이 아예 없는 파일 — 기존(footprint_overlap_descope) 경로 보존."""
        records = [rr(0, unit_number="1", universe=1, address=1)]
        rig = build_designed_rig(records)
        assert rig.footprint_data_present is False
        assert rig.design_overlaps == ()
