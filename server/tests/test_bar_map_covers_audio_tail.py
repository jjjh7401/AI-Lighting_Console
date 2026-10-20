"""마디 지도는 음원 끝까지 덮는다 — 곡 꼬리(조용한 끝 구간)가 잘리지 않는다(카드 WT-song-tail).

결함(2026-10-20 실측): 음원은 197.2초인데 박 검출기(``librosa.beat.beat_track`` — 기본
``trim=True``)가 끝의 약한 박을 잘라 마지막 박이 175.1초에 멈췄다. 마디 지도는 검출된 박으로만
마디를 만들어서 마지막 마디가 177.2초에 끝났고, 이 값을 읽는 세 곳이 함께 짧아졌다:

* 배치 격자 — 마지막 구간(177~197초)이 마디 하나만 받아 칸을 못 놓는다.
* 콘솔 타임코드 — ``Duration`` 이 마지막 마디 끝(+ 지연)이다.
* 앱 재생 끝·콘솔 끄기 — 화면은 마디 수로 곡 끝을 잡는다.

이 시험은 곡 이름·장비·BPM 상수 없이, 클릭이 중간에 멈추고 무음 꼬리가 20초 이어지는 합성
음원으로 같은 모양을 재현한다. 저장소에 오디오 파일을 두지 않는다. 콘솔 접촉: 0건.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pytest

from server.audio.analyze import analysis_available
from server.audio.bar_map import BeatGridResult, detect_beat_grid, extend_beats_to_duration
from server.audio.bar_map_entry import synthesize_bar_map
from server.audio.bar_map_store import validate_bar_map
from server.design.analysis_timeline import build_analysis_timeline
from server.design.beat_grid_send import song_end_seconds_from_bar_map
from server.web.messages import fill_bar_map_header

requires_analysis = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)

#: hop_length(512)가 박 간격을 정확히 나누는 표본율(test_audio_bar_map_entry.py 와 같은 이유).
_SAMPLE_RATE = 24 * 1024
_BPM = 96.0
#: 클릭이 울리는 구간과 그 뒤 무음 꼬리. 꼬리는 결함 실측(약 20초)과 같은 크기다.
_CLICK_SEC = 20.0
_TAIL_SEC = 20.0
_DURATION_SEC = _CLICK_SEC + _TAIL_SEC


def _click_track_with_silent_tail() -> bytes:
    """``_CLICK_SEC`` 동안 클릭, 그 뒤 ``_TAIL_SEC`` 무음인 WAV 바이트열."""
    import numpy as np
    import soundfile as sf

    beat_sec = 60.0 / _BPM
    n_samples = int(_SAMPLE_RATE * _DURATION_SEC)
    y = np.zeros(n_samples, dtype=np.float32)
    click_len = int(0.02 * _SAMPLE_RATE)
    t_click = np.arange(click_len) / _SAMPLE_RATE
    click = np.sin(2 * np.pi * 1200 * t_click) * np.exp(-t_click / 0.005)
    for i in range(int(_CLICK_SEC / beat_sec)):
        start = int(round(i * beat_sec * _SAMPLE_RATE))
        y[start : start + click_len] += click
    buf = io.BytesIO()
    sf.write(buf, y, _SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(scope="module")
def tail_track() -> bytes:
    return _click_track_with_silent_tail()


@pytest.fixture(scope="module")
def detected(tail_track: bytes) -> BeatGridResult:
    grid = detect_beat_grid(tail_track)
    assert isinstance(grid, BeatGridResult), grid
    return grid


@dataclass(frozen=True)
class _Section:
    label: str
    start_ms: int
    end_ms: int
    d_level: int


def _bar_end_ms(bar_map: dict, bar: dict) -> float:
    numerator = bar_map["time_signature"][0]
    return bar["start_ms"] + numerator * 60000.0 / bar_map["bpm"]


def test_extension_fills_up_to_but_not_past_the_audio_end() -> None:
    """순수 함수 — 검출된 박은 앞에 그대로, 뒤는 BPM 간격으로 음원 끝 앞까지만."""
    extended = extend_beats_to_duration((0, 500, 1000), 120.0, 3000)
    assert extended == (0, 500, 1000, 1500, 2000, 2500)


@pytest.mark.parametrize(
    ("beats", "bpm", "duration_ms"),
    [
        ((0, 500, 1000), 120.0, None),  # 길이를 모른다
        ((0, 500, 1000), 120.0, 1200),  # 이미 끝까지 덮었다
        ((), 120.0, 3000),  # 박이 없다
        ((0, 500), 0.0, 3000),
        ((0, 500), -1.0, 3000),
        ((0, 500), float("nan"), 3000),
        ((0, 500), float("inf"), 3000),
        ((0, 500), True, 3000),
    ],
)
def test_extension_leaves_the_grid_alone_when_it_cannot_or_need_not_extend(
    beats: tuple[int, ...], bpm: float, duration_ms: int | None
) -> None:
    assert extend_beats_to_duration(beats, bpm, duration_ms) == beats


@requires_analysis
def test_precondition_detector_stops_before_the_audio_ends(detected: BeatGridResult) -> None:
    """전제 — 이 합성 음원에서 검출기의 마지막 박은 음원 끝보다 한참 앞이다(결함의 모양).

    이 전제가 깨지면 아래 시험이 꼬리 없이 공허하게 통과한다."""
    assert detected.beat_times_ms[-1] < (_DURATION_SEC - 15.0) * 1000


@pytest.mark.parametrize("offset", [0, 1, 3])
@requires_analysis
def test_bar_map_reaches_the_end_of_the_audio(tail_track: bytes, offset: int) -> None:
    """마디 지도의 마지막 마디가 음원 끝을 품는다 — 시작은 끝 앞, 끝은 끝 뒤."""
    result = synthesize_bar_map(tail_track, offset)
    assert isinstance(result, dict), result
    assert validate_bar_map(result) is None
    last = result["bars"][-1]
    assert last["start_ms"] <= _DURATION_SEC * 1000
    assert _bar_end_ms(result, last) >= _DURATION_SEC * 1000


@requires_analysis
def test_detected_beats_are_kept_and_the_tail_continues_at_the_song_tempo(
    tail_track: bytes, detected: BeatGridResult
) -> None:
    """검출된 박은 하나도 바뀌지 않고 앞에 그대로 있다. 이어 붙인 박은 곡 BPM 간격이고 음원
    안에만 있다."""
    result = synthesize_bar_map(tail_track, 0)
    assert isinstance(result, dict), result
    beats = [ms for bar in result["bars"] for ms in bar["beats_ms"]]
    count = len(detected.beat_times_ms)
    assert tuple(beats[:count]) == detected.beat_times_ms
    tail = beats[count - 1 :]
    assert len(tail) > 1
    period_ms = 60000.0 / result["bpm"]
    assert all(abs((b - a) - period_ms) <= 1 for a, b in zip(tail, tail[1:], strict=False))
    assert tail[-1] < _DURATION_SEC * 1000


@requires_analysis
def test_timecode_duration_reaches_the_end_of_the_audio(tail_track: bytes) -> None:
    """콘솔 타임코드 ``Duration`` 의 출처(마지막 마디 끝)가 음원 끝 뒤다."""
    result = synthesize_bar_map(tail_track, 1)
    assert isinstance(result, dict), result
    song_end = song_end_seconds_from_bar_map(result)
    assert song_end is not None
    assert song_end >= _DURATION_SEC


@requires_analysis
def test_last_section_gets_bars_through_the_end_of_the_audio(tail_track: bytes) -> None:
    """배치 격자 — 꼬리에서 시작하는 마지막 구간이 음원 끝까지 마디를 받는다."""
    bar_map = synthesize_bar_map(tail_track, 1)
    assert isinstance(bar_map, dict), bar_map
    duration_ms = int(_DURATION_SEC * 1000)
    tail_start_ms = int((_CLICK_SEC + 2.0) * 1000)
    timeline = build_analysis_timeline(
        song_title="tail",
        sections=[
            _Section("A1", 0, tail_start_ms, 3),
            _Section("D1", tail_start_ms, duration_ms, 1),
        ],
        bar_map=bar_map,
        layout=[],
        source_sha256="0" * 64,
    )
    last_section = timeline["sections"][-1]
    last_bar_no = last_section["bar_start"] + last_section["bar_count"] - 1
    by_number = {bar["bar"]: bar for bar in bar_map["bars"]}
    assert _bar_end_ms(bar_map, by_number[last_bar_no]) >= duration_ms
    assert timeline["beat_grid"]["bar_range"]["end"] == last_bar_no
    # 꼬리 구간이 마디 하나로 쪼그라들지 않는다 — 꼬리 길이만큼 마디가 있다.
    seconds_per_bar = 4 * 60.0 / bar_map["bpm"]
    assert last_section["bar_count"] >= int((_DURATION_SEC - _CLICK_SEC - 2.0) / seconds_per_bar)


@requires_analysis
def test_screen_bar_count_follows_the_full_bar_map(tail_track: bytes) -> None:
    """앱 재생 끝 — 화면이 받는 마디 수가 음원 끝까지 덮은 마디 지도의 마디 수다."""
    bar_map = synthesize_bar_map(tail_track, 1)
    assert isinstance(bar_map, dict), bar_map
    header = fill_bar_map_header({"bar_map": bar_map, "seconds_per_bar": 4 * 60.0 / bar_map["bpm"]})
    # 마디 0(못갖춘마디)이 있는 지도에서 화면의 곡 끝 = 0마디 시작 + 마디 수 × 한 마디 길이.
    end_seconds = header["bar_zero_start_seconds"] + header["bar_count"] * header["seconds_per_bar"]
    assert end_seconds >= _DURATION_SEC
