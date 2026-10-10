"""M2 — 마디 지도: 자동 비트 격자 + 사람이 지정한 첫 박 오프셋 (SPEC-LDBARMAP-001).

REQ-LDBARMAP-016 · AC-LDBARMAP-015/016. 세 층으로 나뉜다:

1. ``derive_bars`` 순수 함수 시험 — librosa 없이 CI 어디서나 돈다.
2. ``detect_beat_grid`` 를 in-test 합성 클릭 트랙(알려진 BPM)에 돌리는 CI-safe 시험
   + 쓰레기 바이트열의 실패 경로.
3. LOVE ATTACK **326개 검출 비트 시각 고정 픽스처**(``fixtures/love_attack_beat_grid.json``,
   오디오가 아니라 파생 숫자)로 AC-LDBARMAP-016(다운비트·마디 경계 적중률 ≥90%)을
   ``tools/barmap`` 의 엄격한 순서 대응 채점기로 재현.
4. 로컬 전용 회귀 — 실제 LOVE ATTACK mp3가 있을 때만(``pytest.skip`` 부재 시 건너뜀),
   ``detect_beat_grid`` 가 그 픽스처와 같은 숫자를 다시 내는지 확인.

콘솔 접촉 0건 — 이 파일은 오디오 분석기만 다룬다(REQ-LDBARMAP-001/015).
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import pytest

from server.audio.analyze import analysis_available
from server.audio.bar_map import (
    BarMap,
    BarMapFailure,
    BeatGridFailure,
    BeatGridResult,
    derive_bars,
    detect_beat_grid,
)
from tools.barmap.ground_truth import DOWNBEAT_TOLERANCE_SEC, parse_downbeats
from tools.barmap.scorer import strict_index_hit_rate

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LOVE_ATTACK_BEAT_GRID_PATH = FIXTURES_DIR / "love_attack_beat_grid.json"
LOVE_ATTACK_MP3_PATH = Path("/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3")

# AC-LDBARMAP-016 — 감독이 귀로 확인해 확정한 첫 박 오프셋(progress.md §E.2, plan.md M2).
CONFIRMED_FIRST_BEAT_OFFSET = 1
AC016_HIT_RATE_THRESHOLD_PCT = 90.0
NEGATIVE_OFFSET_CEILING_PCT = 10.0


# ---------------------------------------------------------------------------
# 1. derive_bars — 순수 함수, librosa 없이 돈다.
# ---------------------------------------------------------------------------


def test_derive_bars_offset0_first_beat_is_bar1_no_pickup() -> None:
    """오프셋 0 — 첫 박이 곧 마디 1(못갖춘마디 없음)."""
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    result = derive_bars(beats, 0)
    assert isinstance(result, BarMap)
    assert result.downbeats_ms == (0, 2000)
    assert result.bar_boundaries_ms == result.downbeats_ms  # 4/4박자 — 동일해야 한다
    assert result.pickup_beats_ms == ()
    assert result.first_beat_offset == 0


def test_derive_bars_offset1_first_beat_is_pickup() -> None:
    """오프셋 1 — 인덱스 0 박은 못갖춘마디, 마디 1은 인덱스 1(REQ-LDBARMAP-016)."""
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    result = derive_bars(beats, 1)
    assert isinstance(result, BarMap)
    assert result.downbeats_ms == (500, 2500)
    assert result.pickup_beats_ms == (0,)
    assert result.first_beat_offset == 1


def test_derive_bars_offset2_two_pickup_beats() -> None:
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    result = derive_bars(beats, 2)
    assert isinstance(result, BarMap)
    assert result.downbeats_ms == (1000, 3000)
    assert result.pickup_beats_ms == (0, 500)


def test_derive_bars_offset3_three_pickup_beats() -> None:
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    result = derive_bars(beats, 3)
    assert isinstance(result, BarMap)
    assert result.downbeats_ms == (1500, 3500)
    assert result.pickup_beats_ms == (0, 500, 1000)


@pytest.mark.parametrize("bad_offset", [-1, 4, 5, 100, -100])
def test_derive_bars_rejects_out_of_range_offset(bad_offset: int) -> None:
    result = derive_bars([0, 500, 1000, 1500], bad_offset)
    assert isinstance(result, BarMapFailure)
    assert "0~3" in result.reason


@pytest.mark.parametrize("bad_offset", [1.0, "1", None, 1.5, [1]])
def test_derive_bars_rejects_non_int_offset(bad_offset) -> None:
    result = derive_bars([0, 500, 1000, 1500], bad_offset)
    assert isinstance(result, BarMapFailure)
    assert "정수" in result.reason


def test_derive_bars_rejects_bool_offset_despite_being_an_int_subtype() -> None:
    """``bool`` 은 파이썬에서 ``int`` 의 서브타입이지만, 오프셋으로는 의미가 없다."""
    result = derive_bars([0, 500, 1000, 1500], True)
    assert isinstance(result, BarMapFailure)


def test_derive_bars_rejects_empty_beat_grid() -> None:
    result = derive_bars([], 0)
    assert isinstance(result, BarMapFailure)
    assert "비어" in result.reason


def test_derive_bars_short_grid_under_one_bar_has_no_downbeats_past_offset() -> None:
    """한 마디(4박)보다 짧은 격자 — 오프셋(=3)에 닿는 박이 격자 안에 없으면
    다운비트가 0개일 수 있다(인덱스 0·1·2뿐이라 (i-3)%4==0 을 만족하는 i가 없다)."""
    result = derive_bars([0, 500, 1000], 3)
    assert isinstance(result, BarMap)
    assert result.downbeats_ms == ()
    assert result.pickup_beats_ms == (0, 500, 1000)  # 격자 전체가 못갖춘마디뿐


def test_derive_bars_bar_boundaries_equal_downbeats_in_4_4() -> None:
    """spec.md §5 열린 결정 3 — 4/4박자라 마디 경계와 다운비트가 같은 수열이다."""
    beats = list(range(0, 8000, 500))
    result = derive_bars(beats, CONFIRMED_FIRST_BEAT_OFFSET)
    assert isinstance(result, BarMap)
    assert result.bar_boundaries_ms == result.downbeats_ms


def test_derive_bars_matches_appendix_a_bar1_bar2_with_love_attack_timing() -> None:
    """부록 A 마디 1(1.50s)·2(3.66s) — 지도 보고서 손 측정과 같은 간격을 재현한다."""
    beat_interval_ms = round(1000 * 60.0 / 112.35)
    beats = [round(0.964 * 1000) + i * beat_interval_ms for i in range(8)]
    result = derive_bars(beats, 1)
    assert isinstance(result, BarMap)
    # 마디 1·2 다운비트가 ±60ms 안에서 부록 A(1.50s·3.66s)에 들어맞는다.
    assert abs(result.downbeats_ms[0] / 1000.0 - 1.50) <= 0.06
    assert abs(result.downbeats_ms[1] / 1000.0 - 3.66) <= 0.06


# ---------------------------------------------------------------------------
# AC-LDBARMAP-015 — M2 구현 시점부터 실제 함수 시그니처 검사로 전환한다.
# ---------------------------------------------------------------------------


def test_ac015_detect_beat_grid_takes_only_completed_audio_bytes() -> None:
    """완결된 바이트열 하나만 받는다 — 스트리밍 핸들·실시간 콜백 인자가 없다."""
    sig = inspect.signature(detect_beat_grid)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "audio_bytes"
    assert params[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_ac015_derive_bars_is_pure_no_streaming_no_callback() -> None:
    sig = inspect.signature(derive_bars)
    param_names = [p.name for p in sig.parameters.values()]
    assert param_names == ["beat_times_ms", "first_beat_offset"]
    for name in param_names:
        assert "stream" not in name.lower()
        assert "callback" not in name.lower()
        assert "handle" not in name.lower()


# ---------------------------------------------------------------------------
# 2. detect_beat_grid — in-test 합성 클릭 트랙(알려진 BPM) + 실패 경로.
# ---------------------------------------------------------------------------

#: hop_length=512(analyze.py와 동일)의 프레임 길이가 박 간격을 정확히 나누는
#: 표본율 — 22*1024. 이 값을 쓰지 않으면(예: 22050Hz) librosa 의 동적 계획법
#: 추적기가 프레임 양자화로 487ms/511ms를 번갈아 내 중앙값 BPM 이 120에서
#: 약 2% 어긋난다(실측, t530) — 그 어긋남은 이 테스트가 재는 대상(오프셋/파생
#: 로직)과 무관한 트래커 양자화 잡음이라 표본율로 피한다.
_CLICK_TRACK_SAMPLE_RATE = 22 * 1024
_CLICK_TRACK_BPM = 120.0
_CLICK_TRACK_DURATION_SEC = 30.0


def _synthesize_click_track(
    bpm: float = _CLICK_TRACK_BPM,
    duration_sec: float = _CLICK_TRACK_DURATION_SEC,
    sample_rate: int = _CLICK_TRACK_SAMPLE_RATE,
) -> bytes:
    """알려진 BPM의 클릭 트랙을 numpy로 합성해 WAV 바이트열로 돌려준다.

    ``server/tests/fixtures/audio`` 의 stdlib 전용 생성기를 재사용하지 않는 이유:
    그 픽스처는 구간별 진폭 계단(``SECTION_GAINS``)이 있어 BPM 정밀도 시험에는
    맞지 않는다(분석기의 boundary/D등급 회귀가 그 목적) — 이 시험은 순수하게
    일정한 클릭만 필요하다.
    """
    import numpy as np
    import soundfile as sf

    beat_sec = 60.0 / bpm
    n_samples = int(sample_rate * duration_sec)
    y = np.zeros(n_samples, dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    t_click = np.arange(click_len) / sample_rate
    click = np.sin(2 * np.pi * 1200 * t_click) * np.exp(-t_click / 0.005)
    n_beats = int(duration_sec / beat_sec)
    for i in range(n_beats):
        start = int(round(i * beat_sec * sample_rate))
        end = min(start + click_len, n_samples)
        y[start:end] += click[: end - start]
    buf = io.BytesIO()
    sf.write(buf, y, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(scope="module")
def click_track() -> bytes:
    return _synthesize_click_track()


def test_detect_beat_grid_synthetic_click_track_bpm_within_1_percent(
    click_track: bytes,
) -> None:
    result = detect_beat_grid(click_track)
    assert isinstance(result, BeatGridResult)
    error_pct = abs(result.bpm - _CLICK_TRACK_BPM) / _CLICK_TRACK_BPM * 100.0
    assert error_pct <= 1.0, f"bpm={result.bpm}, error_pct={error_pct}"


def test_detect_beat_grid_synthetic_click_track_beat_count_matches(
    click_track: bytes,
) -> None:
    result = detect_beat_grid(click_track)
    assert isinstance(result, BeatGridResult)
    expected_beats = int(_CLICK_TRACK_DURATION_SEC / (60.0 / _CLICK_TRACK_BPM))
    # librosa 의 비트 추적기는 흔히 맨 처음 박 하나를 놓친다 — 느슨한 허용폭.
    assert abs(len(result.beat_times_ms) - expected_beats) <= 2


def test_detect_beat_grid_synthetic_click_track_records_bpm_check_rationale(
    click_track: bytes,
) -> None:
    """REQ-LDBARMAP-006 — 절반/두 배 후보 비교 근거가 항상 채워진다."""
    result = detect_beat_grid(click_track)
    assert isinstance(result, BeatGridResult)
    check = result.bpm_check
    assert check.rationale
    assert check.raw_bpm > 0
    assert check.half_bpm == pytest.approx(check.raw_bpm / 2.0)
    assert check.double_bpm == pytest.approx(check.raw_bpm * 2.0)


def test_detect_beat_grid_garbage_bytes_returns_failure_not_raise() -> None:
    result = detect_beat_grid(b"this is not an audio file, just garbage bytes \x00\x01\x02")
    assert isinstance(result, BeatGridFailure)
    assert result.reason


def test_detect_beat_grid_empty_bytes_returns_failure() -> None:
    result = detect_beat_grid(b"")
    assert isinstance(result, BeatGridFailure)
    assert "비어" in result.reason


@pytest.mark.parametrize("bad_input", [None, "a string, not bytes", 12345, 3.14, []])
def test_detect_beat_grid_non_bytes_input_returns_failure_not_raise(bad_input) -> None:
    result = detect_beat_grid(bad_input)
    assert isinstance(result, BeatGridFailure)
    assert "바이트열" in result.reason


# ---------------------------------------------------------------------------
# 3. LOVE ATTACK 326개 검출 비트 시각 고정 픽스처 — AC-LDBARMAP-016.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def love_attack_fixture() -> dict:
    with LOVE_ATTACK_BEAT_GRID_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_ground_truth_parses_82_downbeats() -> None:
    """채점에 쓸 정답지 자체가 82마디로 파싱되는지 검산한다(검출기와 무관)."""
    truth = parse_downbeats()
    assert len(truth) == 82


def test_fixture_has_326_beats_matching_m1_report(love_attack_fixture: dict) -> None:
    beats = love_attack_fixture["beat_times_ms"]
    assert len(beats) == 326
    assert love_attack_fixture["bpm"] == pytest.approx(112.347, abs=0.01)


def test_ac016_offset1_downbeat_and_bar_boundary_hit_rate_at_least_90_percent(
    love_attack_fixture: dict,
) -> None:
    """AC-LDBARMAP-016 — 사람이 지정한 첫 박 오프셋(=1, 감독 귀 확정)을 베이스로
    다운비트·마디 경계 적중률이 각각 90% 이상이어야 PASS.

    이 픽스처의 비트는 ``detect_beat_grid`` 가 실제 LOVE ATTACK에서 검출한 것과
    같은 ``beat_track`` 경로(hop=512)에서 나왔다 — 그래서 이 시험이 실제로
    재는 것은 비트 검출기의 독립성이 아니라 ``derive_bars`` 의 오프셋/파생
    로직이다(지도 보고서 비트 추적 경로와 같은 계기로 같은 것을 다시 재는
    순환성은 M1 ``tools/barmap/candidates.py`` 의 후보 A와 동일하게 존재한다
    — 검증 증거로 제시하는 것은 "엄격한 순서 대응 채점기 + 오프셋 파생 공식이
    옳다"는 것이지 "비트 추적이 독립적으로 맞다"가 아니다).
    """
    truth_sec = parse_downbeats()
    bar_map = derive_bars(love_attack_fixture["beat_times_ms"], CONFIRMED_FIRST_BEAT_OFFSET)
    assert isinstance(bar_map, BarMap)

    downbeat_sec = [t / 1000.0 for t in bar_map.downbeats_ms]
    downbeat_hit = strict_index_hit_rate(downbeat_sec, truth_sec, DOWNBEAT_TOLERANCE_SEC)
    assert downbeat_hit.rate_pct >= AC016_HIT_RATE_THRESHOLD_PCT, str(downbeat_hit)

    boundary_sec = [t / 1000.0 for t in bar_map.bar_boundaries_ms]
    boundary_hit = strict_index_hit_rate(boundary_sec, truth_sec, DOWNBEAT_TOLERANCE_SEC)
    assert boundary_hit.rate_pct >= AC016_HIT_RATE_THRESHOLD_PCT, str(boundary_hit)


@pytest.mark.parametrize("wrong_offset", [0, 2])
def test_ac016_wrong_offset_hit_rate_below_10_percent(
    love_attack_fixture: dict, wrong_offset: int
) -> None:
    """음성 대조군 — 오프셋 0·2(정답이 아닌 위상)는 10% 밑으로 떨어져야 한다.

    scorer.py의 엄격한 순서 대응이 「우연히 맞는 위상」을 통과시키지 않는다는
    것을 재확인한다(M1 D3 교정, REQ-LDBARMAP-005와 같은 발상을 오프셋 축에
    적용).
    """
    truth_sec = parse_downbeats()
    bar_map = derive_bars(love_attack_fixture["beat_times_ms"], wrong_offset)
    assert isinstance(bar_map, BarMap)
    downbeat_sec = [t / 1000.0 for t in bar_map.downbeats_ms]
    hit = strict_index_hit_rate(downbeat_sec, truth_sec, DOWNBEAT_TOLERANCE_SEC)
    assert hit.rate_pct < NEGATIVE_OFFSET_CEILING_PCT, str(hit)


# ---------------------------------------------------------------------------
# 4. 로컬 전용 회귀 — 실제 LOVE ATTACK mp3가 있을 때만 돈다.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not LOVE_ATTACK_MP3_PATH.exists(),
    reason=f"로컬 전용 — 원곡 부재: {LOVE_ATTACK_MP3_PATH}",
)
def test_detect_beat_grid_real_love_attack_matches_fixture_and_ac016() -> None:
    """로컬 전용 회귀 — 실제 LOVE ATTACK mp3로 다시 재도 BPM·격자·AC-016이 재현된다."""
    audio_bytes = LOVE_ATTACK_MP3_PATH.read_bytes()
    result = detect_beat_grid(audio_bytes)
    assert isinstance(result, BeatGridResult)

    assert result.bpm == pytest.approx(112.35, rel=0.005)

    with LOVE_ATTACK_BEAT_GRID_PATH.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    fixture_beats = fixture["beat_times_ms"]
    assert len(result.beat_times_ms) == len(fixture_beats)
    for detected, fixed in zip(result.beat_times_ms, fixture_beats, strict=True):
        assert abs(detected - fixed) <= 1, f"detected={detected} fixed={fixed}"

    truth_sec = parse_downbeats()
    bar_map = derive_bars(result.beat_times_ms, CONFIRMED_FIRST_BEAT_OFFSET)
    assert isinstance(bar_map, BarMap)
    downbeat_sec = [t / 1000.0 for t in bar_map.downbeats_ms]
    hit = strict_index_hit_rate(downbeat_sec, truth_sec, DOWNBEAT_TOLERANCE_SEC)
    assert hit.rate_pct >= AC016_HIT_RATE_THRESHOLD_PCT, str(hit)
