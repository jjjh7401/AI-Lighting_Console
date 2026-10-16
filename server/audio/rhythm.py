"""박·히트·구간 특징 — 자동 배치가 읽는 음악 분석 값 (SPEC-LDRHYTHM-001, 결과 형식 v1).

마디 지도 사전의 선택 키 ``rhythm`` 을 만든다. 붙이고 검증하는 일은
``bar_map_store.attach_rhythm`` 이 맡는다. 모든 점수는 **이 곡 안에서** 상대로 정한다 —
곡마다 다른 절대 문턱을 코드에 넣지 않는다. 문턱 상수는 일반 규칙이고 단위를 붙였다:
σ 는 이 곡 점수의 표준편차다.

출력. 시각은 곡 시작부터 정수 ms(``bars[].start_ms`` 와 같은 시계)이고, 마디와 박은
정수 번호다(마디 0 은 못갖춘마디, 박 1 은 그 마디의 첫 박).

- ``beats[]``: 박마다 한 항목. kick·snare·onset 은 이 곡 박들 가운데의 백분위(0~1),
  kick_hit·snare_hit 은 이 곡 점수가 평균 + HIT_SIGMA·σ 이상인지 여부.
- ``hits[]``: 큰 히트 순간. strength 는 합성 점수의 백분위(0~1), kind 는 ``"big"``.
- ``sections[]``: 구간 경계를 가장 가까운 마디 시작에 맞춘 구간. start_bar·end_bar 는
  양끝 포함, d_level 은 겹침이 가장 큰 원래 구간의 D 등급(1~5). 선택 키 kind 는 구간의 종류
  (``SECTION_KINDS`` 중 하나)이고, 이 곡의 마디 에너지 순위·이벤트·구간 순서만 근거로 정한다.

4·8마디 묶음은 여기서 강제하지 않는다. 구간의 ``bars`` 수를 보고 소비자가 정한다.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Mapping, Sequence
from typing import Any

from server.audio.analyze import _FRAME_LENGTH, _HOP_LENGTH

#: 킥 대역(Hz). HPSS 로 분리한 타악 성분의 전력을 잰다 — ``bar_map.extract_bar_features``
#: 의 저역 타악과 같은 정의다.
KICK_BAND_HZ = (35.0, 120.0)
#: 스네어 몸통 대역(Hz). 양의 스펙트럼 변화(플럭스)로 잰다.
SNARE_BODY_HZ = (150.0, 300.0)
#: 스네어 살 대역(Hz). 양의 스펙트럼 변화(플럭스)로 잰다.
SNARE_CRACK_HZ = (1500.0, 5000.0)
#: 박 창의 앞 끝(ms, 박 시각보다 앞). 박 전사 흔들림(약 12 ms)을 덮는다.
WINDOW_BEFORE_MS = 30.0
#: 박 창의 뒤 끝 상한(ms). 박 간격의 절반과 이 값 중 작은 쪽을 쓴다 — 다음 박을 넘지 않는다.
WINDOW_AFTER_MS = 150.0
#: 킥·스네어 히트 문턱(σ). 이 곡 박 점수의 평균 + 1.0σ 이상이면 히트다.
HIT_SIGMA = 1.0
#: 큰 히트 문턱(σ). 이 곡 합성 점수의 평균 + 2.0σ 이상이고, 앞뒤 BIG_HIT_NEIGHBOUR_BEATS 박
#: 안에서 국소 최대여야 한다.
BIG_HIT_SIGMA = 2.0
#: 큰 히트 국소 최대를 보는 범위(박 수, 앞뒤 각각).
BIG_HIT_NEIGHBOUR_BEATS = 2

#: 구간 종류. ``bar_map_store._SECTION_KINDS`` 와 같은 값이다(저장소는 이 모듈을 쓰지 않는다).
SECTION_KINDS = ("intro", "verse", "pre", "chorus", "bridge", "drop", "outro")

#: 가장자리 무음 길이(초). 곡의 첫·끝 프레임 효과를 덮는 앞뒤 패딩이고, 곡 시각은 되돌려 쓴다.
EDGE_PAD_S = 1.0
#: 로그 바닥값. 0 전력이 로그에서 발산하지 않게 한다.
_LOG_FLOOR = 1e-6


def song_relative(values: Sequence[float]) -> tuple[list[float], list[float]]:
    """이 곡 값들의 로그 전력을 (z 점수, 백분위 0~1) 로 돌려준다.

    z 의 단위는 σ(이 곡 로그 값의 표준편차)다. 값이 모두 같으면 z 는 0이다.
    """
    return _z_and_percentile(_log10(values))


def big_hit_indices(score: Sequence[float]) -> list[int]:
    """합성 점수가 이 곡 평균 + BIG_HIT_SIGMA·σ 이상이고, 앞뒤 BIG_HIT_NEIGHBOUR_BEATS 박 안에서
    국소 최대인 박의 순번(0부터)을 돌려준다."""
    import numpy

    values = numpy.asarray(score, dtype=float)
    if values.size == 0:
        return []
    threshold = float(values.mean()) + BIG_HIT_SIGMA * float(values.std())
    picked: list[int] = []
    for index in range(values.size):
        if values[index] < threshold:
            continue
        low = max(0, index - BIG_HIT_NEIGHBOUR_BEATS)
        high = min(values.size, index + BIG_HIT_NEIGHBOUR_BEATS + 1)
        if values[index] >= values[low:high].max():
            picked.append(index)
    return picked


def snap_sections(
    bars: Sequence[Mapping[str, Any]],
    boundaries_ms: Sequence[int],
    d_candidates: Sequence[Any],
) -> list[dict[str, Any]]:
    """구간 경계를 가장 가까운 마디 시작에 맞추고, 그 사이를 마디 번호 구간으로 나눈다.

    span 의 d_level 은 span 과 시간이 가장 많이 겹치는 원래 구간의 D 등급이다. 겹침이 같으면
    span 시작 시각을 품은 구간을, 그것도 없으면 시작에 가장 가까운 구간을 쓴다.
    """
    import numpy

    if not bars:
        raise ValueError("마디가 없어 구간을 맞출 수 없습니다")
    if not d_candidates:
        raise ValueError("구간 D 등급이 없어 구간을 만들 수 없습니다")
    starts = [int(bar["start_ms"]) for bar in bars]
    numbers = [int(bar["bar"]) for bar in bars]

    snapped = {0}
    for boundary in boundaries_ms:
        spot = bisect.bisect_left(starts, int(boundary))
        near = [k for k in (spot - 1, spot) if 0 <= k < len(starts)]
        snapped.add(min(near, key=lambda k: abs(starts[k] - int(boundary))))
    first_indexes = sorted(snapped)

    median_bar_ms = float(numpy.median(numpy.diff(starts))) if len(starts) > 1 else 0.0
    spans: list[dict[str, Any]] = []
    for position, first in enumerate(first_indexes):
        if position + 1 < len(first_indexes):
            last = first_indexes[position + 1] - 1
        else:
            last = len(bars) - 1
        start_ms = starts[first]
        if last + 1 < len(bars):
            end_ms = starts[last + 1]
        else:
            end_ms = starts[last] + int(round(median_bar_ms))
        spans.append(
            {
                "start_bar": numbers[first],
                "end_bar": numbers[last],
                "bars": numbers[last] - numbers[first] + 1,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "d_level": _grade_for_span(start_ms, end_ms, d_candidates),
            }
        )
    return spans


def classify_section_kinds(
    sections: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    bar_energy: Mapping[int, float],
) -> list[str]:
    """구간(마디 순서)마다 종류를 정해 같은 순서로 돌려준다.

    근거는 이 곡 안의 것뿐이다 — 마디 에너지 순위, 마디 지도의 이벤트, 구간 순서.
    ``bar_energy`` 는 {마디 번호: 에너지(0~1)} 이고 없는 마디는 에너지가 없는 것으로 본다.
    규칙은 R1~R8 순서로 적용하며, 이미 종류가 정해진 구간은 뒤 규칙이 바꾸지 않는다.
    """
    count = len(sections)
    kinds: list[str | None] = [None] * count

    def event_starts(kind: str) -> list[int]:
        return [int(event["start_bar"]) for event in events if event["kind"] == kind]

    def holds(section: Mapping[str, Any], bar: int) -> bool:
        return int(section["start_bar"]) <= bar <= int(section["end_bar"])

    drop_starts = event_starts("drop")
    build_starts = event_starts("build")
    break_starts = event_starts("break")

    # R1 drop, R2 pre: 이벤트의 시작 마디를 품은 구간.
    for index, section in enumerate(sections):
        if any(holds(section, bar) for bar in drop_starts):
            kinds[index] = "drop"
    for index, section in enumerate(sections):
        if kinds[index] is None and any(holds(section, bar) for bar in build_starts):
            kinds[index] = "pre"
    # R3 intro, R4 outro: 곡의 처음과 끝 구간.
    if count and kinds[0] is None:
        kinds[0] = "intro"
    if count >= 2 and kinds[-1] is None:
        kinds[-1] = "outro"
    # R5 chorus: 앞 구간이 pre 나 drop 이면 후렴이다(앞에서부터 차례로 본다).
    for index in range(1, count):
        if kinds[index] is None and kinds[index - 1] in ("pre", "drop"):
            kinds[index] = "chorus"
    # R6 bridge: break 로 시작하고 바로 다음이 drop 인 구간.
    for index in range(count - 1):
        if (
            kinds[index] is None
            and int(sections[index]["start_bar"]) in break_starts
            and kinds[index + 1] == "drop"
        ):
            kinds[index] = "bridge"

    # R7 chorus 를 이벤트로 못 찾았을 때만: 에너지 순위로 상위 1/3(올림)을 후렴으로 본다.
    # 1/3 은 곡마다 다른 값이 아니라 "이 곡 구간 가운데 가장 센 몫"을 뜻하는 일반 규칙이다.
    if "chorus" not in kinds:
        ranked: list[tuple[float, int]] = []
        for index, section in enumerate(sections):
            if kinds[index] is not None:
                continue
            values = [
                bar_energy[bar]
                for bar in range(int(section["start_bar"]), int(section["end_bar"]) + 1)
                if bar in bar_energy
            ]
            if values:
                ranked.append((sum(values) / len(values), index))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        for _, index in ranked[: math.ceil(len(ranked) / 3)]:
            kinds[index] = "chorus"

    # R8 verse: 남은 구간.
    return [kind or "verse" for kind in kinds]


def build_rhythm(
    mono: Any,
    sample_rate: int,
    bars: Sequence[Mapping[str, Any]],
    boundaries_ms: Sequence[int],
    d_candidates: Sequence[Any],
    *,
    events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """곡 소리와 마디 지도로 ``rhythm`` 사전을 만든다.

    ``bars`` 는 ``bars[]`` 와 같은 모양(bar, start_ms, beats_ms)이다. 박 시각은 ``beats_ms`` 를
    그대로 쓴다. 그래서 자동 배치는 저장된 것과 같은 격자를 본다. ``events`` 는 마디 지도의
    ``events[]`` 이고, 구간 종류(kind)를 정하는 데 쓴다. 마디의 ``energy`` 가 있으면 함께 쓴다.
    """
    import librosa
    import numpy

    beats = [
        (int(bar["bar"]), index, int(time_ms))
        for bar in bars
        for index, time_ms in enumerate(bar.get("beats_ms") or [], start=1)
    ]
    if len(beats) < 2:
        raise ValueError("박이 두 개 이상 있어야 리듬 특징을 만들 수 있습니다")
    times = [time_ms for _, _, time_ms in beats]
    period_ms = float(numpy.median(numpy.diff(numpy.asarray(times, dtype=float))))

    # 곡의 첫·끝 프레임은 가장자리 효과로 흐려진다. 앞뒤에 무음을 덧붙여 재고 시각은 되돌린다.
    pad = numpy.zeros(int(round(EDGE_PAD_S * sample_rate)), dtype=mono.dtype)
    padded = numpy.concatenate([pad, mono, pad])
    stft = librosa.stft(padded, n_fft=_FRAME_LENGTH, hop_length=_HOP_LENGTH)
    onset = librosa.onset.onset_strength(y=padded, sr=sample_rate, hop_length=_HOP_LENGTH)
    frames = min(stft.shape[1], onset.shape[0])
    stft = stft[:, :frames]
    frame_ms = (
        librosa.frames_to_time(numpy.arange(frames), sr=sample_rate, hop_length=_HOP_LENGTH)
        * 1000.0
        - EDGE_PAD_S * 1000.0
    )
    freqs = librosa.fft_frequencies(sr=sample_rate, n_fft=_FRAME_LENGTH)

    _, percussive = librosa.decompose.hpss(stft, margin=(1.0, 5.0))
    kick_curve = _band_sum(numpy.abs(percussive) ** 2, freqs, KICK_BAND_HZ)
    log_magnitude = numpy.log(numpy.abs(stft) + _LOG_FLOOR)
    snare_curve = _band_flux(log_magnitude, freqs, SNARE_BODY_HZ) + _band_flux(
        log_magnitude, freqs, SNARE_CRACK_HZ
    )
    onset_curve = onset[:frames]

    windows = [
        (time_ms - WINDOW_BEFORE_MS, time_ms + min(WINDOW_AFTER_MS, 0.5 * period_ms))
        for time_ms in times
    ]
    kick_z, kick_pct = _z_and_percentile(_log10(_window_max(kick_curve, frame_ms, windows)))
    snare_z, snare_pct = _z_and_percentile(_log10(_window_max(snare_curve, frame_ms, windows)))
    onset_z, onset_pct = _z_and_percentile(_log10(_window_max(onset_curve, frame_ms, windows)))
    combined = [k + o for k, o in zip(kick_z, onset_z, strict=True)]
    _, combined_pct = _z_and_percentile(combined)

    beat_items = [
        {
            "bar": bar_no,
            "beat": beat_no,
            "t_ms": time_ms,
            "kick": round(kick_pct[index], 3),
            "snare": round(snare_pct[index], 3),
            "onset": round(onset_pct[index], 3),
            "kick_hit": bool(kick_z[index] >= HIT_SIGMA),
            "snare_hit": bool(snare_z[index] >= HIT_SIGMA),
        }
        for index, (bar_no, beat_no, time_ms) in enumerate(beats)
    ]
    hits = [
        {
            "bar": beats[index][0],
            "beat": beats[index][1],
            "t_ms": beats[index][2],
            "strength": round(combined_pct[index], 3),
            "kind": "big",
        }
        for index in big_hit_indices(combined)
        if beats[index][0]
        != 0  # 못갖춘마디(마디 0)는 곡 시작에 걸친 부분 창이라 히트 후보가 아니다
    ]
    sections = snap_sections(bars, boundaries_ms, d_candidates)
    bar_energy = {int(bar["bar"]): float(bar["energy"]) for bar in bars if "energy" in bar}
    for section, kind in zip(
        sections, classify_section_kinds(sections, events, bar_energy), strict=True
    ):
        section["kind"] = kind
    return {"beats": beat_items, "hits": hits, "sections": sections}


def _log10(values: Any) -> Any:
    import numpy

    return numpy.log10(numpy.asarray(values, dtype=float) + _LOG_FLOOR)


def _z_and_percentile(scores: Any) -> tuple[list[float], list[float]]:
    import numpy

    values = numpy.asarray(scores, dtype=float)
    count = values.size
    if count == 0:
        return [], []
    sd = float(values.std())
    z = (values - float(values.mean())) / sd if sd > 0 else numpy.zeros(count)
    ranks = numpy.argsort(numpy.argsort(values, kind="stable"), kind="stable")
    pct = ranks / (count - 1) if count > 1 else numpy.zeros(count)
    return [float(x) for x in z], [float(x) for x in pct]


def _window_max(curve: Any, frame_ms: Any, windows: Sequence[tuple[float, float]]) -> Any:
    import numpy

    out = numpy.zeros(len(windows))
    for index, (low, high) in enumerate(windows):
        mask = (frame_ms >= low) & (frame_ms < high)
        if mask.any():
            out[index] = float(curve[mask].max())
    return out


def _band_sum(power: Any, freqs: Any, band_hz: tuple[float, float]) -> Any:
    import numpy

    mask = (freqs >= band_hz[0]) & (freqs < band_hz[1])
    return numpy.asarray(power)[mask].sum(axis=0)


def _band_flux(log_magnitude: Any, freqs: Any, band_hz: tuple[float, float]) -> Any:
    import numpy

    mask = (freqs >= band_hz[0]) & (freqs < band_hz[1])
    band = log_magnitude[mask]
    change = numpy.diff(band, axis=1, prepend=band[:, :1])
    return numpy.maximum(change, 0.0).sum(axis=0)


def _grade_for_span(start_ms: int, end_ms: int, d_candidates: Sequence[Any]) -> int:
    """span 과 시간이 가장 많이 겹치는 원래 구간의 D 등급.

    겹침이 같으면 span 시작 시각을 품은 구간을, 그것도 없으면 시작에 가장 가까운 구간을 쓴다.
    """
    best_key: tuple[int, bool, int] | None = None
    best_grade = 0
    for candidate in d_candidates:
        overlap = max(
            0, min(end_ms, int(candidate.end_ms)) - max(start_ms, int(candidate.start_ms))
        )
        contains = int(candidate.start_ms) <= start_ms < int(candidate.end_ms)
        key = (overlap, contains, -abs(int(candidate.start_ms) - start_ms))
        if best_key is None or key > best_key:
            best_key = key
            best_grade = int(candidate.d_level)
    return best_grade
