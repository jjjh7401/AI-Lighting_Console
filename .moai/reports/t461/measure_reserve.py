"""t461 ② — 리저브(BLIND·STROBE)가 큐 상태에서 처음 켜지는 행과 행별 잔여 그룹 수를
잰다(t454 와 같은 8구간·120 BPM 곡, 콘솔 접촉 0)."""

import sys

sys.path.insert(0, ".")

from server.concept.density import GROUP_ROSTER  # noqa: E402
from server.concept.gates import build_song  # noqa: E402
from server.concept.headroom import compute_cue_headroom  # noqa: E402
from server.concept.session_bridge import _raw_sections_from_pairs  # noqa: E402

pairs = [
    ("Intro", 0),
    ("Verse 1", 15000),
    ("Chorus 1", 40000),
    ("Verse 2", 60000),
    ("Chorus 2", 85000),
    ("Bridge", 105000),
    ("Chorus 3", 125000),
    ("Outro", 150000),
]
build = build_song({"song": "t461", "bpm": 120.0, "sections": _raw_sections_from_pairs(pairs)})
print("GROUP_ROSTER:", GROUP_ROSTER)
print("reserved(input):", build.reserved)
for row, state in zip(build.table, build.states, strict=True):
    print(
        f"q={row.q:>2} {row.kind:<7} {row.section:<20} BLIND={state.dim.get('BLIND', 0):>3}"
        f" STROBE={state.dim.get('STROBE', 0):>3}"
        f" unused={compute_cue_headroom(state).unused_groups}"
    )
print("one_shots:", [(s["ts"], s["shot"], s["target"]) for s in build.one_shots])
