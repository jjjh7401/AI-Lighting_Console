"""등급이 한 띠에 몰려 판별을 못 하면 기준점을 옮긴다 (t412).

## 재현한 결함

t411 이 구간 하한을 마디로 고쳐 `src/Club Diver.mp3`(141초, BPM 139.7)가 39 → 13구간이
됐다. 그런데 그 13구간의 D 등급이 이랬다:

    D 레벨: [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 3]
    역할  : intro, chorus ×11, finale

**12/13 이 D5** 다. 그래서 `_infer_confirmed_role` 의 「최고 레벨이면 chorus」 규칙이
가운데 구간 전부를 chorus 로 만들고, `_ARC_PALETTE`/`_ARC_FX`/`_ARC_TEXTURE` 세 표가
같은 항목을 고른다 — 구간을 13개로 정리해도 무대는 여전히 「전부 똑같다」.

## 원인 — 문턱 하나를 두 가지 양에 재사용했다

`_should_rescale_to_song_range` 는 두 조건을 요구하는데, 두 번째가 `_MIN_LOG_STEP`(0.25)
이다. 실측:

| 잰 것 | 값 |
|---|---|
| 구간 RMS 비율(최대 대비) | 0.812 · 0.87 · 0.90 · 0.964~1.00 (9개) · outro 0.468 |
| robust 폭 log(0.2309/0.1875) | **0.208** |
| 조건2 문턱 `_MIN_LOG_STEP` | 0.25 → **막힘** |

`_MIN_LOG_STEP` 은 「**프레임 사이 계단**으로 인정할 최소 변화」다. 그것을 「**곡 전체
다이내믹 폭**」 문턱으로 빌려 쓰면 두 양을 뭉갠다 — 한 순간의 23% 도약은 잡음일 수
있지만, 곡 전체에 걸친 23% 폭은 구조다. 실제로 0.812 / 0.87 / 0.90 세 구간이 나머지
아홉(0.96~1.00)과 눈에 보이게 갈린다.

t411 과 같은 종류의 결함이다: **단위가 다른 양에 같은 상수를 쓰면 한쪽이 조용히 틀린다.**

## 잡음 바닥은 재서 정했다

이득을 전부 같게 준 합성 트랙(= 진짜 다이내믹 0)에서 구간 평균의 로그 폭:

    구간 4개  → 0.0015
    구간 6개  → 0.0016
    구간 10개 → 0.0017
    (대조: 이득 0.2/0.5/0.9/0.35 → 1.5009)

실제 곡의 0.208 은 그 **122배**다. 다만 이 0.0017 은 클릭 트랙에서 잰 값이므로
**하한**이고, 실제 음악의 잡음 바닥은 더 높다 — 그래서 새 문턱은 이 값에 여유를 크게
두었다. 이 숫자를 「실제 음악의 잡음 바닥」이라고 주장하지 않는다.

## 고친 방향 — 덧붙이기, 갈아끼우기가 아니다

기존 조건은 그대로 두고 **OR 로 새 조건을 더한다.** 그래서 전에 재조정되던 곡은 전부
그대로 재조정된다 — 이 변경으로 새로 깨질 수 있는 것은 「재조정되지 않기를 기대하는」
쪽뿐이고, 그건 아래 음성 대조가 지킨다.

새 조건은 폭이 아니라 **판별 실패**를 본다: 기본 기준점으로 매긴 등급이 한 띠에
몰려 있으면(그리고 폭이 잡음 바닥보다 뚜렷하면) 기준점을 곡의 관측 폭으로 옮긴다.
「폭이 얼마나 큰가」보다 「등급이 일을 하고 있는가」가 이 판정이 실제로 묻고 싶은 것이다.
"""

from __future__ import annotations

import io
import math

import pytest

from server.audio.analyze import (
    _D_LEVEL_BANDS,
    _D_LEVEL_DEGENERATE_SHARE,
    _D_LEVEL_RANGE_NOISE_FLOOR,
    _FRAME_LENGTH,
    _HOP_LENGTH,
    _MIN_LOG_STEP,
    _grade_sections,
    _grading_is_degenerate,
    _should_rescale_to_song_range,
    analysis_available,
)

from .fixtures.audio import FIXTURE_BPM, synthesize_track_with_steps

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa/soundfile 이 없으면 분석기를 돌릴 수 없다.",
)

