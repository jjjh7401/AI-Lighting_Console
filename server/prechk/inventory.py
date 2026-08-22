"""Fixture inventory: enumerate, read the whitelisted properties, judge completeness.

Three measured facts shape this module, and each one costs a design decision.

1. **Truncation is the DEFAULT path, not an edge case.** ``Patch/Stages/1/Fixtures``
   already truncated at 19 fixtures -- the 1900-byte payload budget bites long
   before the 24-child cap (``console/lua/copilot_responder.lua:634-639``). A
   real rig has tens to hundreds of fixtures, so every read here is assumed
   partial until the counts say otherwise.
2. **A truncated snapshot still counts correctly.** ``node.childCount`` carries
   the TRUE total and the budget loop trims only the item list
   (``console/lua/copilot_responder.lua:607``). "How many" is exact; "which
   ones" is not. Completeness therefore comes from the COUNT COMPARISON, never
   from the ``truncated`` flag: the flag says "incomplete" without saying by how
   much, and the missing quantity is precisely what a reader needs
   (REQ-PRECHK-004). An investigation on this repository read ``len(children)``
   as the total, called the rig consistent, and was wrong -- the comparison is
   the guard against that, not a theoretical nicety.
3. **``ok=true`` does not mean the value is usable.** ``prop <fixture> Index``
   answered ``ok=true`` with ``'function: 0x105b0f048'`` because ``safe_property``
   falls back to ``tostring(handle[name])`` (``console/lua/copilot_responder.lua:204-217``).
   Every adopted value passes :func:`shape_error` first; a value that fails is a
   READ FAILURE carrying its reason, and it never reaches a judgement
   (REQ-PRECHK-003).

Property names are a closed whitelist. The responder cannot enumerate property
names, so guessing is the only alternative and guessing is unsafe; and a name
containing a space is rejected by the client protocol before any send
(``server/bridge/protocol.py:136-142``), which is why no space-bearing candidate
is even listed (REQ-PRECHK-001).

``FID`` is deliberately absent from that whitelist. In the calibration show file
slot and fixture id coincide, so no live session can tell a correct fixture-id
probe from a slot probe (``console/lua/PROTOCOL.md:305-324``). This module keys
everything on the SLOT plus the name, never generates a ``Fixture <n>``
selection, and renders any fixture id through :func:`fid_note`
(REQ-PRECHK-005).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Protocol

from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.prechk.mode_read import TypeNameRead
from server.prechk.query import read_properties
from server.prechk.verdicts import validate

FIXTURE_ROOT = "Patch/Stages/1/Fixtures"

# Measured dead in 2.4.2 and inherited, not re-probed (REQ-PRECHK-002). Listed
# so a scanner can prove the generated query set never mentions them.
RETIRED_PATHS = ("Patch/Fixtures", "DataPool/Presets")

# The measured-readable property names, and nothing else (REQ-PRECHK-001).
PROPERTY_WHITELIST = ("Patch", "FixtureType", "Mode", "Name")

# The discriminator is the PREFIX. The pointer reproduced identically across two
# sessions, which makes hardcoding the address tempting and wrong: a stable Lua
# function object says nothing about the next show file.
FUNCTION_REFERENCE_PREFIX = "function: 0x"

# ``safe_property`` falls back to ``tostring`` on every non-nil value, and Lua's
# ``tostring`` renders EVERY non-primitive type as ``<type>: 0x<addr>``. So the
# fault is not "a function came back" -- it is "a pointer came back", and there
# are four such types. Gating on the function prefix alone adopted
# ``table: 0x…`` and ``userdata: 0x…`` as values: a pointer string printed where
# a fixture type belongs, or an address parse failure blamed on the patch when
# the real fault is a responder artefact -- the two faults AC-PRECHK-008 ②
# exists to keep apart.
POINTER_TEXT = re.compile(r"^(?:function|table|userdata|thread): 0x[0-9a-fA-F]+$")

# Absence expressed as a string -- measured on ``CID``. Only the measured form
# is listed; inventing more would reject legitimate names.
ABSENT_VALUE_TEXTS = frozenset({"None"})

FID_UNRESOLVED_MARK = "미확정"


#: The console hands back an object HANDLE where a fixture type name belongs -
#: measured live as ``FixtureType 10`` (SPEC-COPILOT-LXSEQ-001 progress.md:621),
#: with all 86 rows of one read carrying the same form across 8 slots. Code that
#: compares this against a NAME is always false, so the already-patched branch
#: never fires on real hardware while the fake, which answers with names, hides
#: the branch entirely (defect D2).
#:
#: The FORM is an assumption, not a measurement of every path (acceptance.md
#: [HARD]). A different form does not translate, falls to the untranslated path
#: below, and is therefore never silently wrong - only unresolved.
HANDLE_TEXT = re.compile(r"^FixtureType (\d+)$")


#: Why a handle could not be named. The three reasons are kept APART because
#: each calls for a DIFFERENT action, and collapsing any two sends the reader
#: to the wrong place:
#:   - no table       : this path never asked for the tree. An ordering fault,
#:                      fixable in the caller.
#:   - tree unreadable: the tree was asked and did not answer. Retry the
#:                      console; the rig is not at fault.
#:   - slot absent    : the tree answered IN FULL and does not declare that
#:                      slot. A rig fact — retrying changes nothing.
#:   - slot unseen    : the listing could not be confirmed WHOLE (truncated,
#:                      or empty and so indistinguishable from unreadable, or
#:                      a subset because slot-less children were dropped) and
#:                      the slot was not in what arrived. Absence is NOT
#:                      established — this repository already holds that an
#:                      unconfirmed listing invalidates negative conclusions
#:                      only. Positive pairs from it still translate.
#:   - shape invalid  : the listing answered but enumerated nothing usable,
#:                      so it never met the 'answered IN FULL' condition that
#:                      makes absence a rig fact. Fix the READ, not the rig.
#:
#: The last three all mean 'the tree did not give us a trustworthy list', and
#: collapsing any of them into ``slot_absent`` sends someone to edit a rig.
#: This enumeration comes from a measured sweep of the wiring; a sixth reason
#: needs a new measurement, not a hunch.
#: Reporting an unreadable tree as "slot absent" sends someone to edit a rig
#: when what was needed was a re-read.
UNTRANSLATED_NO_TABLE = "no_type_table"
UNTRANSLATED_TREE_UNREADABLE = "type_tree_unreadable"
UNTRANSLATED_SLOT_ABSENT = "slot_absent"
UNTRANSLATED_SLOT_UNSEEN = "slot_unseen_listing_unconfirmed"
UNTRANSLATED_LISTING_SHAPE_INVALID = "listing_shape_invalid"


def translate_fixture_type(
    raw: str | None,
    names: Mapping[int, str] | None,
    *,
    unavailable_reason: str = UNTRANSLATED_NO_TABLE,
    absent_reason: str = UNTRANSLATED_SLOT_ABSENT,
) -> tuple[str | None, str | None]:
    """Return ``(value, untranslated)`` for one FixtureType reading.

    Identity on a name (REQ-PARITY-006): anything not handle-shaped comes back
    unchanged, INCLUDING a name absent from the library. This is a translator,
    not a validator - rejecting unknown names here would invent a second,
    silent failure mode (AC-PARITY-008).

    Forward only (REQ-PARITY-007): slot to name, never name to slot. That is
    what makes a name duplicated across two slots cost nothing - both slots
    carry the same name, so there is nothing to disambiguate.

    ``untranslated`` is True ONLY for a handle that could not be resolved: the
    tree did not answer, or its slot is absent from the table. The raw value is
    returned untouched in that case, because a guessed name is forbidden
    (REQ-PARITY-005, AC-PARITY-009).
    """
    if raw is None:
        return None, None
    hit = HANDLE_TEXT.match(raw)
    if hit is None:
        return raw, None
    if names is None:
        return raw, unavailable_reason
    name = names.get(int(hit.group(1)))
    if name is None:
        return raw, absent_reason
    return name, None


COMPLETE = validate("completeness", "complete")
INCOMPLETE = validate("completeness", "incomplete")
PROPERTY_UNREADABLE = validate("read_failure_kind", "property_unreadable")
SHAPE_INVALID = validate("read_failure_kind", "shape_invalid")


class InventoryReadError(RuntimeError):
    """The fixture root itself is unreadable, so no inventory exists.

    Raised instead of returning an empty inventory: "zero fixtures" is a valid
    rig (acceptance §D) and must never be confused with "the enumeration
    failed".
    """


class InventoryPort(StateQueryPort, PropertyQueryPort, Protocol):
    """The two gate-owned reads this module needs, and nothing more.

    The safety gate's port object implements both; keeping the intersection
    local documents the exact capability without touching the port contracts.
    """


def slot_path(slot: int) -> str:
    """The object path of one fixture slot.

    NEVER ``Fixture <n>``. A slot index is not a fixture id wherever the two
    differ, and emitting that selection form would silently address the wrong
    rig (REQ-PRECHK-005).
    """
    return f"{FIXTURE_ROOT}/{slot}"


def fid_note(observed: str | None = None) -> str:
    """The only sanctioned rendering of a fixture id.

    ``FID`` is outside the whitelist, so the inventory never reads one and the
    default is the bare unresolved mark. The parameter exists so a diagnostic
    that DOES hold a value cannot print it without the mark
    (AC-PRECHK-004 ④).
    """
    if observed is None:
        return FID_UNRESOLVED_MARK
    return f"{observed} ({FID_UNRESOLVED_MARK})"


def shape_error(raw: str | None) -> str | None:
    """Why ``raw`` may not be adopted as a value, or ``None`` when it may.

    This is the per-property shape gate of design slot B. It rejects what the
    responder can hand back with ``ok=true`` and still be unusable: nothing at
    all, a Lua POINTER of any non-primitive type, and absence spelled as a
    string.

    The NUMERIC structure of an address is deliberately NOT checked here. That
    belongs to ``server/prechk/patch.py`` so the report can tell a responder
    artefact (``shape_invalid``) from a malformed address (``address_parse_failed``)
    -- two different faults with two different user actions (AC-PRECHK-008 ②).
    """
    if raw is None:
        return "값이 없다"
    text = raw.strip()
    if not text:
        return "빈 문자열"
    if POINTER_TEXT.match(text):
        return f"Lua 포인터 값: {raw!r}"
    if text in ABSENT_VALUE_TEXTS:
        return f"부재를 문자열로 표현한 값: {raw!r}"
    return None


@dataclass(frozen=True)
class ReadFailure:
    """One property that could not be turned into a usable value.

    ``slot`` is ``None`` only when the enumeration payload gave no index, which
    is itself the failure being reported.
    """

    slot: int | None
    name: str | None
    property: str
    raw_value: str | None
    kind: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "slot": self.slot,
            "name": self.name,
            "property": self.property,
            "raw_value": self.raw_value,
            "kind": self.kind,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class FixtureRecord:
    """One observed fixture, carrying only values that passed the shape gate.

    A property that failed is ``None`` here and lives in :attr:`read_failures`
    with its raw text -- so nothing downstream can adopt it by accident, and
    nothing is silently dropped either.
    """

    slot: int
    name: str | None
    patch_raw: str | None
    fixture_type: str | None
    mode: str | None
    fid_note: str = FID_UNRESOLVED_MARK
    recovered: bool = False
    read_failures: tuple[ReadFailure, ...] = ()
    #: WHY the FixtureType reading is still a handle, or ``None`` when it was
    #: named or needed no naming. Carries the reason rather than a bare flag so
    #: an ordering fault (``UNTRANSLATED_NO_TABLE`` - nobody read the type tree
    #: on this path) is not mistaken for a rig fact (``UNTRANSLATED_SLOT_ABSENT``
    #: - the tree was read and does not declare that slot). The raw handle stays
    #: in :attr:`fixture_type` untouched either way; a guessed name is forbidden
    #: (REQ-PARITY-005).
    #: Appended LAST on purpose: every positional construction stays valid.
    fixture_type_untranslated: str | None = None

    def failed_properties(self) -> tuple[str, ...]:
        return tuple(failure.property for failure in self.read_failures)

    def failure_for(self, property_name: str) -> ReadFailure | None:
        for failure in self.read_failures:
            if failure.property == property_name:
                return failure
        return None


@dataclass(frozen=True)
class InventoryPolicy:
    """Caller-tunable read behaviour.

    The root path and the property whitelist are NOT here on purpose: making
    either injectable is exactly how a retired path or an unreadable name gets
    back in (REQ-PRECHK-001, REQ-PRECHK-002).
    """

    recover_truncated: bool = True


@dataclass(frozen=True)
class Inventory:
    """What the enumeration saw, what it missed, and how it knows.

    ``completeness`` never reaches ``complete`` once the root enumeration came
    back short, even if per-slot recovery then observed every declared child:
    the index domain is unknown, so a bounded probe raises DETAIL, never proof
    (design slot A). ``recovery_boundary`` and ``index_domain_unknown`` say so
    in the payload rather than in prose.
    """

    path: str
    child_count: int
    enumerated_count: int
    recovered_count: int
    observed_count: int
    missing_count: int
    completeness: str
    recovery_boundary: int | None
    index_domain_unknown: bool
    recovered_slots: tuple[int, ...] = ()
    fixtures: tuple[FixtureRecord, ...] = ()
    read_failures: tuple[ReadFailure, ...] = ()
    state_paths: tuple[str, ...] = ()
    property_queries: tuple[tuple[str, str], ...] = ()

    @property
    def still_unobserved_count(self) -> int:
        """Alias of :attr:`missing_count` under the acceptance criteria's name."""
        return self.missing_count

    @property
    def queried_paths(self) -> tuple[str, ...]:
        paths = list(self.state_paths)
        paths.extend(path for path, _ in self.property_queries)
        return tuple(dict.fromkeys(paths))

    @property
    def queried_properties(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(name for _, name in self.property_queries))

    def generated_queries(self) -> tuple[str, ...]:
        """Every request this read generated, as text a scanner can sweep.

        One flat list so a single pass can prove both bans at once: no retired
        path, and no ``Fixture <n>`` selection form.
        """
        lines = [f"state {path}" for path in self.state_paths]
        lines.extend(f"prop {path} {name}" for path, name in self.property_queries)
        return tuple(lines)

    def to_dict(self) -> dict:
        """The ``inventory`` block of the report payload (design §5.1)."""
        return {
            "path": self.path,
            "child_count": self.child_count,
            "observed_count": self.observed_count,
            "recovered_count": self.recovered_count,
            "missing_count": self.missing_count,
            "completeness": self.completeness,
            "recovery_boundary": self.recovery_boundary,
            "index_domain_unknown": self.index_domain_unknown,
        }


