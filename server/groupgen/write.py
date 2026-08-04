"""Pure assembly of grandMA3 group-write command plans (design.md §6).

This module BUILDS command text and never sends any — it imports no OSC
transport layer and no safety gate. Firing and gate traversal are the
follow-up wave's ``server/orchestrator/tools.py`` job,
mirroring the layer split ``server/scene/compile.py`` already draws between
pure assembly and the caller that sends (design.md §6, this SPEC's contract).

Slot selection follows the 3-tier defense ``server/scene/compile.py:243``
(``_select_cue_number``) already proved for the cue domain, reimplemented here
for the group domain with its own error-code vocabulary (design.md §6.1) —
the two domains never share an exception type, because a group write adds a
fourth tier the cue domain does not have: an occupied slot is a **static**
block, never a candidate to skip past (research.md §2.1 — membership cannot
be read back, so an overwritten slot cannot be backed up or restored).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.spatial.choreography import build_spatial_selection_chain

__all__ = [
    "DEFAULT_GROUP_PLAN_CAP",
    "FIXTURE_LIST_TRUNCATED",
    "GROUP_LINE_COLLISION",
    "GROUP_PLAN_TOO_LARGE",
    "GROUP_POOL_TRUNCATED",
    "GROUP_POOL_UNAVAILABLE",
    "GROUP_SLOT_OCCUPIED",
    "GroupSlotError",
    "GroupWritePlan",
    "GroupWriteStep",
    "build_group_write_plan",
    "guard_bundle_collision",
    "guard_fixture_list_truncation",
    "guard_plan_size",
    "is_programmer_state",
    "measure_empty_slots",
    "select_group_slot",
]

GROUP_POOL_UNAVAILABLE = "GROUP_POOL_UNAVAILABLE"  # the group pool could not be read at all
GROUP_POOL_TRUNCATED = "GROUP_POOL_TRUNCATED"  # the re-queried pool listing was cut
GROUP_SLOT_OCCUPIED = "GROUP_SLOT_OCCUPIED"  # the target slot already holds a group
FIXTURE_LIST_TRUNCATED = "FIXTURE_LIST_TRUNCATED"  # the target fixture list was cut
GROUP_PLAN_TOO_LARGE = "GROUP_PLAN_TOO_LARGE"  # the requested plan exceeds the slot-economy cap
GROUP_LINE_COLLISION = "GROUP_LINE_COLLISION"  # one bundle repeats a non-exempt line

# A grid topology's axis-separated naming (design.md §4/§D-Q2) can still ask
# for a double-digit bucket count on a wide rig (a 5x20 grid asks for 25:
# depth 5 + lateral 20) — grandMA3 group slots are a finite, shared LD asset
# (a single reserved GS SHOP showfile pool measured `{2..10, 14, 16+}` empty,
# progress.md §E.2.3), so an unbounded plan can silently eat most of it in one
# call. This is a POLICY DEFAULT, not a measured console limit — no live probe
# has established a hard ceiling on group count. The value borrows this
# repository's already-established batch-size ceiling for one bounded round
# trip against this same console family (`RIG_DRILLDOWN_QUERY_CAP = 16`,
# server/orchestrator/tools.py) as the nearest precedent for "how large a
# single automated batch against this console is allowed to be" — the
# constant is NOT imported (the domains differ: drilldown reads vs. group
# writes), it is re-declared here with its own name and its own rationale.
DEFAULT_GROUP_PLAN_CAP = 16

_CLEAR = "ClearAll"

# @MX:ANCHOR: [AUTO] this exemption set MUST stay equal to
#   `server/orchestrator/tools.py` `_PROGRAMMER_STATE_COMMANDS`.
# @MX:REASON: `guard_bundle_collision` below decides which of THIS module's OWN
#   lines the run_commands dedupe will compare. If this set is wider than the
#   tool's, the guard waves through a line the dedupe then drops — and the drop
#   is silent, because `Store Group N` still runs and the console still answers
#   ok, leaving a group that holds whatever the PREVIOUS chain put in the
#   programmer. Membership is unreadable on this platform (progress.md §E.2.8),
#   so that corruption is neither detectable nor repairable afterwards. The
#   equality is asserted by `server/tests/test_groupgen_write.py`, which may
#   import both sides; this module may NOT import the tool layer, because
#   `tools.py` imports `server.groupgen.write` at registration time and a
#   top-level write->tools import would be circular. That is the identical
#   cycle `server/fx/instantiate.py` faced, and this is its identical answer.
_SELECTION_OPERAND = r"\d+(?:\s*[-+]\s*\d+|\s+Thru(?:\s+\d+)?)*"
_PROGRAMMER_STATE_COMMANDS = (
    re.compile(r"Clear", re.IGNORECASE),
    re.compile(r"ClearAll", re.IGNORECASE),
    re.compile(rf"(?:Fixture|Group)\s+{_SELECTION_OPERAND}", re.IGNORECASE),
)


def is_programmer_state(command: str) -> bool:
    """True for a command that establishes programmer state (exempt from dedupe)."""
    text = command.strip()
    return any(pattern.fullmatch(text) is not None for pattern in _PROGRAMMER_STATE_COMMANDS)


class GroupSlotError(Exception):
    """A group slot or fixture list could not be safely used for a write.

    Carries a ``code`` (one of the four module constants above) so a caller
    can branch on the fact rather than the message text, plus the human
    ``message`` — the same shape as ``server.scene.compile.SceneCompilationError``.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class GroupWriteStep:
    """One group's full write — the fixed chain (design.md §6.2)."""

    slot: int
    name: str
    fids: tuple[int, ...]
    commands: tuple[str, ...]
    verification: tuple[str, ...]


