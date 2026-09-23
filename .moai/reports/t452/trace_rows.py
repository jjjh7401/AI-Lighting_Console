"""t452 원인 추적 — 4초 간격 5구간(Intro/Chorus/Verse/Drop/Chorus @120bpm)을
build_song 에 직접 넣고, resolve_sequence 가 받는 행을 전부 찍는다."""

import sys

sys.path.insert(0, ".")

import server.concept.gates as gates  # noqa: E402
from server.concept.session_bridge import _raw_sections_from_pairs  # noqa: E402

pairs = [("Intro", 0), ("Chorus", 4000), ("Verse", 8000), ("Drop", 12000), ("Chorus", 16000)]
raw_sections = _raw_sections_from_pairs(pairs)
print("raw_sections:", raw_sections)

_orig = gates.resolve_sequence


def _traced(rows):
    for i, row in enumerate(rows):
        refs = [op.get("ref") for op in row["ops"] if op.get("op") in ("reduce", "restore")]
        print(
            f"  row{i} kind={row.get('kind')} section={row['section']} occ={row.get('occurrence')}"
            f" base_name={row.get('base_name')} ops={[op['op'] for op in row['ops']]} refs={refs}"
        )
    return _orig(rows)


gates.resolve_sequence = _traced
try:
    gates.build_song({"song": "t452", "bpm": 120.0, "sections": raw_sections})
    print("build_song OK")
except Exception as error:  # noqa: BLE001
    print("build_song FAIL:", type(error).__name__, error)