@dataclass
class _Log:
    """The generated query record, built as the read proceeds."""

    state_paths: list[str] = field(default_factory=list)
    property_queries: list[tuple[str, str]] = field(default_factory=list)


def _root_payload(port: InventoryPort, log: _Log) -> tuple[int, list[dict]]:
    log.state_paths.append(FIXTURE_ROOT)
    payload = port.query_state(FIXTURE_ROOT)
    if not payload.get("ok"):
        detail = payload.get("error") or "enumeration failed"
        raise InventoryReadError(f"{FIXTURE_ROOT} 열거 실패: {detail}")
    node = payload.get("node") or {}
    try:
        child_count = int(node["childCount"])
    except (KeyError, TypeError, ValueError) as error:
        # Without the true total there is no completeness verdict to make, and
        # guessing one from the returned list is the exact misreading
        # REQ-PRECHK-004 exists to prevent.
        raise InventoryReadError(f"{FIXTURE_ROOT} 스냅샷에 childCount가 없다") from error
    children = payload.get("children") or []
    return child_count, list(children)


def _probe_slot(
    port: InventoryPort, slot: int, log: _Log
) -> tuple[dict | None, ReadFailure | None]:
    """Single-node read of one slot, and the failure if the read itself broke.

    Two outcomes that look alike are kept apart. ``ok=false`` means the path
    segment is not there: an absent index inside a bounded probe range is
    INFORMATION (the pool may be sparse), not a read failure. A raising port is
    a TIMEOUT or a transport fault -- the console did not answer, which says
    nothing about whether the slot exists. Folding the second into the first
    made every probe failure vanish from the report, so a dead link and a sparse
    pool were indistinguishable and the operator could not tell whether to
    suspect the link or the patch. The sibling reader in ``query.py`` already
    captures its own equivalent as a reported failure.

    The verdict numbers do not change either way -- an unrecovered slot stays in
    ``missing_count`` -- so this raises diagnosis, never the judgement.
    """
    path = slot_path(slot)
    log.state_paths.append(path)
    try:
        payload = port.query_state(path)
    except Exception as error:
        return None, ReadFailure(
            slot=slot,
            name=None,
            property=path,
            raw_value=None,
            kind=PROPERTY_UNREADABLE,
            detail=f"슬롯 보강 조회가 응답을 받지 못했다: {error}",
        )
    if not payload.get("ok"):
        return None, None
    return payload, None


