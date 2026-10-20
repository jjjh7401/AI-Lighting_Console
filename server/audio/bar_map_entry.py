"""마디 지도 진입 경로 M1 — 오디오 바이트 + 첫 박 오프셋 → 마디 지도 (SPEC-LDBARMAP-002).

기존 분석 함수를 순서대로 잇는 순수 합성 단계 하나다(REQ-LDBARENTRY-006): 박 격자
검출 → 첫 박 오프셋을 적용한 마디 파생 → 마디별 특징 → 변화 사건 분류 → 저장용
사전. 세션·콘솔·UI 상태 없이 바이트와 오프셋만으로 돈다.

검증 규칙은 다시 구현하지 않는다 — 저장 모양의 정본은 ``build_bar_map_payload`` 가
스스로 부르는 ``validate_bar_map`` 이다. 이 모듈은 저장하지 않고, 세션을 읽지 않고,
콘솔에 닿지 않고, 응답을 보내지 않는다(저장 관문 호출과 응답 전송은 M2 의 몫).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from server.audio.analyze import _FRAME_LENGTH, _HOP_LENGTH, sections_from_rms
from server.audio.bar_map import (
    _OUTCOME_ADOPT_DOUBLE,
    BarEvent,
    BarFeatures,
    BarFeaturesFailure,
    BarMapFailure,
    BeatGridFailure,
    BeatGridResult,
    _decode_mono_audio,
    classify_bar_events,
    compute_bar_energy,
    derive_bars,
    detect_beat_grid,
    extend_beats_to_duration,
    extract_bar_features,
)
from server.audio.bar_map_store import BarMapStoreError, attach_rhythm, build_bar_map_payload
from server.audio.rhythm import build_rhythm

__all__ = [
    "KIND_FAILED",
    "KIND_REJECTED",
    "BarMapEntryFailure",
    "first_beat_offset_problem",
    "synthesize_bar_map",
]

#: 실패 종류 — 규칙이 요청이나 결과를 거절했다(첫 박 오프셋의 범위·형식 점검, 두 배 BPM
#: 채택 거절 — 결정 E1). 사유는 설계된 문장이라 화면에 그대로 보여 줘도 된다.
KIND_REJECTED = "rejected"

#: 실패 종류 — 분석 단계가 실패했다(검출·마디 파생·특징 추출·분류·빌더, 예기치 않은 예외).
#: 사유는 단계나 예외가 낸 원문이라 객체 주소 같은 내부 표현이 들 수 있어, 화면에 보여 주지
#: 않고 로그에만 남긴다.
KIND_FAILED = "failed"

#: 합성이 다루는 박자표 — 분석기(``derive_bars``)가 4/4 전용이다(REQ-LDBARENTRY-015,
#: 결정 D2). 박자표는 이 한 곳에서만 정한다.
_TIME_SIGNATURE = (4, 4)

#: 한 마디의 박 수(박자표 분자). 첫 박 오프셋 범위(0~분자-1)의 기준이다.
_BEATS_PER_BAR = _TIME_SIGNATURE[0]

_DetectStep = Callable[[bytes], BeatGridResult | BeatGridFailure]
_FeaturesStep = Callable[[bytes, Sequence[int]], tuple[BarFeatures, ...] | BarFeaturesFailure]
_ClassifyStep = Callable[[Sequence[BarFeatures]], Sequence[BarEvent]]


@dataclass(frozen=True)
class BarMapEntryFailure:
    """마디 지도를 합성하지 못했다 — 그리고 왜 못 했는지.

    단계별 실패 객체(``BeatGridFailure``·``BarMapFailure``·``BarFeaturesFailure``)와
    빌더의 ``BarMapStoreError`` 를 한 모양으로 모은다. 단계가 낸 사유 문자열은 바꾸지
    않고 그대로 싣는다 — 예외 문구를 끼운 사유도 정제하지 않는다(spec.md Gaps 7번, 미결).

    ``reason`` 은 로그에 남기는 원문이다. 화면에 무엇을 보여 줄지는 부르는 쪽이 ``kind`` 로
    정한다: :data:`KIND_REJECTED` 는 설계된 문장이라 그대로 보여 줘도 되고,
    :data:`KIND_FAILED`(기본값)는 원문에 객체 주소 같은 내부 표현이 들 수 있어 보여 주지 않는다.
    """

    reason: str
    kind: str = KIND_FAILED


def first_beat_offset_problem(first_beat_offset: object) -> str | None:
    """첫 박 오프셋을 쓸 수 없으면 그 사유 문장을, 쓸 수 있으면 ``None`` 을 돌려준다.

    싼 점검이라 오디오를 풀기 전에 부른다(REQ-LDBARENTRY-007). 세션이 base64 를 풀기 전에,
    합성이 박 격자 검출 전에 이 한 곳의 문장을 같이 쓴다. 문구는 ``derive_bars`` 를 따르되,
    정수가 아닐 때는 입력값을 싣지 않는다."""
    if isinstance(first_beat_offset, bool) or not isinstance(first_beat_offset, int):
        # 값을 싣지 않는다 — 임의 객체의 기본 repr 에는 객체 주소가 들어 화면 문구가 샌다.
        return "첫 박 오프셋은 정수여야 합니다."
    if not (0 <= first_beat_offset < _BEATS_PER_BAR):
        return f"첫 박 오프셋은 0~{_BEATS_PER_BAR - 1} 범위여야 합니다: {first_beat_offset}"
    return None


def synthesize_bar_map(
    audio_bytes: bytes,
    first_beat_offset: int,
    *,
    detect: _DetectStep | None = None,
    extract: _FeaturesStep | None = None,
    classify: _ClassifyStep | None = None,
) -> dict[str, Any] | BarMapEntryFailure:
    """오디오 바이트 + 첫 박 오프셋 → 저장용 마디 지도 사전, 또는 실패 객체.

    순서: 오프셋 점검(디코드 전) → ``detect_beat_grid`` → 두 배 BPM 채택이면 거절 →
    ``extend_beats_to_duration``(음원 끝까지 박 잇기) → ``derive_bars`` →
    ``extract_bar_features`` → ``classify_bar_events`` → ``build_bar_map_payload``.
    저장되는 ``bpm`` 은 검출기 값이다(결정 E4 (가)) — 세션의 BPM 확정값을 읽지 않는다.

    예외를 밖으로 내보내지 않는다 — 어떤 입력이든 사전이거나 :class:`BarMapEntryFailure`
    다(내보내면 ``to_thread`` 로 도는 작업이 조용히 죽어 응답이 없다).

    ``detect``·``extract``·``classify`` 는 시험이 단계를 바꿔 끼우는 자리다. ``None``
    이면 호출 시점에 이 모듈이 import 한 분석 함수를 쓴다(import 시점에 묶지 않는다).
    """
    detect_step = detect_beat_grid if detect is None else detect
    extract_step = extract_bar_features if extract is None else extract
    classify_step = classify_bar_events if classify is None else classify
    try:
        return _synthesize(audio_bytes, first_beat_offset, detect_step, extract_step, classify_step)
    except Exception as error:  # 분석 단계의 예기치 않은 예외도 실패 객체로 바꾼다
        # 예외 문구를 그대로 싣는다 — bar_map.py 의 기존 사유와 같은 방식(정제는 미결).
        return BarMapEntryFailure(
            f"마디 지도를 합성하지 못했습니다: {type(error).__name__}: {error}"
        )


def _synthesize(
    audio_bytes: bytes,
    first_beat_offset: int,
    detect: _DetectStep,
    extract: _FeaturesStep,
    classify: _ClassifyStep,
) -> dict[str, Any] | BarMapEntryFailure:
    # 싼 점검은 오디오 디코드 전에 한다(REQ-LDBARENTRY-007).
    problem = first_beat_offset_problem(first_beat_offset)
    if problem is not None:
        return BarMapEntryFailure(problem, kind=KIND_REJECTED)

    grid = detect(audio_bytes)
    if isinstance(grid, BeatGridFailure):
        return BarMapEntryFailure(grid.reason)

    # @MX:NOTE: [AUTO] 두 배 BPM 채택은 저장하지 않고 거절한다(REQ-LDBARENTRY-008, 결정 E1).
    # 검출기는 bpm 만 두 배로 보정하고 박 격자는 다시 만들지 않는다(BeatGridResult 독스트링)
    # — 저장하면 소비자가 bpm 으로 계산하는 마디 시작이 전부 어긋난다.
    check = grid.bpm_check
    if check.outcome == _OUTCOME_ADOPT_DOUBLE:
        return BarMapEntryFailure(
            f"박 격자 검출이 BPM 을 두 배로 보정했습니다(원시 {check.raw_bpm:.2f} → "
            f"보정 {grid.bpm:.2f}). 박 격자는 두 배로 다시 만들어지지 않아 마디 시작이 "
            "어긋나므로 어느 BPM 으로도 마디 지도를 저장하지 않습니다.",
            kind=KIND_REJECTED,
        )

    # @MX:NOTE: [AUTO] 검출기는 끝의 약한 박을 잘라 낸다 — 조용한 아웃트로가 있으면 마디가 음원
    # 끝보다 앞에서 멈추고, 마디 지도를 읽는 격자·타임코드 Duration·재생 끝이 같이 짧아진다
    # (카드 WT-song-tail). 검출된 박은 그대로 두고 곡 BPM 간격으로 음원 끝까지 잇는다.
    beat_times_ms = extend_beats_to_duration(grid.beat_times_ms, grid.bpm, grid.duration_ms)

    bars = derive_bars(beat_times_ms, first_beat_offset)
    if isinstance(bars, BarMapFailure):
        return BarMapEntryFailure(bars.reason)

    # 경계 목록의 i 번째 창이 마디 i+1 이다 — 빌더의 마디 1, 2, … 와 같은 번호 공간이고,
    # 못갖춘마디(마디 0)는 특징에 없다.
    features = extract(audio_bytes, bars.bar_boundaries_ms)
    if isinstance(features, BarFeaturesFailure):
        return BarMapEntryFailure(features.reason)

    events = classify(features)

    try:
        payload = build_bar_map_payload(
            beat_times_ms,
            first_beat_offset,
            bpm=grid.bpm,
            time_signature=_TIME_SIGNATURE,
            events=events,
            bar_energy=compute_bar_energy(features),
        )
    except BarMapStoreError as error:
        return BarMapEntryFailure(str(error))

    rhythm = _rhythm_block(audio_bytes, payload["bars"], grid.bpm, payload["events"])
    if rhythm is None:
        return payload
    try:
        return attach_rhythm(payload, rhythm)
    except BarMapStoreError as error:
        return BarMapEntryFailure(str(error))


def _rhythm_block(audio_bytes: bytes, bars: list, bpm: float, events: list) -> dict | None:
    """곡 소리에서 ``rhythm`` 블록을 만든다. 디코드할 수 없는 입력이면 ``None`` — 그 지도는 키 없이
    저장된다(레인1: 키가 없으면 현재 경로). 분석 중의 실제 오류는 호출자가 실패로 바꾼다.
    ``events`` 는 마디 지도의 이벤트이고 구간 종류(kind)를 정하는 데 쓴다."""
    decoded = _decode_mono_audio(audio_bytes)
    if isinstance(decoded, BeatGridFailure):
        return None
    import librosa
    import numpy

    rms = librosa.feature.rms(y=decoded.mono, frame_length=_FRAME_LENGTH, hop_length=_HOP_LENGTH)[0]
    frame_ms = _HOP_LENGTH * 1000.0 / decoded.sample_rate
    boundaries_ms, d_candidates = sections_from_rms(numpy, rms, frame_ms, decoded.duration_ms, bpm)
    return build_rhythm(
        decoded.mono, decoded.sample_rate, bars, boundaries_ms, d_candidates, events=events
    )
