"""후보 검출기 3종 — M1 보정 대상(REQ-LDBARMAP-003).

**순환성(circularity) 경고**: 후보 A(hop=512)는 지도 보고서의 정답지를 만든
`librosa.beat.beat_track(hop_length=512)`와 **같은 비트 추적 경로**다(지도 보고서
§1 "비트·BPM" 행, `server/audio/analyze.py:352-354`와 동일한 hop). 이 후보가 비트
적중률에서 높은 점수를 받는 것은 같은 계기로 같은 것을 다시 재는 것에 가깝다 —
검증 증거로 제시하지 않는다. 후보 B(hop=256, 같은 알고리즘·다른 hop)는 약하게
독립적이다. 후보 C(PLP, 다른 알고리즘 계열)가 정답지의 비트 출처로부터 가장
독립적인 후보다.

다운비트 위상(1~4박 중 어느 것이 "하나"인가)은 **세 후보 모두 정답지를 보지 않고
자체 신호 규칙으로 고른다**:
- 후보 A: 온셋 강도가 그 위상의 박 위치에 몰리는 정도(온셋 악센트)
- 후보 B: 크로마(화성) 변화가 그 위상의 박 경계에서 가장 큰 정도(화성 변화,
  지도 보고서 §3의 "화성 변화" 근거와 같은 발상이지만 이 코드가 독자적으로 계산한다)
- 후보 C: 저역(35~120Hz) 에너지가 직전 박보다 크게 뛰어오르는 정도(저역 도약)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.audio.analyze import _tempo_from_beats  # noqa: E402  (읽기 전용 import)


@dataclass
class CandidateResult:
    name: str
    hop_length: int
    circular: bool
    raw_bpm: float
    beat_times: np.ndarray
    chosen_phase: int
    phase_scores: dict[int, float]
    downbeats: np.ndarray  # 채택한 위상의 다운비트 시각들(1마디부터)
    onset_times: np.ndarray
    phase_method: str
    bpm_check: Any = None  # scorer.BpmMultipleCheck | None — 후보 C(BPM 보정 경로)만 채움
    grid_fit_ratio: float | None = None  # 후보 C만 — 재구성 격자의 온셋 정합 비율
    raw_peak_count: int | None = None  # 후보 C만 — 보정 전 원시 피크 개수
    bars_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.bars_count = len(self.downbeats)


def _load_audio(audio_path: Path):
    import librosa

    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    return y, sr


def _detect_beats(y, sr, hop_length: int) -> tuple[float, np.ndarray]:
    """analyze.py와 같은 방식으로 박 시각을 재고 BPM을 낸다(박 간격의 중앙값).

    `_tempo_from_beats`는 `server/audio/analyze.py`의 기존 함수를 **읽기만** 하고
    그대로 호출한다 — M1은 `server/` 아래 어떤 파일도 수정하지 않는다
    (REQ-LDBARMAP-002/003, plan.md §D).
    """
    import librosa

    beat_times = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length, units="time")[1]
    bpm, _confidence = _tempo_from_beats(np, beat_times)
    if bpm is None:
        bpm = 0.0
    return float(bpm), np.asarray(beat_times, dtype=float)


def _pick_phase_by_onset_accent(
    y, sr, beat_times: np.ndarray, hop_length: int
) -> tuple[int, dict[int, float]]:
    """위상 선택 1 — 온셋 강도가 그 위상의 박에 몰리는 정도(정답지를 보지 않는다)."""
    import librosa

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    if len(beat_times) < 4:
        return 0, {p: 0.0 for p in range(4)}
    beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=hop_length)
    beat_frames = np.clip(beat_frames, 0, len(onset_env) - 1)
    beat_strengths = onset_env[beat_frames]
    scores: dict[int, float] = {}
    for p in range(4):
        idxs = beat_strengths[p::4]
        scores[p] = float(np.mean(idxs)) if len(idxs) else 0.0
    best_phase = max(scores, key=scores.get)
    return best_phase, scores


def _pick_phase_by_lowband_jump(
    y, sr, beat_times: np.ndarray, hop_length: int
) -> tuple[int, dict[int, float]]:
    """위상 선택 3 — 저역(35~120Hz) 에너지가 그 위상의 박에서 직전 박보다 크게
    뛰어오르는 정도(지도 보고서 §3 "구간 시작 부근 저역 도약" 근거와 같은 발상,
    이 코드가 독자적으로 계산한다). 정답지를 보지 않는다.
    """
    import librosa

    stft = np.abs(librosa.stft(y, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr)
    low_mask = (freqs >= 35) & (freqs <= 120)
    low_energy = stft[low_mask, :].mean(axis=0) if low_mask.any() else np.zeros(stft.shape[1])
    low_frame_times = librosa.frames_to_time(
        np.arange(len(low_energy)), sr=sr, hop_length=hop_length
    )

    n_beats = len(beat_times)
    if n_beats < 5:
        return 0, {p: 0.0 for p in range(4)}
    per_beat_energy = np.zeros(n_beats - 1)
    for i in range(n_beats - 1):
        t0, t1 = beat_times[i], beat_times[i + 1]
        mask = (low_frame_times >= t0) & (low_frame_times < t1)
        per_beat_energy[i] = float(low_energy[mask].mean()) if mask.any() else 0.0

    # 절대 차분을 전체 중앙값으로 정규화 — 직전 박이 거의 0에 가까운 드문 프레임에서
    # 상대 비율(차분/직전값)을 쓰면 분모가 작아 값이 터진다(실측 확인, t530).
    median_energy = float(np.median(per_beat_energy)) or 1e-9
    diff = np.diff(per_beat_energy, prepend=per_beat_energy[0])
    jump = diff / median_energy

    scores: dict[int, float] = {}
    for p in range(4):
        idxs = jump[p::4]
        scores[p] = float(np.mean(idxs)) if len(idxs) else 0.0
    best_phase = max(scores, key=scores.get)
    return best_phase, scores


def _pick_phase_by_harmonic_change(
    y, sr, beat_times: np.ndarray, hop_length: int
) -> tuple[int, dict[int, float]]:
    """위상 선택 2 — 크로마(화성) 변화가 그 위상의 박 경계에서 가장 큰 정도.

    지도 보고서 §3의 "화성 변화" 근거(위상 1에서 69.7, 다른 위상은 40~52)와 같은
    발상이지만, 정답지 숫자를 베끼지 않고 이 코드가 크로마그램에서 독자적으로 계산한다.
    """
    import librosa

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    n_beats = len(beat_times)
    if n_beats < 5:
        return 0, {p: 0.0 for p in range(4)}
    beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=hop_length)
    beat_frames = np.clip(beat_frames, 0, chroma.shape[1] - 1)

    # 박 구간별 평균 크로마 벡터
    vecs = []
    for i in range(n_beats - 1):
        f0, f1 = int(beat_frames[i]), int(beat_frames[i + 1])
        if f1 <= f0:
            f1 = f0 + 1
        vecs.append(chroma[:, f0:f1].mean(axis=1))
    vecs = np.array(vecs)

    change = np.zeros(len(vecs))
    for i in range(1, len(vecs)):
        a, b = vecs[i - 1], vecs[i]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        cos = float(np.dot(a, b) / denom) if denom > 0 else 1.0
        change[i] = 1.0 - cos

    scores: dict[int, float] = {}
    for p in range(4):
        idxs = change[p::4]
        scores[p] = float(np.mean(idxs)) if len(idxs) else 0.0
    best_phase = max(scores, key=scores.get)
    return best_phase, scores


def run_candidate_a_hop512_onset_accent(audio_path: Path) -> CandidateResult:
    """후보 A — hop=512(정답지와 같은 비트 추적, 순환성 있음) + 온셋 악센트 위상 선택."""
    y, sr = _load_audio(audio_path)
    hop_length = 512
    raw_bpm, beat_times = _detect_beats(y, sr, hop_length)
    phase, scores = _pick_phase_by_onset_accent(y, sr, beat_times, hop_length)
    downbeats = beat_times[phase::4]
    import librosa

    onset_times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, units="time")
    return CandidateResult(
        name="A-hop512-onset-accent",
        hop_length=hop_length,
        circular=True,
        raw_bpm=raw_bpm,
        beat_times=beat_times,
        chosen_phase=phase,
        phase_scores=scores,
        downbeats=downbeats,
        onset_times=np.asarray(onset_times, dtype=float),
        phase_method="onset-accent",
    )


def run_candidate_b_hop256_harmonic_change(audio_path: Path) -> CandidateResult:
    """후보 B — hop=256(정답지의 비트 출처로부터 독립) + 화성 변화 위상 선택."""
    y, sr = _load_audio(audio_path)
    hop_length = 256
    raw_bpm, beat_times = _detect_beats(y, sr, hop_length)
    phase, scores = _pick_phase_by_harmonic_change(y, sr, beat_times, hop_length)
    downbeats = beat_times[phase::4]
    import librosa

    onset_times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, units="time")
    return CandidateResult(
        name="B-hop256-harmonic-change",
        hop_length=hop_length,
        circular=False,
        raw_bpm=raw_bpm,
        beat_times=beat_times,
        chosen_phase=phase,
        phase_scores=scores,
        downbeats=downbeats,
        onset_times=np.asarray(onset_times, dtype=float),
        phase_method="harmonic-change",
    )


def run_candidate_c_plp_lowband_jump(audio_path: Path) -> CandidateResult:
    """후보 C — PLP(Predominant Local Pulse, `librosa.beat.plp`) + 저역 도약 위상 선택.

    `librosa.beat.beat_track`(동적 계획법 추적기)과 **다른 알고리즘 계열**이라
    정답지의 비트 출처(`beat_track` hop=512)로부터 가장 독립적인 후보다. 기본
    피크 선택 파라미터로는 이 곡에서 원시 BPM이 224.69(두 배 함정, REQ-LDBARMAP-006)
    로 나온다 — 이 함정이 실제로 걸리는 사례를 그대로 보여 주고, 격자 정합도
    비교를 거쳐 112.35 쪽으로 보정한 등간격 격자를 재구성한다(`check_bpm_multiple`
    + `reconstruct_uniform_grid`, scorer.py).
    """
    import librosa

    from .scorer import check_bpm_multiple, reconstruct_uniform_grid

    y, sr = _load_audio(audio_path)
    hop_length = 512
    duration_sec = len(y) / sr

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    peak_frames = librosa.util.peak_pick(
        pulse, pre_max=10, post_max=10, pre_avg=10, post_avg=10, delta=0.02, wait=10
    )
    raw_peak_times = librosa.frames_to_time(peak_frames, sr=sr, hop_length=hop_length)
    raw_bpm, _confidence = _tempo_from_beats(np, raw_peak_times)
    if raw_bpm is None:
        raw_bpm = 0.0

    bpm_check = check_bpm_multiple(float(raw_bpm), raw_peak_times, duration_sec)
    adopted_bpm = bpm_check.adopted_bpm
    grid, grid_fit_ratio = reconstruct_uniform_grid(raw_peak_times, adopted_bpm, duration_sec)

    phase, scores = _pick_phase_by_lowband_jump(y, sr, grid, hop_length)
    downbeats = grid[phase::4]
    onset_times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, units="time")

    return CandidateResult(
        name="C-plp-lowband-jump",
        hop_length=hop_length,
        circular=False,
        raw_bpm=float(raw_bpm),
        beat_times=grid,
        chosen_phase=phase,
        phase_scores=scores,
        downbeats=downbeats,
        onset_times=np.asarray(onset_times, dtype=float),
        phase_method="lowband-jump",
        bpm_check=bpm_check,
        grid_fit_ratio=grid_fit_ratio,
        raw_peak_count=len(raw_peak_times),
    )


def alternate_phase_downbeats(candidate: CandidateResult, phase: int) -> np.ndarray:
    """같은 후보의 비트 시각에서 다른 위상(예: 채택하지 않은 대안)의 다운비트를 뽑는다.

    지도 보고서 §3/§6이 위상 1을 채택하고 위상 0을 "대안"으로 남겨 둔 것과 같은
    구조 — 각 후보에 대해 위상 0/1 점수를 모두 보고한다(과제 지시사항).
    """
    return candidate.beat_times[phase::4]


def detect_events_from_bars(y, sr, downbeats: np.ndarray, hop_length: int) -> list[tuple[str, int]]:
    """마디별 변화 이벤트(킥 진입·빌드업·킥 멈춤) — 지도 보고서 §1 규칙을 간단화한 버전.

    M1 범위(plan.md §C M1) — "간단한 마디별 규칙"만 쓴다. M3가 본 분류기를 맡는다
    (acceptance.md AC-007 근거 칸). 저역(35~120Hz) 에너지·음량(RMS) 모두 마디 중앙값
    대비 비로 정규화한다(지도 보고서 §1과 같은 정규화 방식).
    """
    import librosa

    n_bars = len(downbeats) - 1  # 마지막 다운비트는 끝 경계로만 쓴다(완결된 마디만 센다)
    if n_bars <= 0:
        return []

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # 저역 35~120Hz 성분 에너지 — STFT 대역 합산
    stft = np.abs(librosa.stft(y, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr)
    low_band_mask = (freqs >= 35) & (freqs <= 120)
    if low_band_mask.any():
        low_band_energy = stft[low_band_mask, :].mean(axis=0)
    else:
        low_band_energy = np.zeros(stft.shape[1])
    low_frame_times = librosa.frames_to_time(
        np.arange(len(low_band_energy)), sr=sr, hop_length=hop_length
    )

    bar_volume = np.zeros(n_bars)
    bar_lowband = np.zeros(n_bars)
    for i in range(n_bars):
        t0, t1 = downbeats[i], downbeats[i + 1]
        rms_mask = (frame_times >= t0) & (frame_times < t1)
        low_mask = (low_frame_times >= t0) & (low_frame_times < t1)
        bar_volume[i] = float(rms[rms_mask].mean()) if rms_mask.any() else 0.0
        bar_lowband[i] = float(low_band_energy[low_mask].mean()) if low_mask.any() else 0.0

    vol_median = np.median(bar_volume) or 1.0
    low_median = np.median(bar_lowband) or 1.0
    vol_norm = bar_volume / vol_median
    low_norm = bar_lowband / low_median

    events: list[tuple[str, int]] = []
    for i in range(n_bars):
        bar_num = i + 1  # 1마디부터
        if low_norm[i] >= 2.5:
            events.append(("kick_entry", bar_num))
        if low_norm[i] <= 0.35:
            # "break" — spec.md §5 열린 결정 0 events[].kind 어휘(카드 t530에서
            # ground_truth.py 와 통일, M1 당시엔 "kick_absence"를 썼다).
            events.append(("break", bar_num))

    # 빌드업 — 음량이 3마디 이상 연속 상승하는 구간의 시작 마디
    i = 0
    while i < n_bars - 2:
        if vol_norm[i] < vol_norm[i + 1] < vol_norm[i + 2]:
            j = i
            while j + 1 < n_bars and vol_norm[j] < vol_norm[j + 1]:
                j += 1
            events.append(("build", i + 1))
            i = j
        else:
            i += 1

    return events
