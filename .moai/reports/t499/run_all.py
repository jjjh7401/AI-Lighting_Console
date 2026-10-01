"""t499 — pilot_baseline.json 의 8곡(오류 2곡 제외)을 rehearse_song.py 로 차례로 돌린다.

곡 하나 = 프로세스 하나(모듈 수준 패치·세션 상태가 곡끼리 섞이지 않게). 병렬로 안 돌린다(부하 규약).

실행: uv run python .moai/reports/t499/run_all.py <음원 폴더> [곡 이름 …]
출력: .moai/reports/t499/runs/<곡 줄기>/ + <곡 줄기>.stdout.txt
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MUSIC = Path(sys.argv[1])
baseline = json.loads((ROOT / "server/tests/fixtures/pilot_baseline.json").read_text("utf-8"))
songs = [row["song"] for row in baseline if "error" not in row]
assert len(songs) == 8, songs
if len(sys.argv) > 2:
    songs = [s for s in songs if s in sys.argv[2:]]

env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
for song in songs:
    stem = Path(song).stem
    out = HERE / "runs" / stem
    out.mkdir(parents=True, exist_ok=True)
    with (HERE / "runs" / f"{stem}.stdout.txt").open("w", encoding="utf-8") as log:
        code = subprocess.call(
            [sys.executable, str(HERE / "rehearse_song.py"), str(MUSIC / song), str(out)],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            env=env,
        )
    print(f"{song}: exit={code}", flush=True)
