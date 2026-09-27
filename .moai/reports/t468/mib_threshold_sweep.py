"""카드 t468 — MIB 문턱(MOVE+SETTLE)을 바꿨을 때 8곡 MIB 판정·G12 가 어떻게 움직이나.

코드는 바꾸지 않는다. ``server.concept.resolver`` 의 모듈 상수를 실행 중에만
바꿔 끼워 같은 입력(server/tests/fixtures/pilot_baseline.json)으로 다시 잰다.

실행(프로젝트 루트)::

    uv run python .moai/reports/t468/mib_threshold_sweep.py > <출력 파일>
"""

from __future__ import annotations

import json
from pathlib import Path

import server.concept.resolver as resolver
from server.concept.gates import GATE_NAMES, evaluate_song

G12 = next(name for name in GATE_NAMES if name.startswith("G12"))
songs = [
    s
    for s in json.loads(Path("server/tests/fixtures/pilot_baseline.json").read_text("utf-8"))
    if "error" not in s
]

# (MOVE, SETTLE) — 현행 §F 잠정값, t464 실측 하한(2.07 부족), 실측 상한(4.05 충분),
# 그리고 양성 대조(100초 — 바꿔 끼운 값이 실제로 읽히면 Mark 가 전부 live 로 뒤집혀야 한다)
SETTINGS = [(1.5, 0.5), (1.6, 0.5), (3.6, 0.5), (99.5, 0.5)]
original = (resolver.MOVE_SECONDS, resolver.SETTLE_SECONDS)
print(f"기준 상수(코드): MOVE={original[0]} SETTLE={original[1]} · 곡 {len(songs)}")
try:
    for move, settle in SETTINGS:
        resolver.MOVE_SECONDS, resolver.SETTLE_SECONDS = move, settle
        passed = 0
        print(f"\n== 문턱 {move + settle:.1f}초 (MOVE {move} + SETTLE {settle})")
        for song in songs:
            result = evaluate_song(song)[G12]
            passed += bool(result.passed)
            print(f"  {song['song']}: {'PASS' if result.passed else 'FAIL'} — {result.detail}")
        print(f"  G12 PASS {passed}/{len(songs)}")
    # Mark·live 판정이 난 전환의 실제 어둠 길이(초) — 문턱과의 여유를 본다
    resolver.MOVE_SECONDS, resolver.SETTLE_SECONDS = original
    from server.concept.gates import build_song

    print("\n== 현행 문턱에서 mark/live 전환의 어둠 창(window_seconds)")
    windows: list[float] = []
    for song in songs:
        build = build_song(song)
        marks = [v.window_seconds for v in build.mib if v is not None and v.status != "dark"]
        windows += marks
        print(f"  {song['song']}: {marks}")
    print(f"  최소 {min(windows) if windows else None} · 개수 {len(windows)}")
finally:
    resolver.MOVE_SECONDS, resolver.SETTLE_SECONDS = original
