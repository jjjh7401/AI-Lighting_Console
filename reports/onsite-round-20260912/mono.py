"""반복 회차의 밝기 순서 — 뒤 회차가 앞 회차보다 어두워지는가."""

import re

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)

SEQS = {"objects": [{"no": 1, "name": "Default"}], "truncated": False, "total": 1}
GROUPS = {
    "objects": [
        {"no": i, "name": n}
        for i, n in enumerate(
            [
                "ALL",
                "KEY",
                "FOH",
                "BACK",
                "SIDE-L",
                "SIDE-R",
                "SIDE-ALL",
                "WASH-U",
                "WASH-D",
                "WASH-ALL",
                "MOVER-U",
                "MOVER-D",
                "MOVER-ALL",
                "BLIND",
                "STROBE",
                "HAZE",
            ],
            start=1,
        )
    ],
    "truncated": False,
    "total": 16,
}
DYN = {"Intro": 2, "Verse": 2, "Chorus": 4, "Bridge": 3, "Outro": 1, "Drop": 5}
CASES = [
    ("edm", ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Chorus", "Chorus", "Outro"]),
    (
        "worship",
        ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Chorus", "Chorus", "Outro"],
    ),
    ("edm", ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Verse", "Chorus", "Outro"]),
]
lib = load_library_from_dir()
for genre, names in CASES:
    raw = [{"name": n, "start": i * 16, "dynamics": DYN[n]} for i, n in enumerate(names)]
    b = build_songcue_bundle(
        "M",
        map_sections_to_looks(parse_sections(raw), lib, genre),
        sequences_section=SEQS,
        groups_section=GROUPS,
    )
    print(f"\n=== {genre} / {' '.join(names)} ===")
    dims = []
    for s in b.stored_sections:
        line = next((c for c in s.commands if "Dimmer' At" in c), "")
        m = re.search(r"Dimmer' At (\d+)", line)
        d = int(m.group(1)) if m else None
        print(f"  cue {s.cue_number:>2} {s.section.label:9}#{s.section.instance}  Dimmer={d}")
        if s.section.label.lower().startswith("chorus"):
            dims.append((s.section.instance, d))
    bad = [
        (a, b2)
        for a, b2 in zip(dims, dims[1:], strict=False)
        if a[1] is not None and b2[1] is not None and b2[1] < a[1]
    ]
    print("  후렴 밝기 순서:", dims, "🔴역전" if bad else "🟢단조증가")
    for a, b2 in bad:
        print(f"    🔴 {a[0]}회차 {a[1]} → {b2[0]}회차 {b2[1]} (뒤가 더 어둡다)")
