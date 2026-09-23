"""t452 — 세 단계(build_song / evaluate_song / compile_song)를 따로 돌려
어느 단계가 reduce ref 오류를 내는지 가리고, 그 단계의 스택을 찍는다."""

import sys
import traceback

sys.path.insert(0, ".")

from server.concept.gates import build_song, evaluate_song  # noqa: E402
from server.concept.session_bridge import _raw_sections_from_pairs, compile_song  # noqa: E402

pairs = [("Intro", 0), ("Chorus", 4000), ("Verse", 8000), ("Drop", 12000), ("Chorus", 16000)]
raw_song = {"song": "t452", "bpm": 120.0, "sections": _raw_sections_from_pairs(pairs)}

build = build_song(raw_song)
print("build_song OK rows=", len(build.table) if hasattr(build, "table") else "?")
for name, fn in (
    ("evaluate_song", lambda: evaluate_song(raw_song)),
    ("compile_song", lambda: compile_song(build)),
):
    try:
        fn()
        print(name, "OK")
    except Exception:  # noqa: BLE001
        print(name, "FAIL")
        traceback.print_exc(file=sys.stdout)
