"""t546 RED — 고치기 전 analyze()(HEAD 의 analyze.py 사본)와 고친 analyze() 에
같은 112 BPM 클릭 트랙을 넣어 BPM 을 나란히 찍는다.

실행(워크트리 루트): uv run python .moai/reports/t546/red_analyze.py
"""

import importlib.util
import io
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.getcwd())
from server.audio.analyze import analyze as analyze_after  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "analyze_before", os.path.join(os.path.dirname(__file__), "analyze_before.py")
)
before = importlib.util.module_from_spec(spec)
sys.modules["analyze_before"] = before
spec.loader.exec_module(before)


def click_wav(bpm, seconds=30, sr=44100):
    audio = np.zeros(sr * seconds, dtype=np.float32)
    burst = np.sin(2 * np.pi * 1000 * np.arange(441) / sr).astype(np.float32)
    burst *= np.hanning(882)[441:].astype(np.float32)
    period = 60.0 / bpm
    for beat in range(int(seconds / period)):
        start = int(round(beat * period * sr))
        end = min(start + burst.size, audio.size)
        audio[start:end] += burst[: end - start]
    buffer = io.BytesIO()
    sf.write(buffer, audio, sr, format="WAV")
    return buffer.getvalue()


print(f"{'true':>7} {'before':>9} {'after':>9}")
for true in (112.0, 120.0, 128.5, 160.0):
    wav = click_wav(true)
    print(f"{true:7.1f} {before.analyze(wav).bpm:9.3f} {analyze_after(wav).bpm:9.3f}")
