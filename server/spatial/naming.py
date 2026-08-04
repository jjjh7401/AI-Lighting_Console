"""Closed-vocabulary group naming for spatial topology buckets (SPEC-COPILOT-GROUPGEN-001).

Pure module — no transport, no gate, no runtime dependency beyond the standard
library. Consumes only the `TopologyResult` / `FixtureTypeInfo` shaped values
already resolved by `topology.py` / `fixture_type.py` (M1/M2); this module never
imports either.

All public naming functions return a string drawn EXCLUSIVELY from:
  - the closed vocabulary table (design.md §4.1 / spec.md §A.3), or
  - a documented numbered fallback (`Electric N` / `Ring N` / `Level N` /
    `Stage Right N` / `Stage Left N`), direction-labelled per REQ-GROUPGEN-017.
No fixture-derived or otherwise arbitrary string ever reaches a returned name
(AC-GROUPGEN-037).

RIGGING-HARDWARE VOCABULARY IS FORBIDDEN (spec.md §D "Out of Scope — 리깅
하드웨어 위치 판정"): FOH, Boom, Box Boom, Ladder, Torm, floor package are
hardware STRUCTURE names that the patch does not contain. Inferring them from
coordinates would persist a false asset in the showfile. `Electric N` is the
SINGLE carved-out borrowing, and only on the depth axis, because "which bar is
this" is honestly expressible from y order. The lateral 4+ fallback therefore
numbers the already-approved `Stage Right` / `Stage Left` tokens instead of
claiming a boom position.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# §D-Q3 — every auto-generated group name carries this prefix.
# ---------------------------------------------------------------------------

GEO_PREFIX = "GEO "

# ---------------------------------------------------------------------------
# §4.5 — MA3 coordinate convention (research.md §6.1). Single point of truth
# for the stage-left/stage-right sign; never re-derived elsewhere.
# ---------------------------------------------------------------------------

STAGE_LEFT_IS_POSITIVE_X = True

# ---------------------------------------------------------------------------
# Depth axis vocabulary (design.md §4.1 / §4.3)
# ---------------------------------------------------------------------------

_DEPTH_2 = ("Downstage", "Upstage")
_DEPTH_3 = ("Downstage", "Center", "Upstage")


def name_depth_bucket(index: int, total: int) -> str:
    """Depth-axis bucket name, downstage(index 0) -> upstage(index total-1).

    total == 2 -> Downstage/Upstage
    total == 3 -> Downstage/Center/Upstage
    total >= 4 -> Electric 1..N (DS -> US), REQ-GROUPGEN-017 direction disclosure.
    """
    if total == 2:
        return GEO_PREFIX + _DEPTH_2[index]
    if total == 3:
        return GEO_PREFIX + _DEPTH_3[index]
    return GEO_PREFIX + f"Electric {index + 1}"


# ---------------------------------------------------------------------------
# Lateral axis vocabulary (design.md §4.1 / §4.2 / §4.3)
# ---------------------------------------------------------------------------

_LATERAL_2 = ("Stage Right", "Stage Left")
_LATERAL_3 = ("Stage Right", "Centerline", "Stage Left")


def name_lateral_bucket(index: int, total: int) -> str:
    """Lateral-axis bucket name, index 0 = stage-right-most -> index total-1 = stage-left-most.

    total == 2 -> Stage Right / Stage Left
    total == 3 -> Stage Right / Centerline / Stage Left (Centerline is a
                  DISTINCT symbol from name_depth_bucket's Center — §4.3)
    total >= 4 -> Stage Right N / Stage Left N, numbered OUTWARD FROM THE
                  CENTRELINE (1 = nearest centre) on each half; an odd total
                  keeps the single middle bucket as Centerline.

    The 4+ form deliberately reuses the approved `Stage Right` / `Stage Left`
    tokens plus an ordinal. It does NOT name rigging hardware (`Boom`, `FOH`,
    `Ladder`, `Torm`): those are structure names absent from the patch, and
    spec.md §D carves out `Electric N` on the DEPTH axis only. Numbering
    outward from centre is the documented direction required by
    REQ-GROUPGEN-017; the stage reference stays baked into the name so the
    house/stage inversion can never bite (REQ-GROUPGEN-016).
    """
    if not 0 <= index < total:
        raise ValueError(f"index {index} out of range for total {total}")
    if total == 2:
        return GEO_PREFIX + _LATERAL_2[index]
    if total == 3:
        return GEO_PREFIX + _LATERAL_3[index]

    middle = total // 2
    if total % 2 == 1:
        if index == middle:
            return GEO_PREFIX + "Centerline"
        if index < middle:
            return GEO_PREFIX + f"Stage Right {middle - index}"
        return GEO_PREFIX + f"Stage Left {index - middle}"
    if index < middle:
        return GEO_PREFIX + f"Stage Right {middle - index}"
    return GEO_PREFIX + f"Stage Left {index - middle + 1}"


# ---------------------------------------------------------------------------
# Concentric axis vocabulary (design.md §4.1)
# ---------------------------------------------------------------------------

_CONCENTRIC_2 = ("Inner", "Outer")
_CONCENTRIC_3 = ("Inner", "Mid", "Outer")


def name_concentric_bucket(index: int, total: int) -> str:
    """Concentric-axis bucket name, index 0 = innermost -> index total-1 = outermost.

    total == 2 -> Inner/Outer
    total == 3 -> Inner/Mid/Outer
    total >= 4 -> Ring 1..N (inner -> outer)
    """
    if total == 2:
        return GEO_PREFIX + _CONCENTRIC_2[index]
    if total == 3:
        return GEO_PREFIX + _CONCENTRIC_3[index]
    return GEO_PREFIX + f"Ring {index + 1}"


# ---------------------------------------------------------------------------
# Vertical axis vocabulary (design.md §4.1)
#
# v0.3.0 정정: 이 축은 ("Low Side", "High Side") 였다. 실제 충돌이 확인돼 교체했다 —
# `server/looks/roles.py` 의 사이드 role 이 힌트 "Side" 를 단어경계로 매칭하므로
# `GEO Low Side` 가 사이드라이트 그룹으로 오인된다. 더 근본적으로 무대에서
# "low side"/"high side" 는 사이드라이트 **위치(system)** 를 뜻하며 REQ-GROUPGEN-019
# (기능/시스템 어휘 차용 금지)가 정확히 금지하는 것이다 — `SR Boom N` 과 같은 오류 계열이다.
# 좌표가 정직하게 말할 수 있는 것은 "더 낮다 / 더 높다" 뿐이다.
# ---------------------------------------------------------------------------

_VERTICAL_2 = ("Low", "High")


def name_vertical_bucket(index: int, total: int) -> str:
    """Vertical-axis bucket name, index 0 = lowest -> index total-1 = highest.

    total == 2 -> Low/High (no 3-way split defined — table §4.1)
    total >= 3 -> Level 1..N (up -> down, REQ-GROUPGEN-017 direction disclosure)

    Reading order for the numbered fallback is UP -> DOWN (opposite of the
    index's low->high construction) per design.md §4.1 table ("위→아래").

    Claims no lighting system and no rigging structure: "Side" would collide
    with `server/looks/roles.py`'s 사이드 role hint AND assert a sidelight
    position the patch does not contain (REQ-GROUPGEN-019, spec.md §D).
    """
    if total == 2:
        return GEO_PREFIX + _VERTICAL_2[index]
    # up -> down: the highest bucket (last index) is Level 1.
    level_number = total - index
    return GEO_PREFIX + f"Level {level_number}"


# ---------------------------------------------------------------------------
# §4.4 — 9-cell composite vocabulary. Defined, not dead-code-eliminated, but
# UNREACHABLE from any v1 caller (D-Q2 slot economy). No production code path
# calls name_grid_9cell.
# ---------------------------------------------------------------------------

GRID_9CELL_VOCAB: tuple[str, ...] = (
    "DSR",
    "DSC",
    "DSL",  # Downstage Right/Center/Left
    "CSR",
    "CS",
    "CSL",  # Center-stage Right/Center/Left
    "USR",
    "USC",
    "USL",  # Upstage Right/Center/Left
)


def name_grid_9cell(depth_idx: int, lateral_idx: int) -> str:
    """Defined but never called by any v1 caller (D-Q2 — slot economy).

    Records the industry-standard 9-cell composite vocabulary (research.md §6.4)
    without deleting it — a reactivation point if slot headroom appears or a
    user explicitly requests 9-cell naming.
    """
    row = ("DSR", "DSC", "DSL"), ("CSR", "CS", "CSL"), ("USR", "USC", "USL")
    return GEO_PREFIX + row[depth_idx][lateral_idx]


# NOTE: fixture-type (species) naming — manufacturer/type_name structured-field
# passthrough — is design.md §5.1 read-logic territory, owned by
# server/spatial/fixture_type.py (a sibling M-task), NOT naming.py. This module
# only defines the closed geometric vocabulary (design.md §4), so every public
# function here satisfies the AC-GROUPGEN-037 closed-set-or-fallback contract
# without exception.
