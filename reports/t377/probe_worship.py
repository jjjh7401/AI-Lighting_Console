from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_chorus_rescue import (
    _WORSHIP_NINE_SECTIONS_FOUR_CHORUS,
    _chorus_sections,
    _sequences,
)

library = load_library_from_dir()
sections = parse_sections(_WORSHIP_NINE_SECTIONS_FOUR_CHORUS)
selections = map_sections_to_looks(sections, library, "worship")
bundle = build_songcue_bundle(
    "Song", selections, sequences_section=_sequences(), groups_section=_groups(*FULL_RIG)
)
chorus = _chorus_sections(bundle)
for c in chorus:
    print(c.section.instance, c.ladder)
print("skipped:", bundle.skipped)
print("stored count:", len(bundle.stored_sections))
print("distinct value lines:", len({s.commands[2] for s in bundle.stored_sections}))
