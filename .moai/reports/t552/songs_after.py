"""t552 — 10곡을 업로드와 같은 바이트열로 analyze()·detect_beat_grid() 에 넣어 잰다 (읽기 전용).

비교 기준: t550 ``songs_after.txt``(같은 detect_beat_grid, 고치기 전 — LoveMe 만 실패).
실행(워크트리 루트): uv run python .moai/reports/t552/songs_after.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from server.audio.analyze import AnalysisFailure, analyze  # noqa: E402
from server.audio.bar_map import BeatGridResult, detect_beat_grid  # noqa: E402

SAMPLE_DIR = "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music"
SONGS = [
    "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3",
    *(
        f"{SAMPLE_DIR}/{n}"
        for n in (
            "Club Diver.mp3",
            "Cut and Run.mp3",
            "Ice cream.mp3",
            "Let's Dance.mp3",
            "LoveMe.mp3",
            "Morning.mp3",
            "Rain.mp3",
            "Too Cool.mp3",
            "scott-buckley-neon.mp3",
        )
    ),
]

print(f"{'song':22} {'analyze':>10} {'grid_bpm':>9} {'outcome':>8} {'beats':>6}")
for path in SONGS:
    raw = Path(path).read_bytes()
    a = analyze(raw)
    g = detect_beat_grid(raw)
    a_txt = f"FAIL {a.reason[:40]}" if isinstance(a, AnalysisFailure) else f"{a.bpm:10.3f}"
    if isinstance(g, BeatGridResult):
        g_txt = f"{g.bpm:9.3f} {g.bpm_check.outcome:>8} {len(g.beat_times_ms):6d}"
    else:
        g_txt = f"FAIL {g.reason[:40]}"
    print(f"{os.path.basename(path)[:22]:22} {a_txt} {g_txt}", flush=True)
