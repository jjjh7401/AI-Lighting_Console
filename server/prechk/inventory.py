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

from dataclasses import dataclass, field
from typing import Protocol

from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
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

# Absence expressed as a string -- measured on ``CID``. Only the measured form
# is listed; inventing more would reject legitimate names.
ABSENT_VALUE_TEXTS = frozenset({"None"})

FID_UNRESOLVED_MARK = "미확정"

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

    This is the per-property shape gate of design slot B. It rejects the three
    forms the responder can hand back with ``ok=true``: nothing at all, a Lua
    function reference, and absence spelled as a string.

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
    if text.startswith(FUNCTION_REFERENCE_PREFIX):
        return f"Lua 함수 참조: {raw!r}"
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


def _probe_slot(port: InventoryPort, slot: int, log: _Log) -> dict | None:
    """Single-node read of one slot; ``None`` when the slot does not exist.

    An absent index inside a bounded probe range is INFORMATION (the pool may
    be sparse), not a read failure, so it is not reported as one.
    """
    path = slot_path(slot)
    log.state_paths.append(path)
    try:
        payload = port.query_state(path)
    except Exception:  # the port raises on failure AND on timeout
        return None
    if not payload.get("ok"):
        return None
    return payload


def read_inventory(port: InventoryPort, policy: InventoryPolicy | None = None) -> Inventory:
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
    root_was_short = child_count > enumerated_count

    recovered: list[int] = []
    recovery_boundary: int | None = None
    if root_was_short and policy.recover_truncated:
        # design slot A: a bounded 1..childCount sweep. It raises detail, and
        # the completeness verdict below refuses to be promoted by it.
        recovery_boundary = child_count
        observed = set(enumerated)
        for slot in range(1, recovery_boundary + 1):
            if slot in observed:
                continue
            payload = _probe_slot(port, slot, log)
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

    observed_count = len(records)
    # Clamped so a self-contradicting snapshot cannot emit a negative deficit.
    # For any well-formed snapshot observed + missing == child_count exactly.
    missing_count = max(child_count - observed_count, 0)
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