#: 실제 곡 실측 (2026-09-14, `src/Club Diver.mp3` 13구간). 파일을 읽지 않고 숫자만 쓴다.
_MEASURED_SECTION_MEANS: tuple[float, ...] = (
    0.1875,
    0.2234,
    0.2008,
    0.2259,
    0.2236,
    0.2242,
    0.2287,
    0.2077,
    0.2279,
    0.2226,
    0.2289,
    0.2309,
    0.1081,
)

#: 이득을 전부 같게 준 합성 트랙에서 잰 구간 평균 로그 폭 (구간 4·6·10개에서
#: 0.0015 / 0.0016 / 0.0017). 클릭 트랙 기준이므로 **하한**이다.
_MEASURED_SYNTHETIC_NOISE_SPREAD = 0.0017


def _ratios(means: tuple[float, ...]) -> list[float]:
    loudest = max(means)
    return [mean / loudest for mean in means]


def _band_of(ratio: float) -> int:
    for upper, level in _D_LEVEL_BANDS:
        if ratio < upper:
            return level
    return 5


class TestTheReportedDefectReproduces:
    def test_the_measured_song_saturates_the_top_band(self):
        """실측 곡의 구간 평균으로 기본 등급을 매기면 12/13 이 D5 다."""
        levels = [_band_of(ratio) for ratio in _ratios(_MEASURED_SECTION_MEANS)]

        assert levels.count(5) == 12, levels
        assert len(set(levels)) == 2, f"등급이 {sorted(set(levels))} 두 종류뿐이다"

    def test_the_old_gate_borrowed_a_frame_step_threshold(self):
        """조건2 가 `_MIN_LOG_STEP` 이라 실측 폭 0.208 이 막혔다 — 산수를 고정한다."""
        spread = math.log(0.2309 / 0.1875)

        assert spread == pytest.approx(0.208, abs=0.001)
        assert spread < _MIN_LOG_STEP, "이 부등호가 결함의 전부다"


class TestTheNoiseFloorIsMeasuredNotChosen:
    def test_the_new_floor_sits_well_above_the_measured_synthetic_noise(self):
        """합성 잡음 바닥(0.0017)보다 충분히 위 — 여유가 10배 이상이다.

        합성 클릭 트랙은 실제 음악보다 조용하므로 0.0017 은 **하한**이다. 그 값을
        그대로 문턱으로 쓰면 실제 음악의 프레임 흔들림을 다이내믹으로 읽는다.
        """
        assert _D_LEVEL_RANGE_NOISE_FLOOR > _MEASURED_SYNTHETIC_NOISE_SPREAD * 10

    def test_the_new_floor_stays_below_the_measured_song_spread(self):
        """실측 곡의 0.208 은 통과해야 한다 — 아니면 결함이 그대로다."""
        assert math.log(0.2309 / 0.1875) > _D_LEVEL_RANGE_NOISE_FLOOR

    def test_the_new_floor_is_stricter_than_a_bare_ratio_of_one(self):
        """완전히 평평한 곡(폭 0)은 통과하지 못한다."""
        assert _D_LEVEL_RANGE_NOISE_FLOOR > 0.0


class TestDegeneracyIsAboutDiscrimination:
    def test_a_saturated_grading_is_degenerate(self):
        ratios = _ratios(_MEASURED_SECTION_MEANS)

        assert _grading_is_degenerate(ratios) is True

    def test_a_well_spread_grading_is_not_degenerate(self):
        """음성 대조 (필수) — 등급이 흩어져 있으면 기준점을 옮기지 않는다.

        이 짝이 없으면 「항상 재조정한다」가 위 시험을 통과한다.
        """
        ratios = [0.15, 0.35, 0.55, 0.75, 0.95]

        assert _grading_is_degenerate(ratios) is False

    def test_the_share_threshold_is_a_majority_not_unanimity(self):
        """만장일치를 요구하면 「11/13 이 한 띠」 같은 실제 사례를 놓친다."""
        assert 0.5 < _D_LEVEL_DEGENERATE_SHARE < 1.0

    def test_an_empty_grading_is_not_degenerate(self):
        """구간이 없으면 판별 실패라고 말할 근거도 없다 — 0 으로 나누지 않는다."""
        assert _grading_is_degenerate([]) is False

    def test_a_single_section_is_not_degenerate(self):
        """구간 하나뿐이면 등급이 하나인 것이 당연하다 — 결함이 아니다."""
        assert _grading_is_degenerate([1.0]) is False


