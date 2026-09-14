"""구간 하한은 초가 아니라 **마디**다 (t411).

## 재현한 결함

`src/Club Diver.mp3`(141초, 실측 BPM 139.7, 확신 0.97)을 분석기에 넣으면:

| 잰 것 | 값 |
|---|---|
| 구간 개수 | **39** |
| 구간 길이 중앙값 | 3.42초 = **2.0마디** |
| 4마디 미만 구간 | **38 / 38** (전부) |

원인은 `_MIN_SEGMENT_SECONDS = 3.0` 이 **초 단위**라는 것이다. 139.7 BPM 에서 한 마디는
1718ms 이므로 3000ms 는 **1.75마디** — 마디보다 짧은 하한이다. 그러면 드럼 패턴의
2마디 프레이즈 경계가 거의 다 통과하고, 결과는 구간 목록이 아니라 박자 격자가 된다.

감독의 관측(「전부 똑같다」)의 원인 중 하나가 이것이다: 39구간에 색·효과를 흩으면
2마디마다 장면이 바뀌어 어느 구간도 자기 성격을 갖지 못한다.

## 하한을 4마디로 두는 근거 (지어낸 값이 아니다)

`docs/proposals/song-structure-lighting-standard.md` §4 — Harmonix 912곡 9,214구간을
BPM 으로 마디 환산한 실측표. **25% 하한이 라벨마다 4.0마디**다:

    intro 4.0 · pre-chorus 4.0 · post-chorus 4.0 · instrumental 4.0
    break 4.0 · transition 4.0 · outro 4.0
    (verse·chorus·bridge·solo 는 7.8~8.0 에서 시작해 더 길다)

즉 4마디 미만 구간은 912곡에서 사실상 나타나지 않는다. 같은 표의 구간 수 중앙값은
**10개**(트랙 중앙 218.6초)이므로, 141초 곡의 39개는 4배 과다다.

## 왜 4마디이고 8마디가 아닌가

같은 문서 §5 가 [HARD] 로 *"8마디를 기본값으로 쓰되 하드 제약으로 걸지 마라 — 절반
이상이 8의 배수가 아니다"* 라고 못박았다. 8마디는 **분포의 최빈값**(42.6%)이고 4마디는
**분포의 하한**이다. 하한으로 걸어야 하는 것은 후자다 — 8마디를 하한으로 걸면 실측된
4마디 구간(12.3%)을 지운다.

## 대조군 규율

「경계를 덜 낸다」는 전부 거절하는 분석기도 만족시킨다. 그래서 이 파일의 모든 축소
시험에는 **살아남아야 하는 짝**이 있다.
"""

from __future__ import annotations

import pytest

from server.audio.analyze import (
    _FRAME_LENGTH,
    _HOP_LENGTH,
    _MIN_SEGMENT_BARS,
    _MIN_SEGMENT_SECONDS,
    _boundaries_from_rms,
    _min_segment_ms,
    analysis_available,
    analyze,
)

from .fixtures.audio import FIXTURE_BPM, synthesize_track_with_steps

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa/soundfile 이 없으면 분석기를 돌릴 수 없다.",
)

#: 실측한 실제 곡의 값 (2026-09-14, `src/Club Diver.mp3`). 저장소에 곡을 두지 않으므로
#: 시험은 이 숫자를 **계산의 입력**으로만 쓰고 파일을 읽지 않는다.
_MEASURED_SONG_BPM = 139.7


def _bar_ms(bpm: float) -> float:
    """4/4 한 마디의 길이."""
    return 4.0 * 60_000.0 / bpm


#: 2마디(128 BPM 에서 3750ms) 격자로 심는 계단 11개. 결함이 나타나는 격자다.
_TWO_BAR_GRID: tuple[int, ...] = tuple(int(round(2 * _bar_ms(FIXTURE_BPM))) * i for i in range(11))

#: 이득을 **교대**로 준다. 완만하게 올리면 계단이 `_MIN_LOG_STEP`(0.25 ≈ 28% 레벨 변화)에
#: 못 미쳐 애초에 경계가 되지 않고, 그러면 하한이 아니라 로그 문턱을 재게 된다 —
#: 실측 확인(완만 0.07씩: 옛 하한 3개 / 새 하한 1개. 하한의 효과가 거의 안 보인다).
_ALTERNATING_GAINS: tuple[float, ...] = tuple(0.2 if i % 2 == 0 else 0.9 for i in range(11))


