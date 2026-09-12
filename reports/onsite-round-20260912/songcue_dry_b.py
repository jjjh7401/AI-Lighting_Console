"""B 항목 — 곡이 바뀌면 룩이 바뀌는가. 쓰기 0."""

from server.looks.loader import load_library_from_dir
from server.looks.songcue import map_sections_to_looks, parse_sections

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

lib = load_library_from_dir()
secs = parse_sections(SECTIONS)

a = map_sections_to_looks(secs, lib, "edm")
used = {s.look.look_id for s in a if s.look}
print("곡 A 룩:", [getattr(s.look, "look_id", None) for s in a])
print("A 가 쓴 룩 집합:", sorted(used))

b = map_sections_to_looks(secs, lib, "edm", used_look_ids=used)
print("곡 B 룩:", [getattr(s.look, "look_id", None) for s in b])
reused = {getattr(s.look, "look_id", None) for s in b} & used
print("🔴 B 가 A 와 겹친 룩:", sorted(x for x in reused if x))
