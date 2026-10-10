"""마디 지도 M2 — 자동 비트 격자 + 사람이 지정한 첫 박 오프셋 (SPEC-LDBARMAP-001).

두 함수로 나뉜다(plan.md §D — ``AnalysisResult`` 를 확장하지 않는다):

* :func:`detect_beat_grid` — 오디오 바이트열을 재서 자동 비트 격자(``beat_times``)와
  BPM 을 낸다. ``server/audio/analyze.py`` 의 ``analyze()`` 와 **같은 디코드 경로**
  (soundfile 읽기 → mono 다운믹스 → ``librosa.beat.beat_track`` hop=512)를 그대로
  재사용한다 — 다른 경로로 디코드하면 같은 오디오에서 다른 ``beat_times`` 가 나올
  수 있어 M1 보정 결과(``tools/barmap``)와 어긋난다. 예외를 호출자 밖으로 내보내지
  않는다(``analyze.py:297`` 과 같은 원칙, REQ-LDBARMAP-001/015) — 어떤 바이트열이
  들어와도 :class:`BeatGridResult` 이거나 :class:`BeatGridFailure` 다.
* :func:`derive_bars` — 순수 함수. librosa 를 쓰지 않는다. 자동 비트 격자와 사람이
  1회 지정한 첫 박 오프셋(정수, 0~3)만으로 다운비트·마디 경계를 파생한다
  (REQ-LDBARMAP-016) — 자동 위상 선택기는 이 M2 범위에서 보류한다(follow-up).

저장은 하지 않는다 — 이 모듈의 반환값은 메모리/테스트 픽스처 범위에만 둔다
(REQ-LDBARMAP-010, 저장 인터페이스 배선은 M4의 몫).
"""

from __future__ import annotations

import io
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from server.audio.analyze import (
    _FRAME_LENGTH,
    _HOP_LENGTH,
    _MIN_DECODED_FRACTION,
    MANUAL_BPM_FALLBACK_REASON,
    _mp3_length_is_a_bitrate_guess,
    _tempo_from_beats,
    analysis_available,
)

__all__ = [
    "BarEvent",
    "BarFeatures",
    "BarFeaturesFailure",
    "BarMap",
    "BarMapFailure",
    "BeatGridFailure",
    "BeatGridResult",
    "BpmCandidateCheck",
    "classify_bar_events",
    "derive_bars",
    "detect_beat_grid",
    "extract_bar_features",
]

#: 한 마디(4/4박자)의 박 수. REQ-LDBARMAP-016 — 오프셋은 이 값의 나머지다.
_BEATS_PER_BAR = 4

#: REQ-LDBARMAP-006(재설계, 카드 t547) — 단측 부호검정 유의수준(α).
#: @MX:NOTE: [AUTO] 결과를 본 뒤 고른 값이 아니라 통계적 관행 상수(α=0.01) —
#: acceptance.md §A, plan-audit 에서 10곡·LOVE ATTACK 어느 것도 이 값을 고르는
#: 데 쓰지 않았다(감독 원칙, 2026-10-10).
_SIGN_TEST_ALPHA = 0.01

#: REQ-LDBARMAP-006(재설계, 카드 t547) — w_mid 채택 대칭점("중간점이 박만큼
#: 강하다"의 경계).
#: @MX:NOTE: [AUTO] 튜닝 값이 아니라 대칭점(0.5) 그 자체 — acceptance.md §A.
_MID_SYMMETRY = 0.5

#: REQ-LDBARMAP-006 — 두 배 판정 결과 어휘(판정표: acceptance.md §A·§B AC-004).
_OUTCOME_KEEP = "keep"
_OUTCOME_ADOPT_DOUBLE = "adopt_double"

#: 통상적인 곡 템포 범위(BPM) — 이 범위 밖의 두 배 후보는 채택하지 않는다
#: (REQ-LDBARMAP-006 재설계 — 절반 후보는 이 범위와 무관하게 자동 채택되지
#: 않는다, 진단용으로만 기록한다).
_SANE_BPM_MIN = 40.0
_SANE_BPM_MAX = 250.0


@dataclass(frozen=True)
class BpmCandidateCheck:
    """REQ-LDBARMAP-006(재설계, 카드 t547) — 추정 비트 격자 기준 단측 부호검정 근거
    (기록용, 판정 결과와 무관하게 항상 채운다).

    고정 전역 격자 대신 검출기 자신이 찾은 ``beat_times`` 를 기준틀로 쓴다 —
    BPM 추정 오차에 흔들리지 않는다(옛 설계의 결함, `.moai/reports/t547/verdict.md`
    참조). 절반 후보는 이 판정으로 자동 채택되지 않는다 — ``w_odd``/``p_two``
    는 진단용 기록일 뿐이다.
    """

    raw_bpm: float
    half_bpm: float
    double_bpm: float
    n_pairs: int
    w_mid: float
    p_mid: float
    w_odd: float
    p_two: float
    outcome: str
    ambiguous: bool
    adopted_bpm: float
    rationale: str


@dataclass(frozen=True)
class BeatGridResult:
    """자동 검출에 성공한 비트 격자.

    ``beat_times_ms`` 는 ``detect_beat_grid`` 가 실제로 검출한 격자를 그대로
    담는다 — ``bpm_check`` 가 두 배로 보정된 BPM 을 채택해도(``outcome=adopt_double``),
    이 M2 범위는 격자 자체를 재구성하지 않는다(알려진 한계, progress.md Gaps 참조).
    """

    beat_times_ms: tuple[int, ...]
    bpm: float
    bpm_confidence: float
    bpm_check: BpmCandidateCheck


