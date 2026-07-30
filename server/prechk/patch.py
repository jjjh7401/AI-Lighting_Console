"""Patch consistency: canonicalise addresses, group collisions, keep the limits.

Three rules govern every judgement here.

**An address is two integers, or it is nothing.** ``Patch`` arrives as
``'<universe>.<address>'`` (measured: ``'1.001'``, ``'2.351'``, ``'2.401'``).
:func:`normalize_address` turns that into two ints or reports a parse failure --
it NEVER substitutes ``0`` or ``1``. A filled-in default would make a fixture
whose address is unknown collide with a fixture whose address really is 1, which
is a fabricated finding (REQ-PRECHK-006). Comparison is on the integers, so
``'1.001'`` and ``'1.1'`` are the same address; a string comparison would call
them different and miss the duplicate.

**Address duplicates are checked unconditionally; range overlap is not.**
``ASSUMPTION-27`` is NEGATIVE: twelve candidate routes from a fixture to its own
channel footprint were enumerated and every one was refuted, because
``FixtureType``/``Mode`` are DISPLAY STRINGS and parsing an index out of a
display name is the same mistake as reading a slot as a fixture id. So the
overlap check is not performed by default and the omission is reported as a
skipped check rather than left silent (REQ-PRECHK-008). The comparison logic
itself is kept and tested: footprints are an OPTIONAL CALLER-INJECTED input, so
a caller that obtains widths some other way (``Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels``
child count) gets the check without this module ever deriving the linkage.

**An incomplete read may not claim consistency.** When the enumeration came back
short, zero collisions means "zero within what was observed", and the unobserved
population is counted as ``not_assessed``. This is not a hypothetical guard: an
investigation on this repository read 18 returned children as the total and
wrote "a consistent rig" on top of it, with the nineteenth fixture unseen
(REQ-PRECHK-010).

``FID`` is not an input to anything here. Judgements key on the slot and the
name (REQ-PRECHK-005).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from server.prechk.footprint import (
    AddressGap,
    WalkOutcome,
    address_gaps,
    bound_source,
    unsettled_gaps,
    upper_bound,
)
from server.prechk.inventory import (
    INCOMPLETE,
    FixtureRecord,
    Inventory,
    ReadFailure,
)
from server.prechk.verdicts import READ_FAILURE_KIND, validate

ADDRESS_DUPLICATE = validate("collision_kind", "address_duplicate")
RANGE_OVERLAP = validate("collision_kind", "range_overlap")
RANGE_OVERLAP_DESCOPE = validate("skipped_check_kind", "range_overlap_descope")
OBSERVED_CLEAR = validate("fixture_verdict", "observed_clear")
COLLISION = validate("fixture_verdict", "collision")
READ_FAILED = validate("fixture_verdict", "read_failed")
NOT_ASSESSED = validate("fixture_verdict", "not_assessed")
ADDRESS_PARSE_FAILED = validate("read_failure_kind", "address_parse_failed")
TYPE_MODE_UNRESOLVED = validate("read_failure_kind", "type_mode_unresolved")
RANGE_OVERLAP_BOUND_INCONCLUSIVE = validate(
    "skipped_check_kind", "range_overlap_bound_inconclusive"
)
EXACT_WIDTHS = validate("overlap_basis", "exact_widths")
BOUND_PROVES_CLEAR = validate("overlap_basis", "bound_proves_clear")
BOUND_INCONCLUSIVE = validate("overlap_basis", "bound_inconclusive")
NOT_PERFORMED = validate("overlap_basis", "not_performed")

ASSUMPTION_27 = "ASSUMPTION-27"

#: The bound axis rests on three propositions no reachable surface can check:
#: one contiguous block per fixture, a channel count that equals DMX slots, and a
#: complete mode enumeration. They are named on the notice so the reader knows
#: what the grade is conditional on, rather than reading it as unqualified.
BOUND_ASSUMPTIONS = "ASSUMPTION-31 · ASSUMPTION-32 · ASSUMPTION-33"

#: The qualifier every claim carries while the read is incomplete.
SCOPE_QUALIFIER = "관측된 범위에서"

RANGE_OVERLAP_DESCOPE_REASON = (
    "픽스처가 주는 FixtureType·Mode는 표시 문자열이고 경로 인덱스가 아니다. "
    "표시 문자열 파싱 없이 점유폭에 도달하는 경로가 후보 12건 전건 부정으로 확정됐다. "
    "주소 중복 판정은 이 축소와 무관하게 수행한다."
)

_ADDRESS = re.compile(r"^(\d+)\.(\d+)$")

#: The lowest index the console's numbering produces. A floor, never a ceiling —
#: see :func:`normalize_address` for why no ceiling exists here.
_MINIMUM_INDEX = 1


@dataclass(frozen=True)
class AddressParse:
    """One ``Patch`` value turned into integers, or the reason it was not.

    On failure both integers stay ``None``. There is no default: a fabricated
    ``0`` or ``1`` would enter collision detection as a real address.
    """

    raw: str | None
    universe: int | None = None
    address: int | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.universe is not None and self.address is not None


def normalize_address(raw: str | None) -> AddressParse:
    """Parse ``'<universe>.<address>'`` into two integers.

    Both halves must be at least :data:`_MINIMUM_INDEX`. The console's own
    numbering starts at one, so ``0.0`` · ``1.0`` · ``0.1`` name no addressable
    channel -- and the exact-match duplicate axis never noticed, because a
    meaningless address only ever collides with itself. Once distances between
    addresses are computed the same value produces a meaningless DISTANCE, and
    that distance reaches a verdict.

    There is deliberately NO upper bound. The per-universe channel capacity is
    unmeasured (``ASSUMPTION-33``), and inventing a ceiling would reject
    addresses the console accepts -- turning a working rig into a read failure.
    So this validation is definite about the FORM and the FLOOR only, and a
    large address parses. What the missing ceiling costs is confined to the
    tail-overflow question, which is out of scope.
    """
    if raw is None:
        return AddressParse(raw=raw, error="값 없음")
    match = _ADDRESS.match(raw.strip())
    if match is None:
        return AddressParse(raw=raw, error="'<유니버스>.<주소>' 형태가 아니다")
    universe, address = int(match.group(1)), int(match.group(2))
    if universe < _MINIMUM_INDEX or address < _MINIMUM_INDEX:
        return AddressParse(
            raw=raw,
            error=f"유니버스·주소는 {_MINIMUM_INDEX} 이상이어야 한다",
        )
    return AddressParse(raw=raw, universe=universe, address=address)


@dataclass(frozen=True)
class FixtureRef:
    """One fixture inside a collision, named the only two safe ways."""

    slot: int
    name: str | None

    def to_dict(self) -> dict:
        return {"slot": self.slot, "name": self.name}


@dataclass(frozen=True)
class Collision:
    """One collision and EVERY fixture involved in it.

    A three-way duplicate is one collision with three members, not three pairs:
    counting pairs would inflate the finding and misstate how many places need
    a decision.
    """

    kind: str
    universe: int
    address: int
    members: tuple[FixtureRef, ...]
    detail: str
    span: tuple[int, int] | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "universe": self.universe,
            "address": self.address,
            "span": list(self.span) if self.span is not None else None,
            "fixtures": [member.to_dict() for member in self.members],
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SkippedCheck:
    """A judgement that was NOT performed, and why."""

    kind: str
    reason: str
    assumption: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "reason": self.reason, "assumption": self.assumption}


@dataclass(frozen=True)
class FootprintPolicy:
    """Channel footprints for the range-overlap check — injected, never derived.

    Keyed by SLOT because that is the one key which does not require the refuted
    fixture-to-mode linkage. Disabled by default: the shipped configuration
    performs address-duplicate detection only, and says so in
    ``skipped_checks``.
    """

    enabled: bool = False
    widths: Mapping[int, int] = field(default_factory=dict)
    source: str = ""


@dataclass(frozen=True)
class FixtureVerdict:
    """One observed fixture's verdict plus the codes behind it.

    ``reasons`` holds closed-vocabulary codes -- read-failure kinds and
    collision kinds -- never free prose, so the report can aggregate them.
    """

    record: FixtureRecord
    universe: int | None
    address: int | None
    verdict: str
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """The ``fixtures`` item of the report payload (design §5.1)."""
        return {
            "slot": self.record.slot,
            "name": self.record.name,
            "patch_raw": self.record.patch_raw,
            "universe": self.universe,
            "address": self.address,
            "fixture_type": self.record.fixture_type,
            "mode": self.record.mode,
            "fid_note": self.record.fid_note,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
        }


#: Claim strength, weakest first. The rig-wide grade is the WEAKEST of the
#: comparisons actually performed: stamping the strongest one would let a slot
#: nobody compared ride on the back of a slot that was compared.
_BASIS_ORDER = (NOT_PERFORMED, BOUND_INCONCLUSIVE, BOUND_PROVES_CLEAR, EXACT_WIDTHS)


@dataclass(frozen=True)
class OverlapBasis:
    """How the range-overlap axis reached its answer, with its own evidence.

    A grade with no origin is unauditable, and the precedent in this module is a
    warning: ``FootprintPolicy.source`` has been a field since the axis shipped
    and never reached the payload, so no consumer has ever been able to ask where
    a width came from. ``bound`` and ``bound_source`` travel together for that
    reason.

    ``basis`` is RIG-WIDE. The two slot lists say which fixtures each axis
    actually covered, so a reader can tell a rig where both axes ran from a rig
    where one of them answered for everything.
    """

    basis: str
    bound: int | None = None
    bound_source: str = ""
    mode_widths: tuple[int, ...] = ()
    exact_width_slots: tuple[int, ...] = ()
    bound_slots: tuple[int, ...] = ()
    observation_note: str = ""

    def to_dict(self) -> dict:
        return {
            "basis": self.basis,
            "bound": self.bound,
            "bound_source": self.bound_source,
            "mode_widths": list(self.mode_widths),
            "exact_width_slots": list(self.exact_width_slots),
            "bound_slots": list(self.bound_slots),
            "observation_note": self.observation_note,
        }


def _weakest(grades: set[str]) -> str:
    for grade in _BASIS_ORDER:
        if grade in grades:
            return grade
    return NOT_PERFORMED


@dataclass(frozen=True)
class PatchEvaluation:
    """The consistency verdict for one inventory.

    ``verdict_counts`` carries all four closed verdicts. The first three sum to
    ``inventory.observed_count``; ``not_assessed`` counts the UNOBSERVED
    population, which has no per-fixture row because its slots are unknown --
    that is exactly what an incomplete read means.

    ``read_failure_counts`` keeps the failure classes apart because the user
    action differs for each: a property the console would not answer, a value
    whose shape is unusable, and an address that would not parse are three
    different problems. ``type_mode_unresolved`` is a per-fixture EXCLUSION
    reason rather than a property row, so it stays at zero here while appearing
    in ``reasons``.
    """

    inventory: Inventory
    rows: tuple[FixtureVerdict, ...]
    address_duplicates: tuple[Collision, ...]
    range_overlaps: tuple[Collision, ...]
    read_failures: tuple[ReadFailure, ...]
    skipped_checks: tuple[SkippedCheck, ...]
    verdict_counts: Mapping[str, int]
    read_failure_counts: Mapping[str, int]
    scope_qualified: bool
    scope_note: str
    #: The range-overlap axis's grade AND its evidence. One new TOP-LEVEL payload
    #: key: every existing block is locked to an exact key set, and this is the
    #: only place a addition breaks nothing (``AC-OVERLAP-016`` pays for that by
    #: locking the new key set itself, because a place where nothing breaks is a
    #: place nobody guards).
    overlap: OverlapBasis = field(default_factory=lambda: OverlapBasis(basis=NOT_PERFORMED))

    @property
    def overlap_basis(self) -> str:
        """The rig-wide grade. Shorthand for ``overlap.basis``."""
        return self.overlap.basis

    @property
    def collision_total(self) -> int:
        return len(self.address_duplicates) + len(self.range_overlaps)

    def to_dict(self) -> dict:
        return {
            "inventory": self.inventory.to_dict(),
            "fixtures": [row.to_dict() for row in self.rows],
            "collisions": {
                "address_duplicates": [c.to_dict() for c in self.address_duplicates],
                "range_overlaps": [c.to_dict() for c in self.range_overlaps],
            },
            "read_failures": [failure.to_dict() for failure in self.read_failures],
            "skipped_checks": [check.to_dict() for check in self.skipped_checks],
            "verdict_counts": dict(self.verdict_counts),
            "read_failure_counts": dict(self.read_failure_counts),
            "scope_qualified": self.scope_qualified,
            "scope_note": self.scope_note,
            "overlap_basis": self.overlap.to_dict(),
        }


@dataclass(frozen=True)
class _Assessed:
    """A fixture with its address parsed and its blocking reasons collected."""

    record: FixtureRecord
    parse: AddressParse
    reasons: tuple[str, ...]
    type_mode_ok: bool


def _ref(record: FixtureRecord) -> FixtureRef:
    return FixtureRef(slot=record.slot, name=record.name)


def _address_groups(assessed: list[_Assessed]) -> dict[tuple[int, int], list[_Assessed]]:
    """Fixtures bucketed by ``(universe, address)`` start point.

    Extracted so the duplicate axis and the bound axis look at the SAME set. Two
    independent groupings would drift the moment one side changed how it treats
    an address, and the two axes would then disagree about which fixtures exist
    without anything failing. The filter is ``parse.ok`` and nothing else: the
    bound argument holds without knowing which mode a fixture uses, so requiring
    a resolved type or mode here would be a misreading of the argument, not a
    safety measure.
    """
    groups: dict[tuple[int, int], list[_Assessed]] = defaultdict(list)
    for item in assessed:
        if item.parse.ok:
            groups[(item.parse.universe, item.parse.address)].append(item)
    return groups


def _address_duplicates(assessed: list[_Assessed]) -> tuple[Collision, ...]:
    """One collision per shared ``(universe, address)`` start point."""
    groups = _address_groups(assessed)
    collisions = []
    for (universe, address), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda item: item.record.slot)
        collisions.append(
            Collision(
                kind=ADDRESS_DUPLICATE,
                universe=universe,
                address=address,
                members=tuple(_ref(item.record) for item in ordered),
                detail=(
                    f"유니버스 {universe} 주소 {address} 시작점을 "
                    f"픽스처 {len(ordered)}개가 점유한다"
                ),
            )
        )
    return tuple(collisions)


def _footprint_width(policy: FootprintPolicy, slot: int) -> int | None:
    """The usable channel width for ``slot``, or ``None`` when there is none.

    One source for "does this fixture have a width", because the overlap check
    and the coverage notice must never disagree: if they drift, the report either
    claims a comparison it skipped or announces a skip it performed.
    """
    width = policy.widths.get(slot)
    if width is None or width < 1:
        return None
    return width


def _judgeable_without_width(assessed: list[_Assessed], policy: FootprintPolicy) -> tuple[int, ...]:
    """Slots the overlap check would have compared, but has no width for.

    ``widths`` carries no totality constraint and its designed source is a
    per-type read that can fail, so a PARTIAL map is a normal result rather than
    a hypothetical. Excluding those fixtures silently gave them ``observed_clear``
    and printed ``충돌 0건`` with no not-performed notice -- a fixture that was
    never compared, reported as clear. "Not compared" and "no overlap" have to be
    different strings.
    """
    return tuple(
        item.record.slot
        for item in assessed
        if item.parse.ok
        and item.type_mode_ok
        and _footprint_width(policy, item.record.slot) is None
    )


def _range_overlaps(assessed: list[_Assessed], policy: FootprintPolicy) -> tuple[Collision, ...]:
    """One collision per maximal cluster of overlapping channel ranges.

    Fixtures whose type or mode is unresolved are excluded: their occupancy
    cannot be judged, and REQ-PRECHK-009 forbids counting them either way.
    """
    intervals: dict[int, list[tuple[int, int, _Assessed]]] = defaultdict(list)
    for item in assessed:
        width = _footprint_width(policy, item.record.slot)
        if not item.parse.ok or not item.type_mode_ok or width is None:
            continue
        start = item.parse.address
        intervals[item.parse.universe].append((start, start + width - 1, item))

    collisions = []
    for universe, entries in sorted(intervals.items()):
        entries.sort(key=lambda entry: (entry[0], entry[1]))
        cluster: list[tuple[int, int, _Assessed]] = []
        cluster_end = 0
        for start, end, item in entries:
            if cluster and start <= cluster_end:
                cluster.append((start, end, item))
                cluster_end = max(cluster_end, end)
                continue
            collisions.extend(_flush_cluster(universe, cluster))
            cluster = [(start, end, item)]
            cluster_end = end
        collisions.extend(_flush_cluster(universe, cluster))
    return tuple(collisions)


def _flush_cluster(universe: int, cluster: list[tuple[int, int, _Assessed]]) -> list[Collision]:
    if len(cluster) < 2:
        return []
    span = (min(start for start, _, _ in cluster), max(end for _, end, _ in cluster))
    ordered = sorted(cluster, key=lambda entry: entry[2].record.slot)
    return [
        Collision(
            kind=RANGE_OVERLAP,
            universe=universe,
            address=span[0],
            members=tuple(_ref(entry[2].record) for entry in ordered),
            detail=(
                f"유니버스 {universe} 채널 {span[0]}~{span[1]} 구간을 "
                f"픽스처 {len(ordered)}개가 겹쳐 점유한다"
            ),
            span=span,
        )
    ]


def _exact_width_slots(assessed: list[_Assessed], policy: FootprintPolicy) -> tuple[int, ...]:
    """Slots the exact-width axis actually compared."""
    if not policy.enabled:
        return ()
    return tuple(
        item.record.slot
        for item in assessed
        if item.parse.ok
        and item.type_mode_ok
        and _footprint_width(policy, item.record.slot) is not None
    )


def _overlap_basis(
    assessed: list[_Assessed], policy: FootprintPolicy, walk: WalkOutcome | None
) -> tuple[OverlapBasis, tuple[AddressGap, ...]]:
    """The rig-wide grade, its evidence, and the pairs the bound left open.

    Exact widths OUTRANK the bound. Where a real footprint is known the verdict
    is unqualified for that slot, so the bound adds nothing there and a gap whose
    both ends have real widths is left to the other axis entirely.

    An unsettled gap is NOT a collision. The bound argument runs one way: a gap
    of at least ``bound`` proves the intervals cannot meet, while a smaller gap
    proves nothing at all, because the fixtures involved may well be using a
    narrow mode. Turning that into a collision would print ``충돌`` for a rig
    nobody has shown to be faulty.

    The returned grade is the WEAKEST of the comparisons performed. A rig where
    three slots were never compared is not a cleared rig, however strong the
    verdict on the rest.
    """
    exact = _exact_width_slots(assessed, policy)
    exact_set = set(exact)
    bound = upper_bound(walk) if walk is not None else None
    groups = _address_groups(assessed)

    covered = set(exact)
    bound_slots: tuple[int, ...] = ()
    unsettled: tuple[AddressGap, ...] = ()
    if bound is not None:
        bound_slots = tuple(
            item.record.slot
            for item in assessed
            if item.parse.ok and item.record.slot not in exact_set
        )
        covered |= set(bound_slots)

        def has_exact_end(gap: AddressGap) -> bool:
            return all(
                item.record.slot in exact_set
                for address in (gap.lower, gap.upper)
                for item in groups.get((gap.universe, address), [])
            )

        relevant = tuple(gap for gap in address_gaps(set(groups)) if not has_exact_end(gap))
        unsettled = unsettled_gaps(relevant, bound)

    grades: set[str] = set()
    if exact:
        grades.add(EXACT_WIDTHS)
    if bound_slots:
        grades.add(BOUND_INCONCLUSIVE if unsettled else BOUND_PROVES_CLEAR)
    if any(item.record.slot not in covered for item in assessed):
        grades.add(NOT_PERFORMED)

    basis = _weakest(grades)
    return (
        OverlapBasis(
            basis=basis,
            bound=bound,
            bound_source=bound_source(walk) if walk is not None else "",
            mode_widths=walk.mode_widths if walk is not None else (),
            exact_width_slots=tuple(sorted(exact_set)),
            bound_slots=tuple(sorted(set(bound_slots))),
            observation_note=_observation_note(basis, walk, len(unsettled)),
        ),
        unsettled,
    )


def _observation_note(basis: str, walk: WalkOutcome | None, unsettled_count: int) -> str:
    """What the grade is limited to, in the reader's language.

    ``bound_proves_clear`` is the dangerous one: without the qualifier it reads as
    an unconditional "no overlap", and the modes that were never enumerated are
    outside the claim. The pre-check has already been wrong in exactly this shape
    once, on the ``incomplete`` label.
    """
    if walk is not None and walk.failure is not None:
        return walk.failure_detail
    if basis == BOUND_PROVES_CLEAR and walk is not None:
        return (
            f"열거된 모드 {len(walk.mode_widths)}개에 한정한 판정이다 — "
            "열거되지 않은 모드와 다중 브레이크 점유는 이 주장 밖이다."
        )
    if basis == BOUND_INCONCLUSIVE:
        return f"상계로 판정하지 못한 인접쌍이 {unsettled_count}건 남았다 — 충돌이 아니다."
    if basis == EXACT_WIDTHS:
        return "실제 점유폭으로 비교했다 — 비교된 슬롯에 대해 한정이 없다."
    return "겹침 비교를 수행하지 않았다 — 겹침이 없다는 뜻이 아니다."


def _unsettled_reason(
    unsettled: tuple[AddressGap, ...], bound: int, groups: Mapping[tuple[int, int], list[_Assessed]]
) -> str:
    """One notice line enumerating every pair the bound did not settle.

    ``skipped_checks`` keeps one row per kind, so the universes and addresses go
    inside this one string rather than into rows that would be dropped.
    """

    def slots_at(universe: int, address: int) -> str:
        members = groups.get((universe, address), [])
        return "/".join(
            str(item.record.slot) for item in sorted(members, key=lambda i: i.record.slot)
        )

    pairs = " · ".join(
        f"유니버스 {gap.universe} 주소 {gap.lower}(슬롯 {slots_at(gap.universe, gap.lower)})"
        f"~{gap.upper}(슬롯 {slots_at(gap.universe, gap.upper)}) 간격 {gap.size}"
        for gap in unsettled
    )
    return (
        f"열거된 모드의 최대 점유폭 {bound}보다 간격이 좁은 인접쌍 {len(unsettled)}건은 "
        f"겹침 여부를 판정하지 못했다({pairs}). "
        "상계는 겹침 없음만 증명할 수 있고 겹침 있음은 증명하지 못한다 — "
        "판정하지 못한 것은 충돌이 아니다."
    )


def _scope_note(collision_total: int, missing_count: int, qualified: bool) -> str:
    if qualified:
        return (
            f"{SCOPE_QUALIFIER} 충돌 {collision_total}건 · "
            f"미관측 {missing_count}건은 판정하지 않았다"
        )
    return f"충돌 {collision_total}건"


def evaluate_patch(
    inventory: Inventory,
    footprint: FootprintPolicy | None = None,
    walk: WalkOutcome | None = None,
) -> PatchEvaluation:
    """Judge one inventory: normalise, group collisions, keep the exclusions."""
    policy = footprint or FootprintPolicy()

    assessed: list[_Assessed] = []
    parse_failures: list[ReadFailure] = []
    for record in inventory.fixtures:
        reasons: list[str] = []
        patch_failure = record.failure_for("Patch")
        parse = normalize_address(record.patch_raw)
        if patch_failure is not None:
            # Already classified upstream (unreadable / unusable shape); do not
            # report the same property twice under a second kind.
            reasons.append(patch_failure.kind)
        elif not parse.ok:
            reasons.append(ADDRESS_PARSE_FAILED)
            parse_failures.append(
                ReadFailure(
                    slot=record.slot,
                    name=record.name,
                    property="Patch",
                    raw_value=record.patch_raw,
                    kind=ADDRESS_PARSE_FAILED,
                    detail=parse.error or "주소 파싱 불가",
                )
            )
        type_mode_ok = record.fixture_type is not None and record.mode is not None
        if not type_mode_ok:
            reasons.append(TYPE_MODE_UNRESOLVED)
        assessed.append(
            _Assessed(
                record=record,
                parse=parse,
                reasons=tuple(dict.fromkeys(reasons)),
                type_mode_ok=type_mode_ok,
            )
        )

    duplicates = _address_duplicates(assessed)
    if policy.enabled:
        overlaps = _range_overlaps(assessed, policy)
        skipped: list[SkippedCheck] = []
        uncovered = _judgeable_without_width(assessed, policy)
        if uncovered:
            # An enabled axis with an incomplete width map did not answer for the
            # whole rig. Without this the report prints `충돌 0건` and NOTHING
            # else: with `enabled=True, widths={}` every fixture is excluded, no
            # collision is found, `skipped_checks` stays empty, and the user reads
            # that the range-overlap check ran and the rig is clean. The shipped
            # handler does not build a policy, so today this is unreachable in
            # production -- and the next caller to build one lands exactly here.
            skipped.append(
                SkippedCheck(
                    kind=RANGE_OVERLAP_DESCOPE,
                    reason=(
                        f"점유폭이 없는 픽스처 {len(uncovered)}개는 구간 비교를 받지 않았다"
                        f"(슬롯 {', '.join(str(slot) for slot in uncovered)}). "
                        "폭 출처가 타입별 조회이므로 부분 판독이 정상 결과다. "
                        "비교하지 않은 것은 겹침이 없다는 뜻이 아니다."
                    ),
                    assumption=ASSUMPTION_27,
                )
            )
    else:
        overlaps = ()
        skipped = [
            SkippedCheck(
                kind=RANGE_OVERLAP_DESCOPE,
                reason=RANGE_OVERLAP_DESCOPE_REASON,
                assumption=ASSUMPTION_27,
            )
        ]

    # The bound axis, when a walk was supplied. Nothing it produces enters
    # ``overlaps``: an unsettled pair is not a collision, and putting it there
    # would give the fixtures a ``collision`` verdict and print ``충돌 N건`` for a
    # rig nobody has shown to be faulty. The unsettled state instead reaches the
    # user through ``skipped_checks``, which is the channel for "ran, did not
    # conclude" -- silence would be the actual defect.
    overlap, unsettled = _overlap_basis(assessed, policy, walk)
    if unsettled and overlap.bound is not None:
        skipped.append(
            SkippedCheck(
                kind=RANGE_OVERLAP_BOUND_INCONCLUSIVE,
                reason=_unsettled_reason(unsettled, overlap.bound, _address_groups(assessed)),
                assumption=BOUND_ASSUMPTIONS,
            )
        )

    duplicate_slots = {member.slot for c in duplicates for member in c.members}
    overlap_slots = {member.slot for c in overlaps for member in c.members}

    rows: list[FixtureVerdict] = []
    counts = {OBSERVED_CLEAR: 0, COLLISION: 0, READ_FAILED: 0, NOT_ASSESSED: 0}
    for item in assessed:
        reasons = list(item.reasons)
        if item.record.slot in duplicate_slots:
            reasons.append(ADDRESS_DUPLICATE)
        if item.record.slot in overlap_slots:
            reasons.append(RANGE_OVERLAP)
        if item.record.slot in duplicate_slots or item.record.slot in overlap_slots:
            # A determined collision outranks an unreadable sibling property:
            # reporting it as a read failure would hide a real finding. The
            # read failure is still listed in ``reasons`` and ``read_failures``.
            verdict = COLLISION
        elif item.reasons:
            verdict = READ_FAILED
        else:
            verdict = OBSERVED_CLEAR
        counts[verdict] += 1
        rows.append(
            FixtureVerdict(
                record=item.record,
                universe=item.parse.universe,
                address=item.parse.address,
                verdict=verdict,
                reasons=tuple(dict.fromkeys(reasons)),
            )
        )
    counts[NOT_ASSESSED] = inventory.missing_count

    # Slot order, so a reader walks the rig once. A slotless failure (the
    # enumeration gave no index) sorts first because it is not about one fixture.
    read_failures = tuple(
        sorted(
            tuple(inventory.read_failures) + tuple(parse_failures),
            key=lambda failure: (failure.slot is not None, failure.slot or 0, failure.property),
        )
    )
    failure_counts = dict.fromkeys(sorted(READ_FAILURE_KIND), 0)
    for failure in read_failures:
        failure_counts[validate("read_failure_kind", failure.kind)] += 1

    qualified = inventory.completeness == INCOMPLETE
    return PatchEvaluation(
        inventory=inventory,
        rows=tuple(rows),
        address_duplicates=duplicates,
        range_overlaps=overlaps,
        read_failures=read_failures,
        skipped_checks=tuple(skipped),
        verdict_counts=counts,
        read_failure_counts=failure_counts,
        scope_qualified=qualified,
        scope_note=_scope_note(len(duplicates) + len(overlaps), inventory.missing_count, qualified),
        overlap=overlap,
    )
