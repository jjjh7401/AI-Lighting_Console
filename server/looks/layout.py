"""Executor layout planner — sequence -> executor -> label wiring (T-F).

Takes an already-built genre bundle (``server.looks.busking.GenreBundle``)
plus a caller-supplied ``sequence_numbers`` mapping and turns them into a
deterministic per-page executor placement plan. This module never invents a
sequence number: SPEC-COPILOT-BUSKWIZ-001 M5's GO-branch (left un-implemented,
``server/tests/test_busking_executor.py::TestGoBranch``) named "the binding
target must already exist" as an unmet precondition for an Assign-to-executor
capability, so ``sequence_numbers`` here is the caller's attestation that each
number already names a real ``DataPool/Sequences/<no>`` object — this module
only decides WHICH executor a given, already-existing sequence lands on.

Pure module: no execution/state port, no gate import. This is the SAME
boundary ``server/looks/busking.py`` documents and ``test_looks_boundary.py``
enforces at the AST level over the whole ``server/looks`` package — a look
module may not name ``SafetyGate``/``screen``/``CommandExecutionPort``/
``server.orchestrator.ports``. The occupancy CHECK against a live console
(task item 4) is therefore a separate, impure step
(``server/web/layout_occupancy.py``) that fetches plain dict state and hands
it back to :func:`mark_occupancy_conflicts` here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from server.looks.busking import GenreBundle
from server.looks.songcue import _ascii_label  # single source of truth for label text

__all__ = [
    "OCCUPIED",
    "PAGE_CAPACITY_EXHAUSTED",
    "SEQUENCE_NOT_PROVIDED",
    "UNCONFIRMED",
    "LayoutItem",
    "LayoutPlan",
    "LayoutSkip",
    "build_layout_commands",
    "console_executor_no",
    "mark_occupancy_conflicts",
    "plan_layout",
]

# Why an item is missing a plan entry — the two reasons are NOT interchangeable
# (mirrors the get_rig_context REASON_UNRESOLVED/REASON_UNREACHABLE split in
# server/orchestrator/tools.py: keep causes that need different fixes apart).
SEQUENCE_NOT_PROVIDED = "sequence_not_provided"
PAGE_CAPACITY_EXHAUSTED = "page_capacity_exhausted"

# Why an item is flagged as a conflict (task item 4 — "충돌로 표시").
OCCUPIED = "occupied"
UNCONFIRMED = "unconfirmed"

# The measured executor-page capacity: page 1 carries exactly 8 executors, all
# uniformly measured (SPEC-COPILOT-SHOWUI-001 live probe, see
# console_executor_no's @MX:ANCHOR below). Not a console-wide constant — a
# different page's real capacity is UNMEASURED — so this is only the default
# a caller may always override.
DEFAULT_PAGE_CAPACITY = 8


@dataclass(frozen=True)
class LayoutItem:
    """One look's placement: which sequence, which executor, what label."""

    look_id: str
    display_name: str
    sequence_number: int
    label: str
    page_no: int
    slot: int
    executor_no: int
    conflict: bool = False
    conflict_reason: str | None = None
    conflict_detail: str = ""


@dataclass(frozen=True)
class LayoutSkip:
    """A look the plan could not place, and why (REQ-BUSKWIZ-013-style honesty)."""

    look_id: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class LayoutPlan:
    """The whole page's placement plan for one genre bundle."""

    genre: str
    page_no: int
    items: tuple[LayoutItem, ...] = ()
    skipped: tuple[LayoutSkip, ...] = ()

    @property
    def complete(self) -> bool:
        """True only when every look in the bundle landed on an executor."""
        return bool(self.items) and not self.skipped

    @property
    def conflicts(self) -> tuple[LayoutItem, ...]:
        return tuple(item for item in self.items if item.conflict)


# @MX:ANCHOR: [AUTO] slot -> console real-executor-number conversion —
# live-measured on onPC 2.4.2 (SPEC-COPILOT-SHOWUI-001, all 8 page-1 slots
# uniformly confirmed): the console's REAL executor number is NOT the slot
# index — it is `page_no * 100 + slot_no` ("Executor 101" is page 1 slot 1).
# `server/web/dash.py::_executor_candidates` carries the SAME fact for the
# READ side (candidate list, live-confirmed per-item via
# `_confirm_executor_no`); this is the WRITE-side twin, used to build the
# Assign target BEFORE any command is emitted.
# @MX:REASON: treating the slot index as the address is the exact defect
# SHOWUI-001 measured — slot 1 fires an unrelated executor with NO console
# error (page1 slot=1 vs the naive address "1" collides with an occupied
# executor elsewhere). `server/tests/test_busking_executor.py`
# (`test_no_page_times_hundred_arithmetic`) additionally forbids
# hardcoding this formula as a general multi-page rule inside
# `server/looks/busking.py`/`report.py` pending a 2+ page live measurement —
# this module lives OUTSIDE that pair specifically so the two concerns (the
# BUSKWIZ preset-store axis vs this SPEC's executor-layout axis) stay
# independently auditable, but the SAME caution applies: only page 1 is
# measured, so a caller MUST NOT treat other pages as verified.
def console_executor_no(page_no: int, slot_no: int) -> int:
    """The console-real "Executor <n>" number for one page-drilled slot.

    Verified ONLY for ``page_no == 1`` (SHOWUI-001). Other pages compute the
    same formula but are UNVERIFIED — a caller targeting page != 1 is
    responsible for its own live confirmation before trusting the result.
    """
    if isinstance(page_no, bool) or isinstance(slot_no, bool):
        raise ValueError(f"page_no/slot_no must be int, not bool: {page_no!r}, {slot_no!r}")
    if page_no < 1:
        raise ValueError(f"page_no must be >= 1: {page_no!r}")
    if slot_no < 1:
        raise ValueError(f"slot_no must be >= 1: {slot_no!r}")
    return page_no * 100 + slot_no


