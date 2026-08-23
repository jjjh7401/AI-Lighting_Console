"""Per-fixture channel-width join — the fixture slot to its measured footprint.

Four steps, each measured live (t4, 2026-08-22 — inherited values, not re-measured
by this card):

    (1) prop Fixtures/<slot> FixtureType   -> 'FixtureType 10'
    (2) Patch/FixtureTypes/10              -> the type name
    (3) prop Fixtures/<slot> Mode          -> '3 Direct'  -> mode slot 3
    (4) prop .../DMXModes/3 TotalFootprint -> '12'

Steps 1-2 already live in ``inventory.translate_fixture_type``; steps 3-4 in
``mode_read.read_type_mode_widths``. This module owns the JOIN and nothing else.

The two display strings put their number on OPPOSITE sides:

    FixtureType  'FixtureType 10'   number LAST
    Mode         '3 Direct'         number FIRST

and a mode name may itself begin with a digit (measured: '4 4 channel' ='
slot 4, name "4 channel"). So the Mode string is split ONCE on the first space
and never re-split — a greedy or digit-hungry parse silently mis-slots.

Width comes from ``TotalFootprint`` and never from the ``DMXChannels`` child
count. The two agree on simple fixtures and diverge exactly where it matters:
a 16-bit channel occupies two addresses but counts once. ``mode_read`` carries
the live evidence for that (Esprite Mode 1: 채널 40 vs 폭 49); this module only
consumes what that module already read correctly.

ASSUMPTION-27 is NOT reopened by this module. That assumption asked whether the
path index is reachable **without parsing** the display strings
(`acceptance.md:285`); the answer was no and stays no. This join parses, which
is the case that assumption explicitly excluded. Its original GO path would
have taken the width from `DMXChannels` childCount (`acceptance.md:165`) — the
wrong metric — so reopening it verbatim would have been wrong twice over.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from server.prechk.mode_read import TypeModeRead

#: A Mode display string carries its slot first and its name after ONE space.
#: Split once: a name may begin with a digit.
MODE_SPLIT_MAXSPLIT = 1


@dataclass(frozen=True)
class ModeReference:
    """A parsed Mode display string: which mode slot, and the name it claimed."""

    slot: int
    name: str


@dataclass(frozen=True)
class FixtureModeRef:
    """One fixture as this join needs it: its slot, type NAME, and raw Mode."""

    slot: int
    type_name: str | None
    mode_raw: str | None


@dataclass(frozen=True)
class WidthResolution:
    """Widths that resolved, and a reason for every slot that did not.

    ``unresolved`` is not an error channel — a console that cannot answer, a
    type whose read failed, or a mode whose name disagrees are all NORMAL
    outcomes here. The caller reports them; it must not silently drop them,
    because a missing width turns an overlap check into a claim about a set it
    never compared.
    """

    widths: dict[int, int] = field(default_factory=dict)
    unresolved: dict[int, str] = field(default_factory=dict)


def parse_mode_reference(raw: str | None) -> ModeReference | None:
    """Parse a Mode display string, or ``None`` when it is not one.

    The slot comes FIRST and the name follows one space. The split happens
    exactly once because a mode name may itself begin with a digit — measured:
    ``4 4 channel`` is slot 4 named ``4 channel``, not slot 44 or slot 4 named
    ``channel``. A greedy split mis-slots it silently.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    head, sep, tail = text.partition(" ")
    if not sep or not head.isdigit():
        return None
    name = tail.strip()
    if not name:
        return None
    return ModeReference(slot=int(head), name=name)


def resolve_widths(
    fixtures: list[FixtureModeRef] | tuple[FixtureModeRef, ...],
    type_reads: dict[str, TypeModeRead],
) -> WidthResolution:
    """Join fixtures to their measured widths. Never guesses, never raises.

    The self-check is load-bearing: the Mode string names a mode, and the node
    reached by its slot names one too. They must agree. When they do not, the
    slot resolves to NO width and says why — proceeding on a mismatch would
    silently address a fixture by another mode footprint, which is exactly the
    failure this join exists to prevent.
    """
    widths: dict[int, int] = {}
    unresolved: dict[int, str] = {}

    for fixture in fixtures:
        slot = fixture.slot
        if fixture.type_name is None:
            unresolved[slot] = "type_name_absent"
            continue
        parsed = parse_mode_reference(fixture.mode_raw)
        if parsed is None:
            unresolved[slot] = "mode_unparsed"
            continue
        read = type_reads.get(fixture.type_name)
        if read is None or not read.type_found:
            unresolved[slot] = "type_not_read"
            continue
        choice = next((m for m in read.modes if m.slot == parsed.slot), None)
        if choice is None:
            unresolved[slot] = "mode_slot_absent"
            continue
        if choice.name != parsed.name:
            unresolved[slot] = "mode_name_mismatch"
            continue
        if choice.width is None or choice.width < 1:
            unresolved[slot] = "width_unread"
            continue
        widths[slot] = choice.width

    return WidthResolution(widths=widths, unresolved=unresolved)
