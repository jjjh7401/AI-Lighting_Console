"""Pure group-write plan assembly (SPEC-COPILOT-GROUPGEN-001 §6)."""

from server.groupgen.write import (
    FIXTURE_LIST_TRUNCATED,
    GROUP_POOL_TRUNCATED,
    GROUP_POOL_UNAVAILABLE,
    GROUP_SLOT_OCCUPIED,
    GroupSlotError,
    GroupWritePlan,
    GroupWriteStep,
    build_group_write_plan,
    guard_fixture_list_truncation,
    measure_empty_slots,
    select_group_slot,
)

__all__ = [
    "FIXTURE_LIST_TRUNCATED",
    "GROUP_POOL_TRUNCATED",
    "GROUP_POOL_UNAVAILABLE",
    "GROUP_SLOT_OCCUPIED",
    "GroupSlotError",
    "GroupWritePlan",
    "GroupWriteStep",
    "build_group_write_plan",
    "guard_fixture_list_truncation",
    "measure_empty_slots",
    "select_group_slot",
]