class TestTheFloorIsMeasuredInBars:
    def test_the_reported_defect_reproduces_in_the_old_units(self):
        """결함의 산수 자체를 고정한다 — 3초는 139.7 BPM 에서 1.75마디다."""
        assert _MIN_SEGMENT_SECONDS * 1000.0 / _bar_ms(_MEASURED_SONG_BPM) == pytest.approx(
            1.75, abs=0.01
        )

    def test_the_floor_is_four_bars_at_the_measured_song_tempo(self):
        """139.7 BPM 에서 하한이 4마디(≈6873ms)로 올라간다."""
        expected = _MIN_SEGMENT_BARS * _bar_ms(_MEASURED_SONG_BPM)

        assert _min_segment_ms(bpm=_MEASURED_SONG_BPM, duration_ms=141_000) == pytest.approx(
            expected, abs=1.0
        )

    def test_the_floor_is_four_bars_not_eight(self):
        """8마디를 하한으로 걸면 실측된 4마디 구간(12.3%)을 지운다 — 기준 문서 §5."""
        assert _MIN_SEGMENT_BARS == 4.0

    def test_an_unknown_tempo_falls_back_to_the_old_seconds_floor(self):
        """BPM 을 모르면 옛 하한 그대로다 — 120 BPM 을 가정하지 않는다.

        기준 문서와 계약(`LD-TIME-002`)이 같은 것을 요구한다: tempo 불명에 기본값을
        대입하지 않는다. 이 저장소의 `profile.py` 도 같은 이유로 FX-Rate 역산을
        채택 후보에서 뺐다.
        """
        assert _min_segment_ms(bpm=None, duration_ms=141_000) == _MIN_SEGMENT_SECONDS * 1000.0

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
    def test_an_unusable_tempo_falls_back_too(self, bad: float):
        """0·음수·비유한 BPM 은 「모른다」와 같이 다룬다 — 0 으로 나누지 않는다."""
        assert _min_segment_ms(bpm=bad, duration_ms=141_000) == _MIN_SEGMENT_SECONDS * 1000.0

    def test_the_floor_never_drops_below_the_old_seconds_floor(self):
        """단조 증가 — 아주 빠른 곡에서도 하한이 낮아지지 않는다.

        이 성질이 중요한 이유: 하한이 오르기만 하면, **경계가 거절되기를 기대하는**
        기존 시험은 새로 깨질 수 없다. 깨질 수 있는 것은 경계가 통과하기를
        기대하는 쪽뿐이고, 그건 픽스처를 보면 알 수 있다.
        """
        very_fast = 400.0  # 계약 §6.1 의 bpm 상한
        assert _bar_ms(very_fast) * _MIN_SEGMENT_BARS < _MIN_SEGMENT_SECONDS * 1000.0

        assert _min_segment_ms(bpm=very_fast, duration_ms=141_000) == _MIN_SEGMENT_SECONDS * 1000.0


class TestTheFloorCannotSwallowTheWholeTrack:
    """느린 곡에서 하한이 곡을 통째로 삼키지 않는다.

    20 BPM(계약 하한)이면 한 마디가 12초이고 4마디는 48초다 — 그 하한을 그대로 걸면
    3분 곡이 4구간이 된다. 기준 문서 §4 의 구간 수 중앙값이 **10개**이므로, 최소
    6구간은 가능해야 한다는 것을 상한으로 쓴다(10 보다 보수적인 값).
    """

    def test_a_slow_tempo_floor_is_capped_by_the_track_length(self):
        duration_ms = 180_000
        uncapped = _MIN_SEGMENT_BARS * _bar_ms(20.0)  # 48000ms
        assert uncapped > duration_ms / 6.0

        assert _min_segment_ms(bpm=20.0, duration_ms=duration_ms) == pytest.approx(
            duration_ms / 6.0
        )

    def test_a_normal_tempo_is_not_capped(self):
        """양성 대조 — 보통 템포에서는 상한이 걸리지 않는다."""
        duration_ms = 180_000
        expected = _MIN_SEGMENT_BARS * _bar_ms(128.0)
        assert expected < duration_ms / 6.0

        assert _min_segment_ms(bpm=128.0, duration_ms=duration_ms) == pytest.approx(expected)

    def test_the_cap_never_drops_below_the_old_seconds_floor(self):
        """아주 짧은 트랙에서도 옛 하한 아래로 내려가지 않는다."""
        assert _min_segment_ms(bpm=20.0, duration_ms=6_000) == _MIN_SEGMENT_SECONDS * 1000.0


