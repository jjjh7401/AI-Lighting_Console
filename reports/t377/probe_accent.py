from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    SongCueLookSelection,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import LXSEQ_RIG

GROUPS = tuple((index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG))


def _look(look_id, *, dynamics=5, dimmer=60, roles=("백라이트",)):
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=roles,
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
    )


def _sequences(*numbers):
    return {
        "objects": [{"no": n, "name": f"Sequence {n}"} for n in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _bundle_of(*pairs, allow_strobe=False, title="Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*GROUPS),
        allow_strobe=allow_strobe,
    )


look = _look("chorus", dimmer=60)
sections = parse_sections(tuple(("Chorus", f"{m}:00") for m in range(6)))
bundle = _bundle_of(*((s, look) for s in sections), allow_strobe=True)
print("with allow_strobe=True")
for s in bundle.stored_sections:
    print(s.cue_number, s.ladder, s.commands[2], "accent:", s.accent_fixture)
print("skipped:", bundle.skipped)

bundle2 = _bundle_of(*((s, look) for s in sections), allow_strobe=False)
print()
print("with allow_strobe=False")
for s in bundle2.stored_sections:
    print(s.cue_number, s.ladder, "accent:", s.accent_fixture)
print("skipped:", bundle2.skipped)