@dataclass(frozen=True)
class GroupWritePlan:
    """The full plan for one ``create_arrangement_groups`` call.

    ``fixture_list_truncated``/``fixture_list_truncated_reason`` are
    STRUCTURAL fields (design.md §10 policy (c), 4th layer "정직한 고지"),
    never docstring-only prose (함정 6) — a caller that only reads the
    ``plan`` field still receives the truncation fact.
    """

    steps: tuple[GroupWriteStep, ...]
    unverified: tuple[str, ...]
    unverified_reason: str
    human_check_commands: tuple[str, ...]
    fixture_list_truncated: bool
    fixture_list_truncated_reason: str


def _group_numbers(groups_section: Mapping[str, object]) -> set[int]:
    listed = groups_section.get("objects")
    if not isinstance(listed, list):
        raise GroupSlotError(
            GROUP_POOL_UNAVAILABLE,
            "the group pool could not be read, so no empty slot can be measured; "
            "inventing one is forbidden (REQ-GROUPGEN-020)",
        )
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            # A group in this pool carries no number — one entry is unreadable
            # and we cannot say which slot it occupies, so no slot in the pool
            # can be claimed empty (same split cue's `_cue_numbers` makes).
            raise GroupSlotError(
                GROUP_POOL_UNAVAILABLE,
                "a group in the pool carries no number, so no slot in the pool "
                "can be measured empty",
            )
        occupied.add(number)
    return occupied


def _guard_pool_readable(groups_section: Mapping[str, object]) -> None:
    unavailable = groups_section.get("reason")
    if isinstance(unavailable, str) or groups_section.get("ok") is False:
        raise GroupSlotError(
            GROUP_POOL_UNAVAILABLE,
            "the group pool could not be read "
            f"({unavailable or 'the section reported not-ok'}), so no empty "
            "slot can be measured",
        )
    if groups_section.get("truncated"):
        raise GroupSlotError(
            GROUP_POOL_TRUNCATED,
            "the group pool listing was truncated, so an unlisted group may "
            "hold any candidate slot; automatic assignment is refused",
        )


def select_group_slot(groups_section: Mapping[str, object], *, requested: int) -> int:
    """Measure one target slot's availability from the re-queried pool.

    Never counts a "next" number — an occupied slot is a static, unconditional
    block (research.md §2.1): membership cannot be read back, so an overwrite
    can be neither backed up nor restored.
    """
    _guard_pool_readable(groups_section)
    occupied = _group_numbers(groups_section)
    if requested in occupied:
        raise GroupSlotError(
            GROUP_SLOT_OCCUPIED,
            f"group {requested} is already occupied; group writes never target "
            "an existing slot (membership cannot be read back for backup — "
            "research.md §2.1)",
        )
    return requested


def measure_empty_slots(groups_section: Mapping[str, object], *, count: int) -> tuple[int, ...]:
    """Measure ``count`` empty slots from the re-queried pool, ascending.

    Scans the actually-occupied set found in ``groups_section`` one candidate
    number at a time — this is measurement against the real pool, not a count
    of how many slots are occupied (REQ-GROUPGEN-020: "번호를 세지 않는다").
    """
    _guard_pool_readable(groups_section)
    occupied = _group_numbers(groups_section)
    empty: list[int] = []
    candidate = 1
    while len(empty) < count:
        if candidate not in occupied:
            empty.append(candidate)
        candidate += 1
    return tuple(empty)


