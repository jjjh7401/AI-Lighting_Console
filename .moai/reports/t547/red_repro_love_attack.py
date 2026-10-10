"""t547 RED reproduction (로컬 전용) — OLD ``_check_bpm_half_double``가 LOVE ATTACK
의 회귀 BPM(정확한 추정, t546 PR #593 이후 ``analyze()``가 쓰는 값)을 받으면
112→224 로 거짓 두 배를 낸다는 것을 실제 오디오로 확인한다(RED 단계 증거).

실행: uv run python .moai/reports/t547/red_repro_love_attack.py
로컬 전용 — 원곡이 없으면 메시지만 찍고 종료한다.
"""

import io
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, ".")

from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression, _tempo_from_beats
from server.audio.bar_map import _check_bpm_half_double

LOVE_ATTACK_MP3_PATH = Path("/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3")

if not LOVE_ATTACK_MP3_PATH.exists():
    print(f"로컬 전용 — 원곡 부재: {LOVE_ATTACK_MP3_PATH} — 건너뜀")
    sys.exit(0)

audio_bytes = LOVE_ATTACK_MP3_PATH.read_bytes()
samples, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
mono = np.ascontiguousarray(samples.mean(axis=1), dtype=np.float32)

beat_times = librosa.beat.beat_track(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")[1]
onset_times = librosa.onset.onset_detect(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")

median_bpm, _ = _tempo_from_beats(np, beat_times)
reg_bpm, _ = _tempo_from_beat_regression(np, beat_times)
print(f"median_bpm (detect_beat_grid 현재 추정)={median_bpm}")
print(f"regression_bpm (t546 회귀 BPM, analyze() 가 쓰는 값)={reg_bpm}")

check_median = _check_bpm_half_double(np, float(median_bpm), np.asarray(onset_times, dtype=float))
print(f"\n[median bpm 로 호출] adopted_bpm={check_median.adopted_bpm:.3f}")
print(f"  trap_triggered={check_median.trap_triggered}")

check_reg = _check_bpm_half_double(np, float(reg_bpm), np.asarray(onset_times, dtype=float))
print(f"[regression bpm 으로 호출] adopted_bpm={check_reg.adopted_bpm:.3f}")
print(f"  trap_triggered={check_reg.trap_triggered}")
print(check_reg.rationale)

doubled = check_reg.trap_triggered and check_reg.adopted_bpm > reg_bpm * 1.9
defect = "DEFECT REPRODUCED (false double, 112→224)" if doubled else "did not double"
print(f"\nOLD CODE RESULT: {defect}")
