"""Per-type DMX-mode read — one named fixture type's modes WITH measured widths.

``footprint.walk_mode_widths`` folds every type into one upper bound and forgets
names; the patch flow needs the opposite: the MODE NAMES of one type so the user
can choose, and each mode's measured ADDRESS footprint so the address plan never
runs on a model-guessed width (2026-08-18 실전: LEDBeam 350을 14ch 간격으로 깔아
전량 거부 — 폭은 콘솔이 안다, 모델이 아니다).

Lives OUTSIDE ``footprint.py`` on purpose: that module's surface is pinned to
``query_state`` only (AC-OVERLAP-002 ①), and the footprint of a mode is a
PROPERTY read — ``TotalFootprint`` — not a child count. The ``DMXChannels``
child count is the WRONG metric: it counts logical channels, so a 16-bit
channel (coarse+fine, two addresses) counts once and the derived address plan
collides on the console (실기 2026-08-18: Esprite Mode 1 채널 40 vs 폭 49).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.prechk.footprint import (
    _MODES_SEGMENT,
    PropertyReader,
    StateReader,
    _Budget,
    _listing_is_whole,
    _payload_ok,
)

#: The mode property that carries the ADDRESS footprint. Live-verified
#: 2026-08-18 (onPC 2.4.2.2, ``Get("TotalFootprint")``): Robin Esprite
#: Mode 1=49 / Mode 2=42, LEDBeam 350 Mode 1=22, Sharpy Plus Mode 0=31 — each
#: matching the console's own "DMX Footprint" column.
FOOTPRINT_PROPERTY = "TotalFootprint"


@dataclass(frozen=True)
class ModeChoice:
    """One DMX mode of one fixture type: its console name and measured width."""

    name: str
    #: ``TotalFootprint`` as the console declares it; ``None`` when the property
    #: read did not answer with a usable count.
    width: int | None
    slot: int


@dataclass(frozen=True)
class TypeModeRead:
    """What the per-type read established.

    ``type_found`` is only meaningful when ``attempted`` is true. ``modes`` may
    carry ``width=None`` entries — a mode whose name enumerated but whose
    footprint property did not answer. The caller decides whether that is fatal.
    """

    attempted: bool
    type_found: bool = False
    modes: tuple[ModeChoice, ...] = ()
    detail: str = ""


def _named_children(payload: dict) -> list[tuple[int, str]] | None:
    """(slot, name) pairs of the returned children, or ``None`` on any gap."""
    pairs: list[tuple[int, str]] = []
    for child in payload.get("children") or []:
        if not isinstance(child, dict):
            return None
        slot = child.get("i")
        name = child.get("name")
        if isinstance(slot, bool) or not isinstance(slot, int) or not isinstance(name, str):
            return None
        pairs.append((slot, name))
    return pairs


@dataclass(frozen=True)
class TypeNameRead:
    """Every (slot, name) pair the fixture-type tree declares.

    Distinct from :class:`TypeModeRead`, which answers "what modes does THIS
    NAMED type have" and so takes a name as INPUT. This read takes no name, so
    it can answer the opposite direction: the console hands back a
    ``FixtureType <slot>`` handle where a name belongs, and only a slot-to-name
    table can translate it (REQ-PARITY-004).

    ``attempted`` separates "the tree did not answer" from "the tree answered
    and declared nothing". Both leave ``pairs`` empty, and a caller that
    conflates them would report a read failure as "slot absent".
    """

    attempted: bool
    pairs: tuple[tuple[int, str], ...] = ()
    #: The listing came back short of the total it declared. Load-bearing for
    #: the caller: a slot missing from a TRUNCATED listing is not absent, it is
    #: UNSEEN, and this repository already holds that truncation invalidates
    #: negative conclusions only. Without this flag a caller can only say
    #: "not in the pairs I got", which reads as a rig fact.
    #: The listing could NOT be confirmed to be the whole library. Three shapes
    #: reach it and they are deliberately one flag, because the CONSEQUENCE is
    #: identical: a slot missing from an unconfirmed listing is UNSEEN, never
    #: absent.
    #:   - the listing declared more children than it returned (truncation);
    #:   - it returned no children at all, which is INDISTINGUISHABLE from
    #:     children that could not be read (the sibling walk in ``footprint.py``
    #:     documents the mechanism and forces the same verdict there — the
    #:     responder hands back an empty table when both ``Children()`` and
    #:     ``Count()`` fail, and ``childCount`` derives from that same empty
    #:     read, so nothing marks it);
    #:   - some children were dropped for want of a usable slot, so what
    #:     arrived is a subset.
    whole_unconfirmed: bool = False
    #: The tree answered, but its children carried no usable (slot, name) pair.
    #: Distinct from an empty library, which is a rig fact: this is a READ that
    #: cannot be trusted to have enumerated anything, so a slot missing from it
    #: is not absent. Kept apart from ``attempted`` on purpose — "no answer" and
    #: "an answer of the wrong shape" call for different handling, and this
    #: module already draws that line.
    shape_invalid: bool = False
    detail: str = ""

    def by_slot(self) -> dict[int, str]:
        """Slot to name. On a duplicate SLOT the FIRST wins.

        A duplicate NAME across two slots is measured reality (live: Robin
        Spiider at slots 4 and 12) and is harmless here - both slots carry the
        same name, so the forward direction has nothing to disambiguate. That
        is why REQ-PARITY-007 can forbid the reverse direction without
        blocking this one. A duplicate SLOT would be a self-contradicting tree;
        first-wins keeps it deterministic instead of adopting the last.
        """
        table: dict[int, str] = {}
        for slot, name in self.pairs:
            table.setdefault(slot, name)
        return table


def read_fixture_type_names(reader: StateReader, *, root: str) -> TypeNameRead:
    """Enumerate the fixture-type tree ONCE for every (slot, name) pair.

    Query count is 1 - the type listing, nothing per type.
    ``read_type_mode_widths`` cannot serve this purpose at any cost: it takes
    ``type_name`` as an argument, which is the very value this read exists to
    produce (spec.md A.4). An unconfirmed listing is NOT an error here - the
    pairs that did arrive are POSITIVE evidence and translate fine; only the
    negative conclusion ("this slot does not exist") is withheld.

    Children are degraded ONE BY ONE, not all-or-nothing: ``PROTOCOL.md``
    (responder 1.2.0) makes ``i`` optional, omitted when the real pool slot
    could not be established, and states that the server already degrades such
    a child to a name-only entry. Dropping the whole table because one type is
    slot-less would switch translation off for a rig that is mostly readable.
    Dropped children do, however, make the listing a SUBSET, so the read stops
    claiming to be whole.
    """
    try:
        payload = reader.query_state(root)
    except Exception:
        return TypeNameRead(attempted=False, detail=root + " 조회에 응답이 없다")
    if not _payload_ok(payload):
        return TypeNameRead(attempted=False, detail=root + " 조회에 응답이 없다")

    children = payload.get("children") or []
    pairs: list[tuple[int, str]] = []
    dropped = 0
    for child in children:
        slot = child.get("i") if isinstance(child, dict) else None
        name = child.get("name") if isinstance(child, dict) else None
        if isinstance(slot, bool) or not isinstance(slot, int) or not isinstance(name, str):
            dropped += 1
            continue
        pairs.append((slot, name))

    if children and not pairs:
        return TypeNameRead(
            attempted=True,
            shape_invalid=True,
            whole_unconfirmed=True,
            detail=root + " 자식에 쓸 수 있는 슬롯/이름이 하나도 없다",
        )

    notes: list[str] = []
    unconfirmed = False
    if not _listing_is_whole(payload):
        unconfirmed = True
        notes.append("열거가 선언 총계보다 짧다")
    if not pairs:
        # 자식 0개 보고는 자식을 못 읽은 것과 구별되지 않는다 — 형제 순회
        # walk_mode_widths 가 같은 페이로드에 같은 판정을 내린다(footprint.py).
        unconfirmed = True
        notes.append("자식이 하나도 열거되지 않았다 - 못 읽은 것과 구별되지 않는다")
    if dropped:
        unconfirmed = True
        notes.append(f"슬롯 없는 자식 {dropped}건을 버렸다 - 목록이 부분집합이다")

    detail = ""
    if notes:
        detail = root + " 전수 확인 불가: " + " · ".join(notes)
    return TypeNameRead(
        attempted=True,
        pairs=tuple(pairs),
        whole_unconfirmed=unconfirmed,
        detail=detail,
    )


def _usable_pairs(payload: dict) -> tuple[list[tuple[int, str]], int]:
    """(usable (slot, name) pairs, how many children were dropped).

    Degrades child by child, never all-or-nothing. ``PROTOCOL.md`` (responder
    1.2.0) makes ``i`` optional — omitted when the real pool slot could not be
    established — and states the server already degrades such a child to a
    name-only entry. Discarding the whole listing because ONE type is slot-less
    switches the read off for a library that is mostly readable, and downstream
    that costs fixtures: a type whose modes cannot be read is planned as
    ``mode_unresolved`` and never patched.

    The drop count is returned rather than swallowed, because what arrived is
    then a SUBSET and the caller must not conclude absence from it.
    """
    pairs: list[tuple[int, str]] = []
    dropped = 0
    for child in payload.get("children") or []:
        slot = child.get("i") if isinstance(child, dict) else None
        name = child.get("name") if isinstance(child, dict) else None
        if isinstance(slot, bool) or not isinstance(slot, int) or not isinstance(name, str):
            dropped += 1
            continue
        pairs.append((slot, name))
    return pairs, dropped


def read_type_mode_widths(
    reader: StateReader,
    properties: PropertyReader,
    *,
    root: str,
    type_name: str,
    budget: int = 64,
) -> TypeModeRead:
    """Enumerate ONE named type's modes with their measured ADDRESS footprints.

    Query count is ``2 + modes``: the type listing, the mode listing, and one
    ``TotalFootprint`` property read per mode. Failures are classified, never
    raised — a console that cannot answer must not cost the caller its report.
    """
    limit = _Budget(limit=budget)

    def read(path: str) -> dict | None:
        try:
            limit.spend()
            payload = reader.query_state(path)
        except Exception:
            return None
        return payload if _payload_ok(payload) else None

    types = read(root)
    if types is None:
        return TypeModeRead(attempted=False, detail=f"{root} 조회에 응답이 없다")
    pairs, dropped = _usable_pairs(types)
    if not pairs:
        return TypeModeRead(attempted=False, detail=f"{root} 자식에 슬롯/이름이 없다")

    exact = [(slot, name) for slot, name in pairs if name == type_name]
    if not exact:
        folded = [(slot, name) for slot, name in pairs if name.casefold() == type_name.casefold()]
        exact = folded if len(folded) == 1 else []
    if not exact:
        # 버린 자식이 있으면 목록은 부분집합이다 — "없다"고 단정하지 않는다.
        absent = (
            f"'{type_name}'이(가) {root} 목록에 없다"
            if not dropped
            else f"'{type_name}'을(를) {root} 목록에서 찾지 못했다 - 슬롯 없는 자식 "
            f"{dropped}건을 버려 목록이 부분집합이라 없다고 단정할 수 없다"
        )
        return TypeModeRead(attempted=True, type_found=False, detail=absent)
    type_slot = exact[0][0]

    modes_path = f"{root}/{type_slot}/{_MODES_SEGMENT}"
    modes = read(modes_path)
    if modes is None:
        return TypeModeRead(
            attempted=True, type_found=True, detail=f"{modes_path} 조회에 응답이 없다"
        )
    mode_pairs, _mode_dropped = _usable_pairs(modes)
    if not mode_pairs:
        return TypeModeRead(
            attempted=True, type_found=True, detail=f"{modes_path}에서 모드를 열거하지 못했다"
        )

    choices: list[ModeChoice] = []
    for mode_slot, mode_name in mode_pairs:
        width: int | None = None
        try:
            limit.spend()
            answer = properties.query_property(f"{modes_path}/{mode_slot}", FOOTPRINT_PROPERTY)
        except Exception:
            answer = None
        if isinstance(answer, dict) and answer.get("ok") is not False:
            value = answer.get("value")
            try:
                parsed = int(str(value).strip())
            except (TypeError, ValueError):
                parsed = 0
            if parsed >= 1:
                width = parsed
        choices.append(ModeChoice(name=mode_name, width=width, slot=mode_slot))
    return TypeModeRead(attempted=True, type_found=True, modes=tuple(choices))
