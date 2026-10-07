# ruff: noqa: E501 — 한국어 요약 출력 줄
"""t520 — 대본 행 → 큐·타임코드 시각·값 요약(판정서 표의 원천). 실행: uv run python .moai/reports/t520/row_map.py"""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
from m2a_batch1 import SCENE, build, rhythm_cue_lines, rhythm_states, tc_time  # noqa: E402

print("SCENE 250")
for cue, label, fade, t, row, lines in SCENE:
    print(
        f"{cue}\t{label}\tmusic {t:.2f}\tTC {tc_time(t)}\tfade {fade:g}\t{row}\tlines {len(lines)}"
    )
print("RHYTHM 251")
for cue, label, t, row, st in rhythm_states():
    b, sl, sr, u, d = (st[k] for k in ("back", "side_l", "side_r", "mov_u", "mov_d"))
    print(
        f"{cue}\t{label}\tmusic {t:.2f}\tTC {tc_time(t)}\t{row}\t"
        f"BACK {b[0]}/{b[1]} M{b[2]} | SIDE-L {sl[0]}/{sl[1]} SIDE-R {sr[0]}/{sr[1]} M{sl[2]} | "
        f"U Pan {u[0]}/{u[1]} Tilt {u[2]}/{u[3]} Ph {u[4]} M{u[5]} | "
        f"D Pan {d[0]}/{d[1]} Tilt {d[2]}/{d[3]} Ph {d[4]} M{d[5]}"
    )
print("EXAMPLE rhythm cue 7 lines:")
for line in rhythm_cue_lines(rhythm_states()[6][4]):
    print("  ", line[:170])
for label, cmds in build():
    print(label, len(cmds))
