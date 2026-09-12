"""곡 구성 전수 쓸기 — 어느 조합에서 큐가 사라지는가. 콘솔 쓰기 0, 읽기 1회."""

import collections

from server.looks.busking import genres_in
from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SHAPES = {
    "verse-chorus x2 + drop": [
        "Intro",
        "Verse",
        "Chorus",
        "Verse",
        "Chorus",
        "Breakdown",
        "Drop",
        "Outro",
    ],
    "verse-chorus x3": ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Verse", "Chorus", "Outro"],
    "build-drop x2": ["Intro", "Build", "Drop", "Breakdown", "Build", "Drop", "Outro"],
    "후렴 4회": [
        "Intro",
        "Verse",
        "Chorus",
        "Verse",
        "Chorus",
        "Bridge",
        "Chorus",
        "Chorus",
        "Outro",
    ],
    "드롭 없음": ["Intro", "Verse", "Chorus", "Bridge", "Chorus", "Outro"],
}
DYN = {
    "Intro": 2,
    "Verse": 2,
    "Chorus": 4,
    "Breakdown": 2,
    "Drop": 5,
    "Outro": 1,
    "Build": 3,
    "Bridge": 3,
}

stack = build_console_stack(receive_port=9005)
try:
    q = stack.gate.state_port.query_state
    rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
    seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
    groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)
finally:
    stack.stop()

lib = load_library_from_dir()
tally = collections.Counter()
print(f"{'장르':8} {'구성':24} 큐  저장  건너뜀  사유")
for genre in genres_in(lib):
    for shape_name, names in SHAPES.items():
        raw = [{"name": n, "start": i * 16, "dynamics": DYN[n]} for i, n in enumerate(names)]
        secs = parse_sections(raw)
        sel = map_sections_to_looks(secs, lib, genre)
        b = build_songcue_bundle(f"S-{genre}", sel, sequences_section=seqs, groups_section=groups)
        n_all, n_ok = len(b.sections), len(b.stored_sections)
        reasons = sorted({s.reason for s in b.skipped})
        drop_lost = any(s.section.label.lower().startswith("drop") for s in b.skipped)
        mark = "🔴DROP" if drop_lost else ("⚠️" if b.skipped else "")
        tally[(genre, bool(b.skipped))] += 1
        print(
            f"{genre:8} {shape_name:24} {n_all:2}  {n_ok:3}   "
            f"{n_all - n_ok:3}   {','.join(reasons) or '-':28} {mark}"
        )
