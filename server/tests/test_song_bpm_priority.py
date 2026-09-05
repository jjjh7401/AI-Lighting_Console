"""M2 — BPM 정본 우선순위와 3원 불일치 (AC-MUSICSYNC-016 · AC-MUSICSYNC-018).

우선순위는 **측정(사람이 확인 카드에서 확정한 값) > 시트 ``HEAD.BPM`` > 기본값
120** 이고, ``FX-Rate`` 는 **대조 전용**이다(plan.md §C 결정 3).

``FX-Rate`` 를 판정에 안 쓰는 이유는 취향이 아니다 —
``FX-Rate = SongBPM ÷ 사이클당 박수`` 인데 **사이클당 박수가 사람의 의도**라
역산이 일의적이지 않다. 하나의 ``FX-Rate`` 가 여러 BPM 과 양립한다.

콘솔 접촉: 0건.
"""

from __future__ import annotations

import pytest

from server.design.interview import _tempo_band_texture
from server.design.lint import lint_sheet
from server.design.profile import (
    BPM_SOURCE_DEFAULT,
    BPM_SOURCE_MEASURED,
    BPM_SOURCE_SHEET,
    DEFAULT_BPM,
    MusicProfile,
    parse_sheet_bpm,
    resolve_bpm,
)

# =============================================================================
# 시트 HEAD.BPM 문자열 파싱
# =============================================================================