def _name_handle_types(
    records: list[FixtureRecord], type_names: TypeNameRead | None
) -> list[FixtureRecord]:
    """Name every handle-shaped FixtureType reading, or say why it could not be.

    Takes the READ, not the table it produced. That is deliberate: the table
    alone cannot distinguish "the tree answered and declares no such slot" from
    "the tree never answered", because both arrive as an empty mapping. A caller
    holding only the mapping has already lost the distinction and will report an
    unreadable tree as a rig fact — which sends someone to edit a rig when what
    was needed was a re-read. Accepting :class:`TypeNameRead` makes that loss
    impossible to express.

    This pass performs NO read of its own. The caller supplies it, because the
    callers that need translation are already walking the fixture-type tree for
    their own reasons; reading it again here would add a query to a path that
    already paid for one, and this repository treats a query-budget guard as
    ratified rather than adjustable.

    The cost of consuming instead of reading is an ORDERING dependency: a caller
    that never asked hands ``None``, and nothing can be named. That is reported,
    never silent.

    A second, subtler limit belongs where a reader will meet it: the handle FORM
    is what triggers translation, so a value in some THIRD form nobody has seen
    is passed through as if it were a name, unmarked. Testing the value against
    the set of names the tree declares would catch that, and is possible only on
    a path that holds the table. Same OUTCOME on the two known forms; DIFFERENT
    DETECTION on an unknown third. Catching format drift is left to the
    live-survey card, and this paragraph is where it starts.
    """
    if not any(
        record.fixture_type is not None and HANDLE_TEXT.match(record.fixture_type)
        for record in records
    ):
        return records

    if type_names is None:
        names: Mapping[int, str] | None = None
        unavailable = UNTRANSLATED_NO_TABLE
    elif not type_names.attempted:
        names = None
        unavailable = UNTRANSLATED_TREE_UNREADABLE
    else:
        names = type_names.by_slot()
        unavailable = UNTRANSLATED_NO_TABLE
    # 전수임을 확인 못 한 목록에서 슬롯이 안 보인 것은 「없다」가 아니라 「못 봤다」다.
    # slot_absent 는 「전수 답했고 없다」는 리그 사실이다. 목록을 믿을 수 없는
    # 두 경우(절단 · 형태 불량)는 그 계약을 만족하지 않으므로 따로 낸다.
    absent = UNTRANSLATED_SLOT_ABSENT
    if type_names is not None:
        if type_names.shape_invalid:
            absent = UNTRANSLATED_LISTING_SHAPE_INVALID
        elif type_names.whole_unconfirmed:
            absent = UNTRANSLATED_SLOT_UNSEEN

    return [
        replace(record, fixture_type=value, fixture_type_untranslated=reason)
        for record, (value, reason) in (
            (
                record,
                translate_fixture_type(
                    record.fixture_type,
                    names,
                    unavailable_reason=unavailable,
                    absent_reason=absent,
                ),
            )
            for record in records
        )
    ]


