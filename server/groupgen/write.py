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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.spatial.choreography import build_spatial_selection_chain

__all__ = [
    "DEFAULT_GROUP_PLAN_CAP",
    "FIXTURE_LIST_TRUNCATED",
    "GROUP_PLAN_TOO_LARGE",
    "GROUP_POOL_TRUNCATED",
    "GROUP_POOL_UNAVAILABLE",
    "GROUP_SLOT_OCCUPIED",
    "GroupSlotError",
    "GroupWritePlan",
    "GroupWriteStep",
    "build_group_write_plan",
    "guard_fixture_list_truncation",
    "guard_plan_size",
    "measure_empty_slots",
    "select_group_slot",
]

GROUP_POOL_UNAVAILABLE = "GROUP_POOL_UNAVAILABLE"  # the group pool could not be read at all
GROUP_POOL_TRUNCATED = "GROUP_POOL_TRUNCATED"  # the re-queried pool listing was cut
GROUP_SLOT_OCCUPIED = "GROUP_SLOT_OCCUPIED"  # the target slot already holds a group
FIXTURE_LIST_TRUNCATED = "FIXTURE_LIST_TRUNCATED"  # the target fixture list was cut
GROUP_PLAN_TOO_LARGE = "GROUP_PLAN_TOO_LARGE"  # the requested plan exceeds the slot-economy cap

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
    """The full plan for one ``create_arrangement_groups`` call."""

    steps: tuple[GroupWriteStep, ...]
    unverified: tuple[str, ...]
    unverified_reason: str
    human_check_commands: tuple[str, ...]


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
    """Refuse a group write whose target fixture list was truncated.

    An 18/19-fixture group would silently persist as a wrong asset
    (research.md §5.2) — the selection that built it vanishes on the next
    ``ClearAll``, but the group itself does not (design.md §6.3, "함정 7").
    """
    if fixtures_section.get("truncated"):
        raise GroupSlotError(
            FIXTURE_LIST_TRUNCATED,
            "the fixture list to be grouped was truncated, so an incomplete "
            "group would silently persist as a wrong asset; automatic "
            "grouping is refused",
        )


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
    """
    guard_fixture_list_truncation(fixtures_section)
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
    )