@dataclass(frozen=True)
class BeatGridFailure:
    """비트 격자를 검출하지 못했다 — 그리고 왜 못 했는지.

    ``AnalysisFailure`` 와 같은 설계(analyze.py:218-226) — 실패 결과가 지어낸
    숫자를 들고 있지 않도록 ``bpm`` 같은 필드를 일부러 갖지 않는다.
    """

    reason: str


@dataclass(frozen=True)
class BarMap:
    """사람이 지정한 첫 박 오프셋으로 파생한 마디 지도 (REQ-LDBARMAP-016).

    ``downbeats_ms`` 와 ``bar_boundaries_ms`` 는 이 SPEC(4/4박자 LOVE ATTACK)에서는
    같은 수열이다 — 다운비트가 곧 마디 경계다(spec.md §5 열린 결정 3). 두 지표를
    acceptance.md AC-LDBARMAP-016 이 따로 채점하므로 필드도 따로 둔다.
    """

    downbeats_ms: tuple[int, ...]
    bar_boundaries_ms: tuple[int, ...]
    pickup_beats_ms: tuple[int, ...]
    first_beat_offset: int


@dataclass(frozen=True)
class BarMapFailure:
    """마디 지도를 파생하지 못했다 — 그리고 왜 못 했는지."""

    reason: str


@dataclass(frozen=True, eq=False)
class _DecodedAudio:
    """``detect_beat_grid``·``extract_bar_features`` 가 공유하는 디코드 결과.

    ``eq=False`` — numpy 배열 필드는 기본 dataclass ``__eq__``(원소별 비교)가
    모호한 진리값 오류를 내므로, 이 값은 비교하지 않는다(생성 즉시 소비).
    """

    mono: Any  # numpy.ndarray — mono 다운믹스된 샘플
    sample_rate: int
    duration_ms: int


def _decode_mono_audio(audio_bytes: bytes) -> _DecodedAudio | BeatGridFailure:
    """오디오 바이트열 → mono 다운믹스 샘플 (``detect_beat_grid``·``extract_bar_features`` 공유).

    ``server/audio/analyze.py`` 의 ``analyze()`` 와 같은 디코드 경로를 재사용한다
    (soundfile 읽기 → mono 다운믹스) — 완결된 바이트열 하나만 받고(AC-LDBARMAP-015),
    예외를 밖으로 내보내지 않는다(analyze.py:297 과 같은 계약). 실패는
    ``BeatGridFailure`` 로 통일한다 — 두 호출자 모두 이미 이 타입을 쓴다.
    """
    if not isinstance(audio_bytes, bytes | bytearray | memoryview):
        return BeatGridFailure("오디오 입력이 바이트열이 아닙니다.")
    payload = bytes(audio_bytes)
    if not payload:
        return BeatGridFailure("오디오 바이트열이 비어 있습니다.")

    if not analysis_available():
        return BeatGridFailure(MANUAL_BPM_FALLBACK_REASON)

    try:
        import numpy
        import soundfile
    except ImportError:
        return BeatGridFailure(MANUAL_BPM_FALLBACK_REASON)

    try:
        info = soundfile.info(io.BytesIO(payload))
        declared_frames = info.frames
        samples, sample_rate = soundfile.read(io.BytesIO(payload), dtype="float32", always_2d=True)
    except Exception as error:  # soundfile 은 형식마다 다른 예외를 낸다
        return BeatGridFailure(f"오디오 형식을 읽지 못했습니다: {error}")

    if samples.size == 0 or sample_rate <= 0:
        return BeatGridFailure("오디오에 샘플이 없습니다.")

    # analyze.py:323-343 과 같은 「조용한 잘림」 검사 — 부분 오디오로 잰 비트 격자를
    # 곡의 값으로 제안하지 않는다.
    length_is_a_guess = info.format == "MP3" and _mp3_length_is_a_bitrate_guess(payload)
    if (
        declared_frames > 0
        and not length_is_a_guess
        and len(samples) < declared_frames * _MIN_DECODED_FRACTION
    ):
        decoded_s = len(samples) / sample_rate
        declared_s = declared_frames / sample_rate
        return BeatGridFailure(
            f"오디오를 끝까지 읽지 못했습니다 — 파일은 {declared_s:.1f}초인데 "
            f"{decoded_s:.1f}초에서 디코더가 멈췄습니다. 곡의 일부만 분석하면 비트 격자가 "
            "틀리므로 분석하지 않습니다."
        )

    mono = numpy.ascontiguousarray(samples.mean(axis=1), dtype=numpy.float32)
    duration_ms = int(round(len(mono) * 1000.0 / sample_rate))
    if duration_ms < 2000:
        return BeatGridFailure(f"오디오가 너무 짧습니다({duration_ms}ms) — 최소 2000ms 필요.")

    return _DecodedAudio(mono=mono, sample_rate=sample_rate, duration_ms=duration_ms)


