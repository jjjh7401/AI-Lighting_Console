from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_cross_song import _sequences, _two_chorus_looks

library = _two_chorus_looks()
sections = parse_sections((("Verse", "0:00"), ("Chorus", "0:40")))
without = map_sections_to_looks(sections, library, "rock")
bundle = build_songcue_bundle(
    "Song", without, sequences_section=_sequences(), groups_section=_groups(*FULL_RIG)
)
for c in bundle.commands:
    print(repr(c))
