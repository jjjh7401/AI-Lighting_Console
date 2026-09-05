"""SPEC-COPILOT-MUSICSYNC-001 M1 — `mm:ss.f` 판독기 단위 검사.

이 파일이 못 박는 것 하나: **판독 결과는 「초 또는 없음」이 아니라 다섯 갈래다.**
`None` 하나로 미확정 셋을 뭉치는 순간 어딘가에 `or 0` 이 붙고, 그것이 곧
**첫 박 발사**다(REQ-MUSICSYNC-003). 그래서 부정 대조군 — 진짜 `00:00.0` 과
빈칸이 **서로 다른 값**임 — 이 이 파일의 중심이다.

콘솔 접촉 0. 순수 함수만 부른다.
"""

from __future__ import annotations

import pytest

from server.design.song_plan import SongPlanError, TimestampedSection
from server.lxseq.cue_time import (
    CUE_TIME_BLANK,
    CUE_TIME_MALFORMED,
    CUE_TIME_NEEDS_CHECK,
    CUE_TIME_OK,
    CUE_TIME_PREROLL,
    UNDETERMINED_CUE_TIME_KINDS,
    parse_cue_time,
    project_cue_timeline,
)


class TestFiveKinds:
    """다섯 갈래가 **서로 구별되는 값**이어야 한다(REQ-MUSICSYNC-002)."""

    def test_the_five_kinds_are_distinct_values(self):
        kinds = {
            CUE_TIME_OK,
            CUE_TIME_PREROLL,
            CUE_TIME_NEEDS_CHECK,
            CUE_TIME_BLANK,
            CUE_TIME_MALFORMED,
        }
        assert len(kinds) == 5

    def test_the_three_undetermined_kinds_are_named_and_distinct(self):
        assert set(UNDETERMINED_CUE_TIME_KINDS) == {
            CUE_TIME_NEEDS_CHECK,
            CUE_TIME_BLANK,
            CUE_TIME_MALFORMED,
        }
        assert len(UNDETERMINED_CUE_TIME_KINDS) == 3

    @pytest.mark.parametrize(
        ("raw", "kind", "ms"),
        [
            ("00:00.0", CUE_TIME_OK, 0),
            ("00:08.0", CUE_TIME_OK, 8000),
            ("01:12.5", CUE_TIME_OK, 72500),
            ("03:56.0", CUE_TIME_OK, 236000),
            ("-00:30.0", CUE_TIME_PREROLL, -30000),
            ("확인필요", CUE_TIME_NEEDS_CHECK, None),
            ("", CUE_TIME_BLANK, None),
            ("   ", CUE_TIME_BLANK, None),
            (None, CUE_TIME_BLANK, None),
            ("abc", CUE_TIME_MALFORMED, None),
        ],
    )
    def test_each_input_lands_in_its_own_kind(self, raw, kind, ms):
        parsed = parse_cue_time(raw)
        assert parsed.kind == kind
        assert parsed.ms == ms


class TestNegativeControlZeroIsNotAbsence:
    """🔴 부정 대조군 — 진짜 `00:00.0` 과 미확정을 **값으로** 가른다.

    이 검사가 없으면 「0 이면 미확정」과 「0 이면 첫 박」이 같은 코드로 통과한다.
    """

    def test_a_real_zero_is_determined_and_carries_zero_milliseconds(self):
        parsed = parse_cue_time("00:00.0")
        assert parsed.is_determined is True
        assert parsed.ms == 0

    @pytest.mark.parametrize("raw", ["확인필요", "", None, "abc"])
    def test_undetermined_never_carries_a_number(self, raw):
        parsed = parse_cue_time(raw)
        assert parsed.is_determined is False
        assert parsed.ms is None

    def test_blank_and_a_real_zero_are_not_the_same_value(self):
        assert parse_cue_time("") != parse_cue_time("00:00.0")


