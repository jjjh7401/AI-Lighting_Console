"""M1 보정 실행기 — 후보 3종을 LOVE ATTACK에 돌리고 지도 보고서 대비 채점한다.

실행(저장소 루트에서):
    .venv/bin/python tools/barmap/run_calibration.py \
        "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3" \
        > .moai/reports/SPEC-LDBARMAP-001-probes/m1-raw-stdout.txt

산출물: stdout에 사람이 읽을 표 + 기계가 읽을 JSON을 모두 찍는다(후속 보고서
작성이 이 출력을 그대로 인용한다). `server/` 아래 파일은 0줄도 바꾸지 않는다
(REQ-LDBARMAP-002/003) — `server/audio/analyze.py`를 읽기만 한다.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.barmap.candidates import (  # noqa: E402
    CandidateResult,
    alternate_phase_downbeats,
    detect_events_from_bars,
    run_candidate_a_hop512_onset_accent,
    run_candidate_b_hop256_harmonic_change,
    run_candidate_c_plp_lowband_jump,
)
from tools.barmap.ground_truth import (  # noqa: E402
    BAR_INTERVAL_SEC,
    BEAT_INTERVAL_SEC,
    TARGET_BPM,
    parse_downbeats,
    parse_events,
    shift_downbeats,
)
from tools.barmap.scorer import (  # noqa: E402
    bpm_error_rate_pct,
    check_bpm_multiple,
    event_recall,
    strict_index_hit_rate,
)


def _score_candidate(
    name: str,
    candidate: CandidateResult,
    truth: list[float],
    truth_events,
    duration_sec: float,
    y_full,
    sr_full,
) -> dict:
    # 지표 1 — BPM 오차율
    bpm_err = bpm_error_rate_pct(candidate.raw_bpm)

    # REQ-LDBARMAP-006 — 절반/두 배 비교(후보 C는 이미 자체적으로 수행했다; A/B는
    # 투명성을 위해 여기서 똑같이 수행한다 — 원시치가 함정에 안 걸렸어도 기록한다)
    bpm_check = candidate.bpm_check
    if bpm_check is None:
        bpm_check = check_bpm_multiple(candidate.raw_bpm, candidate.onset_times, duration_sec)

    # 지표 2 — 다운비트 적중률(채택 위상 + 위상 0/1 명시 비교, 과제 지시사항)
    chosen_hit = strict_index_hit_rate(list(candidate.downbeats), truth)
    phase0_downbeats = alternate_phase_downbeats(candidate, 0)
    phase1_downbeats = alternate_phase_downbeats(candidate, 1)
    phase0_hit = strict_index_hit_rate(list(phase0_downbeats), truth)
    phase1_hit = strict_index_hit_rate(list(phase1_downbeats), truth)

    # 지표 3 — 마디 경계 적중률(이 곡은 4/4라 다운비트와 같은 사건 — spec.md §5 결정 3)
    bar_boundary_hit = chosen_hit  # 같은 격자, 같은 숫자 — 설계상 동일(plan.md §D)

    # 지표 4 — 마디별 변화 이벤트 재현율(간단 규칙, M1 범위)
    events = detect_events_from_bars(y_full, sr_full, candidate.downbeats, candidate.hop_length)
    recall = event_recall(events, truth_events)

    return {
        "name": name,
        "circular": candidate.circular,
        "hop_length": candidate.hop_length,
        "phase_method": candidate.phase_method,
        "raw_bpm": candidate.raw_bpm,
        "bpm_error_rate_pct": bpm_err,
        "bpm_multiple_check": {
            "raw_bpm": bpm_check.raw_bpm,
            "half_bpm": bpm_check.half_bpm,
            "double_bpm": bpm_check.double_bpm,
            "grid_lock_raw": bpm_check.grid_lock_raw,
            "grid_lock_half": bpm_check.grid_lock_half,
            "grid_lock_double": bpm_check.grid_lock_double,
            "trap_triggered": bpm_check.trap_triggered,
            "adopted_bpm": bpm_check.adopted_bpm,
            "rationale": bpm_check.rationale,
        },
        "chosen_phase": candidate.chosen_phase,
        "phase_scores": candidate.phase_scores,
        "downbeat_hit_rate": {
            "chosen_phase": str(chosen_hit),
            "phase0": str(phase0_hit),
            "phase1": str(phase1_hit),
        },
        "bar_boundary_hit_rate": str(bar_boundary_hit),
        "event_recall": str(recall),
        "event_matches": recall.matches,
        "n_downbeats_detected": len(candidate.downbeats),
        "n_truth_downbeats": len(truth),
        "grid_fit_ratio": candidate.grid_fit_ratio,
        "raw_peak_count": candidate.raw_peak_count,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: run_calibration.py <audio-path>", file=sys.stderr)
        sys.exit(2)
    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print(f"오디오 파일을 찾지 못했습니다: {audio_path}", file=sys.stderr)
        sys.exit(2)

    truth = parse_downbeats()
    truth_events = parse_events()
    print(
        f"[정답지] 다운비트 {len(truth)}개, 사건 {len(truth_events)}개 "
        "(REQ-LDBARMAP-004/008/009)"
    )

    # --- 음성 대조군(REQ-LDBARMAP-005) — 후보와 무관하게 채점기 자체를 먼저 검증 ---
    print("\n=== 음성 대조군(REQ-LDBARMAP-005) ===")
    positive = strict_index_hit_rate(truth, truth)
    print(f"양성 대조군(정답지 vs 정답지): {positive}  (기대: 100%)")
    shifted_1beat = shift_downbeats(truth, BEAT_INTERVAL_SEC)
    neg1 = strict_index_hit_rate(shifted_1beat, truth)
    print(
        f"음성 대조군 1(1박={BEAT_INTERVAL_SEC:.3f}s 밀림): {neg1}  "
        "(기대: <10%, AC-LDBARMAP-002)"
    )
    shifted_1bar = shift_downbeats(truth, BAR_INTERVAL_SEC)
    neg2 = strict_index_hit_rate(shifted_1bar, truth)
    print(
        f"음성 대조군 2(1마디={BAR_INTERVAL_SEC:.3f}s 밀림): {neg2}  "
        "(기대: <10%, AC-LDBARMAP-003)"
    )

    control_results = {
        "positive_control": str(positive),
        "negative_control_1beat": str(neg1),
        "negative_control_1bar": str(neg2),
    }

    # --- 후보 3종 실행 ---
    print("\n=== 후보 검출기 실행 ===")
    results = []
    t0 = time.time()
    duration_sec = None

    import librosa

    y_full, sr_full = librosa.load(str(audio_path), sr=None, mono=True)
    duration_sec = len(y_full) / sr_full

    for label, runner in (
        ("A-hop512-onset-accent(순환)", run_candidate_a_hop512_onset_accent),
        ("B-hop256-harmonic-change", run_candidate_b_hop256_harmonic_change),
        ("C-plp-lowband-jump", run_candidate_c_plp_lowband_jump),
    ):
        t_start = time.time()
        candidate = runner(audio_path)
        elapsed = time.time() - t_start
        scored = _score_candidate(
            label, candidate, truth, truth_events, duration_sec, y_full, sr_full
        )
        scored["elapsed_sec"] = round(elapsed, 2)
        results.append(scored)
        print(f"\n--- 후보 {label} (elapsed {elapsed:.2f}s) ---")
        print(f"raw_bpm={candidate.raw_bpm:.3f}  bpm_error={scored['bpm_error_rate_pct']:.3f}%")
        print(f"chosen_phase={candidate.chosen_phase}  phase_scores={candidate.phase_scores}")
        print(f"downbeat_hit(chosen)={scored['downbeat_hit_rate']['chosen_phase']}")
        print(f"downbeat_hit(phase0)={scored['downbeat_hit_rate']['phase0']}")
        print(f"downbeat_hit(phase1)={scored['downbeat_hit_rate']['phase1']}")
        print(f"bar_boundary_hit={scored['bar_boundary_hit_rate']}")
        print(f"event_recall={scored['event_recall']}")
        print(f"bpm_multiple_check.trap_triggered={scored['bpm_multiple_check']['trap_triggered']}")
        print(f"bpm_multiple_check.rationale={scored['bpm_multiple_check']['rationale']}")

    print(f"\n총 실행 시간: {time.time() - t0:.2f}s")

    out = {
        "controls": control_results,
        "candidates": results,
        "truth_downbeat_count": len(truth),
        "truth_event_count": len(truth_events),
        "target_bpm": TARGET_BPM,
        "duration_sec": duration_sec,
    }
    print("\n=== JSON ===")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