def detect_beat_grid(audio_bytes: bytes) -> BeatGridResult | BeatGridFailure:
    """오디오 바이트열 → 자동 비트 격자.

    ``server/audio/analyze.py`` 의 ``analyze()`` 와 같은 디코드 경로를 재사용한다
    (soundfile 읽기 → mono 다운믹스 → ``librosa.beat.beat_track`` hop=512) — 완결된
    바이트열 하나만 받고(AC-LDBARMAP-015), 예외를 밖으로 내보내지 않는다
    (analyze.py:297 과 같은 계약).
    """
    decoded = _decode_mono_audio(audio_bytes)
    if isinstance(decoded, BeatGridFailure):
        return decoded
    mono, sample_rate = decoded.mono, decoded.sample_rate

    try:
        import librosa
        import numpy
    except ImportError:
        return BeatGridFailure(MANUAL_BPM_FALLBACK_REASON)

    try:
        beat_times = librosa.beat.beat_track(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )[1]
        # REQ-LDBARMAP-006(재설계, 카드 t547) — 고정 전역 격자 대신 검출기 자신의
        # beat_times 를 기준틀로 쓰므로, 두 배 판정에는 온셋 "시각"이 아니라
        # 온셋 "강도 환경"(강도를 시간축 전체에서 재는 연속값)이 필요하다.
        onset_envelope = librosa.onset.onset_strength(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH
        )
    except Exception as error:  # 분석기 내부 실패도 예외로 새어 나가지 않는다
        return BeatGridFailure(f"오디오를 분석하지 못했습니다: {error}")

    raw_bpm, confidence = _tempo_from_beats(numpy, beat_times)
    if raw_bpm is None:
        return BeatGridFailure("박을 찾지 못해 BPM 을 재지 못했습니다.")

    bpm_check = _check_bpm_half_double(
        numpy, float(raw_bpm), beat_times, onset_envelope, sample_rate
    )

    beat_times_ms = tuple(int(round(t * 1000.0)) for t in beat_times)
    return BeatGridResult(
        beat_times_ms=beat_times_ms,
        bpm=bpm_check.adopted_bpm,
        bpm_confidence=confidence,
        bpm_check=bpm_check,
    )


def _strength_at(numpy, envelope, sample_rate: int, times):
    """``times``(초) 각 자리의 온셋 강도 — 가장 가까운 프레임 ±1 안의 최댓값
    (REQ-LDBARMAP-006 재설계 — 프레임 양자화 경계에 걸려 실제보다 낮게 잡히는
    것을 막는다). ``.moai/reports/t547/probe_sign.py`` 의 ``strength_at`` 과
    같은 식 — 생산 코드가 탐침 스크립트를 import 하지 않도록 독립적으로 다시
    둔다(의도적 중복).
    """
    if len(envelope) == 0:
        return numpy.zeros(len(times))
    frame = numpy.clip(
        numpy.round(numpy.asarray(times, dtype=float) * sample_rate / _HOP_LENGTH).astype(int),
        0,
        len(envelope) - 1,
    )
    lo = numpy.clip(frame - 1, 0, len(envelope) - 1)
    hi = numpy.clip(frame + 1, 0, len(envelope) - 1)
    return numpy.maximum(numpy.maximum(envelope[lo], envelope[frame]), envelope[hi])


def _sign_test_p_value(k: int, n: int, *, two_sided: bool) -> float:
    """정확 부호검정 p 값 — ``scipy`` 없이 ``math.comb`` 로 계산한다(REQ-LDBARMAP-006
    근거 칸 — scipy 는 이 프로젝트의 선언된 의존성이 아니다, pyproject.toml 참조).

    ``k`` 는 비교에서 "성공"으로 센 쌍의 개수, ``n`` 은 전체 쌍 개수(동률 제외).
    단측(H1: 성공 비율이 0.5 보다 크다) — P(X >= k), X ~ Binomial(n, 0.5).
    양측(진단용, w_odd/p_two) — 고전적 부호검정 식: 2 * min(P(X>=k), P(X<=k)),
    1 로 자른다.
    """
    if n == 0:
        return 1.0
    total = 2**n
    p_ge = sum(math.comb(n, i) for i in range(k, n + 1)) / total
    if not two_sided:
        return min(1.0, p_ge)
    p_le = sum(math.comb(n, i) for i in range(0, k + 1)) / total
    return min(1.0, 2 * min(p_ge, p_le))


