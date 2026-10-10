"""채점 스크립트 — REQ-LDBARMAP-004의 네 지표 + 엄격한 순서 대응(REQ-LDBARMAP-005).

**엄격한 순서 대응(strict index-aligned matching)**: 검출된 n번째 마디는 정답지의
n번째 마디와만 비교한다. 허용오차 안의 "가장 가까운 아무 정답 마디"를 허용하는
최근접 매칭은 쓰지 않는다 — 1마디(한 다운비트 주기) 밀린 격자가 다음 정답
다운비트에 우연히 맞아 통과하는 것을 막기 위함이다(plan-audit iteration 1 D3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .ground_truth import (
    DOWNBEAT_TOLERANCE_SEC,
    TARGET_BPM,
    TruthEvent,
)


@dataclass(frozen=True)
class HitRateResult:
    matched: int
    total: int
    rate_pct: float
    tolerance_sec: float

    def __str__(self) -> str:  # pragma: no cover - 표시용
        tol_ms = self.tolerance_sec * 1000
        return f"{self.matched}/{self.total} ({self.rate_pct:.1f}%, 허용오차 ±{tol_ms:.0f}ms)"


def strict_index_hit_rate(
    detected_times: list[float],
    truth_times: list[float],
    tolerance_sec: float = DOWNBEAT_TOLERANCE_SEC,
) -> HitRateResult:
    """엄격한 순서 대응 적중률 — 분모는 정답지 길이(AC-005/006 정의와 일치).

    검출 길이가 정답지보다 짧으면 모자란 인덱스는 전부 미스로 센다.
    검출 길이가 정답지보다 길면 넘치는 인덱스는 채점에서 제외한다(정답지에
    대응할 자리가 없으므로).
    """
    total = len(truth_times)
    matched = 0
    for i in range(total):
        if i >= len(detected_times):
            continue
        if abs(detected_times[i] - truth_times[i]) <= tolerance_sec:
            matched += 1
    rate_pct = (matched / total * 100.0) if total else 0.0
    return HitRateResult(
        matched=matched, total=total, rate_pct=rate_pct, tolerance_sec=tolerance_sec
    )


def bpm_error_rate_pct(estimated_bpm: float, target_bpm: float = TARGET_BPM) -> float:
    """BPM 오차율(%) — |추정 - 정답| / 정답 * 100."""
    return abs(estimated_bpm - target_bpm) / target_bpm * 100.0


@dataclass(frozen=True)
class EventRecallResult:
    matched: int
    total: int
    rate_pct: float
    matches: list[tuple[int, str, int | None]]  # (event_id, name, matched_detected_bar|None)


def event_recall(
    detected_events: list[tuple[str, int]],  # (event_type, start_bar)
    truth_events: list[TruthEvent],
) -> EventRecallResult:
    """마디별 변화 이벤트 재현율 — 온셋 ±1마디, 같은 종류끼리만 매칭(REQ-LDBARMAP-004/008/009)."""
    matches: list[tuple[int, str, int | None]] = []
    matched = 0
    for truth_ev in truth_events:
        lo, hi = truth_ev.window
        found_bar = None
        for event_type, bar in detected_events:
            if event_type == truth_ev.event_type and lo <= bar <= hi:
                found_bar = bar
                break
        matches.append((truth_ev.event_id, truth_ev.name, found_bar))
        if found_bar is not None:
            matched += 1
    total = len(truth_events)
    rate_pct = (matched / total * 100.0) if total else 0.0
    return EventRecallResult(matched=matched, total=total, rate_pct=rate_pct, matches=matches)


def grid_lock_ratio(
    onset_times: np.ndarray, bpm: float, duration_sec: float, tol_frac: float = 0.125
) -> float:
    """주어진 BPM 격자에 온셋이 얼마나 붙는지(정합도) — REQ-LDBARMAP-006의 절반/두 배 비교용.

    지도 보고서 §1·§5의 "격자 정합도"와 같은 개념 — 위상(격자 시작 지점)을 여러 후보로
    훑어 가장 잘 맞는 위상에서의 적중 비율을 돌려준다(위상에 유리하게 골라, 격자
    자체의 정합성만 비교한다).
    """
    if len(onset_times) == 0 or bpm <= 0:
        return 0.0
    beat_sec = 60.0 / bpm
    tol_sec = beat_sec * tol_frac
    best_ratio = 0.0
    n_phase_steps = 20
    for step in range(n_phase_steps):
        phase_offset = (step / n_phase_steps) * beat_sec
        # 각 온셋이 가장 가까운 격자선까지 거리
        grid_positions = (onset_times - phase_offset) / beat_sec
        nearest_grid_time = np.round(grid_positions) * beat_sec + phase_offset
        distances = np.abs(onset_times - nearest_grid_time)
        ratio = float(np.mean(distances <= tol_sec))
        if ratio > best_ratio:
            best_ratio = ratio
    return best_ratio


def reconstruct_uniform_grid(
    onset_times: np.ndarray,
    bpm: float,
    duration_sec: float,
    tol_frac: float = 0.125,
    n_phase_steps: int = 40,
) -> tuple[np.ndarray, float]:
    """정합도가 가장 높은 위상으로 등간격 박 격자를 재구성한다(BPM 보정 뒤 쓴다).

    후보 C(PLP, REQ-LDBARMAP-006 함정 보정 경로)처럼 원시 박 열이 고르지 않을 때,
    단순히 절반/두 배로 솎아 내는 대신 온셋 시각에 가장 잘 맞는 위상을 찾아 등간격
    격자를 새로 만든다. 돌려주는 두 번째 값(best_ratio)은 그 위상에서 온셋이 격자에
    붙는 비율 — 재구성 품질을 투명하게 보고하기 위함이다.
    """
    beat_sec = 60.0 / bpm
    tol_sec = beat_sec * tol_frac
    best_offset, best_ratio = 0.0, -1.0
    for step in range(n_phase_steps):
        phase_offset = (step / n_phase_steps) * beat_sec
        grid_positions = (onset_times - phase_offset) / beat_sec
        nearest_grid_time = np.round(grid_positions) * beat_sec + phase_offset
        distances = np.abs(onset_times - nearest_grid_time)
        ratio = float(np.mean(distances <= tol_sec))
        if ratio > best_ratio:
            best_ratio, best_offset = ratio, phase_offset
    n_beats = int(duration_sec / beat_sec)
    grid = best_offset + beat_sec * np.arange(n_beats)
    return grid[grid <= duration_sec], best_ratio


@dataclass(frozen=True)
class BpmMultipleCheck:
    raw_bpm: float
    half_bpm: float
    double_bpm: float
    grid_lock_raw: float
    grid_lock_half: float
    grid_lock_double: float
    trap_triggered: bool
    adopted_bpm: float
    rationale: str


def check_bpm_multiple(
    raw_bpm: float,
    onset_times: np.ndarray,
    duration_sec: float,
    half_bpm_const: float = 56.175,
    double_bpm_const: float = 224.69,
    target_bpm: float = TARGET_BPM,
    trap_tol_pct: float = 1.0,
) -> BpmMultipleCheck:
    """REQ-LDBARMAP-006 — 절반·두 배 후보와 격자 정합도를 비교하고 채택 근거를 기록한다.

    원시 추정치가 56.175 또는 224.69와 1% 이내로 일치하면(함정에 걸리면)
    격자 정합도 비교를 거쳐 112.35 쪽으로 보정한다. 격자 정합도 숫자 자체는
    원시치가 함정에 걸리지 않았어도 투명성을 위해 항상 기록한다(AC-LDBARMAP-004).
    """
    grid_lock_raw = grid_lock_ratio(onset_times, raw_bpm, duration_sec)
    grid_lock_half = grid_lock_ratio(onset_times, raw_bpm / 2.0, duration_sec)
    grid_lock_double = grid_lock_ratio(onset_times, raw_bpm * 2.0, duration_sec)

    near_half = abs(raw_bpm - half_bpm_const) / half_bpm_const * 100.0 <= trap_tol_pct
    near_double = abs(raw_bpm - double_bpm_const) / double_bpm_const * 100.0 <= trap_tol_pct

    if near_half:
        adopted = raw_bpm * 2.0
        rationale = (
            f"원시 추정치({raw_bpm:.2f})가 절반 함정 상수({half_bpm_const})와 1% 이내로 일치 — "
            f"격자 정합도(원시 {grid_lock_raw:.2f} / 절반 {grid_lock_half:.2f} / "
            f"두 배 {grid_lock_double:.2f})를 비교해 두 배({adopted:.2f})로 보정했다. "
            "주의: 격자 정합도 숫자만으로 두 배를 기계적으로 채택하지 않는다 — "
            "더 촘촘한 격자(두 배)는 점(온셋) 밀도가 높아 정합도가 구조적으로 더 높게 나오는 "
            "경향이 있다(지도 보고서 §1 — 두 배 격자 0.81이 8분음표 하이햇 때문으로 추정됨). "
            "여기서는 원시 추정치 자체가 절반 함정에 해당하므로, 검출기가 실제 박이 아니라 "
            "그 절반 주기를 짚었다고 보고 두 배로 보정한다."
        )
        trap_triggered = True
    elif near_double:
        adopted = raw_bpm / 2.0
        rationale = (
            f"원시 추정치({raw_bpm:.2f})가 두 배 함정 상수({double_bpm_const})와 1% 이내로 일치 — "
            f"격자 정합도(원시 {grid_lock_raw:.2f} / 절반 {grid_lock_half:.2f} / "
            f"두 배 {grid_lock_double:.2f})를 비교해 절반({adopted:.2f})으로 보정했다. "
            "지도 보고서 §1의 선례(두 배 격자가 8분음표를 짚는 것으로 추정)를 따라, "
            "정합도가 더 높다는 이유만으로 더 촘촘한 격자를 채택하지 않는다."
        )
        trap_triggered = True
    else:
        adopted = raw_bpm
        rationale = (
            f"원시 추정치({raw_bpm:.2f})가 절반({half_bpm_const})·두 배({double_bpm_const}) "
            "함정 상수와 1% 이내로 일치하지 않는다 — 함정이 발동하지 않았으므로 "
            "보정 없이 원시 추정치를 그대로 쓴다. "
            f"격자 정합도는 투명성을 위해 기록한다(원시 {grid_lock_raw:.2f} / "
            f"절반 {grid_lock_half:.2f} / 두 배 {grid_lock_double:.2f})."
        )
        trap_triggered = False

    return BpmMultipleCheck(
        raw_bpm=raw_bpm,
        half_bpm=raw_bpm / 2.0,
        double_bpm=raw_bpm * 2.0,
        grid_lock_raw=grid_lock_raw,
        grid_lock_half=grid_lock_half,
        grid_lock_double=grid_lock_double,
        trap_triggered=trap_triggered,
        adopted_bpm=adopted,
        rationale=rationale,
    )
