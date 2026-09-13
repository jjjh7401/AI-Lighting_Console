"""감독이 본 것을 코드로 확인한다 — 무엇이 어느 그룹에 갔고 무엇이 안 갔나."""

from pathlib import Path

from server.audio.analyze import AnalysisResult, analyze
from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SONG = Path("src/걸그룹DinoDino_C_max최고품질.wav")
NAMES = [
    "Intro",
    "Verse",
    "Verse",
    "Chorus",
    "Chorus",
    "Bridge",
    "Bridge",
    "Chorus",
    "Verse",
    "Chorus",
    "Verse",
    "Chorus",
    "Breakdown",
    "Chorus",
    "Bridge",
    "Chorus",
]

out = analyze(SONG.read_bytes())
assert isinstance(out, AnalysisResult)
raw = [
    {"name": n, "start": c.start_ms / 1000.0, "dynamics": c.d_level}
    for n, c in zip(NAMES, out.d_candidates, strict=True)
]

stack = build_console_stack(receive_port=9005)
try:
    q = stack.gate.state_port.query_state
    rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
    gnames = {c.get("i"): c.get("name") for c in rg.get("children", [])}
    seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
    groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)
finally:
    stack.stop()

lib = load_library_from_dir()
b = build_songcue_bundle(
    "Diag",
    map_sections_to_looks(parse_sections(raw), lib, "edm"),
    sequences_section=seqs,
    groups_section=groups,
)

print("== 큐마다: 어느 그룹에 무슨 값이 갔나 ==")
used_groups = set()
for s in b.stored_sections:
    gline = next((c for c in s.commands if c.startswith("Group ")), "")
    vline = next((c for c in s.commands if "At " in c and "Attribute" in c), "")
    gs = [int(x) for x in gline.replace("Group ", "").split(" + ") if x.strip().isdigit()]
    used_groups |= set(gs)
    attrs = [a.split("'")[1] for a in vline.split(";") if "'" in a]
    names = [gnames.get(g, f"?{g}") for g in gs]
    lid = getattr(s.selection.look, "look_id", "")[:22]
    print(
        f"  cue {s.cue_number:>2} {s.section.label:10} {lid:22} "
        f"그룹 {','.join(names) or '—'}  속성 {','.join(attrs)}"
    )

print(f"\n== 리그 그룹 {len(gnames)}개 중 큐가 건드린 그룹 ==")
touched = sorted(used_groups)
print("  건드림:", [gnames.get(g) for g in touched])
print("  🔴 한 번도 안 건드림:", [n for g, n in sorted(gnames.items()) if g not in used_groups])

print("\n== 룩 종류 ==")
looks = {}
for s in b.stored_sections:
    lid = getattr(s.selection.look, "look_id", None)
    looks[lid] = looks.get(lid, 0) + 1
print(f"  {len(looks)}종 / 큐 {len(b.stored_sections)}개:", looks)

print("\n== 음악 동기 ==")
tc = [c for c in b.commands if "Timecode" in c or "TrigTime" in c or "Follow" in c]
print("  타임코드/자동진행 명령:", tc or "🔴 0건 — 큐가 음악에 안 붙어 있다")