class TestTheAnalyzerStopsCuttingOnATwoBarGrid:
    """왕복 시험 — 합성 트랙으로 실제 분석기를 돌린다.

    `FIXTURE_BPM` 은 128 이므로 한 마디 1875ms, 4마디 7500ms 다.
    """

    def _boundaries(self, **kwargs) -> tuple[int, ...]:
        outcome = analyze(synthesize_track_with_steps(bpm=FIXTURE_BPM, **kwargs))
        assert not hasattr(outcome, "reason"), getattr(outcome, "reason", "")
        return outcome.boundaries_ms

    def test_a_two_bar_grid_no_longer_becomes_a_section_list(self):
        """2마디(3750ms) 간격으로 강한 계단을 심어도 4마디 미만 구간이 나오지 않는다.

        이득을 **교대**(0.2/0.9)로 주는 것이 의도다 — 완만하게 올리면 계단이
        `_MIN_LOG_STEP` 에 못 미쳐 애초에 경계가 되지 않고, 그러면 이 시험은 하한을
        재지 못한 채 초록이 된다(실측 확인). 이 입력은 옛 하한에서 경계 11개를 낸다.
        """
        two_bars = int(round(2 * _bar_ms(FIXTURE_BPM)))  # 3750ms
        planted = tuple(two_bars * i for i in range(11))  # 0 … 37500
        gains = tuple(0.2 if i % 2 == 0 else 0.9 for i in range(11))

        detected = self._boundaries(duration_ms=45_000, boundaries_ms=planted, gains=gains)

        # 공허 방지 — 경계가 하나뿐이면 아래 간격 단언은 아무것도 재지 않는다.
        assert len(detected) >= 3, f"검출 {detected} — 이 입력에서 과소 검출이다"

        four_bar_ms = _bar_ms(FIXTURE_BPM) * _MIN_SEGMENT_BARS
        gaps = [detected[i + 1] - detected[i] for i in range(len(detected) - 1)]
        too_short = [gap for gap in gaps if gap < four_bar_ms - 1]
        assert too_short == [], f"4마디 미만 간격 {too_short} · 검출 {detected}"

    def test_an_eight_bar_grid_still_yields_every_boundary(self):
        """양성 대조 (필수) — 8마디(15000ms) 간격은 전부 살아남는다.

        이 짝이 없으면 위 시험은 「경계를 하나도 안 내는 분석기」도 통과시킨다.
        """
        eight_bars = int(round(8 * _bar_ms(FIXTURE_BPM)))  # 15000ms
        planted = (0, eight_bars, eight_bars * 2)

        detected = self._boundaries(
            duration_ms=48_000, boundaries_ms=planted, gains=(0.15, 0.55, 0.95)
        )

        misses = [
            expected
            for expected in planted
            if not any(abs(found - expected) <= 1_000 for found in detected)
        ]
        assert misses == [], f"미검출 경계 {misses} · 검출 {detected}"

    def test_a_four_bar_grid_still_yields_every_boundary(self):
        """양성 대조 — 하한과 **같은** 4마디 간격은 지워지지 않는다(경계값).

        하한을 `>` 로 구현하면 이 시험이 빨개진다. 실측 분포의 하한 자체가
        4마디이므로 4마디는 통과해야 한다.
        """
        four_bars = int(round(4 * _bar_ms(FIXTURE_BPM)))  # 7500ms
        planted = (0, four_bars, four_bars * 2, four_bars * 3)

        detected = self._boundaries(
            duration_ms=40_000, boundaries_ms=planted, gains=(0.15, 0.45, 0.95, 0.30)
        )

        misses = [
            expected
            for expected in planted
            if not any(abs(found - expected) <= 1_000 for found in detected)
        ]
        assert misses == [], f"미검출 경계 {misses} · 검출 {detected}"