class TestBoundaries:
    def test_minutes_may_exceed_fifty_nine(self):
        assert parse_cue_time("100:00.0").ms == 6_000_000

    def test_seconds_at_sixty_are_malformed(self):
        assert parse_cue_time("00:60.0").kind == CUE_TIME_MALFORMED

    def test_the_fraction_may_be_omitted(self):
        parsed = parse_cue_time("01:12")
        assert parsed.kind == CUE_TIME_OK
        assert parsed.ms == 72000

    def test_three_fraction_digits_are_milliseconds(self):
        assert parse_cue_time("00:01.250").ms == 1250

    def test_four_fraction_digits_are_malformed_not_rounded(self):
        """지어내지 않는다 — 밀리초보다 잘게 적힌 값은 반올림이 아니라 미확정이다."""
        assert parse_cue_time("00:01.2505").kind == CUE_TIME_MALFORMED

    def test_surrounding_whitespace_is_stripped(self):
        assert parse_cue_time("  00:08.0  ").ms == 8000

    def test_a_signed_zero_is_not_pre_roll(self):
        parsed = parse_cue_time("-00:00.0")
        assert parsed.kind == CUE_TIME_OK
        assert parsed.ms == 0

    def test_a_non_string_non_none_value_is_malformed_not_coerced(self):
        parsed = parse_cue_time(8.0)
        assert parsed.kind == CUE_TIME_MALFORMED
        assert parsed.ms is None


class TestTimelineProjection:
    """PRE-ROLL 은 `TrigTime` 에는 실리고 **타임라인 투사에서는 빠진다**
    (REQ-MUSICSYNC-006). `TimestampedSection.start_ms` 의 `minimum=0` 계약은
    건드리지 않는다 — 두 계약이 모두 옳기 때문이다(design §2.3).
    """

    def test_a_pre_roll_cue_is_excluded_and_named(self):
        projection = project_cue_timeline(
            [
                ("Q005", "PRE-ROLL", parse_cue_time("-00:30.0"), parse_cue_time("00:00.0")),
                ("Q010", "INTRO", parse_cue_time("00:00.0"), parse_cue_time("00:08.0")),
            ]
        )
        assert [s.label for s in projection.sections] == ["Q010 INTRO"]
        assert projection.excluded_preroll == ("Q005",)

    def test_the_projection_raises_no_song_plan_error_on_a_negative_cue(self):
        entries = [("Q005", "PRE-ROLL", parse_cue_time("-00:30.0"), parse_cue_time("00:00.0"))]
        try:
            project_cue_timeline(entries)
        except SongPlanError as error:  # pragma: no cover - 실패 시에만 도달
            pytest.fail(f"음수 TC 가 타임라인 계약을 깼다: {error}")

    def test_sections_are_timestamped_sections_with_end_from_tc_out(self):
        projection = project_cue_timeline(
            [("Q010", "INTRO", parse_cue_time("00:00.0"), parse_cue_time("00:08.0"))]
        )
        (section,) = projection.sections
        assert isinstance(section, TimestampedSection)
        assert section.index == 1
        assert section.start_ms == 0
        assert section.end_ms == 8000

    def test_an_unusable_tc_out_leaves_end_ms_none_instead_of_inventing_one(self):
        projection = project_cue_timeline(
            [("Q010", "INTRO", parse_cue_time("00:10.0"), parse_cue_time("00:05.0"))]
        )
        (section,) = projection.sections
        assert section.end_ms is None

    def test_undetermined_cues_are_listed_not_projected(self):
        projection = project_cue_timeline(
            [
                ("Q010", "INTRO", parse_cue_time("확인필요"), parse_cue_time("")),
                ("Q020", "VERSE1", parse_cue_time("00:08.0"), parse_cue_time("00:24.0")),
            ]
        )
        assert [s.label for s in projection.sections] == ["Q020 VERSE1"]
        assert projection.undetermined == ("Q010",)

    def test_the_warning_is_carried_into_the_projection_result(self):
        projection = project_cue_timeline(
            [("Q010", "INTRO", parse_cue_time("00:00.0"), parse_cue_time("00:08.0"))],
            warning="TC_METHOD=DERIVED — 리허설 LTC 대조 전까지 실행 확정본이 아님",
        )
        assert "리허설 LTC 대조 전까지 실행 확정본이 아님" in projection.warning

    def test_a_label_falls_back_to_the_cue_number_when_the_section_is_blank(self):
        projection = project_cue_timeline(
            [("Q010", "", parse_cue_time("00:00.0"), parse_cue_time("00:08.0"))]
        )
        assert projection.sections[0].label == "Q010"
