from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

SECTIONS = (
    ("Intro", "0:00"),
    ("Verse", "0:20"),
    ("Chorus", "0:50"),
    ("Verse", "1:20"),
    ("Chorus", "1:50"),
    ("Breakdown", "2:20"),
    ("Drop", "2:40"),
    ("Outro", "3:10"),
)

library = load_library_from_dir()
sections = parse_sections(SECTIONS)
selections = map_sections_to_looks(sections, library, "edm")
for s, sel in zip(sections, selections, strict=True):
    print(
        s.index,
        s.label,
        s.instance,
        "->",
        sel.look.look_id if sel.look else sel.reason,
        getattr(sel.look, "dynamics", None),
        sel.requested_dynamics,
    )

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

print("stored cue numbers:", [sb.cue_number for sb in bundle.stored_sections])
print(
    "skipped:",
    [(sk.reason, sk.detail) for section in bundle.sections for sk in section.skipped],
)

print()
for sb in bundle.stored_sections:
    print(
        sb.cue_number,
        sb.section.label,
        sb.section.instance,
        "ladder=",
        sb.ladder,
        "->",
        sb.commands[2],
    )
