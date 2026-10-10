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
from collections.abc import Sequence
from dataclasses import dataclass

from server.audio.analyze import (
    _HOP_LENGTH,
    _MIN_DECODED_FRACTION,
    MANUAL_BPM_FALLBACK_REASON,
    _mp3_length_is_a_bitrate_guess,
    _tempo_from_beats,
    analysis_available,
)

__all__ = [
    "BarMap",
    "BarMapFailure",
    "BeatGridFailure",
    "BeatGridResult",
    "BpmCandidateCheck",
    "derive_bars",
    "detect_beat_grid",
]

#: 한 마디(4/4박자)의 박 수. REQ-LDBARMAP-016 — 오프셋은 이 값의 나머지다.
_BEATS_PER_BAR = 4

#: REQ-LDBARMAP-006 — 절반/두 배 후보의 격자 정합도 비교 문턱.
#:
#: 생산 코드(이 모듈)는 M1 보정 스크립트(``tools/barmap/scorer.py``)와 달리 목표
#: BPM 을 미리 알지 못한다 — 그래서 고정 함정 상수(M1 의 56.175/224.69, LOVE ATTACK
#: 전용 값)에 기대지 않고, 원시 추정치 자신의 절반·두 배와 비교한다. 더 촘촘한
#: 격자(두 배)는 점(온셋) 밀도가 높아 정합도가 구조적으로 더 높게 나오는 경향이
#: 있으므로(지도 보고서 §1, `tools/barmap/scorer.py` `check_bpm_multiple` 의 동일
#: 경고) 두 배 채택 문턱을 절반 채택 문턱보다 높게 둔다.
_HALF_TRAP_MARGIN = 0.05
_DOUBLE_TRAP_MARGIN = 0.20

#: 통상적인 곡 템포 범위(BPM) — 이 범위 밖의 절반/두 배 후보는 비교에서 제외한다.
_SANE_BPM_MIN = 40.0
_SANE_BPM_MAX = 250.0


@dataclass(frozen=True)
class BpmCandidateCheck:
    """REQ-LDBARMAP-006 — 절반·두 배 후보 비교 근거 (기록용, 채택 여부와 무관하게 항상 채운다)."""

    raw_bpm: float
    half_bpm: float
    double_bpm: float
    grid_lock_raw: float
    grid_lock_half: float
    grid_lock_double: float
    trap_triggered: bool
    adopted_bpm: float
    rationale: str


