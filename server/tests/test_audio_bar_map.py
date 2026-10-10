"""M2/M3 — 마디 지도 + 마디별 변화 이벤트 분류기 (SPEC-LDBARMAP-001).

REQ-LDBARMAP-016(M2) · REQ-LDBARMAP-008(M3) · AC-LDBARMAP-015/016/007. 다섯 층으로
나뉜다:

1. ``derive_bars`` 순수 함수 시험 — librosa 없이 CI 어디서나 돈다.
2. ``detect_beat_grid`` 를 in-test 합성 클릭 트랙(알려진 BPM)에 돌리는 CI-safe 시험
   + 쓰레기 바이트열의 실패 경로.
3. LOVE ATTACK **326개 검출 비트 시각 고정 픽스처**(``fixtures/love_attack_beat_grid.json``,
   오디오가 아니라 파생 숫자)로 AC-LDBARMAP-016(다운비트·마디 경계 적중률 ≥90%)을
   ``tools/barmap`` 의 엄격한 순서 대응 채점기로 재현.
4. 로컬 전용 회귀(M2) — 실제 LOVE ATTACK mp3가 있을 때만(``pytest.skip`` 부재 시
   건너뜀), ``detect_beat_grid`` 가 그 픽스처와 같은 숫자를 다시 내는지 확인.
5. ``classify_bar_events`` 합성 특징 시험(M3, 순수 함수, CI-safe) — 네 종류 각각 +
   무이벤트.
6. LOVE ATTACK **부록 A 표 자체를 파싱한 특징 픽스처**(M3, 오디오 아님 — 지도
   보고서가 이미 커밋한 숫자, ``tools/barmap/ground_truth.parse_bar_features``)로
   AC-LDBARMAP-007(≥5/7) 재현 + 문턱 ±20% 민감도.
7. 로컬 전용 회귀(M3) — 실제 LOVE ATTACK mp3가 있을 때만, ``extract_bar_features``
   가 음량을 재현하고 전체 파이프라인이 AC-007 을 통과하는지 확인.
8. AC-LDBARMAP-007 **정밀도 조건**(카드 t535, 2026-10-10) — 브레이크 분류의
   저역+온셋 비율 결합(순수 함수, CI-safe), 정답지 "순간" 칸 증거 파서
   (``ground_truth.parse_precision_evidence``), 정밀도 채점기
   (``scorer.event_precision``), 그리고 LOVE ATTACK **실제 오디오 마디별
   특징 고정 픽스처**(``fixtures/love_attack_bar_features_real.json`` — 오디오가
   아니라 파생 숫자, CI에서 원곡 없이도 돈다)로 재현율·정밀도 둘 다 확인.

콘솔 접촉 0건 — 이 파일은 오디오 분석기만 다룬다(REQ-LDBARMAP-001/015).
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import pytest

from server.audio import bar_map as bar_map_module
from server.audio.analyze import analysis_available
from server.audio.bar_map import (
    BarEvent,
    BarFeatures,
    BarFeaturesFailure,
    BarMap,
    BarMapFailure,
    BeatGridFailure,
    BeatGridResult,
    classify_bar_events,
    derive_bars,
    detect_beat_grid,
    extract_bar_features,
)
from tools.barmap.gen_ear_check_candidates import build_candidate_rows, load_fixture
from tools.barmap.ground_truth import (
    DOWNBEAT_TOLERANCE_SEC,
    parse_bar_features,
    parse_downbeats,
    parse_precision_evidence,
)
from tools.barmap.scorer import event_precision, event_recall, strict_index_hit_rate

pytestmark = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LOVE_ATTACK_BEAT_GRID_PATH = FIXTURES_DIR / "love_attack_beat_grid.json"
LOVE_ATTACK_BAR_FEATURES_REAL_PATH = FIXTURES_DIR / "love_attack_bar_features_real.json"
LOVE_ATTACK_MP3_PATH = Path("/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3")

#: AC-LDBARMAP-007 정밀도 조건(카드 t535) — 70% 이상.
AC007_PRECISION_THRESHOLD_PCT = 70.0

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


# ---------------------------------------------------------------------------
# REQ-LDBARMAP-006(재설계, 카드 t547) — 추정 비트 격자 기준 단측 부호검정.
# AC-LDBARMAP-004a~d. 고정 전역 격자 비교(옛 설계)는 BPM 추정 오차에 흔들리고
# (`.moai/reports/t547/red_repro.py` — 정확한 BPM 을 받으면 112→224 로 거짓
# 두 배를 낸다), 새 설계는 검출기 자신의 비트 격자를 기준틀로 쓴다.
# ---------------------------------------------------------------------------

_SIGN_TEST_SAMPLE_RATE = 22050


def _render_click_pattern(bpm: float, duration_sec: float, pattern: list[list[float]], seed: int):
    """REQ-LDBARMAP-006 시험용 합성 클릭 — ``.moai/reports/t547/probe_synth.py``
    의 ``render``/``click`` 과 같은 식(의도적 중복, 생산 코드가 탐침 스크립트를
    import 하지 않는다). ``pattern`` 은 한 박을 n등분한 자리별 세기 목록이다.

    plan-audit D5 교정 — 각 호출이 ``seed`` 로 독립된 RNG 를 새로 만든다. 케이스
    마다 자기만의 시드로 렌더하라는 것(난수를 공유하지 않음)이지, 여러 케이스가
    같은 숫자값을 쓰라는 뜻이 아니다 — 아래 호출마다 다른 ``seed`` 를 쓴다.
    """
    import numpy as np

    sr = _SIGN_TEST_SAMPLE_RATE
    rng = np.random.default_rng(seed)

    def click(sig, t, amp):
        i = int(t * sr)
        n = int(0.03 * sr)
        if i + n < len(sig):
            sig[i : i + n] += amp * np.exp(-np.arange(n) / (0.004 * sr)) * rng.standard_normal(n)

    sig = np.zeros(int(duration_sec * sr))
    beat = 60.0 / bpm
    k = 0
    t = 0.5
    while t < duration_sec - 1:
        pat = pattern[k % len(pattern)]
        for j, amp in enumerate(pat):
            if amp > 0:
                click(sig, t + j * beat / len(pat), amp)
        t += beat
        k += 1
    return (sig + 0.001 * rng.standard_normal(len(sig))).astype(np.float32)


def _bpm_check_for_pattern(bpm: float, pattern: list[list[float]], seed: int):
    """패턴을 렌더하고 박 추적 + 온셋 강도 환경으로 ``_check_bpm_half_double`` 을
    직접 호출한다(REQ-LDBARMAP-006). 회귀 BPM(정확한 추정, t546 PR #593 이후
    ``analyze()`` 가 쓰는 값)을 쓴다 — ``probe_synth.py``·``probe_sign.py`` 와
    같은 선택이고, 옛 설계의 결함이 실제로 드러나는 입력이다(median BPM 으로는
    드러나지 않는다, `.moai/reports/t547/red_repro.py` 참조)."""
    import librosa
    import numpy as np

    from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression

    y = _render_click_pattern(bpm, 90.0, pattern, seed)
    beat_times = librosa.beat.beat_track(
        y=y, sr=_SIGN_TEST_SAMPLE_RATE, hop_length=_HOP_LENGTH, units="time"
    )[1]
    envelope = librosa.onset.onset_strength(y=y, sr=_SIGN_TEST_SAMPLE_RATE, hop_length=_HOP_LENGTH)
    raw_bpm, _ = _tempo_from_beat_regression(np, beat_times)
    return bar_map_module._check_bpm_half_double(
        np, float(raw_bpm), beat_times, envelope, _SIGN_TEST_SAMPLE_RATE
    )


@pytest.mark.parametrize("true_bpm", [224, 240])
def test_ac004a_synthetic_true_double_tracked_as_half_adopts_double(true_bpm: float) -> None:
    """AC-LDBARMAP-004a — 실제로는 두 배인데 추적기가 절반으로(잘못) 짚은 합성
    신호는 새 설계의 단측 부호검정으로 두 배 채택(adopt_double)된다."""
    check = _bpm_check_for_pattern(true_bpm, [[1.0]], seed=547)
    assert check.raw_bpm < true_bpm  # 추적기가 실제로 절반쯤을 짚었는지 확인(~112/~120)
    assert check.p_mid >= bar_map_module._SIGN_TEST_ALPHA
    assert check.w_mid >= bar_map_module._MID_SYMMETRY
    assert check.outcome == bar_map_module._OUTCOME_ADOPT_DOUBLE
    assert not check.ambiguous
    assert check.adopted_bpm == pytest.approx(check.raw_bpm * 2.0)
    assert check.rationale


@pytest.mark.parametrize(
    "pattern",
    [
        [[1.0, 0.3]],  # 균일 세기 박 + 8분음표 하이햇 0.3
        [[1.0, 0.3], [0.6, 0.3], [1.0, 0.3], [0.6, 0.3]],  # 킥/스네어 1.0/0.6 + 8분 0.3
    ],
)
def test_ac004b_eighth_hihat_density_does_not_cause_false_double(
    pattern: list[list[float]],
) -> None:
    """AC-LDBARMAP-004b — 8분음표 하이햇이 섞여도(밀도 편향) 거짓 두 배가 나오지
    않는다 — 옛 고정 격자 비교의 결함(`.moai/reports/t547/red_repro.py` 가 재현한
    결함)이 새 설계에서는 사라진다."""
    check = _bpm_check_for_pattern(112, pattern, seed=547)
    assert check.p_mid < bar_map_module._SIGN_TEST_ALPHA
    assert check.outcome == bar_map_module._OUTCOME_KEEP
    assert not check.ambiguous
    assert check.adopted_bpm == pytest.approx(check.raw_bpm)
    assert check.rationale


def test_ac004d_loud_eighth_hihat_keeps_with_ambiguous_flag() -> None:
    """AC-LDBARMAP-004d — 세기 0.7(강함)의 8분음표 하이햇은 판정 경계 가까이
    있지만(plan-audit D5), keep + ambiguous=True 로 안정적으로 떨어진다
    (`.moai/reports/t547/d5.txt` — 11개 시드 전부 같은 경로, 문턱 조정 없음)."""
    check = _bpm_check_for_pattern(112, [[1.0, 0.7]], seed=547)
    assert check.outcome == bar_map_module._OUTCOME_KEEP
    assert check.ambiguous is True
    assert check.p_mid >= bar_map_module._SIGN_TEST_ALPHA
    assert check.w_mid < bar_map_module._MID_SYMMETRY
    assert check.adopted_bpm == pytest.approx(check.raw_bpm)


def test_half_candidate_is_never_auto_adopted_for_true_half_tracked_as_double() -> None:
    """절반 후보는 이 판정으로 자동 채택되지 않는다 — 실제로는 56 BPM인데
    추적기가 112로(두 배로) 짚은 합성 신호도 outcome=keep 이고, 보정된 BPM이
    추적된 값(~112)에 머문다 — 56쪽(절반)으로는 결코 보정되지 않는다."""
    check = _bpm_check_for_pattern(56, [[1.0, 0.3]], seed=547)
    assert check.raw_bpm > 100.0  # 추적기가 실제로 두 배(~112)를 짚었는지 확인
    assert check.outcome == bar_map_module._OUTCOME_KEEP
    assert check.adopted_bpm == pytest.approx(check.raw_bpm)
    assert check.adopted_bpm != pytest.approx(check.raw_bpm / 2.0)


def test_check_bpm_half_double_fewer_than_two_beats_is_ambiguous_keep() -> None:
    """박이 2개 미만이면 쌍을 지을 수 없다 — keep + ambiguous, 근거에 사유를 남긴다."""
    import numpy as np

    check = bar_map_module._check_bpm_half_double(
        np, 112.0, np.asarray([0.5], dtype=float), np.zeros(10, dtype=float), 22050
    )
    assert check.outcome == bar_map_module._OUTCOME_KEEP
    assert check.ambiguous is True
    assert check.adopted_bpm == pytest.approx(112.0)
    assert check.n_pairs == 0
    assert check.rationale


@pytest.mark.skipif(
    not LOVE_ATTACK_MP3_PATH.exists(),
    reason=f"로컬 전용 — 원곡 부재: {LOVE_ATTACK_MP3_PATH}",
)
def test_ac004c_real_love_attack_sign_test_keeps_local_only() -> None:
    """AC-LDBARMAP-004c — 로컬 전용. LOVE ATTACK 실제 트랙 전체에 부호검정을
    적용하면 outcome=keep 이고 보정된 BPM 이 112.35(±0.5%) 범위 안에 있다
    (순환 아님 — 실제 오디오로 재확인, `.moai/reports/t547/probe_sign.txt` 참고
    실측: p_mid=2.34e-38, n=326, 같은 결론)."""
    import io

    import librosa
    import numpy as np
    import soundfile as sf

    from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression

    audio_bytes = LOVE_ATTACK_MP3_PATH.read_bytes()
    samples, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(samples.mean(axis=1), dtype=np.float32)

    beat_times = librosa.beat.beat_track(
        y=mono, sr=sample_rate, hop_length=_HOP_LENGTH, units="time"
    )[1]
    envelope = librosa.onset.onset_strength(y=mono, sr=sample_rate, hop_length=_HOP_LENGTH)
    reg_bpm, _ = _tempo_from_beat_regression(np, beat_times)

    check = bar_map_module._check_bpm_half_double(
        np, float(reg_bpm), beat_times, envelope, sample_rate
    )
    assert check.outcome == bar_map_module._OUTCOME_KEEP
    assert check.adopted_bpm == pytest.approx(112.35, rel=0.005)
    assert check.p_mid < bar_map_module._SIGN_TEST_ALPHA


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


# ---------------------------------------------------------------------------
# 5. classify_bar_events — 순수 함수, 합성 특징(M3, 카드 t530).
# ---------------------------------------------------------------------------

# AC-LDBARMAP-007 — 7개 사건 중 5개 이상(70% 이상) 적중해야 PASS.
AC007_RECALL_THRESHOLD = 5


def test_classify_bar_events_empty_features_returns_empty_list() -> None:
    assert classify_bar_events([]) == []


def test_classify_bar_events_flat_sequence_yields_zero_events() -> None:
    """무이벤트 — 모든 마디가 중앙값과 같으면(평탄) 어떤 이벤트도 나오지 않는다."""
    features = [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in range(1, 21)]
    assert classify_bar_events(features) == []


def test_classify_bar_events_kick_entry_only() -> None:
    """저역이 문턱(2.0배) 이상인 마디 하나 — 킥 진입(큰 히트)만 나온다."""
    features = [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in range(1, 6)]
    features[2] = BarFeatures(bar=3, volume_norm=1.0, low_band_norm=4.0)
    events = classify_bar_events(features)
    kick_events = [e for e in events if e.kind == "kick_entry"]
    assert kick_events == [BarEvent("kick_entry", 3, 3, grade="measured")]


def test_classify_bar_events_break_only() -> None:
    """저역이 문턱(0.45배) 이하인 마디 하나 — 브레이크(킥 멈춤)만 나온다."""
    features = [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in range(1, 6)]
    features[2] = BarFeatures(bar=3, volume_norm=1.0, low_band_norm=0.1)
    events = classify_bar_events(features)
    break_events = [e for e in events if e.kind == "break"]
    assert break_events == [BarEvent("break", 3, 3, grade="measured")]


def test_classify_bar_events_build_anchored_before_kick_entry() -> None:
    """큰 히트 직전 3마디 이상 연속 상승 — 빌드업 하나가 그 구간으로 나온다.

    bar=8이 큰 히트(저역 4.0배)고, bar 4~7이 음량 연속 상승(0.6→0.7→0.8→0.9).
    """
    features = []
    for i in range(1, 11):
        features.append(BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0))
    features[3] = BarFeatures(bar=4, volume_norm=0.6, low_band_norm=1.0)
    features[4] = BarFeatures(bar=5, volume_norm=0.7, low_band_norm=1.0)
    features[5] = BarFeatures(bar=6, volume_norm=0.8, low_band_norm=1.0)
    features[6] = BarFeatures(bar=7, volume_norm=0.9, low_band_norm=1.0)
    features[7] = BarFeatures(bar=8, volume_norm=1.0, low_band_norm=4.0)

    events = classify_bar_events(features)
    build_events = [e for e in events if e.kind == "build"]
    assert build_events == [BarEvent("build", 4, 7, grade="measured")]


def test_classify_bar_events_build_requires_minimum_3_bars() -> None:
    """상승이 2마디뿐이면(문턱 미달) 빌드업으로 치지 않는다."""
    features = []
    for i in range(1, 7):
        features.append(BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0))
    features[3] = BarFeatures(bar=4, volume_norm=0.8, low_band_norm=1.0)
    features[4] = BarFeatures(bar=5, volume_norm=0.9, low_band_norm=1.0)
    features[5] = BarFeatures(bar=6, volume_norm=1.0, low_band_norm=4.0)

    events = classify_bar_events(features)
    build_events = [e for e in events if e.kind == "build"]
    assert build_events == []


def test_classify_bar_events_drop_only() -> None:
    """보컬 대역 비율이 낮고(≤0.15) 저역이 강한(≥1.4배) 구간 — 드롭(참고 지표)만 나온다."""
    features = [
        BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0, vocal_band_ratio=0.5)
        for i in range(1, 6)
    ]
    features[2] = BarFeatures(bar=3, volume_norm=1.0, low_band_norm=1.5, vocal_band_ratio=0.05)
    features[3] = BarFeatures(bar=4, volume_norm=1.0, low_band_norm=1.5, vocal_band_ratio=0.04)

    events = classify_bar_events(features)
    drop_events = [e for e in events if e.kind == "drop"]
    assert drop_events == [BarEvent("drop", 3, 4, grade="estimated")]


def test_classify_bar_events_drop_without_vocal_band_ratio_is_skipped() -> None:
    """``vocal_band_ratio`` 가 ``None`` 이면(값을 못 쟀으면) 드롭 분류만 건너뛴다 —
    킥 진입·브레이크·빌드업에는 영향이 없다(BarFeatures 독스트링 참조)."""
    features = [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in range(1, 6)]
    features[2] = BarFeatures(bar=3, volume_norm=1.0, low_band_norm=4.0, vocal_band_ratio=None)
    events = classify_bar_events(features)
    assert [e for e in events if e.kind == "drop"] == []
    assert [e for e in events if e.kind == "kick_entry"] == [
        BarEvent("kick_entry", 3, 3, grade="measured")
    ]


def test_classify_bar_events_break_onset_count_none_is_not_read_as_zero() -> None:
    """``onset_count`` 가 ``None`` 이면 온셋 중앙값 계산과 온셋 기반 브레이크 분기
    양쪽에서 제외된다 — "0개"로 잘못 읽어 모든 마디를 브레이크로 분류하는 결함을
    재발 방지(``_BREAK_DIP_LOW_BAND_RATIO`` 주석 참조). 저역도 평탄하면(1.0)
    어떤 브레이크도 나오지 않아야 한다.
    """
    features = [
        BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0, onset_count=None)
        for i in range(1, 11)
    ]
    events = classify_bar_events(features)
    assert [e for e in events if e.kind == "break"] == []


def test_classify_bar_events_break_dip_conjunction_both_conditions_required() -> None:
    """브레이크(카드 t535 교정) — 저역 완화(dip, 0.45<저역≤0.7)와 온셋 중앙값 대비
    낮은 온셋이 **함께** 있어야 브레이크다. 저역만 dip거나 온셋만 낮으면(절대
    문턱 없이) 브레이크가 아니다 — 과거 "절대 온셋 개수" 방식의 결함(검출기
    자신의 온셋 척도가 지도 보고서 계기의 척도와 달라, 저역이 전혀 낮지 않은
    마디까지 브레이크로 잘못 분류됐다, progress.md §E.2 M3 "리드 재측정 메모")을
    재발 방지한다."""
    features = [
        BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0, onset_count=4) for i in range(1, 11)
    ]
    # bar 5 — 저역 dip(0.6, 0.45<0.6<=0.7) AND 온셋(1) <= 중앙값(4)*0.25=1.0 → 브레이크.
    features[4] = BarFeatures(bar=5, volume_norm=1.0, low_band_norm=0.6, onset_count=1)
    # bar 7 — 저역은 dip(0.6)이지만 온셋이 중앙값과 같다(4, 낮지 않음) → 브레이크 아님.
    features[6] = BarFeatures(bar=7, volume_norm=1.0, low_band_norm=0.6, onset_count=4)
    # bar 8 — 온셋은 0으로 아주 낮지만 저역이 dip 범위 밖(1.0, 평탄) → 브레이크 아님
    # (과거 절대 문턱 방식이면 onset=0<=2라 브레이크로 잘못 분류됐을 자리).
    features[7] = BarFeatures(bar=8, volume_norm=1.0, low_band_norm=1.0, onset_count=0)

    events = classify_bar_events(features)
    break_events = [e for e in events if e.kind == "break"]
    assert break_events == [BarEvent("break", 5, 5, grade="measured")]


def test_classify_bar_events_break_median_onset_excludes_none_entries() -> None:
    """온셋 중앙값은 ``onset_count`` 를 실제로 잰 마디만으로 계산한다 — ``None``
    이 섞인 마디를 "0개"로 읽어 중앙값을 왜곡하지 않는다."""
    # 중앙값 계산 표본 3개(8, 8, 8) → median=8, 문턱=0.25*8=2.0.
    features = [
        BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0, onset_count=8) for i in range(1, 4)
    ]
    features += [
        # bar 4 — dip(0.6) AND onset(2) <= 2.0 → 브레이크.
        BarFeatures(bar=4, volume_norm=1.0, low_band_norm=0.6, onset_count=2),
        # bar 5 — dip(0.6) 이지만 onset_count 를 못 쟀다(None) → 이 분기 제외,
        # None 을 0으로 잘못 읽었다면 브레이크가 됐을 자리.
        BarFeatures(bar=5, volume_norm=1.0, low_band_norm=0.6, onset_count=None),
    ]
    events = classify_bar_events(features)
    break_events = [e for e in events if e.kind == "break"]
    assert break_events == [BarEvent("break", 4, 4, grade="measured")]


# ---------------------------------------------------------------------------
# 6. LOVE ATTACK 부록 A 특징 픽스처(M3) — AC-LDBARMAP-007 + ±20% 민감도.
# ---------------------------------------------------------------------------


def _love_attack_truth_features() -> list[BarFeatures]:
    """지도 보고서 부록 A를 직접 파싱한 특징 — 오디오가 아니라 이미 커밋된 수치표다
    (``tools/barmap/ground_truth.parse_bar_features``, 하드코딩 사본 아님).
    """
    return [
        BarFeatures(
            bar=row.bar,
            volume_norm=row.volume_norm,
            low_band_norm=row.low_band_norm,
            vocal_band_ratio=row.vocal_band_ratio,
            onset_count=None,  # 부록 A 표에는 온셋 개수 열이 없다 — 못 쟀다고 읽는다.
        )
        for row in parse_bar_features()
    ]


def _event_recall_for(features: list[BarFeatures]) -> tuple[int, int, list]:
    events = classify_bar_events(features)
    detected = [(e.kind, e.start_bar) for e in events]
    from tools.barmap.ground_truth import parse_events

    truth = parse_events()
    result = event_recall(detected, truth)
    return result.matched, result.total, result.matches


def test_ac007_love_attack_report_features_recall_at_least_5_of_7() -> None:
    """AC-LDBARMAP-007 — 지도 보고서 부록 A 수치(음량·저역)만으로 분류해도 7개 사건
    중 5개 이상(70%) 적중해야 PASS. 드롭(63~66마디)은 참고 지표로만 보고하고
    이 분모·판정에 포함하지 않는다(REQ-LDBARMAP-009)."""
    features = _love_attack_truth_features()
    matched, total, matches = _event_recall_for(features)
    assert total == 7
    assert matched >= AC007_RECALL_THRESHOLD, f"{matched}/{total} — matches: {matches}"

    # 드롭은 참고 지표 — AC-007 분모에 들지 않으므로 여기서는 보고만 한다.
    drop_events = [e for e in classify_bar_events(features) if e.kind == "drop"]
    assert drop_events, "드롭(참고 지표)이 보고서 수치 경로에서는 적어도 하나 나와야 한다"


@pytest.mark.parametrize(
    ("constant_name", "factor"),
    [
        ("_KICK_ENTRY_LOW_BAND_RATIO", 0.8),
        ("_KICK_ENTRY_LOW_BAND_RATIO", 1.2),
        ("_BREAK_LOW_BAND_RATIO", 0.8),
        ("_BREAK_LOW_BAND_RATIO", 1.2),
    ],
)
def test_ac007_sensitivity_thresholds_plus_minus_20_percent_stay_at_least_5_of_7(
    monkeypatch: pytest.MonkeyPatch, constant_name: str, factor: float
) -> None:
    """문턱 ±20% 민감도(카드 t530 지시 3) — kick_entry·break 저역 문턱을 각각
    ±20% 흔들어도 AC-007 재현율이 5/7 밑으로 떨어지지 않는지 확인한다. 지식-날 위가
    아니라 견고함을 보여 주는 회귀다(진행기록 §E.2 M3 민감도 표와 같은 수치)."""
    base_value = getattr(bar_map_module, constant_name)
    monkeypatch.setattr(bar_map_module, constant_name, base_value * factor)
    features = _love_attack_truth_features()
    matched, total, matches = _event_recall_for(features)
    assert matched >= AC007_RECALL_THRESHOLD, (
        f"{constant_name}*{factor}={base_value * factor}: {matched}/{total} — {matches}"
    )


@pytest.mark.parametrize("build_min_bars", [2, 3, 4])
def test_ac007_sensitivity_build_min_bars_stays_at_least_5_of_7(
    monkeypatch: pytest.MonkeyPatch, build_min_bars: int
) -> None:
    """빌드업 최소 마디 수 문턱(정수라 ±20%는 ±1마디로 해석)도 흔들어 본다."""
    monkeypatch.setattr(bar_map_module, "_BUILD_MIN_BARS", build_min_bars)
    features = _love_attack_truth_features()
    matched, total, matches = _event_recall_for(features)
    assert matched >= AC007_RECALL_THRESHOLD, f"build_min_bars={build_min_bars}: {matched}/{total}"


# ---------------------------------------------------------------------------
# 7. 로컬 전용 회귀(M3) — 실제 LOVE ATTACK mp3가 있을 때만 돈다.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not LOVE_ATTACK_MP3_PATH.exists(),
    reason=f"로컬 전용 — 원곡 부재: {LOVE_ATTACK_MP3_PATH}",
)
def test_real_love_attack_extraction_reproduces_volume_and_achieves_ac007() -> None:
    """로컬 전용 — 실제 오디오에서 ``extract_bar_features`` 로 잰 음량(RMS)이 지도
    보고서 부록 A 수치와 가깝게 재현되고(같은 RMS 방법론, analyze.py 와 같은 경로),
    전체 파이프라인(``detect_beat_grid`` → ``derive_bars`` → ``extract_bar_features``
    → ``classify_bar_events``)이 AC-LDBARMAP-007 ≥5/7 을 재현하는지 확인한다.

    **알려진 한계(정직하게 기록, progress.md Gaps 참조)**: 저역(``low_band_norm``)과
    보컬 대역 비율(``vocal_band_ratio``)은 지도 보고서의 비공개 전용 파이프라인
    (``measure_music_map.py``, 이 저장소에 없음)과 **다른** 분리 방법(이 모듈은
    ``librosa.decompose.hpss``)을 쓰므로 절대 수치까지 재현하지는 않는다 — 이
    시험은 음량만 수치로 재현을 확인하고, 저역·보컬 대역은 **분류 결과(재현율)**
    로만 재현을 확인한다.

    카드 t535 확장 — AC-LDBARMAP-007 **정밀도 조건**(≥70%, 분모는 범위② 점
    사건만)도 같은 실제 오디오 경로에서 재확인한다(progress.md §E.2 M3 "정밀도
    보강" 참조).
    """
    audio_bytes = LOVE_ATTACK_MP3_PATH.read_bytes()
    grid = detect_beat_grid(audio_bytes)
    assert isinstance(grid, BeatGridResult)
    bar_map = derive_bars(grid.beat_times_ms, CONFIRMED_FIRST_BEAT_OFFSET)
    assert isinstance(bar_map, BarMap)

    features = extract_bar_features(audio_bytes, bar_map.bar_boundaries_ms)
    assert isinstance(features, tuple)
    assert len(features) == 82

    truth_rows = parse_bar_features()
    assert len(truth_rows) == len(features)
    for extracted, truth in zip(features, truth_rows, strict=True):
        assert extracted.bar == truth.bar
        assert extracted.volume_norm == pytest.approx(truth.volume_norm, abs=0.05), (
            f"bar={extracted.bar} extracted={extracted.volume_norm} truth={truth.volume_norm}"
        )

    matched, total, matches = _event_recall_for(list(features))
    assert total == 7
    assert matched >= AC007_RECALL_THRESHOLD, f"{matched}/{total} — matches: {matches}"

    events = classify_bar_events(list(features))
    detected = [(e.kind, e.start_bar) for e in events if e.kind in ("break", "kick_entry")]
    evidence = parse_precision_evidence()
    precision = event_precision(detected, evidence)
    assert precision.total > 0, "분모 0 — 빈 분류기는 정밀도를 주장할 수 없다"
    assert precision.rate_pct >= AC007_PRECISION_THRESHOLD_PCT, str(precision)


# ---------------------------------------------------------------------------
# 8. AC-LDBARMAP-007 정밀도 조건(카드 t535) — 증거 파서 + 정밀도 채점기 +
#    LOVE ATTACK 실제 오디오 마디별 특징 고정 픽스처(CI-safe, 오디오 아님).
# ---------------------------------------------------------------------------

#: acceptance.md AC-LDBARMAP-007 § "근거 있음 판정" 표의 스냅샷(카드 t535,
#: 2026-10-10) — 아래 테스트는 ``parse_precision_evidence`` 가 부록 A "순간"
#: 칸에서 직접 파싱한 결과가 이 스냅샷과 같은지 검산한다(검산 대상이지, 생산
#: 코드가 이 리터럴을 쓰지는 않는다 — 생산 코드는 항상 보고서를 다시 읽는다).
EXPECTED_BREAK_EVIDENCE_BARS = frozenset({3, 14, 33, 34, 61, 62, 67, 82})
EXPECTED_KICK_ENTRY_EVIDENCE_BARS = frozenset({7, 8, 18, 46, 69, 70})


def test_ground_truth_parses_precision_evidence_matches_ac_table() -> None:
    """부록 A "순간" 칸 파서가 acceptance.md AC-007 § 근거 있음 판정 표와 같은
    마디 집합을 낸다 — 17마디(빌드업의 꼬리, kick_entry 아님)가 제외됐는지도
    확인한다."""
    evidence = parse_precision_evidence()
    assert evidence["break"] == EXPECTED_BREAK_EVIDENCE_BARS
    assert evidence["kick_entry"] == EXPECTED_KICK_ENTRY_EVIDENCE_BARS
    assert 17 not in evidence["kick_entry"], "17마디는 빌드업의 꼬리다 — kick_entry 증거가 아니다"


def test_event_precision_counts_each_detection_independently_against_evidence() -> None:
    """``event_precision`` — 검출별 독립 판정(증거 쪽 1:1 소진 요구 없음).

    한 증거 표시(바 10)가 ±1마디 안의 검출 둘(9·11)을 동시에 지지할 수 있다."""
    evidence = {"break": frozenset({10}), "kick_entry": frozenset({20})}
    detected = [("break", 9), ("break", 11), ("break", 50), ("kick_entry", 20)]
    result = event_precision(detected, evidence)
    assert result.total == 4
    assert result.supported == 3
    assert result.rate_pct == pytest.approx(75.0)
    assert result.unsupported == [("break", 50)]


def test_event_precision_denominator_zero_is_fail_not_vacuous_pass() -> None:
    """분모 0 규칙(acceptance.md § 문턱) — 검출이 하나도 없으면 ``rate_pct`` 는
    0.0(공허한 100%로 읽지 않는다). 70% 문턱과 비교하면 FAIL이다."""
    result = event_precision([], {"break": frozenset({10})})
    assert result.total == 0
    assert result.supported == 0
    assert result.rate_pct == 0.0
    assert result.rate_pct < AC007_PRECISION_THRESHOLD_PCT


@pytest.fixture(scope="module")
def love_attack_bar_features_real_fixture() -> dict:
    with LOVE_ATTACK_BAR_FEATURES_REAL_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _bar_features_from_real_fixture(fixture: dict) -> list[BarFeatures]:
    return [
        BarFeatures(
            bar=row["bar"],
            volume_norm=row["volume_norm"],
            low_band_norm=row["low_band_norm"],
            vocal_band_ratio=row["vocal_band_ratio"],
            onset_count=row["onset_count"],
        )
        for row in fixture["bar_features"]
    ]


def _recall_and_precision_for(features: list[BarFeatures]) -> tuple[int, int, object]:
    matched, total, _matches = _event_recall_for(features)
    events = classify_bar_events(features)
    detected = [(e.kind, e.start_bar) for e in events if e.kind in ("break", "kick_entry")]
    precision = event_precision(detected, parse_precision_evidence())
    return matched, total, precision


def test_ac007_real_audio_fixture_has_82_bars(
    love_attack_bar_features_real_fixture: dict,
) -> None:
    """픽스처 자체의 검산 — 82마디, 첫 박 오프셋이 AC-LDBARMAP-016 확정값(1)과 같다."""
    assert len(love_attack_bar_features_real_fixture["bar_features"]) == 82
    assert love_attack_bar_features_real_fixture["first_beat_offset"] == CONFIRMED_FIRST_BEAT_OFFSET


def test_ac007_real_audio_fixture_recall_and_precision_both_pass(
    love_attack_bar_features_real_fixture: dict,
) -> None:
    """CI-safe(원곡 불필요) — LOVE ATTACK 실제 오디오 경로②에서 재현율(≥5/7)과
    **정밀도(≥70%)** 가 새 브레이크 규칙(카드 t535)으로 함께 PASS 하는지 확인한다."""
    features = _bar_features_from_real_fixture(love_attack_bar_features_real_fixture)
    matched, total, precision = _recall_and_precision_for(features)
    assert total == 7
    assert matched >= AC007_RECALL_THRESHOLD, f"recall {matched}/{total}"
    assert precision.total > 0
    assert precision.rate_pct >= AC007_PRECISION_THRESHOLD_PCT, str(precision)


def test_ac007_real_audio_fixture_old_absolute_onset_rule_would_have_failed_precision(
    love_attack_bar_features_real_fixture: dict,
) -> None:
    """정직한 회귀 기록(카드 t535) — 카드 t535 **이전**의 구 규칙(저역≤0.45배 OR
    온셋 절대 개수≤2개)을 이 픽스처에 그대로 돌리면 정밀도가 8/18(44.4%)로
    70% 문턱에 크게 못 미친다(progress.md §E.2 M3 "리드 재측정 메모"의 실측과
    일치). 구 상수는 ``bar_map.py``에서 이미 제거됐으므로 여기서는 역사적
    수치로만 재현한다 — 생산 코드가 이 값을 쓰지 않는다."""
    features = _bar_features_from_real_fixture(love_attack_bar_features_real_fixture)
    by_bar = {f.bar: f for f in features}
    old_break_bars = sorted(
        bar
        for bar, f in by_bar.items()
        if f.low_band_norm <= 0.45 or (f.onset_count is not None and f.onset_count <= 2)
    )
    old_kick_bars = sorted(bar for bar, f in by_bar.items() if f.low_band_norm >= 2.0)
    old_detected = [("break", b) for b in old_break_bars] + [
        ("kick_entry", b) for b in old_kick_bars
    ]
    precision = event_precision(old_detected, parse_precision_evidence())
    assert precision.total == 18
    assert precision.supported == 8
    assert precision.rate_pct == pytest.approx(44.4, abs=0.1)
    assert precision.rate_pct < AC007_PRECISION_THRESHOLD_PCT, (
        "이 테스트는 구 규칙이 FAIL 했음을 문서화한다 — PASS 하면 역사 재현이 깨졌다는 뜻"
    )


@pytest.mark.parametrize(
    ("constant_name", "factor"),
    [
        ("_KICK_ENTRY_LOW_BAND_RATIO", 0.8),
        ("_KICK_ENTRY_LOW_BAND_RATIO", 1.2),
        ("_BREAK_LOW_BAND_RATIO", 0.8),
        ("_BREAK_LOW_BAND_RATIO", 1.2),
        ("_BREAK_ONSET_FRACTION_OF_MEDIAN", 0.8),
        ("_BREAK_ONSET_FRACTION_OF_MEDIAN", 1.2),
    ],
)
def test_ac007_real_audio_fixture_sensitivity_recall_and_precision_stay_passing(
    love_attack_bar_features_real_fixture: dict,
    monkeypatch: pytest.MonkeyPatch,
    constant_name: str,
    factor: float,
) -> None:
    """문턱 ±20% 민감도(카드 t535) — 실제 오디오 경로에서 재현율·정밀도 둘 다
    여전히 PASS 선 위인지 확인한다. ``_BREAK_DIP_LOW_BAND_RATIO`` 는 지식의 날
    (−20%에서 recall 이 정확히 문턱에 닿는다)이라 별도 테스트로 정직하게
    기록한다(아래 ``test_...dip_ratio_minus_20_percent_is_a_knife_edge``)."""
    base_value = getattr(bar_map_module, constant_name)
    monkeypatch.setattr(bar_map_module, constant_name, base_value * factor)
    features = _bar_features_from_real_fixture(love_attack_bar_features_real_fixture)
    matched, total, precision = _recall_and_precision_for(features)
    assert matched >= AC007_RECALL_THRESHOLD, (
        f"{constant_name}*{factor}={base_value * factor}: recall {matched}/{total}"
    )
    assert precision.total > 0
    assert precision.rate_pct >= AC007_PRECISION_THRESHOLD_PCT, (
        f"{constant_name}*{factor}={base_value * factor}: precision {precision}"
    )


def test_ac007_real_audio_fixture_dip_ratio_minus_20_percent_is_a_knife_edge(
    love_attack_bar_features_real_fixture: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """지식의 날, 정직하게 기록(카드 t535 지시) — ``_BREAK_DIP_LOW_BAND_RATIO``
    기준값(0.7)을 −20%(0.56)로 낮추면 33·61마디(저역 0.6·0.59 — 기준값 안쪽이지만
    0.56 밖)가 브레이크에서 빠져 재현율이 **정확히** 5/7(문턱에 닿는다, 그 밑은
    아니다)로, 정밀도가 **정확히** 3/4(75%)로 떨어진다. 둘 다 여전히 PASS지만
    문턱에 바로 붙어 있다는 사실을 숨기지 않는다."""
    base = bar_map_module._BREAK_DIP_LOW_BAND_RATIO
    monkeypatch.setattr(bar_map_module, "_BREAK_DIP_LOW_BAND_RATIO", base * 0.8)
    features = _bar_features_from_real_fixture(love_attack_bar_features_real_fixture)
    matched, total, precision = _recall_and_precision_for(features)
    assert (matched, total) == (5, 7), f"지식의 날 수치가 바뀌었다: {matched}/{total}"
    assert precision.total == 4
    assert precision.supported == 3
    assert precision.rate_pct == pytest.approx(75.0)
    assert matched >= AC007_RECALL_THRESHOLD
    assert precision.rate_pct >= AC007_PRECISION_THRESHOLD_PCT


def test_gen_ear_check_candidates_build_candidate_rows_matches_real_fixture() -> None:
    """``gen_ear_check_candidates.build_candidate_rows`` — 새 규칙 기준, 실제
    오디오 고정 픽스처에서 근거 없음 검출이 정확히 kick_entry 4마디 하나인지
    확인한다(진행기록 §E.2 M3 "정밀도 보강"의 실측과 일치)."""
    features, bar_boundaries_ms = load_fixture()
    by_bar = {f.bar: f for f in features}
    events = classify_bar_events(features)
    detected = [(e.kind, e.start_bar) for e in events if e.kind in ("break", "kick_entry")]
    evidence = parse_precision_evidence()
    result = event_precision(detected, evidence)

    rows = build_candidate_rows(features, bar_boundaries_ms, result.unsupported)
    assert len(rows) == 1
    assert rows[0]["bar"] == 4
    assert rows[0]["kind"] == "kick_entry"
    assert rows[0]["downbeat_mmss"] == "0:07.92"
    assert by_bar[4].low_band_norm == pytest.approx(rows[0]["low_band_norm"])


def test_extract_bar_features_garbage_bytes_returns_failure_not_raise() -> None:
    result = extract_bar_features(
        b"this is not an audio file, just garbage bytes \x00\x01\x02", (0, 2136, 4272)
    )
    assert isinstance(result, BarFeaturesFailure)
    assert result.reason


def test_extract_bar_features_rejects_fewer_than_2_bar_boundaries() -> None:
    result = extract_bar_features(b"irrelevant for this check", (0,))
    assert isinstance(result, BarFeaturesFailure)
    assert "2개 미만" in result.reason
