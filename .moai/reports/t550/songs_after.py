"""t550 — detect_beat_grid 를 박 회귀 BPM 으로 맞춘 뒤 10곡 반/두배 재측정 (읽기 전용).

t547 ``after_songs.py`` 는 ``_check_bpm_half_double`` 을 직접 불렀다. 이 스크립트는
생산 함수 ``detect_beat_grid`` 를 그대로 부른다 — 고친 경로 자체를 잰다.
같은 10곡 목록. 비교 기준: ``.moai/reports/t547/after_songs.txt`` 의 outcome@reg·adopt@reg.

실행(워크트리 루트): uv run python .moai/reports/t550/songs_after.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
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

print(f"{'song':22} {'raw_bpm':>8} {'adopted':>8} {'outcome':>12} {'amb':>5} {'p_mid':>9} {'n':>4}")
for path in SONGS:
    result = detect_beat_grid(Path(path).read_bytes())
    name = os.path.basename(path)[:22]
    if not isinstance(result, BeatGridResult):
        print(f"{name:22} FAILURE {result.reason}")
        continue
    c = result.bpm_check
    print(
        f"{name:22} {c.raw_bpm:8.3f} {result.bpm:8.3f} {c.outcome:>12} "
        f"{str(c.ambiguous):>5} {c.p_mid:9.2e} {c.n_pairs:4d}",
        flush=True,
    )
