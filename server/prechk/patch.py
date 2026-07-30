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

ASSUMPTION_27 = "ASSUMPTION-27"

#: The qualifier every claim carries while the read is incomplete.
SCOPE_QUALIFIER = "관측된 범위에서"

RANGE_OVERLAP_DESCOPE_REASON = (
    "픽스처가 주는 FixtureType·Mode는 표시 문자열이고 경로 인덱스가 아니다. "
    "표시 문자열 파싱 없이 점유폭에 도달하는 경로가 후보 12건 전건 부정으로 확정됐다. "
    "주소 중복 판정은 이 축소와 무관하게 수행한다."
)

_ADDRESS = re.compile(r"^(\d+)\.(\d+)$")


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

    Leading zeros are insignificant, so ``'1.001'`` and ``'1.1'`` normalise to
    the same address -- duplicate detection must not hinge on how the console
    happened to pad the text.
    """
    if raw is None:
        return AddressParse(raw=raw, error="Patch 값이 없다")
    match = _ADDRESS.match(raw.strip())
    if match is None:
        return AddressParse(raw=raw, error=f"'<유니버스>.<주소>' 형태가 아니다: {raw!r}")
    return AddressParse(raw=raw, universe=int(match.group(1)), address=int(match.group(2)))


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


def _address_duplicates(assessed: list[_Assessed]) -> tuple[Collision, ...]:
    """One collision per shared ``(universe, address)`` start point."""
    groups: dict[tuple[int, int], list[_Assessed]] = defaultdict(list)
    for item in assessed:
        if item.parse.ok:
            groups[(item.parse.universe, item.parse.address)].append(item)
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


def _range_overlaps(assessed: list[_Assessed], policy: FootprintPolicy) -> tuple[Collision, ...]:
    """One collision per maximal cluster of overlapping channel ranges.

    Fixtures whose type or mode is unresolved are excluded: their occupancy
    cannot be judged, and REQ-PRECHK-009 forbids counting them either way.
    """
    intervals: dict[int, list[tuple[int, int, _Assessed]]] = defaultdict(list)
    for item in assessed:
        width = policy.widths.get(item.record.slot)
        if not item.parse.ok or not item.type_mode_ok or width is None or width < 1:
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


def _scope_note(collision_total: int, missing_count: int, qualified: bool) -> str:
    if qualified:
        return (
            f"{SCOPE_QUALIFIER} 충돌 {collision_total}건 · "
            f"미관측 {missing_count}건은 판정하지 않았다"
        )
    return f"충돌 {collision_total}건"


def evaluate_patch(
    inventory: Inventory, footprint: FootprintPolicy | None = None
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
    else:
        overlaps = ()
        skipped = [
            SkippedCheck(
                kind=RANGE_OVERLAP_DESCOPE,
                reason=RANGE_OVERLAP_DESCOPE_REASON,
                assumption=ASSUMPTION_27,
            )
        ]

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
    )