class TestTheSheetTempoIsReadOutOfAnAnnotatedString:
    """실측 시트가 ``120 (고정)`` 처럼 주석을 달고 온다(spec.md REQ-MUSICSYNC-017)."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("120 (고정)", 120.0),
            ("120", 120.0),
            (" 128.5 ", 128.5),
            ("BPM 96 (측정)", 96.0),
            ("140 bpm", 140.0),
        ],
    )
    def test_a_number_with_an_annotation_still_reads(self, raw, expected):
        assert parse_sheet_bpm(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "미정", "확인필요", None, "(고정)"])
    def test_a_string_with_no_number_reads_as_absent_not_as_zero(self, raw):
        # 「없음」을 0 으로 접으면 그 곡은 0 BPM 으로 계산된다.
        assert parse_sheet_bpm(raw) is None

    @pytest.mark.parametrize("raw", ["0", "-40", "0 (고정)"])
    def test_a_nonpositive_tempo_is_absent_not_adopted(self, raw):
        assert parse_sheet_bpm(raw) is None


# =============================================================================
# 우선순위 (AC-MUSICSYNC-018)
# =============================================================================


class TestMeasuredBeatsSheetBeatsDefault:
    def test_the_measured_value_wins_when_all_three_exist(self):
        resolution = resolve_bpm(measured_bpm=128.0, sheet_bpm="120 (고정)")
        assert resolution.bpm == 128.0
        assert resolution.source == BPM_SOURCE_MEASURED

    def test_the_sheet_value_wins_when_nothing_was_measured(self):
        resolution = resolve_bpm(measured_bpm=None, sheet_bpm="120 (고정)")
        assert resolution.bpm == 120.0
        assert resolution.source == BPM_SOURCE_SHEET

    def test_the_default_stands_when_neither_exists(self):
        resolution = resolve_bpm()
        assert resolution.source == BPM_SOURCE_DEFAULT
        # 기본값 경로에서는 **숫자를 싣지 않는다** — MusicProfile 이 None 을 받아야
        # bpm_is_default 가 True 로 남고 「기본값이다」가 하류에 전달된다.
        assert resolution.bpm is None

    def test_the_reason_names_the_whole_chain_not_just_the_winner(self):
        resolution = resolve_bpm(measured_bpm=128.0, sheet_bpm="120 (고정)")
        assert "측정" in resolution.reason
        assert "시트" in resolution.reason
        assert "기본값" in resolution.reason


class TestNothingIsAdoptedSilently:
    """AC-MUSICSYNC-018 — 불일치는 채택 여부와 무관하게 **항상** 보고된다."""

    def test_a_measured_sheet_disagreement_is_reported(self):
        resolution = resolve_bpm(measured_bpm=128.0, sheet_bpm="120 (고정)")
        assert resolution.mismatches
        joined = " ".join(resolution.mismatches)
        assert "128" in joined
        assert "120" in joined

    def test_an_agreement_reports_no_mismatch(self):
        # 대조군: 언제나 불일치를 외치면 위 시험은 공허하다.
        resolution = resolve_bpm(measured_bpm=120.0, sheet_bpm="120 (고정)")
        assert resolution.mismatches == ()

    def test_a_sub_tolerance_difference_is_not_called_a_disagreement(self):
        resolution = resolve_bpm(measured_bpm=120.05, sheet_bpm="120")
        assert resolution.mismatches == ()

    def test_the_winner_is_still_reported_when_the_sheet_is_absent(self):
        resolution = resolve_bpm(measured_bpm=128.0)
        assert resolution.source == BPM_SOURCE_MEASURED
        assert resolution.mismatches == ()


class TestFxRateIsComparedNeverAdopted:
    """AC-MUSICSYNC-018 둘째 Given — 역산값은 대조 항목으로만 보고된다."""

    def test_the_back_calculated_value_is_reported(self):
        resolution = resolve_bpm(
            measured_bpm=128.0, sheet_bpm="120 (고정)", fx_rate=25.0, beats_per_cycle=4
        )
        assert resolution.fx_rate_back_calculated == 100.0

    def test_the_back_calculated_value_never_becomes_the_source(self):
        resolution = resolve_bpm(measured_bpm=None, sheet_bpm=None, fx_rate=25.0, beats_per_cycle=4)
        # 측정도 시트도 없는, 역산값이 이길 수 있는 유일한 자리에서도 안 이긴다.
        assert resolution.source == BPM_SOURCE_DEFAULT
        assert resolution.bpm is None

    def test_a_disagreeing_back_calculation_is_reported_as_a_comparison(self):
        resolution = resolve_bpm(
            measured_bpm=128.0, sheet_bpm="120 (고정)", fx_rate=25.0, beats_per_cycle=4
        )
        joined = " ".join(resolution.mismatches)
        assert "FX-Rate" in joined
        assert "대조" in joined

    def test_the_non_uniqueness_of_the_back_calculation_is_stated(self):
        # 사이클당 박수가 사람의 의도라 하나의 FX-Rate 가 여러 BPM 과 양립한다.
        # 그 사실이 보고에 적히지 않으면 다음 사람이 역산값을 측정값으로 읽는다.
        resolution = resolve_bpm(measured_bpm=128.0, fx_rate=25.0, beats_per_cycle=4)
        assert "사이클당" in " ".join(resolution.mismatches)

    def test_no_fx_rate_means_no_comparison_entry(self):
        resolution = resolve_bpm(measured_bpm=128.0, sheet_bpm="120 (고정)")
        assert resolution.fx_rate_back_calculated is None
        assert "FX-Rate" not in " ".join(resolution.mismatches)


# =============================================================================
# 측정 BPM 이 기본값 표식을 끈다 (AC-MUSICSYNC-016)
# =============================================================================


def _profile_from(resolution) -> MusicProfile:
    """해소 결과를 오늘의 ``MusicProfile`` 로 옮기는 유일한 자리.

    별도 배선을 만들지 않는 것이 설계다(design.md §4.4) — 소비자가 이미
    ``bpm_is_default`` 를 읽고 있으므로 이 한 자리만 정직해지면 하류 전부가
    따라온다.
    """
    return MusicProfile(bpm=resolution.bpm)


class TestAConfirmedTempoTurnsOffTheDefaultMarker:
    def test_a_confirmed_128_lands_on_the_profile(self):
        profile = _profile_from(resolve_bpm(measured_bpm=128.0, sheet_bpm="120 (고정)"))
        assert profile.bpm_is_default is False
        assert profile.effective_bpm == 128.0

    def test_no_confirmation_leaves_today_untouched(self):
        # 회귀 없음: 아무도 BPM 을 주지 않으면 오늘과 같다.
        profile = _profile_from(resolve_bpm())
        assert profile.bpm_is_default is True
        assert profile.effective_bpm == DEFAULT_BPM == 120.0

    def test_the_sheet_value_also_turns_the_marker_off(self):
        profile = _profile_from(resolve_bpm(sheet_bpm="120 (고정)"))
        assert profile.bpm_is_default is False
        assert profile.effective_bpm == 120.0


class TestLintL11RunsOnceTheTempoIsReal:
    """AC-MUSICSYNC-016 — 「린트 L11 이 실행되고」.

    ``lint_sheet`` 은 건너뛴 규칙을 침묵이 아니라 :class:`DisabledRuleNote` 로
    적는다. 그래서 「돌았다」는 그 목록에 L11 이 **없다**로 판정된다.
    """

    @staticmethod
    def _disabled_ids(profile: MusicProfile) -> set[str]:
        from server.tests.test_design_lint import _SINGLE_LAYER_RIG, _sheet

        report = lint_sheet(_sheet([]), profile, _SINGLE_LAYER_RIG)
        return {note.rule_id for note in report.disabled_rules}

    def test_l11_is_disabled_while_the_tempo_is_the_default(self):
        assert "L11" in self._disabled_ids(_profile_from(resolve_bpm()))

    def test_l11_runs_once_a_measured_tempo_is_confirmed(self):
        assert "L11" not in self._disabled_ids(_profile_from(resolve_bpm(measured_bpm=128.0)))


class TestTheDefaultTempoDisclosureFollowsTheMarker:
    """AC-MUSICSYNC-016 — 「BPM 미지정, 120 기본값」 문구가 사라진다.

    ⚠️ **측정된 한계.** 이 문구를 만드는 자리는 ``interview.py``
    ``_tempo_band_texture`` 하나뿐이고(저장소 전수 grep), 그 반환값의 사유
    문자열은 ``_build_q5`` 의 중복 제거 루프에서 **버려진다** — 즉 오늘 이
    문구는 사용자 출력에 애초에 닿지 않는다(Q5_TEXTURE 카드 직렬화 실측:
    기본값 프로필에서도 미포함). 그래서 이 클래스는 **생산 지점**에서 판정한다.
    소비 지점의 그 공백은 이 SPEC 의 범위가 아니며 고치지 않는다 —
    완료 보고의 미검증 절에 적는다.
    """

    def test_the_disclosure_is_attached_while_the_tempo_is_defaulted(self):
        _texture, reason = _tempo_band_texture(_profile_from(resolve_bpm()))
        assert "BPM 미지정, 120 기본값" in reason

    def test_the_disclosure_disappears_once_a_tempo_is_confirmed(self):
        _texture, reason = _tempo_band_texture(_profile_from(resolve_bpm(measured_bpm=128.0)))
        assert "BPM 미지정, 120 기본값" not in reason
        assert "BPM 128" in reason
