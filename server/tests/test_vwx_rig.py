"""server/vwx/rig.py 설계상 리그 모델 테스트 (M4 — AC-VWX-013~017). 문서 근거 · 실물 미검증."""

from __future__ import annotations

from server.vwx.address import PATCHED, UNPATCHED_DESIGNED, ResolvedRecord
from server.vwx.rig import (
    STATIC_ACCESSORY,
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
    position: str | None = None,
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
    if position is not None:
        fields["position"] = position
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


class TestUnitNumberIsScopedToPositionNotGlobal:
    """v0.1.5 회귀 — REQ-VWX-016 조인 키 우선순위 수정(코디네이터 재현).

    ``Unit Number``는 Vectorworks에서 **포지션 안에서만 유일**하다(트러스마다
    1번부터 다시 센다) — 전역 유일로 취급하면 포지션이 2개 이상인 실사용 리그
    대부분이 전멸한다(전 행이 unit_number 충돌로 탈락 → fixture_count 0 →
    "대조 미수행" 오판정). 이 클래스는 그 결함의 정확한 재현과, 스코프가
    실제로 살아있음(같은 포지션에서는 여전히 충돌을 잡음)을 함께 증명한다.
    """

    def test_same_unit_number_in_different_positions_is_not_a_conflict(self):
        """핵심 회귀 — 코디네이터 재현 A. 수정 전에는 fixture_count 0이었다."""
        records = [
            rr(0, unit_number="1", position="Upstage Truss", instrument_type="MAC Encore"),
            rr(1, unit_number="1", position="FOH", instrument_type="Source Four"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2
        assert rig.join_key_conflicts == ()

    def test_same_unit_number_in_the_same_position_is_still_a_conflict(self):
        """대조군 — 스코프가 죽어있지 않음을 증명(이게 없으면 1번 수정이 충돌
        탐지 자체를 통째로 죽인 것을 못 잡는다)."""
        records = [
            rr(0, unit_number="1", position="FOH", instrument_type="A"),
            rr(1, unit_number="1", position="FOH", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert rig.fixtures == ()
        assert len(rig.join_key_conflicts) == 1
        detail = rig.join_key_conflicts[0].detail
        assert "포지션" in detail and "FOH" in detail  # 어느 스코프에서 중복인지 명시.

    def test_blank_position_is_its_own_scope_only_blanks_collide(self):
        """position이 공란인 레코드끼리는 여전히 하나의 스코프로 충돌하지만,
        공란 스코프와 실제 포지션 스코프는 서로 다른 스코프다(비공허성)."""
        records = [
            rr(0, unit_number="1", position=None, instrument_type="A"),
            rr(1, unit_number="1", position="FOH", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2  # 공란 스코프 vs 'FOH' 스코프 — 서로 다르다.
        assert rig.join_key_conflicts == ()

        records_both_blank = [
            rr(0, unit_number="1", position=None, instrument_type="A"),
            rr(1, unit_number="1", position=None, instrument_type="B"),
        ]
        rig_blank = build_designed_rig(records_both_blank)
        assert rig_blank.fixtures == ()
        assert len(rig_blank.join_key_conflicts) == 1  # 공란끼리는 충돌한다.

    def test_channel_takes_priority_over_position_unit_number_scope(self):
        """channel이 있으면 그것이 최우선 조인 키다 — position/unit_number는 보지 않는다."""
        records = [
            rr(0, unit_number=None, channel="10", instrument_type="A"),
            rr(1, unit_number=None, channel="20", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2
        assert rig.join_key_conflicts == ()

    def test_channel_join_works_when_unit_number_is_blank_across_all_rows(self):
        records = [
            rr(0, unit_number=None, channel="1", instrument_type="A", universe=1, address=1),
            rr(1, unit_number=None, channel="2", instrument_type="B", universe=1, address=2),
            rr(2, unit_number=None, channel="3", instrument_type="C", universe=1, address=3),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 3
        assert rig.join_key_conflicts == ()

    def test_non_numeric_channel_name_still_joins_correctly(self):
        """channel은 문서상 비숫자("channel name")일 수 있다 — 문자열로 다룬다."""
        records = [
            rr(0, unit_number=None, channel="House Left A", instrument_type="A"),
            rr(1, unit_number=None, channel="House Left B", instrument_type="B"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 2
        assert rig.join_key_conflicts == ()

    def test_part_index_multicell_folding_still_works_within_the_new_scope(self):
        """요구사항 3 — part_index가 있으면 기존 멀티셀 폴딩 규약이 새 스코프에서도 유지된다."""
        records = [
            rr(0, unit_number="1", position="FOH", part_index="1", instrument_type="MMX Head"),
            rr(1, unit_number="1", position="FOH", part_index="2", instrument_type="MMX Head"),
        ]
        rig = build_designed_rig(records)
        assert len(rig.fixtures) == 1
        assert rig.join_key_conflicts == ()
        assert rig.fixtures[0].part_indices == ("1", "2")


class TestVectorworksNativeConflictPassthrough:
    """AC-VWX-017 — VW 자체 충돌 분류 통과(예외 없음)."""

    def test_same_channel_is_caught_as_a_join_key_conflict_before_reaching_vw_classification(self):
        """v0.1.5 조인 키 우선순위 수정(REQ-VWX-016) 이후 행동이 바뀌었다 — 명시적 회귀 기록.

        수정 전에는 이 입력(두 행이 문자 그대로 같은 ``channel``)이 join 계층을
        그냥 통과해 2개의 독립 픽스처가 되고, 그중 하나가 ``VW_IDENTICAL_PATCH``로
        분류됐다. 하지만 channel은 이제 **전역 유일** 조인 키다 — 두 행이 정말로
        같은 channel 값을 가진다면 그건 서로 다른 두 픽스처가 아니라 **조인 키
        중복**이고, Part Index 없이는 조용히 병합하지 않고 거부하는 것이 맞다.
        이 시나리오는 이제 join_key_conflict로 먼저 잡히며, `_classify_vw_conflicts`
        단계(서로 다른 조인 키로 만들어진 2개의 독립 픽스처가 우연히 같은 주소를
        공유하는 경우)에는 아예 도달하지 않는다 — `VW_IDENTICAL_PATCH`는 여전히
        존재하는 코드 경로이지만 channel이 있는 파일에서는 이 형태로 재현되지
        않는다(아래 두 테스트가 channel 부재/상이 조건에서 여전히 재현됨을 보인다).
        """
        records = [
            rr(0, unit_number="1", universe=1, address=1, channel="1"),
            rr(1, unit_number="2", universe=1, address=1, channel="1"),
        ]
        rig = build_designed_rig(records)  # must not raise
        assert rig.fixtures == ()
        assert len(rig.join_key_conflicts) == 1
        assert "channel '1'" in rig.join_key_conflicts[0].detail
        assert rig.vw_patch_conflicts == ()

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