def read_inventory(
    port: InventoryPort,
    policy: InventoryPolicy | None = None,
    *,
    type_names: TypeNameRead | None = None,
) -> Inventory:
    """Enumerate the fixture root, read the whitelisted properties, count.

    Raises :class:`InventoryReadError` when the root itself is unreadable --
    the caller reports a query failure instead of an empty rig.
    """
    policy = policy or InventoryPolicy()
    log = _Log()
    child_count, children = _root_payload(port, log)

    snapshot_names: dict[int, str | None] = {}
    failures: list[ReadFailure] = []
    enumerated: list[int] = []
    for position, child in enumerate(children, start=1):
        slot = child.get("i")
        if not isinstance(slot, int) or isinstance(slot, bool):
            # The child's own index is the slot. Promoting a LIST POSITION to a
            # slot is forbidden: it is wrong for any sparse pool and worse once
            # the list is truncated (design §7).
            failures.append(
                ReadFailure(
                    slot=None,
                    name=child.get("name"),
                    property="i",
                    raw_value=None if child.get("i") is None else str(child.get("i")),
                    kind=SHAPE_INVALID,
                    detail=f"열거 {position}번째 자식에 슬롯 인덱스 i가 없다",
                )
            )
            continue
        if slot in snapshot_names:
            continue
        snapshot_names[slot] = child.get("name")
        enumerated.append(slot)

    enumerated_count = len(enumerated)
    # The root read is SHORT only when it returned FEWER children than the node
    # declared. A child that carried no slot index, or a duplicate index, was
    # still RETURNED: folding those into "short" makes the completeness label
    # assert a cause that did not happen, and slot-index absence is documented
    # responder behaviour rather than a hypothesis -- the responder omits ``i``
    # whenever the slot is unestablished (``console/lua/copilot_responder.lua``
    # ``safe_children``/``M.safe_children`` serialization) and ``PROTOCOL.md``
    # §4.2 fixes that as the contract. The predicate is now the same
    # count-vs-returned one the writing path uses for the macro pool.
    root_was_short = child_count > len(children)

    recovered: list[int] = []
    recovery_boundary: int | None = None
    # A numeric path segment degrades to a LIST POSITION when not one child of
    # the node has an established slot: the responder's resolver only returns
    # ``children[wanted_slot]`` after finding ``any_slot_known`` false. That is
    # precisely the state that leaves ``enumerated`` empty, so sweeping then
    # would adopt positions as slots -- the promotion this function forbids
    # above, and the defect that issued commands against pools 1/5/7 once
    # before. One established slot is the proof the resolver needs.
    slots_established = enumerated_count > 0
    if root_was_short and slots_established and policy.recover_truncated:
        # design slot A: a bounded 1..childCount sweep. It raises detail, and
        # the completeness verdict below refuses to be promoted by it.
        recovery_boundary = child_count
        observed = set(enumerated)
        for slot in range(1, recovery_boundary + 1):
            if slot in observed:
                continue
            payload, probe_failure = _probe_slot(port, slot, log)
            if probe_failure is not None:
                failures.append(probe_failure)
            if payload is None:
                continue
            node = payload.get("node") or {}
            snapshot_names[slot] = node.get("name")
            recovered.append(slot)

    recovered_set = set(recovered)
    records: list[FixtureRecord] = []
    for slot in sorted(snapshot_names):
        path = slot_path(slot)
        reads = read_properties(port, path, PROPERTY_WHITELIST)
        log.property_queries.extend((path, name) for name in PROPERTY_WHITELIST)

        values: dict[str, str | None] = {}
        pending: list[tuple[str, str | None, str, str]] = []
        for name in PROPERTY_WHITELIST:
            read = reads[name]
            if not read.ok:
                values[name] = None
                pending.append((name, None, PROPERTY_UNREADABLE, read.error or "판독 실패"))
                continue
            problem = shape_error(read.value)
            if problem is not None:
                values[name] = None
                pending.append((name, read.value, SHAPE_INVALID, problem))
                continue
            values[name] = read.value

        # The snapshot name is a separate, valid source -- falling back to it
        # keeps the fixture identifiable without adopting the failed value.
        name = values["Name"] or snapshot_names.get(slot)
        slot_failures = tuple(
            ReadFailure(
                slot=slot,
                name=name,
                property=property_name,
                raw_value=raw_value,
                kind=kind,
                detail=detail,
            )
            for property_name, raw_value, kind, detail in pending
        )
        failures.extend(slot_failures)
        records.append(
            FixtureRecord(
                slot=slot,
                name=name,
                patch_raw=values["Patch"],
                fixture_type=values["FixtureType"],
                mode=values["Mode"],
                fid_note=fid_note(),
                recovered=slot in recovered_set,
                read_failures=slot_failures,
            )
        )

    records = _name_handle_types(records, type_names)

    observed_count = len(records)
    if observed_count > child_count:
        # The clamp below used to absorb this, and the arithmetic
        # AC-PRECHK-003 requires -- observed + still_unobserved == child_count --
        # then closed FALSELY: a snapshot declaring two children while listing
        # three reported "관측 3개 / 보고된 자식 수 2개" and called itself COMPLETE in
        # the same sentence. Nothing verified the identity at runtime; the
        # docstring merely asserted it. A root snapshot that contradicts its own
        # count is not a rig fact, so it is refused exactly like an unreadable
        # root rather than reported as a rig with a self-contradicting census.
        raise InventoryReadError(
            f"{FIXTURE_ROOT} 스냅샷이 자기모순이다: childCount {child_count}인데 "
            f"관측 {observed_count}개"
        )
    # observed + missing == child_count now holds by construction, not by claim.
    missing_count = child_count - observed_count
    complete = not root_was_short and missing_count == 0
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=child_count,
        enumerated_count=enumerated_count,
        recovered_count=len(recovered),
        observed_count=observed_count,
        missing_count=missing_count,
        completeness=COMPLETE if complete else INCOMPLETE,
        recovery_boundary=recovery_boundary,
        index_domain_unknown=root_was_short,
        recovered_slots=tuple(sorted(recovered)),
        fixtures=tuple(records),
        read_failures=tuple(failures),
        state_paths=tuple(log.state_paths),
        property_queries=tuple(log.property_queries),
    )
