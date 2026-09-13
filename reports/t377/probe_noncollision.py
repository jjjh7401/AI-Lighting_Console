from server.looks.schema import AttributeValue, Look
from server.looks.songcue import SongCueLookSelection, build_songcue_bundle, parse_sections
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups


def _look(look_id, *, dynamics=5, dimmer=90, zoom=None, iris=None, roles=("백라이트",)):
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", 72),
        AttributeValue("ColorRGB_G", 100),
        AttributeValue("ColorRGB_B", 0),
    ]
    if zoom is not None:
        attributes.append(AttributeValue("Zoom", zoom))
    if iris is not None:
        attributes.append(AttributeValue("Iris", iris))
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=roles,
        attributes=tuple(attributes),
    )


def _sequences(*numbers):
    return {
        "objects": [{"no": n, "name": f"Sequence {n}"} for n in numbers],
        "truncated": False,
        "total": len(numbers),
    }


first, second = parse_sections((("Chorus", "0:00"), ("Verse", "0:40")))
bundle = build_songcue_bundle(
    "Song",
    (
        SongCueLookSelection(
            section=first, requested_dynamics=(5,), look=_look("chorus", dimmer=90, zoom=18)
        ),
        SongCueLookSelection(
            section=second, requested_dynamics=(5,), look=_look("verse", dimmer=45)
        ),
    ),
    sequences_section=_sequences(),
    groups_section=_groups(*FULL_RIG),
)
for c in bundle.commands:
    print(repr(c))