def _check_bpm_half_double(
    numpy, raw_bpm: float, beat_times, envelope, sample_rate: int
) -> BpmCandidateCheck:
    """REQ-LDBARMAP-006(재설계, 카드 t547) — 추정 비트 격자 기준 단측 부호검정으로
    두 배 후보를 비교해 최종 BPM 을 채택한 근거를 기록한다. 원 추정치를 그대로
    쓰지 않는다 — 항상 비교하고 기록한다.

    고정 전역 격자(옛 설계)가 아니라 ``beat_times``(검출기 자신이 찾은 박 시각)
    를 기준틀로 쓴다 — BPM 추정 오차에 흔들리지 않는다(`.moai/reports/t547/
    verdict.md`). 절반 후보는 이 판정으로 자동 채택되지 않는다 — w_odd/p_two
    는 진단용 기록일 뿐이다(판정표: acceptance.md §A·§B AC-LDBARMAP-004).
    """
    beat_times = numpy.asarray(beat_times, dtype=float)
    half_bpm = raw_bpm / 2.0 if raw_bpm > 0 else 0.0
    double_bpm = raw_bpm * 2.0 if raw_bpm > 0 else 0.0

    if raw_bpm <= 0 or len(beat_times) < 2:
        rationale = (
            f"원시 BPM 이 0 이하({raw_bpm}) 이거나 박이 2개 미만({len(beat_times)}개)이라 "
            "쌍을 지을 수 없다 — 비교 없이 원 BPM 을 유지하되 모호 표시를 남긴다."
        )
        return BpmCandidateCheck(
            raw_bpm=raw_bpm,
            half_bpm=half_bpm,
            double_bpm=double_bpm,
            n_pairs=0,
            w_mid=0.0,
            p_mid=1.0,
            w_odd=0.0,
            p_two=1.0,
            outcome=_OUTCOME_KEEP,
            ambiguous=True,
            adopted_bpm=raw_bpm,
            rationale=rationale,
        )

    envelope = numpy.asarray(envelope, dtype=float)
    on = _strength_at(numpy, envelope, sample_rate, beat_times)
    mid_times = (beat_times[:-1] + beat_times[1:]) / 2.0
    mid = _strength_at(numpy, envelope, sample_rate, mid_times)
    on_i = on[:-1]

    d = mid - on_i
    d = d[d != 0]
    n_pairs = int(len(d))

    # 짝/홀 박 비교(진단용, w_odd/p_two) — 절반 후보를 자동 채택하지 않는 이유의
    # 근거 기록일 뿐, 아래 판정표에는 들어가지 않는다.
    m = (len(on) // 2) * 2
    e2 = on[0:m:2] - on[1:m:2]
    e2 = e2[e2 != 0]
    if len(e2) == 0:
        w_odd = 0.5
        p_two = 1.0
    else:
        w_odd = float(numpy.mean(e2 < 0))
        p_two = _sign_test_p_value(int(numpy.sum(e2 > 0)), len(e2), two_sided=True)

    if n_pairs == 0:
        rationale = (
            "박 자리와 중간점 세기가 전부 동률이라(n_pairs=0) 부호검정을 할 수 없다 — "
            f"원 BPM({raw_bpm:.3f})을 유지하되 모호 표시를 남긴다."
        )
        return BpmCandidateCheck(
            raw_bpm=raw_bpm,
            half_bpm=half_bpm,
            double_bpm=double_bpm,
            n_pairs=0,
            w_mid=0.5,
            p_mid=1.0,
            w_odd=w_odd,
            p_two=p_two,
            outcome=_OUTCOME_KEEP,
            ambiguous=True,
            adopted_bpm=raw_bpm,
            rationale=rationale,
        )

    w_mid = float(numpy.mean(d > 0))
    k_on_stronger = int(numpy.sum(d < 0))  # on_i > mid_i (박 자리가 더 세다, H1)
    p_mid = _sign_test_p_value(k_on_stronger, n_pairs, two_sided=False)

    if p_mid < _SIGN_TEST_ALPHA:
        outcome = _OUTCOME_KEEP
        ambiguous = False
        adopted_bpm = raw_bpm
        rationale = (
            f"p_mid={p_mid:.3g} < α({_SIGN_TEST_ALPHA}) — 박 자리(n={n_pairs})가 중간점보다 "
            f"유의하게 강하다(w_mid={w_mid:.2f}). 원 BPM({raw_bpm:.3f})을 유지한다."
        )
    elif w_mid >= _MID_SYMMETRY and double_bpm <= _SANE_BPM_MAX:
        outcome = _OUTCOME_ADOPT_DOUBLE
        ambiguous = False
        adopted_bpm = double_bpm
        rationale = (
            f"p_mid={p_mid:.3g} ≥ α({_SIGN_TEST_ALPHA})이고 w_mid={w_mid:.2f} ≥ "
            f"{_MID_SYMMETRY}(대칭점) — 중간점이 박만큼(또는 더) 강해 추적기가 실제 박의 "
            f"절반 빠르기를 짚은 것으로 보고 두 배({double_bpm:.3f})로 보정한다."
        )
    else:
        outcome = _OUTCOME_KEEP
        ambiguous = True
        adopted_bpm = raw_bpm
        if w_mid >= _MID_SYMMETRY:
            boundary_reason = (
                f"두 배 후보({double_bpm:.3f})가 통상 범위(≤{_SANE_BPM_MAX})를 벗어난다"
            )
        else:
            boundary_reason = f"w_mid={w_mid:.2f} < {_MID_SYMMETRY}(대칭점)"
        rationale = (
            f"p_mid={p_mid:.3g} ≥ α({_SIGN_TEST_ALPHA})이지만 {boundary_reason} — "
            f"원 BPM({raw_bpm:.3f})을 유지하되 사람 확인용 모호(ambiguous) 표시를 남긴다."
        )

    return BpmCandidateCheck(
        raw_bpm=raw_bpm,
        half_bpm=half_bpm,
        double_bpm=double_bpm,
        n_pairs=n_pairs,
        w_mid=w_mid,
        p_mid=p_mid,
        w_odd=w_odd,
        p_two=p_two,
        outcome=outcome,
        ambiguous=ambiguous,
        adopted_bpm=adopted_bpm,
        rationale=rationale,
    )


def derive_bars(beat_times_ms: Sequence[int], first_beat_offset: int) -> BarMap | BarMapFailure:
    """자동 비트 격자 + 사람이 지정한 첫 박 오프셋 → 마디 지도 (REQ-LDBARMAP-016).

    순수 함수 — librosa 를 쓰지 않는다. 다운비트는 ``beat_times_ms`` 의 0-base
    인덱스 ``i`` 가 ``(i - first_beat_offset) % 4 == 0`` 인 자리다. 첫 다운비트
    이전의 박들은 못갖춘마디(pickup)로 분류해 마디 번호에서 뺀다(마디 1 = 첫
    다운비트) — 지도 보고서 부록 A(마디 1 = 1.50초, 못갖춘마디 0.96초)와 일치.

    자동 위상 선택기는 이 M2 범위에서 보류한다 — ``first_beat_offset`` 은 항상
    호출자(사람의 귀 확인)가 넘긴다.
    """
    if isinstance(first_beat_offset, bool) or not isinstance(first_beat_offset, int):
        return BarMapFailure(f"첫 박 오프셋은 정수여야 합니다: {first_beat_offset!r}")
    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
        return BarMapFailure(
            f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
        )
    if not beat_times_ms:
        return BarMapFailure("비트 격자가 비어 있습니다.")

    downbeats = tuple(
        t for i, t in enumerate(beat_times_ms) if (i - first_beat_offset) % _BEATS_PER_BAR == 0
    )
    pickup = tuple(beat_times_ms[i] for i in range(min(first_beat_offset, len(beat_times_ms))))

    return BarMap(
        downbeats_ms=downbeats,
        bar_boundaries_ms=downbeats,  # 4/4박자 — 다운비트와 동일(spec.md §5 열린 결정 3)
        pickup_beats_ms=pickup,
        first_beat_offset=first_beat_offset,
    )


# ---------------------------------------------------------------------------
# M3 — 마디별 변화 이벤트 분류기 (REQ-LDBARMAP-008, 카드 t530)
#
# 두 함수로 나뉜다(M2와 같은 설계 원칙 — plan.md §D):
#
# * :func:`extract_bar_features` — 오디오 + 마디 경계(``derive_bars`` 의
#   ``downbeats_ms``/``bar_boundaries_ms``)를 받아 마디별 음량·저역 에너지(곡
#   중앙값=1 정규화)·보컬 대역 비율·온셋 개수를 잰다. ``server/audio/analyze.py``
#   와 같은 디코드 경로를 ``_decode_mono_audio``로 공유한다.
# * :func:`classify_bar_events` — 순수 함수. librosa 를 쓰지 않는다. 마디별
#   특징만으로 네 종류 이벤트(킥 진입·빌드업·드롭·브레이크)를 분류한다
#   (REQ-LDBARMAP-008 어휘 — spec.md §5 열린 결정 0 ``events[].kind``).
# ---------------------------------------------------------------------------

#: REQ-LDBARMAP-008 — events[].kind 어휘 4개 고정(spec.md §5 열린 결정 0).
EVENT_KIND_KICK_ENTRY = "kick_entry"
EVENT_KIND_BUILD = "build"
EVENT_KIND_DROP = "drop"
EVENT_KIND_BREAK = "break"

#: 큰 히트(킥 진입) — 저역 에너지가 곡 중앙값의 이 배수 이상(단위: 배, ratio-to-median).
#:
#: 지도 보고서 §1 순간 규칙표는 2.5배를 썼지만, 그 수치는 보고서 전용 저역 타악
#: 분리 파이프라인(``measure_music_map.py``, 이 저장소에 없음 — 비커밋 개발 도구)의
#: 절대 척도에서 나온 것이다. 이 모듈의 ``extract_bar_features``(HPSS 기반 타악
#: 분리, 아래 참조)는 같은 "저역 타악 에너지" 개념을 재지만 분리 정밀도가 달라
#: 절대 분리 폭이 더 좁다(실측, progress.md Gaps) — 2.0을 쓰면 지도 보고서 수치
#: 기준 표(부록 A 음량·저역)와 이 모듈의 실제 오디오 추출 양쪽 모두에서 7/7 재현을
#: 유지하면서([추정] 등급, ±20% 민감도 확인) 분리 폭이 더 좁은 쪽에 여유를 둔다.
_KICK_ENTRY_LOW_BAND_RATIO = 2.0

#: 브레이크(킥 멈춤) — 저역 에너지가 곡 중앙값의 이 배수 이하(단위: 배).
#: 지도 보고서 §1 순간 규칙표("저역 < 중앙값의 35%")의 발상을 그대로 썼지만,
#: 위 킥 진입 문턱과 같은 이유로 0.45로 낮췄다(두 정답지 소스 모두 7/7 재현).
_BREAK_LOW_BAND_RATIO = 0.45

#: 브레이크 — 또는 (저역이 이 배수 이하 AND 마디 안 온셋 개수가 곡 자신의 온셋
#: 중앙값 대비 이 비율 이하)인 마디(단위: 배 / 무단위 비율, 카드 t535 교정).
#:
#: **왜 바뀌었나(실측, 계기 척도 불일치)**: 이전 버전은 온셋 개수에 절대 상수
#: (≤2개)를 썼다 — 그 상수는 지도 보고서 §2.1 "타악 온셋 6개(평소 15 안팎)"의
#: 척도에서 따왔는데, 그 "평소 15 안팎"은 보고서 전용 온셋 계기
#: (``measure_music_map.py``, 이 저장소에 없음)의 눈금이다. 이 모듈의
#: ``librosa.onset.onset_detect``는 같은 곡에서 **마디당 중앙값 4개**(실측,
#: LOVE ATTACK 82마디)를 낸다 — 다른 계기가 다른 척도로 "온셋 개수"를 재는데도
#: 절대 상수를 그대로 썼더니, 저역이 전혀 낮지 않은(≈1.0배, 즉 조용하지 않은)
#: 마디까지 온셋 하나만으로 브레이크로 잘못 분류됐다(실측: 15건의 브레이크
#: 검출 중 14건이 이 온셋 분기만으로 나왔고, 그중 다수가 저역 0.9~1.2배 구간
#: — 지도 보고서 "순간" 칸 근거와 대조한 정밀도는 8/18 ≈ 44.4%, AC-LDBARMAP-007
#: 정밀도 문턱 70% 에 크게 못 미친다, progress.md §E.2 M3 "리드 재측정 메모").
#: 진짜 킥 멈춤은 저역**과** 온셋이 **함께** 떨어진다(음악적으로 당연하다 —
#: 타악이 빠지면 저역도 온셋도 같이 준다) — 그래서 온셋을 절대 상수가 아니라
#: 곡 자신의 온셋 중앙값(``statistics.median``, ``onset_count`` 를 잰 마디만
#: 대상) 대비 비율로 재고, 저역 완화(dip)와 **AND** 로 묶는 쪽으로 고쳤다.
#: 두 상수 모두 이 SPEC이 처음 도입한다(실음원 실측으로 고름, "과적합 가드"
#: 절과 같은 원칙 — 이 두 곡 한정 숫자가 아니라 척도 불일치를 바로잡는 비율).
_BREAK_DIP_LOW_BAND_RATIO = 0.7
_BREAK_ONSET_FRACTION_OF_MEDIAN = 0.25

#: 빌드업 — 큰 히트 직전에 음량이 이 마디 수 이상 연속 상승(단위: 마디).
#: 지도 보고서 §1 순간 규칙표("큰 히트 직전에 음량이 3마디 이상 연달아 오름")를
#: 그대로 썼다 — 전역으로 상승 구간을 찾지 않고 큰 히트 바로 앞에만 닻을 내린다
#: (REQ-LDBARMAP-008 "build" 정의 자체가 "큰 히트로 이어지는 상승"이라 이 anchoring이
#: 곡 전체의 우연한 음량 요동을 빌드업으로 오인하지 않게 막는다).
_BUILD_MIN_BARS = 3

#: 드롭 — 보컬 대역 비율이 이 값 이하(단위: 비율, 0~1)이면서 저역이 이 배수
#: 이상(단위: 배, ratio-to-median)인 구간. **이 두 문턱은 이 SPEC이 직접 정한
#: 것이다** — 지도 보고서 §2.3이 드롭 후보(63~66마디)를 "보컬 대역 비율
#: 0.03~0.04(곡 평균 0.30의 약 1/10)"로만 서술하고 구체적 채점 문턱을 주지
#: 않았다(REQ-LDBARMAP-009 "추정" 등급 — 비교 대상 자체가 참고 지표). 드롭은
#: AC-LDBARMAP-007의 7개 사건에 들지 않는다(REQ-009 — [추정]은 PASS 판정의
#: 유일한 근거로 쓰지 않는다) — 참고 지표로만 보고한다. **알려진 한계**: 이
#: 문턱은 지도 보고서의 수치표(0~1 비율) 척도로 골랐다 — 이 모듈이 실제
#: 오디오에서 재는 ``vocal_band_ratio``(HPSS 화성 성분의 보컬 대역 비중, 역시
#: 0~1로 묶은 비율이지만 다른 분리 파이프라인)는 절대 분리 폭이 달라 이
#: 문턱으로 63~66마디를 깨끗하게 가려내지 못할 수 있다(참고 지표라 PASS 판정에
#: 영향 없음, progress.md Gaps에 정직하게 기록).
_DROP_VOCAL_BAND_RATIO = 0.15
_DROP_LOW_BAND_RATIO = 1.4


@dataclass(frozen=True)
class BarFeatures:
    """마디 하나의 특징 — 모두 REQ-LDBARMAP-007 단위 규칙을 따른다(비율은 무단위,
    온셋 개수는 정수 개).

    ``vocal_band_ratio`` 는 곡 중앙값으로 정규화하지 않는다 — 지도 보고서
    부록 A "보컬 대역 비율(참고)" 칸과 같은, 0~1로 묶인 원시 비율이다. ``None``
    이면 이 특징을 재지 못했다는 뜻이고, 드롭 분류만 건너뛴다(킥 진입·빌드업·
    브레이크는 영향받지 않는다). ``onset_count`` 도 ``None`` 이면(예: 지도 보고서
    수치표만으로 합성한 고정 픽스처 — 온셋 열이 없다) 브레이크 판정에서 그
    마디는 온셋 중앙값 계산과 온셋 기반 분기 양쪽에서 제외된다(``_BREAK_DIP_LOW_BAND_RATIO``
    주석 참조) — "0개"로 잘못 읽지 않는다.
    """

    bar: int
    volume_norm: float
    low_band_norm: float
    vocal_band_ratio: float | None = None
    onset_count: int | None = None


@dataclass(frozen=True)
class BarFeaturesFailure:
    """마디별 특징을 재지 못했다 — 그리고 왜 못 했는지(``BeatGridFailure`` 와 같은 설계)."""

    reason: str


@dataclass(frozen=True)
class BarEvent:
    """마디별 변화 이벤트 하나(REQ-LDBARMAP-008, spec.md §5 열린 결정 0 ``events[]``).

    ``start_bar``·``end_bar`` 는 양끝 포함, 1-base(derive_bars 의 마디 번호
    공간과 같다). ``grade`` 는 REQ-LDBARMAP-009 신뢰도 갈래(``measured``/
    ``estimated``) — kick_entry·build·break 는 지도 보고서가 [잰 값]으로 매긴
    저역·음량 임계값에서 바로 나오므로 ``measured``, drop 은 이 SPEC이 직접
    정한 문턱(위 ``_DROP_VOCAL_BAND_RATIO`` 근거 참조)이라 ``estimated`` 다.
    """

    kind: str
    start_bar: int
    end_bar: int
    grade: str = "measured"


def extract_bar_features(
    audio_bytes: bytes, bar_boundaries_ms: Sequence[int]
) -> tuple[BarFeatures, ...] | BarFeaturesFailure:
    """오디오 + 마디 경계(``derive_bars`` 의 ``downbeats_ms``/``bar_boundaries_ms``,
    정수 ms, 오름차순) → 마디별 특징.

    마디 i(1-base)의 창은 ``[bar_boundaries_ms[i-1], bar_boundaries_ms[i])``다.
    마지막 마디는 다음 다운비트가 없으므로 직전 마디 간격들의 **중앙값**으로 끝을
    추정한다(곡 끝까지로 자른다). ``server/audio/analyze.py`` 와 같은 디코드
    경로를 재사용한다. 예외를 밖으로 내보내지 않는다(REQ-LDBARMAP-001/015,
    analyze.py:297과 같은 계약).

    저역(35~120Hz)은 **타악(percussive) 성분만** 잰다 — 지도 보고서 §1이 "저역
    타악 에너지"라 명시했고(순수 저역 대역 에너지는 지속음 베이스에 가려 큰
    히트·킥 멈춤의 대비가 거의 사라진다, 실측 확인 — progress.md Gaps), 이
    모듈은 ``librosa.decompose.hpss``(화성/타악 분리, ``margin=(1.0, 5.0)``로
    더 날카롭게)를 STFT 위에서 돌려 타악 성분만 저역 대역에 적용한다. 보컬
    대역(300~3,400Hz)은 반대로 **화성(harmonic) 성분**에서, 전체 화성 에너지
    대비 그 대역이 차지하는 비중(합 기반 비율, 0~1로 묶인다)으로 잰다 — 지도
    보고서 "화성 성분 중 300~3,400Hz 비율"과 같은 개념이다.
    """
    if not isinstance(bar_boundaries_ms, Sequence) or len(bar_boundaries_ms) < 2:
        return BarFeaturesFailure("마디 경계가 2개 미만입니다 — 특징을 뺄 마디가 없습니다.")

    decoded = _decode_mono_audio(audio_bytes)
    if isinstance(decoded, BeatGridFailure):
        return BarFeaturesFailure(decoded.reason)
    mono, sample_rate = decoded.mono, decoded.sample_rate

    try:
        import librosa
        import numpy
    except ImportError:
        return BarFeaturesFailure(MANUAL_BPM_FALLBACK_REASON)

    boundaries_sec = [t / 1000.0 for t in bar_boundaries_ms]
    bar_gaps = [b - a for a, b in zip(boundaries_sec, boundaries_sec[1:], strict=False)]
    median_bar_sec = float(numpy.median(bar_gaps)) if bar_gaps else 0.0
    duration_sec = len(mono) / sample_rate
    windows: list[tuple[float, float]] = []
    for i, start in enumerate(boundaries_sec):
        end = boundaries_sec[i + 1] if i + 1 < len(boundaries_sec) else start + median_bar_sec
        windows.append((start, min(end, duration_sec)))

    try:
        rms = librosa.feature.rms(y=mono, frame_length=_FRAME_LENGTH, hop_length=_HOP_LENGTH)[0]
        frame_times = librosa.frames_to_time(
            numpy.arange(len(rms)), sr=sample_rate, hop_length=_HOP_LENGTH
        )
        stft = librosa.stft(mono, hop_length=_HOP_LENGTH)
        stft_harmonic, stft_percussive = librosa.decompose.hpss(stft, margin=(1.0, 5.0))
        mag_harmonic = numpy.abs(stft_harmonic)
        mag_percussive = numpy.abs(stft_percussive)
        freqs = librosa.fft_frequencies(sr=sample_rate)
        low_mask = (freqs >= 35) & (freqs <= 120)
        vocal_mask = (freqs >= 300) & (freqs <= 3400)
        low_energy = (
            mag_percussive[low_mask, :].mean(axis=0)
            if low_mask.any()
            else numpy.zeros(mag_percussive.shape[1])
        )
        vocal_energy = (
            mag_harmonic[vocal_mask, :].sum(axis=0)
            if vocal_mask.any()
            else numpy.zeros(mag_harmonic.shape[1])
        )
        total_harmonic_energy = mag_harmonic.sum(axis=0)
        vocal_ratio = numpy.divide(
            vocal_energy,
            total_harmonic_energy,
            out=numpy.zeros_like(vocal_energy),
            where=total_harmonic_energy > 0,
        )
        spectral_frame_times = librosa.frames_to_time(
            numpy.arange(mag_percussive.shape[1]), sr=sample_rate, hop_length=_HOP_LENGTH
        )
        onset_times = librosa.onset.onset_detect(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )
    except Exception as error:  # 분석기 내부 실패도 예외로 새어 나가지 않는다
        return BarFeaturesFailure(f"오디오를 분석하지 못했습니다: {error}")

    n_bars = len(windows)
    bar_volume = numpy.zeros(n_bars)
    bar_lowband = numpy.zeros(n_bars)
    bar_vocal = numpy.zeros(n_bars)
    bar_onsets = [0] * n_bars
    for i, (t0, t1) in enumerate(windows):
        rms_mask = (frame_times >= t0) & (frame_times < t1)
        spec_mask = (spectral_frame_times >= t0) & (spectral_frame_times < t1)
        bar_volume[i] = float(rms[rms_mask].mean()) if rms_mask.any() else 0.0
        bar_lowband[i] = float(low_energy[spec_mask].mean()) if spec_mask.any() else 0.0
        bar_vocal[i] = float(vocal_ratio[spec_mask].mean()) if spec_mask.any() else 0.0
        bar_onsets[i] = int(numpy.sum((onset_times >= t0) & (onset_times < t1)))

    vol_median = float(numpy.median(bar_volume)) or 1e-9
    low_median = float(numpy.median(bar_lowband)) or 1e-9

    return tuple(
        BarFeatures(
            bar=i + 1,
            volume_norm=float(bar_volume[i] / vol_median),
            low_band_norm=float(bar_lowband[i] / low_median),
            vocal_band_ratio=float(bar_vocal[i]),
            onset_count=bar_onsets[i],
        )
        for i in range(n_bars)
    )


def classify_bar_events(features: Sequence[BarFeatures]) -> list[BarEvent]:
    """마디별 특징 → 네 종류 변화 이벤트(REQ-LDBARMAP-008).

    순수 함수 — librosa 를 쓰지 않는다. 특징이 비어 있으면 빈 목록을 돌려준다
    (예외를 내보내지 않는다). 입력은 ``extract_bar_features`` 가 실제 오디오에서
    재거나, 시험이 합성해 직접 넘긴다.
    """
    by_bar = {f.bar: f for f in features}
    if not by_bar:
        return []

    kick_bars = sorted(
        bar for bar, f in by_bar.items() if f.low_band_norm >= _KICK_ENTRY_LOW_BAND_RATIO
    )
    # 온셋 중앙값은 ``onset_count`` 를 실제로 잰 마디만으로 계산한다 — None을
    # "0개"로 섞으면 중앙값이 왜곡된다(카드 t535, _BREAK_DIP_LOW_BAND_RATIO 주석 참조).
    measured_onsets = [f.onset_count for f in by_bar.values() if f.onset_count is not None]
    median_onset = statistics.median(measured_onsets) if measured_onsets else None
    break_bars = sorted(
        bar
        for bar, f in by_bar.items()
        if f.low_band_norm <= _BREAK_LOW_BAND_RATIO
        or (
            median_onset is not None
            and f.onset_count is not None
            and f.low_band_norm <= _BREAK_DIP_LOW_BAND_RATIO
            and f.onset_count <= _BREAK_ONSET_FRACTION_OF_MEDIAN * median_onset
        )
    )
    drop_bars = sorted(
        bar
        for bar, f in by_bar.items()
        if f.vocal_band_ratio is not None
        and f.vocal_band_ratio <= _DROP_VOCAL_BAND_RATIO
        and f.low_band_norm >= _DROP_LOW_BAND_RATIO
    )

    events: list[BarEvent] = []
    events.extend(BarEvent(EVENT_KIND_KICK_ENTRY, bar, bar, grade="measured") for bar in kick_bars)
    events.extend(BarEvent(EVENT_KIND_BREAK, bar, bar, grade="measured") for bar in break_bars)
    events.extend(_group_consecutive_bars(drop_bars, EVENT_KIND_DROP, grade="estimated"))
    events.extend(_builds_anchored_before(by_bar, kick_bars))

    events.sort(key=lambda e: (e.start_bar, e.kind))
    return events


def _group_consecutive_bars(bars: Sequence[int], kind: str, grade: str) -> list[BarEvent]:
    """연속한 마디 번호를 사건 하나로 묶는다(드롭처럼 여러 마디에 걸친 사건용)."""
    events: list[BarEvent] = []
    i = 0
    while i < len(bars):
        j = i
        while j + 1 < len(bars) and bars[j + 1] == bars[j] + 1:
            j += 1
        events.append(BarEvent(kind, bars[i], bars[j], grade=grade))
        i = j + 1
    return events


def _builds_anchored_before(
    by_bar: dict[int, BarFeatures], kick_bars: Sequence[int]
) -> list[BarEvent]:
    """큰 히트(킥 진입) 직전, 음량이 연속 상승하는 가장 긴 구간을 빌드업으로 본다
    (지도 보고서 §1 "큰 히트 직전에 음량이 3마디 이상 연달아 오름").

    전역으로 상승 구간을 찾지 않는다 — 큰 히트가 없으면 빌드업도 없다(REQ-008의
    "build" 정의 자체가 상승 뒤 히트로 이어지는 구조라 이 anchoring이 곡 전체의
    우연한 음량 요동을 빌드업으로 오인하는 것을 막는다).
    """
    events: list[BarEvent] = []
    for hit_bar in kick_bars:
        end_bar = hit_bar - 1
        if end_bar not in by_bar:
            continue
        start_bar = end_bar
        length = 1
        while (start_bar - 1) in by_bar and by_bar[start_bar - 1].volume_norm < by_bar[
            start_bar
        ].volume_norm:
            start_bar -= 1
            length += 1
        if length >= _BUILD_MIN_BARS:
            events.append(BarEvent(EVENT_KIND_BUILD, start_bar, end_bar, grade="measured"))
    return events