def guard_plan_size(requested: int, *, cap: int) -> None:
    """Refuse a group-write plan that would explode past the slot-economy cap.

    Same discipline as REQ-GROUPGEN-021/024 (D-Q6): **reject**, never "warn
    and proceed" (`.plan-contract.md` §2 D-Q6) — and never silently truncate
    the plan to the first ``cap`` buckets and store only those (a partial
    plan is the worst outcome: an incomplete auto-generated set persists in
    the showfile exactly like an 18/19-fixture group does, REQ-GROUPGEN-024).
    A caller that genuinely needs more slots must say so explicitly via
    ``build_group_write_plan(..., max_plan_size=...)`` — the cap is a
    default, not a ceiling baked into the code.
    """
    if requested > cap:
        raise GroupSlotError(
            GROUP_PLAN_TOO_LARGE,
            f"the requested plan needs {requested} group slots, which exceeds "
            f"the plan-size cap of {cap}; group slots are a finite, shared LD "
            "asset and an unbounded write is refused rather than silently "
            "truncated — either split the request into smaller batches or "
            "pass an explicit max_plan_size to build_group_write_plan to "
            "raise the cap for this call",
        )


def guard_fixture_list_truncation(fixtures_section: Mapping[str, object]) -> None:
    """Refuse an AUTO-SELECTED fixture list that was truncated.

    An 18/19-fixture group would silently persist as a wrong asset
    (research.md §5.2) — the selection that built it vanishes on the next
    ``ClearAll``, but the group itself does not (design.md §6.3, "함정 7").

    **Not called by ``build_group_write_plan`` (amended 2026-08-04, user
    decision).** ``build_group_write_plan`` takes explicit caller-supplied
    ``fids`` per group — the group's membership is fully determined by that
    argument, so a truncated *re-query* of the fixture container cannot make
    an explicitly-named group incomplete. This guard remains for a FUTURE
    auto-selection caller ("group the whole rig for me") that would derive
    ``fids`` FROM the (possibly truncated) fixture listing itself — there,
    REQ-GROUPGEN-024's original rationale still applies unchanged.
    """
    if fixtures_section.get("truncated"):
        raise GroupSlotError(
            FIXTURE_LIST_TRUNCATED,
            "the fixture list to be grouped was truncated, so an incomplete "
            "group would silently persist as a wrong asset; automatic "
            "grouping is refused",
        )


def guard_bundle_collision(commands: Sequence[str]) -> None:
    """Refuse ONE ``run_commands`` bundle that repeats a non-exempt line.

    The mirror precedents are `server/fx/instantiate.py` ``_guard_collision``
    and `server/scene/compile.py` ``_guard_collision`` — the same class of
    fact, guarded the same way: the module that BUILT the lines classifies
    them, because only the builder knows the repeat was meant as two distinct
    moments rather than one instruction typed twice.

    ``run_commands`` drops the second occurrence of a line that already
    succeeded in the same bundle or earlier in the same instruction turn
    (``skipped_already_executed``), unless the line establishes programmer
    state. A group chain's SELECTION line is not exempt: only a single bare
    ``Fixture <operand>`` matches, never the multi-fixture
    ``Fixture 1 + Fixture 2 + Fixture 3`` form this module emits
    (``build_spatial_selection_chain``). So if one bundle carries two groups
    that select the same fids, the second selection is dropped, the following
    ``Store Group N`` fires against a programmer holding nothing (the chain's
    own ``ClearAll`` ran first), and the console still answers ok. grandMA3
    exposes no channel to read group membership back (progress.md §E.2.8), so
    that outcome is neither detectable nor repairable afterwards — refusing to
    build such a bundle is the only honest move.

    Pass EXACTLY the list about to be handed to one ``run_commands`` call.
    Concatenating several groups' chains into one bundle is the shape this
    refuses; the tool layer therefore fires one bundle per group.
    """
    seen: set[str] = set()
    for command in commands:
        if is_programmer_state(command):
            continue
        if command in seen:
            raise GroupSlotError(
                GROUP_LINE_COLLISION,
                f"this bundle would send the line {command!r} twice; the second one "
                "is dropped by the run_commands dedupe and the following Store then "
                "runs against a programmer that is missing its selection — silently, "
                "because grandMA3 exposes no channel to read group membership back",
            )
        seen.add(command)


def _label_command(slot: int, name: str) -> str:
    if "'" in name:
        # No escape convention for an embedded single quote is established
        # (00_grammar.md:66 documents none), and a double-quoted value is
        # rejected by the transport layer outright — embedding a raw single
        # quote would prematurely close the quoted argument, so this is
        # refused rather than guessed at.
        raise ValueError(f"group name must not contain a single quote ('): {name!r}")
    if '"' in name:
        raise ValueError(f'group name must not contain a double quote ("): {name!r}')
    return f"Label Group {slot} '{name}'"


