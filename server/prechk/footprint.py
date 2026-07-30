"""Upper-bound channel footprint from the fixture-type tree (design slots A-D).

The pre-check cannot join a patched fixture to its own DMX footprint: the fixture
node reports its type and mode as DISPLAY STRINGS, and every candidate route from
those strings to a path index was refuted (SPEC-COPILOT-PRECHK-001,
``ASSUMPTION-27``). So the range-overlap axis shipped disabled.

This module takes the weaker proposition that survives the refutation. Let ``W``
be the largest footprint among the modes that can be ENUMERATED. Every mode of
every type occupies at most ``W`` channels, so for two start addresses in the
same universe a gap of ``W`` or more cannot overlap -- no matter which mode
either fixture actually uses. **The asymmetry is the whole design**: this proves
ABSENCE of overlap and can never prove PRESENCE. A gap under ``W`` is not a
collision; it is unsettled, and the caller must report it as such.

Three properties of the shape here exist because getting them wrong produces a
false all-clear rather than an error:

1. **The walk returns ``(completeness, widths)``, never a bound.** Folding
   ``max`` over a PARTIAL mode set yields a number SMALLER than the true bound,
   and a smaller bound wrongly clears wider gaps. A flag added afterwards does
   not undo it: the flag decorates the WALK while the verdict decorates an
   ADDRESS PAIR, and the verdict travels to the report on its own. So the bound
   is folded only inside the completeness-true branch -- see :func:`upper_bound`.
2. **Tiers 1-2 and tier 3 use different truncation predicates.** The mode and
   type listings must be WHOLE (a short listing silently shrinks the bound),
   while the channel listing needs only its COUNT -- measured live as
   ``truncated: true`` with an exact ``childCount``. One shared predicate either
   kills tier 3 on every real rig or lets a partial tier 2 through.
3. **Budget exhaustion invalidates globally, not locally.** Unlike a per-object
   drilldown note, a mode this walk never read is a mode missing from ``W``.

Every read rides ``StateQueryPort.query_state``; no property is read, which is
why this module needs no new opening in the safety chokepoint. Paths and the
query budget arrive as ARGUMENTS -- the module hardcodes no rig path, no width,
no gap and no bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

#: Retyped from ``server.orchestrator.tools``, which this module MUST NOT import
#: (that module imports the pre-check, so the edge would be a cycle -- and the
#: walk has to stay callable without a toolset for the unsettled branch to be
#: testable at all). No new reason vocabulary is invented here:
#: ``server/tests/test_prechk_footprint.py`` pins both values against the
#: originals, so a drift fails rather than forks the classification.
#:
#: The split is the same one: a sibling path answered, so the console is
#: reachable and THIS path is wrong for this showfile (a configuration defect)
#: versus nothing answered at all (an operational condition). Production throws
#: the SAME exception type for both, so the discriminator cannot be the exception
#: -- it is whether any query in this walk already succeeded.
REASON_UNRESOLVED = "path_not_resolved"
REASON_UNREACHABLE = "console_unreachable"

#: The child listing that carries one mode's channel count.
_CHANNELS_SEGMENT = "DMXChannels"
#: The child listing that carries one type's modes.
_MODES_SEGMENT = "DMXModes"


class StateReader(Protocol):
    """The one port method this walk uses. Deliberately narrower than the
    production port: a reader that also offers a property read cannot be
    distinguished from one that does not, and this module must not grow a
    property dependency by accident."""

    def query_state(self, path: str) -> dict: ...


class BudgetExhausted(RuntimeError):
    """The query budget ran out mid-walk. Not an error condition of the rig."""


@dataclass
class _Budget:
    """A hard query ceiling. Counted, not estimated."""

    limit: int
    spent: int = 0

    def spend(self) -> None:
        if self.spent >= self.limit:
            raise BudgetExhausted(f"조회 예산 {self.limit}회를 초과했다")
        self.spent += 1


@dataclass(frozen=True)
class ModeFootprint:
    """One mode's channel count, kept WITH the path that answered it.

    The number alone cannot be audited. A reader who sees a bound of 31 and no
    origin has to trust it; a reader who sees the path and the field name can
    re-query and disagree.
    """

    path: str
    width: int


@dataclass(frozen=True)
class WalkOutcome:
    """What the three-tier walk established -- and did NOT establish.

    ``complete`` is about the MODE SET, not about the walk finishing: a walk that
    returns without raising can still be incomplete. There is deliberately no
    ``bound`` attribute; :func:`upper_bound` is the only way to get one and it
    refuses when ``complete`` is false.
    """

    complete: bool
    footprints: tuple[ModeFootprint, ...] = ()
    queried_paths: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    failure: str | None = None
    failure_detail: str = ""

    @property
    def mode_widths(self) -> tuple[int, ...]:
        return tuple(footprint.width for footprint in self.footprints)

    @property
    def query_count(self) -> int:
        return len(self.queried_paths)


def upper_bound(outcome: WalkOutcome) -> int | None:
    """The largest enumerated footprint, or ``None`` when there is no bound.

    The completeness test guards the fold. An incomplete walk has no bound at
    all -- returning ``max`` of what it saw would be a number that looks like a
    bound, is smaller than the real one, and clears gaps it must not clear.
    """
    if outcome.complete and outcome.mode_widths:
        return max(outcome.mode_widths)
    return None


def bound_source(outcome: WalkOutcome) -> str:
    """Where the bound came from: the path, and the field read on it.

    Guarded by the same completeness test as the fold, in the same positive-branch
    shape: a walk with no bound must not hand back an origin for a number it never
    produced, and the AST check that pins the fold's placement covers this
    function too. The string matches the exact-width axis's own ``source`` shape,
    so a reader compares like with like.
    """
    if outcome.complete and outcome.footprints:
        widest = max(outcome.footprints, key=lambda footprint: footprint.width)
        return f"{widest.path} childCount"
    return ""


def _payload_ok(payload: object) -> bool:
    return isinstance(payload, dict) and payload.get("ok") is not False


def _listing_is_whole(payload: dict) -> bool:
    """Tier 1-2 predicate: did this listing return EVERY child it declares?

    Count comparison first, because the flag says "incomplete" without saying by
    how much. The flag is honoured as well: a listing that flags truncation while
    its count matches is self-contradictory, and a bound must not be folded over
    a self-contradictory snapshot.
    """
    node = payload.get("node")
    if not isinstance(node, dict):
        return False
    declared = node.get("childCount")
    if isinstance(declared, bool) or not isinstance(declared, int):
        return False
    children = payload.get("children")
    if not isinstance(children, list) or len(children) != declared:
        return False
    return payload.get("truncated") is not True


def _declared_child_count(payload: dict) -> int | None:
    """Tier 3 predicate: the declared count, or ``None`` when there is none.

    Reads the COUNT and nothing else. It never looks at the returned items, so a
    truncated channel listing still yields its width -- which is the measured
    shape on the live rig. Writing ``childCount > len(...)`` here would make the
    feature permanently unavailable on every real showfile.
    """
    node = payload.get("node")
    if not isinstance(node, dict):
        return None
    declared = node.get("childCount")
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 1:
        return None
    return declared


def _child_slots(payload: dict) -> list[int] | None:
    """Pool slots of the returned children, or ``None`` if any child lacks one.

    A numeric path segment addresses the POOL SLOT the snapshot reports as ``i``
    (``console/lua/PROTOCOL.md`` §2 · ``console/lua/copilot_responder.lua``
    426-449). Position in the list is NOT an address: on a sparse pool the two
    disagree and the walk would read a neighbour's channel count.
    """
    slots: list[int] = []
    for child in payload.get("children") or []:
        if not isinstance(child, dict):
            return None
        slot = child.get("i")
        if isinstance(slot, bool) or not isinstance(slot, int):
            return None
        slots.append(slot)
    return slots


def walk_mode_widths(reader: StateReader, *, root: str, budget: int) -> WalkOutcome:
    """Enumerate every mode footprint reachable under ``root``.

    ``root`` is the fixture-type listing path and arrives as an argument so the
    ``rig_paths`` override seam applies to this axis too; ``budget`` caps the
    number of queries, which is ``1 + types + modes`` and therefore unknown
    before the first read.

    Returns an outcome whose ``complete`` is true only when every tier answered
    wholly and the budget held. Failures are classified, never raised: a walk
    that cannot run must not cost the caller the rest of its report.
    """
    limit = _Budget(limit=budget)
    queried: list[str] = []
    notes: list[str] = []
    widths: list[ModeFootprint] = []

    def read(path: str) -> dict:
        limit.spend()
        payload = reader.query_state(path)
        queried.append(path)
        if not _payload_ok(payload):
            raise LookupError(path)
        return payload

    def classify(path: str) -> WalkOutcome:
        # Whether a SIBLING answered is the discriminator, not the exception
        # type: production reports "no such path" and "no reply" identically.
        if queried:
            return WalkOutcome(
                complete=False,
                queried_paths=tuple(queried),
                notes=tuple(notes),
                failure=REASON_UNRESOLVED,
                failure_detail=(
                    f"경로 {path}를 이 쇼파일에서 찾지 못했다 — 다른 경로가 답했으므로 "
                    "콘솔은 도달 가능하다. 점유폭 상계를 얻지 못했다."
                ),
            )
        return WalkOutcome(
            complete=False,
            queried_paths=(),
            notes=tuple(notes),
            failure=REASON_UNREACHABLE,
            failure_detail=(
                f"경로 {path} 조회에 어느 응답도 오지 않았다 — 콘솔이 답하지 않는다. "
                "점유폭 상계를 얻지 못했다."
            ),
        )

    try:
        types = read(root)
    except BudgetExhausted as error:
        return _exhausted(queried, notes, error)
    except Exception:
        return classify(root)

    whole = _listing_is_whole(types)
    if not whole:
        notes.append(f"타입 열거가 불완전하다({root})")
    type_slots = _child_slots(types)
    if type_slots is None:
        whole = False
        notes.append(f"타입 자식에 풀 슬롯이 없다({root})")
        type_slots = []

    for type_slot in type_slots:
        modes_path = f"{root}/{type_slot}/{_MODES_SEGMENT}"
        try:
            modes = read(modes_path)
        except BudgetExhausted as error:
            return _exhausted(queried, notes, error)
        except Exception:
            return classify(modes_path)
        if not _listing_is_whole(modes):
            whole = False
            notes.append(f"모드 열거가 불완전하다({modes_path})")
        mode_slots = _child_slots(modes)
        if mode_slots is None:
            whole = False
            notes.append(f"모드 자식에 풀 슬롯이 없다({modes_path})")
            mode_slots = []
        for mode_slot in mode_slots:
            channels_path = f"{modes_path}/{mode_slot}/{_CHANNELS_SEGMENT}"
            try:
                channels = read(channels_path)
            except BudgetExhausted as error:
                return _exhausted(queried, notes, error)
            except Exception:
                return classify(channels_path)
            width = _declared_child_count(channels)
            if width is None:
                whole = False
                notes.append(f"점유폭 계수를 얻지 못했다({channels_path})")
                continue
            widths.append(ModeFootprint(path=channels_path, width=width))

    if not widths:
        whole = False
        notes.append("관측된 모드가 0개다")
    return WalkOutcome(
        complete=whole,
        footprints=tuple(widths),
        queried_paths=tuple(queried),
        notes=tuple(notes),
    )


def _exhausted(queried: list[str], notes: list[str], error: BudgetExhausted) -> WalkOutcome:
    """Exhaustion invalidates the whole bound, not one branch of the walk.

    A per-branch note would be the ``drilldown_capped`` shape, and it is wrong
    here: the modes this walk never reached are modes missing from the fold, so
    the surviving maximum is not a bound at all.
    """
    return WalkOutcome(
        complete=False,
        queried_paths=tuple(queried),
        notes=(*notes, str(error)),
    )


@dataclass(frozen=True)
class AddressGap:
    """The distance between two adjacent start addresses in ONE universe."""

    universe: int
    lower: int
    upper: int

    @property
    def size(self) -> int:
        return self.upper - self.lower


def address_gaps(starts: set[tuple[int, int]]) -> tuple[AddressGap, ...]:
    """Adjacent start-address distances, computed INSIDE each universe.

    ``starts`` is the key set of the address-duplicate grouping, so a shared
    start point appears once: a distance of zero belongs to the duplicate axis,
    and producing it here as well would report one fault twice.

    Buckets never merge. Subtracting an address in universe 2 from one in
    universe 1 subtracts across separate address spaces, and the result would be
    compared against a bound as though it meant something. The last fixture in
    each universe contributes no distance, so the count is the sum of
    ``members - 1`` over the universes rather than ``total - 1``.
    """
    buckets: dict[int, list[int]] = {}
    for universe, address in sorted(starts):
        buckets.setdefault(universe, []).append(address)
    return tuple(
        AddressGap(universe=universe, lower=lower, upper=upper)
        for universe, addresses in sorted(buckets.items())
        for lower, upper in zip(addresses, addresses[1:], strict=False)
    )


def unsettled_gaps(gaps: tuple[AddressGap, ...], bound: int) -> tuple[AddressGap, ...]:
    """Gaps the bound does not settle: those STRICTLY smaller than ``bound``.

    ``size == bound`` is settled. A fixture starting at ``a`` and occupying at
    most ``bound`` channels ends at ``a + bound - 1`` inclusive, and the next
    start is ``a + bound``, so the intervals touch without sharing a channel.
    Writing ``<=`` here reports a demonstrably clear rig as unsettled -- and on
    the measured rig the gap is far wider than the bound, so both spellings give
    the same answer and the error stays dormant until a rig lands exactly on the
    boundary.
    """
    return tuple(gap for gap in gaps if gap.size < bound)
