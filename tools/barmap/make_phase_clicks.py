"""LOVE ATTACK 위상 후보(phase0~3) 클릭 wav 생성기 (카드 t530, 감독 귀 확인용).

출력은 저장소 밖(OUT)이며 커밋하지 않는다(REQ-LDBARMAP-014).
박 시각은 지도 보고서와 같은 경로(librosa beat_track, hop 512)로 낸다.
위상 규칙은 보고서 §3 그대로: 박 번호 i 에서 (i - phase) % 4 == 0 인 박이 마디 첫 박.

사용: python tools/barmap/make_phase_clicks.py <음원 경로> <출력 폴더>
"""

import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

SECONDS = 40.0
SR = 44100
HOP = 512


def _click(freq: float, dur: float, gain: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    return gain * np.sin(2 * np.pi * freq * t) * np.exp(-t * 40.0)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: make_phase_clicks.py <audio-path> <out-dir>")
        return 2
    src, out = Path(argv[1]), Path(argv[2])
    y_full, _ = librosa.load(str(src), sr=SR, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y_full, sr=SR, hop_length=HOP)
    beats = librosa.frames_to_time(frames, sr=SR, hop_length=HOP)
    bpm = float(np.atleast_1d(tempo)[0])
    print(f"beats={len(beats)} tempo={bpm:.2f} first5={np.round(beats[:5], 2).tolist()}")

    y = y_full[: int(SR * SECONDS)] * 0.6
    strong = _click(1760.0, 0.08, 0.9)
    weak = _click(880.0, 0.05, 0.35)
    out.mkdir(parents=True, exist_ok=True)
    for phase in range(4):
        mix = y.copy()
        downbeats = []
        for i, t in enumerate(beats):
            if t >= SECONDS:
                break
            is_one = (i - phase) % 4 == 0
            c = strong if is_one else weak
            if is_one:
                downbeats.append(round(float(t), 2))
            s = int(t * SR)
            e = min(len(mix), s + len(c))
            mix[s:e] += c[: e - s]
        path = out / f"LOVE_ATTACK_t530_phase{phase}_40s.wav"
        sf.write(str(path), np.clip(mix, -1.0, 1.0), SR)
        print(f"{path.name} 첫 박(강클릭) 앞 4개={downbeats[:4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