def build_group_write_plan(
    *,
    buckets: Mapping[str, Sequence[int]],
    names: Mapping[str, str],
    groups_section: Mapping[str, object],
    fixtures_section: Mapping[str, object],
    max_plan_size: int = DEFAULT_GROUP_PLAN_CAP,
) -> GroupWritePlan:
    """Assemble the full write plan for one ``create_arrangement_groups`` call.

    Membership is never claimed verified (policy (c), design.md §6 contract) —
    ``unverified`` always carries ``"membership"`` as a structural field, not
    prose, so a caller cannot lose the caveat by skipping a docstring
    (함정 6: 툴 설명문은 지시일 뿐 강제가 아니다).

    ``max_plan_size`` bounds how many group slots a single call may claim
    (``guard_plan_size`` — DEFAULT_GROUP_PLAN_CAP, a policy default, not a
    measured console limit). A caller may raise it explicitly per call; the
    default is never silently widened.

    **``fixtures_section`` truncation never blocks this call (amended
    2026-08-04, user decision — REQ-GROUPGEN-024 correction).** Every
    group's membership here is the caller-supplied ``fids`` in ``buckets``,
    never a value derived from re-reading ``fixtures_section`` — a rig that
    answers 18 of 39 fixtures in one UDP round trip (``truncated: true``)
    still names all 39 correctly if the caller already knows their fids.
    REQ-GROUPGEN-024's original "18/19-fixture group persists silently"
    hazard applies only to a caller that AUTO-SELECTS fids from the
    (possibly truncated) listing — that hazard does not exist here, so the
    call proceeds and the truncation fact is carried structurally on the
    returned plan instead (``fixture_list_truncated`` /
    ``fixture_list_truncated_reason``), never as a raised refusal.
    REQ-GROUPGEN-021 (a truncated GROUP POOL blocks slot allocation) is a
    separate, unchanged guard — see ``guard_pool_readable`` via
    ``measure_empty_slots`` below.

    Each step's ``commands`` tuple is ONE ``run_commands`` bundle, and the
    caller MUST fire it as one — never concatenated with another step's.
    ``guard_bundle_collision`` states why, and is applied to every step here
    so this module never hands out a self-colliding chain.
    """
    bucket_keys = list(buckets)
    guard_plan_size(len(bucket_keys), cap=max_plan_size)
    empty_slots = measure_empty_slots(groups_section, count=len(bucket_keys))

    steps: list[GroupWriteStep] = []
    written_slots: list[int] = []
    for key, slot in zip(bucket_keys, empty_slots, strict=True):
        selected = select_group_slot(groups_section, requested=slot)
        fids = tuple(buckets[key])
        name = names[key]
        selection_line = build_spatial_selection_chain(fids)
        commands = (
            _CLEAR,
            selection_line,
            f"Store Group {selected}",
            _label_command(selected, name),
            _CLEAR,
        )
        guard_bundle_collision(commands)
        verification = (
            f"state DataPool/Groups/{selected}",
            f"prop DataPool/Groups/{selected} Name",
        )
        steps.append(
            GroupWriteStep(
                slot=selected,
                name=name,
                fids=fids,
                commands=commands,
                verification=verification,
            )
        )
        written_slots.append(selected)

    # 범위 봉쇄 정적 단언 (design.md §6.5) — a construction-order guard, not a
    # trust boundary: `written_slots` is built from `empty_slots` above, so
    # this assertion is a static proof the two never diverge under refactor.
    assert set(written_slots) <= set(empty_slots), (
        f"write scope {written_slots} exceeds measured empty slots {empty_slots}"
    )

    fixture_list_truncated = bool(fixtures_section.get("truncated"))
    return GroupWritePlan(
        steps=tuple(steps),
        unverified=("membership",),
        unverified_reason=(
            "grandMA3 does not expose group membership on any readable "
            "channel (progress.md §E.2.8) — re-querying after Store cannot "
            "confirm which fixtures actually landed in the slot; only the "
            "slot's existence and its label are re-queried as evidence"
        ),
        human_check_commands=tuple(f"Group {slot}" for slot in written_slots),
        fixture_list_truncated=fixture_list_truncated,
        fixture_list_truncated_reason=(
            "the re-queried fixture container listing was truncated "
            "(truncated: true) — this does NOT affect this call's groups, "
            "which were built from caller-supplied fids, not from the "
            "truncated listing; recorded structurally so a reviewer can see "
            "the rig may hold more fixtures than any single listing showed"
            if fixture_list_truncated
            else ""
        ),
    )
