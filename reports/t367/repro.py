from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

sections = parse_sections(
    (
        ("Intro", "0:00"),
        ("Verse", "0:20"),
        ("Chorus", "0:50"),
        ("Verse", "1:20"),
        ("Chorus", "1:50"),
        ("Breakdown", "2:20"),
        ("Drop", "2:40"),
        ("Outro", "3:10"),
    )
)
library = load_library_from_dir()
selections = map_sections_to_looks(sections, library, "edm")
bundle = build_songcue_bundle(
    "Song",
    selections,
    sequences_section={
        "objects": [{"no": 1, "name": "Sequence 1"}],
        "truncated": False,
        "total": 1,
    },
    groups_section=_groups(*FULL_RIG),
)

for s in bundle.movement_sections:
    print(f"MOVES:    cue {s.cue_number} {s.section.label} {s.movement}")
for w in bundle.withheld_movement:
    print(f"withheld: cue {w.cue_number} {w.section.label} {w.reason}")