def plan_layout(
    bundle: GenreBundle,
    sequence_numbers: Mapping[str, int],
    *,
    page_no: int = 1,
    start_slot: int = 1,
    page_capacity: int = DEFAULT_PAGE_CAPACITY,
) -> LayoutPlan:
    """Deterministically place ``bundle.looks`` onto page ``page_no``.

    Order (the sort rule, chosen and fixed here): ``bundle.looks`` already
    carries ``looks_for_genre``'s dynamics-ascending, ``look_id``-tiebreak
    order (busking.py:82-97) — quiet/base looks first, climax/effect looks
    last. Reusing that order rather than re-deriving one keeps a single
    definition of "look order" across the preset-store axis and this
    executor-layout axis; re-sorting here would let the two silently diverge.

    A look with no entry in ``sequence_numbers`` is skipped
    (``SEQUENCE_NOT_PROVIDED``) rather than assigned a placeholder — this
    module never allocates a sequence number (module docstring). Looks beyond
    ``page_capacity`` are skipped (``PAGE_CAPACITY_EXHAUSTED``) rather than
    spilling onto an unrequested page.
    """
    if start_slot < 1:
        raise ValueError(f"start_slot must be >= 1: {start_slot!r}")
    items: list[LayoutItem] = []
    skipped: list[LayoutSkip] = []
    slot = start_slot
    for plan in bundle.looks:
        if slot > page_capacity:
            skipped.append(
                LayoutSkip(
                    look_id=plan.look_id,
                    reason=PAGE_CAPACITY_EXHAUSTED,
                    detail=(
                        f"page {page_no} holds {page_capacity} executors; "
                        f"slot {slot} would overflow"
                    ),
                )
            )
            continue
        sequence_number = sequence_numbers.get(plan.look_id)
        if sequence_number is None:
            skipped.append(
                LayoutSkip(
                    look_id=plan.look_id,
                    reason=SEQUENCE_NOT_PROVIDED,
                    detail=(
                        f"no existing sequence number was supplied for look "
                        f"{plan.look_id!r} — this planner does not create sequences"
                    ),
                )
            )
            continue
        items.append(
            LayoutItem(
                look_id=plan.look_id,
                display_name=plan.display_name,
                sequence_number=sequence_number,
                label=_ascii_label(plan.display_name, fallback=f"Look {plan.look_id}"),
                page_no=page_no,
                slot=slot,
                executor_no=console_executor_no(page_no, slot),
            )
        )
        slot += 1
    return LayoutPlan(
        genre=bundle.genre, page_no=page_no, items=tuple(items), skipped=tuple(skipped)
    )


def mark_occupancy_conflicts(
    plan: LayoutPlan, executor_states: Mapping[int, Mapping[str, object]]
) -> LayoutPlan:
    """Flag every item whose target executor is already in use (task item 4).

    Pure: ``executor_states`` is ALREADY-FETCHED plain data — one
    ``"Executor <n>"`` state-query payload per target, keyed by
    ``executor_no``. The occupancy signal is ``node.get("sequenceNo")``, the
    SAME field ``server/web/cue_monitor.py::build_executor_cue_progress``
    reads to tell an assigned executor from an ``"unassigned"`` one — an
    executor with an integer ``sequenceNo`` already has a sequence bound to
    it and MUST NOT be silently overwritten (task instruction; overwrite
    decisions are a human call, this module only reports the conflict).

    An executor missing from ``executor_states`` entirely (the query failed,
    or the caller never fetched it) is treated as a conflict too
    (``UNCONFIRMED``), not as free — "unobserved" is never "observed empty"
    (the same fail-closed discipline ``server/looks/instantiate.py``'s
    ``PoolBinding.occupied is None`` case documents).
    """
    marked: list[LayoutItem] = []
    for item in plan.items:
        state = executor_states.get(item.executor_no)
        if state is None:
            marked.append(
                replace(
                    item,
                    conflict=True,
                    conflict_reason=UNCONFIRMED,
                    conflict_detail=(
                        f"Executor {item.executor_no} was never confirmed by a state query"
                    ),
                )
            )
            continue
        node = state.get("node") if isinstance(state, Mapping) else None
        sequence_no = node.get("sequenceNo") if isinstance(node, Mapping) else None
        if isinstance(sequence_no, int):
            marked.append(
                replace(
                    item,
                    conflict=True,
                    conflict_reason=OCCUPIED,
                    conflict_detail=(
                        f"Executor {item.executor_no} already carries Sequence {sequence_no}"
                    ),
                )
            )
            continue
        marked.append(item)
    return replace(plan, items=tuple(marked))


def build_layout_commands(plan: LayoutPlan) -> tuple[str, ...]:
    """The rulebook-validated command bundle for every NON-conflicted item.

    Only two validated forms are ever emitted (31_choreography_patterns.md):
    ``Assign Sequence <n> At Executor <m>`` and ``Label Sequence <n> '<name>'``
    — never ``Label Executor ...`` (no rulebook entry validates that form; an
    executor's displayed name follows the sequence assigned to it, per the
    same pattern ``server/looks/songcue.py``'s own bundle already uses:
    ``Label Sequence {sequence_number} '{sequence_name}'``). A conflicted
    item is EXCLUDED, never silently overwritten — the caller decides,
    outside this function, whether to re-plan or override (task instruction).
    """
    commands: list[str] = []
    for item in plan.items:
        if item.conflict:
            continue
        commands.append(f"Assign Sequence {item.sequence_number} At Executor {item.executor_no}")
        commands.append(f"Label Sequence {item.sequence_number} '{item.label}'")
    return tuple(commands)
