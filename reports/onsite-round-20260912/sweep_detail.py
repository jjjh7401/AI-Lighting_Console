from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

CASES = [
    ("edm", ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Chorus", "Chorus", "Outro"]),
    ("edm", ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Verse", "Chorus", "Outro"]),
    (
        "worship",
        ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Chorus", "Chorus", "Outro"],
    ),
]
DYN = {"Intro": 2, "Verse": 2, "Chorus": 4, "Drop": 5, "Outro": 1, "Bridge": 3}

stack = build_console_stack(receive_port=9005)
try:
    q = stack.gate.state_port.query_state
    rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
    seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
    groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)
finally:
    stack.stop()

lib = load_library_from_dir()
for genre, names in CASES:
    raw = [{"name": n, "start": i * 16, "dynamics": DYN[n]} for i, n in enumerate(names)]
    b = build_songcue_bundle(
        f"S-{genre}",
        map_sections_to_looks(parse_sections(raw), lib, genre),
        sequences_section=seqs,
        groups_section=groups,
    )
    print(f"\n=== {genre} / {' '.join(names)} ===")
    for s in b.sections:
        lk = getattr(s.selection.look, "look_id", None)
        print(f"  cue {s.cue_number:>3} {s.section.label:10}#{s.section.instance} {lk}")
    for s in b.skipped:
        print(
            f"  🔴 사라짐: cue {s.cue_number} {s.section.label}#{s.section.instance} — {s.detail}"
        )
