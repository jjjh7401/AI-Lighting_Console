"""콘솔에 실제로 쓰기 전, 무엇이 어디로 나가는지 전부 인쇄한다. 아직 쓰기 0."""

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SECTIONS = [
    {"name": "Intro", "start": "0:00", "dynamics": 2},
    {"name": "Verse", "start": "0:16", "dynamics": 2},
    {"name": "Chorus", "start": "0:48", "dynamics": 4},
    {"name": "Verse", "start": "1:20", "dynamics": 3},
    {"name": "Chorus", "start": "1:52", "dynamics": 4},
    {"name": "Breakdown", "start": "2:24", "dynamics": 2},
    {"name": "Drop", "start": "2:40", "dynamics": 5},
    {"name": "Outro", "start": "3:12", "dynamics": 1},
]

stack = build_console_stack(receive_port=9005)
try:
    q = stack.gate.state_port.query_state
    rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
    print("현재 콘솔 시퀀스:", [(c.get("i"), c.get("name")) for c in rs.get("children", [])])
    seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
    groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)
finally:
    stack.stop()

lib = load_library_from_dir()
sel = map_sections_to_looks(parse_sections(SECTIONS), lib, "edm")
b = build_songcue_bundle("VerifyA", sel, sequences_section=seqs, groups_section=groups)
print(f"\n쓸 자리: Sequence {b.sequence_number} '{b.sequence_name}'")
print(f"저장될 큐: {[s.cue_number for s in b.stored_sections]}")
print(f"\n나갈 명령 {len(b.commands)}줄:")
for i, c in enumerate(b.commands, 1):
    print(f"  {i:3}  {c}")