class TestTheSameAudioWithOnlyTheFloorChanged:
    """**같은 오디오, 하한만 다르게** — 결함과 처방을 한 회차에서 나란히 잰다.

    이 대조가 이 파일에서 가장 중요하다. 「경계가 줄었다」만 재면 오디오가 달라서
    줄었을 수도, 분석기가 나빠져서 줄었을 수도 있다. `bpm=None`(옛 초 하한)과
    `bpm=128`(새 마디 하한)을 **동일한 rms 배열**에 적용하면 차이의 원인이 하한뿐이다.

    실측 (2026-09-14, 45초 트랙, 2마디 격자로 계단 11개, 이득 0.2/0.9 교대):

    | 하한 | 경계 | 간격 |
    |---|---|---|
    | 옛 3000ms | **11개** | 전부 ~3700ms = **2마디** |
    | 새 7500ms | **5개** | 11215 / 7500 / 7500 / 7500 |

    이득을 **교대**로 준 것이 의도다. 완만하게(0.07씩) 올리면 대부분의 계단이
    `_MIN_LOG_STEP`(0.25 ≈ 28% 레벨 변화)에 못 미쳐 애초에 경계가 되지 않고, 그러면
    이 시험은 하한이 아니라 로그 문턱을 재게 된다 — 실측으로 확인했다(완만: 옛 3개 /
    새 1개. 하한의 효과가 거의 안 보인다).
    """

    PLANTED = _TWO_BAR_GRID
    GAINS = _ALTERNATING_GAINS
    DURATION_MS = 45_000

    @pytest.fixture(scope="class")
    @classmethod
    def rms_input(cls) -> tuple[object, object, float, int]:
        """트랙을 한 번 디코딩해 두 하한에 같은 입력을 준다."""
        import io

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
        return numpy, rms, frame_ms, duration_ms

    def _gaps(self, boundaries: tuple[int, ...]) -> list[int]:
        return [boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)]

    def test_the_old_seconds_floor_reproduces_the_two_bar_grid(self, rms_input):
        """결함의 재현 — 옛 하한은 2마디 격자를 그대로 통과시킨다."""
        numpy, rms, frame_ms, duration_ms = rms_input

        old = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=None)

        gaps = self._gaps(old)
        assert len(gaps) >= 8, f"재현 실패 — 옛 하한에서 경계가 {len(old)}개뿐이다"
        two_bar_ms = _bar_ms(FIXTURE_BPM) * 2
        assert all(gap < two_bar_ms * 1.2 for gap in gaps), f"간격 {gaps}"

    def test_the_bar_floor_stops_it_on_the_very_same_input(self, rms_input):
        """처방 — 같은 입력에 마디 하한을 걸면 4마디 미만 간격이 사라진다."""
        numpy, rms, frame_ms, duration_ms = rms_input

        new = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=FIXTURE_BPM)

        four_bar_ms = _bar_ms(FIXTURE_BPM) * _MIN_SEGMENT_BARS
        short = [gap for gap in self._gaps(new) if gap < four_bar_ms - 1]
        assert short == [], f"4마디 미만 간격 {short} · 검출 {new}"

    def test_the_bar_floor_does_not_erase_everything(self, rms_input):
        """음성 대조 (필수) — 줄이기만 하는 것이 아니라 실제 계단은 남는다.

        이 짝이 없으면 위 시험은 「경계를 하나도 안 내는 분석기」도 통과시킨다.
        """
        numpy, rms, frame_ms, duration_ms = rms_input

        new = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=FIXTURE_BPM)

        # 45초에 4마디(7.5초) 하한이면 산술 상한은 6구간이다.
        assert 3 <= len(new) <= 6, f"구간 {len(new)}개 — 심은 계단 11개에서 이 범위여야 한다"

    def test_the_bar_floor_detects_strictly_fewer_than_the_seconds_floor(self, rms_input):
        """방향 단언 — 마디 하한이 초 하한보다 적게 낸다. 개수 차의 방향을 고정한다."""
        numpy, rms, frame_ms, duration_ms = rms_input

        old = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=None)
        new = _boundaries_from_rms(numpy, rms, frame_ms, duration_ms, bpm=FIXTURE_BPM)

        assert len(new) < len(old), f"옛 {len(old)}개 · 새 {len(new)}개"
        # 새 경계는 옛 경계의 부분집합이어야 한다 — 하한만 올렸으므로 없던 경계가
        # 새로 생기면 다른 것이 바뀐 것이다.
        assert set(new) <= set(old), f"옛 경계에 없던 새 경계 {sorted(set(new) - set(old))}"