@dataclass(frozen=True)
class BeatGridResult:
    """자동 검출에 성공한 비트 격자.

    ``beat_times_ms`` 는 ``detect_beat_grid`` 가 실제로 검출한 격자를 그대로
    담는다 — ``bpm_check`` 가 절반/두 배로 보정된 BPM 을 채택해도(``trap_triggered``),
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


def detect_beat_grid(audio_bytes: bytes) -> BeatGridResult | BeatGridFailure:
    """오디오 바이트열 → 자동 비트 격자.

    ``server/audio/analyze.py`` 의 ``analyze()`` 와 같은 디코드 경로를 재사용한다
    (soundfile 읽기 → mono 다운믹스 → ``librosa.beat.beat_track`` hop=512) — 완결된
    바이트열 하나만 받고(AC-LDBARMAP-015), 예외를 밖으로 내보내지 않는다
    (analyze.py:297 과 같은 계약).
    """
    if not isinstance(audio_bytes, bytes | bytearray | memoryview):
        return BeatGridFailure("오디오 입력이 바이트열이 아닙니다.")
    payload = bytes(audio_bytes)
    if not payload:
        return BeatGridFailure("오디오 바이트열이 비어 있습니다.")

    if not analysis_available():
        return BeatGridFailure(MANUAL_BPM_FALLBACK_REASON)

    try:
        import librosa
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

    try:
        beat_times = librosa.beat.beat_track(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )[1]
        onset_times = librosa.onset.onset_detect(
            y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
        )
    except Exception as error:  # 분석기 내부 실패도 예외로 새어 나가지 않는다
        return BeatGridFailure(f"오디오를 분석하지 못했습니다: {error}")

    raw_bpm, confidence = _tempo_from_beats(numpy, beat_times)
    if raw_bpm is None:
        return BeatGridFailure("박을 찾지 못해 BPM 을 재지 못했습니다.")

    bpm_check = _check_bpm_half_double(
        numpy, float(raw_bpm), numpy.asarray(onset_times, dtype=float)
    )

    beat_times_ms = tuple(int(round(t * 1000.0)) for t in beat_times)
    return BeatGridResult(
        beat_times_ms=beat_times_ms,
        bpm=bpm_check.adopted_bpm,
        bpm_confidence=confidence,
        bpm_check=bpm_check,
    )


def _grid_lock_ratio(numpy, onset_times, bpm: float, tol_frac: float = 0.125) -> float:
    """온셋이 주어진 BPM 격자에 얼마나 붙는지 — 위상(격자 시작 지점)에 유리하게
    가장 잘 맞는 위상에서의 적중 비율을 돌려준다.

    ``tools/barmap/scorer.py`` 의 ``grid_lock_ratio`` 와 같은 개념이다 — 생산 코드가
    개발 도구 모듈을 import 하지 않도록 여기서 독립적으로 다시 둔다(의도적 중복).
    """
    if len(onset_times) == 0 or bpm <= 0:
        return 0.0
    beat_sec = 60.0 / bpm
    tol_sec = beat_sec * tol_frac
    best_ratio = 0.0
    n_phase_steps = 20
    for step in range(n_phase_steps):
        phase_offset = (step / n_phase_steps) * beat_sec
        grid_positions = (onset_times - phase_offset) / beat_sec
        nearest_grid_time = numpy.round(grid_positions) * beat_sec + phase_offset
        distances = numpy.abs(onset_times - nearest_grid_time)
        ratio = float(numpy.mean(distances <= tol_sec))
        if ratio > best_ratio:
            best_ratio = ratio
    return best_ratio


def _check_bpm_half_double(numpy, raw_bpm: float, onset_times) -> BpmCandidateCheck:
    """REQ-LDBARMAP-006 — 절반·두 배 후보와 격자 정합도를 비교해 최종 BPM 을 채택한
    근거를 기록한다. 원 추정치를 그대로 쓰지 않는다 — 항상 비교하고 기록한다."""
    if raw_bpm <= 0:
        rationale = f"원시 BPM 이 0 이하({raw_bpm}) — 비교 없이 그대로 둔다."
        return BpmCandidateCheck(
            raw_bpm=raw_bpm,
            half_bpm=0.0,
            double_bpm=0.0,
            grid_lock_raw=0.0,
            grid_lock_half=0.0,
            grid_lock_double=0.0,
            trap_triggered=False,
            adopted_bpm=raw_bpm,
            rationale=rationale,
        )

    half_bpm = raw_bpm / 2.0
    double_bpm = raw_bpm * 2.0
    grid_lock_raw = _grid_lock_ratio(numpy, onset_times, raw_bpm)
    grid_lock_half = (
        _grid_lock_ratio(numpy, onset_times, half_bpm) if half_bpm >= _SANE_BPM_MIN else -1.0
    )
    grid_lock_double = (
        _grid_lock_ratio(numpy, onset_times, double_bpm) if double_bpm <= _SANE_BPM_MAX else -1.0
    )

    half_margin = grid_lock_half - grid_lock_raw
    double_margin = grid_lock_double - grid_lock_raw

    if half_margin >= _HALF_TRAP_MARGIN:
        adopted_bpm = half_bpm
        trap_triggered = True
        rationale = (
            f"원시 추정치({raw_bpm:.3f})의 절반({half_bpm:.3f})이 격자 정합도에서 "
            f"{half_margin:.2f} 더 높다(원시 {grid_lock_raw:.2f} vs 절반 {grid_lock_half:.2f}) "
            "— 원시 추정이 실제 박의 두 배 빠르기를 짚은 것으로 보고 절반으로 보정한다."
        )
    elif double_margin >= _DOUBLE_TRAP_MARGIN:
        adopted_bpm = double_bpm
        trap_triggered = True
        rationale = (
            f"원시 추정치({raw_bpm:.3f})의 두 배({double_bpm:.3f})가 격자 정합도에서 "
            f"{double_margin:.2f} 더 높다(원시 {grid_lock_raw:.2f} "
            f"vs 두 배 {grid_lock_double:.2f}). "
            "더 촘촘한 격자는 점 밀도 때문에 구조적으로 정합도가 높아지는 경향이 있어 "
            f"문턱을 절반({_HALF_TRAP_MARGIN})보다 높게({_DOUBLE_TRAP_MARGIN}) 두었다 — 그래도 "
            "그 문턱을 넘었으므로 원시 추정이 실제 박의 절반 빠르기를 짚은 것으로 보고 "
            "두 배로 보정한다."
        )
    else:
        adopted_bpm = raw_bpm
        trap_triggered = False
        rationale = (
            f"원시 추정치({raw_bpm:.3f})가 절반·두 배 후보보다 격자 정합도에서 뚜렷하게 "
            f"낮지 않다(원시 {grid_lock_raw:.2f} / 절반 {grid_lock_half:.2f} / "
            f"두 배 {grid_lock_double:.2f}) — 함정이 발동하지 않았으므로 보정 없이 그대로 쓴다."
        )

    return BpmCandidateCheck(
        raw_bpm=raw_bpm,
        half_bpm=half_bpm,
        double_bpm=double_bpm,
        grid_lock_raw=grid_lock_raw,
        grid_lock_half=grid_lock_half,
        grid_lock_double=grid_lock_double,
        trap_triggered=trap_triggered,
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