class TestTheGateIsAdditive:
    """기존 조건은 그대로 살아 있다 — 새 조건은 OR 로 더했을 뿐이다."""

    def test_the_old_condition_still_fires_on_its_own(self):
        """양성 대조 — 폭이 넓고 조용한 구간도 높은 곡은 전과 같이 재조정된다."""
        loudest, quietest = 1.0, 0.7  # 비 0.7 >= 0.60, log 0.357 >= 0.25

        assert _should_rescale_to_song_range(loudest, quietest, ratios=None) is True

    def test_the_new_condition_fires_where_the_old_one_did_not(self):
        """실측 곡의 값 — 전에는 False 였다."""
        loudest, quietest = 0.2309, 0.1875
        ratios = _ratios(_MEASURED_SECTION_MEANS)

        assert _should_rescale_to_song_range(loudest, quietest, ratios=None) is False
        assert _should_rescale_to_song_range(loudest, quietest, ratios=ratios) is True

    def test_a_genuinely_flat_song_is_still_not_rescaled(self):
        """음성 대조 (필수) — 다이내믹이 정말 없는 곡에 없는 것을 지어내지 않는다.

        등급은 한 띠에 몰려 있지만(판별 실패) 폭이 잡음 바닥 미만이므로 재조정하지
        않는다. 두 조건을 **함께** 요구하는 이유가 이것이다.
        """
        flat = (0.5000, 0.5001, 0.5002, 0.5001, 0.5000)
        ratios = _ratios(flat)
        assert _grading_is_degenerate(ratios) is True  # 판별은 실패했다

        assert _should_rescale_to_song_range(max(flat), min(flat), ratios=ratios) is False

    def test_a_reversed_or_zero_range_is_refused(self):
        """경계 — 0·음수·역전된 폭은 그대로 거절한다."""
        ratios = _ratios(_MEASURED_SECTION_MEANS)

        assert _should_rescale_to_song_range(0.0, 0.0, ratios=ratios) is False
        assert _should_rescale_to_song_range(0.1, 0.2, ratios=ratios) is False


class TestTheGradesActuallySpreadEndToEnd:
    """왕복 시험 — 압축된 합성 트랙이 여러 등급을 받는가.

    이득을 0.80~1.00 사이에 몰아 실제 곡의 상황(전 구간이 상위 띠)을 만든다.
    """

    GAINS = (0.80, 0.95, 0.84, 1.00, 0.88, 0.97)
    PLANTED = tuple(15_000 * i for i in range(6))
    DURATION_MS = 90_000

    @pytest.fixture(scope="class")
    @classmethod
    def graded(cls):
        import librosa
        import numpy
        import soundfile

        track = synthesize_track_with_steps(
            bpm=FIXTURE_BPM,
            duration_ms=cls.DURATION_MS,
            boundaries_ms=cls.PLANTED,
            gains=cls.GAINS,
        )
        samples, sample_rate = soundfile.read(io.BytesIO(track), dtype="float32", always_2d=True)
        mono = numpy.ascontiguousarray(samples.mean(axis=1), dtype=numpy.float32)
        rms = librosa.feature.rms(y=mono, frame_length=_FRAME_LENGTH, hop_length=_HOP_LENGTH)[0]
        frame_ms = _HOP_LENGTH * 1000.0 / sample_rate
        duration_ms = int(round(len(mono) * 1000.0 / sample_rate))
        return _grade_sections(numpy, rms, frame_ms, cls.PLANTED, duration_ms)

    def test_a_compressed_track_no_longer_collapses_into_one_grade(self, graded):
        levels = [candidate.d_level for candidate in graded]

        assert len(set(levels)) >= 3, f"등급 {levels} — 압축 곡이 여전히 뭉개진다"

    def test_the_loudest_section_still_grades_highest(self, graded):
        """양성 대조 — 순서가 뒤집히면 재조정이 의미를 부순 것이다."""
        levels = [candidate.d_level for candidate in graded]
        loudest_index = self.GAINS.index(max(self.GAINS))

        assert levels[loudest_index] == max(levels), f"등급 {levels} · 이득 {self.GAINS}"

    def test_the_quietest_section_still_grades_lowest(self, graded):
        levels = [candidate.d_level for candidate in graded]
        quietest_index = self.GAINS.index(min(self.GAINS))

        assert levels[quietest_index] == min(levels), f"등급 {levels} · 이득 {self.GAINS}"

    def test_grades_are_monotone_in_gain(self, graded):
        """이득 순서와 등급 순서가 어긋나지 않는다 — 재조정은 순서를 보존한다."""
        levels = [candidate.d_level for candidate in graded]
        pairs = sorted(zip(self.GAINS, levels, strict=True))

        assert [level for _gain, level in pairs] == sorted(level for _g, level in pairs)
