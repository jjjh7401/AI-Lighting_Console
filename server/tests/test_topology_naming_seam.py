"""Cross-module seam: topology.classify() -> naming.* (SPEC-COPILOT-GROUPGEN-001).

M1a (`topology.py`) and M2 (`naming.py`) were built in parallel against the
frozen schema contract in design.md §2.2. Neither module's own test file can
see the seam between them, and two real defects hid exactly there:

  1. `name_lateral_bucket` raised on 4+ buckets and pointed at a PRIVATE
     helper, so the public API could not name the grid case at all — the very
     scenario D-Q2 makes primary (axis-separated grid -> many lateral buckets).
  2. That private helper emitted `GEO SR Boom N`, claiming a rigging hardware
     position. spec.md §D lists Boom/FOH/Ladder/Torm as out of scope precisely
     because "좌표로 추정해 이름 붙이면 거짓 자산이 영속한다", and carves out
     `Electric N` on the DEPTH axis only.

This file exists so the seam is covered by something that fails when either
side drifts.
"""

from __future__ import annotations

import math

import pytest

from server.spatial import naming
from server.spatial.rows import analyze_spatial_rows
from server.spatial.schema import SpatialFixture
from server.spatial.topology import classify

_RIGGING_HARDWARE_TOKENS = ("Boom", "FOH", "Ladder", "Torm")


def _ring(first_fid: int, count: int, radius: float) -> list[SpatialFixture]:
    return [
        SpatialFixture(
            fid=first_fid + i,
            name=f"MMX {first_fid + i}",
            x=round(radius * math.cos(2 * math.pi * i / count), 4),
            y=round(radius * math.sin(2 * math.pi * i / count), 4),
            z=0.0,
        )
        for i in range(count)
    ]


@pytest.fixture
def two_ring_concentric() -> tuple[SpatialFixture, ...]:
    """research.md §3 live-measured case: inner 6 @ r=2.0, outer 12 @ r=5.0."""
    return tuple(_ring(1, 6, 2.0) + _ring(7, 12, 5.0))


@pytest.fixture
def grid_3x10() -> tuple[SpatialFixture, ...]:
    return tuple(
        SpatialFixture(fid=1 + row * 10 + col, name=f"F{1 + row * 10 + col}",
                       x=float(col) - 4.5, y=float(row * 3), z=0.0)
        for row in range(3)
        for col in range(10)
    )


def test_concentric_rig_is_no_longer_misread_as_rows(two_ring_concentric):
    """AC-GROUPGEN-003 at the seam — this SPEC's whole reason for existing.

    research.md §3 measured the OLD layer answering rows=9 with
    low_confidence=False on this exact rig. That misread is reproduced here as
    a live baseline so the assertion below cannot silently become vacuous.
    """
    old = analyze_spatial_rows(two_ring_concentric)
    assert len(old.rows) == 9 and old.low_confidence is False, (
        "the documented rows.py misread no longer reproduces; re-measure "
        "research.md §3 before trusting this test's contrast"
    )

    selected = classify(two_ring_concentric).selected
    assert selected.kind == "concentric"
    assert [len(b) for b in selected.fids_by_bucket] == [6, 12]

    names = [
        naming.name_concentric_bucket(i, len(selected.fids_by_bucket))
        for i in range(len(selected.fids_by_bucket))
    ]
    assert names == ["GEO Inner", "GEO Outer"]


def test_grid_names_both_axes_without_collision(grid_3x10):
    """D-Q2: grid -> axis-separated groups, read from grid_axes (not fids_by_bucket)."""
    selected = classify(grid_3x10).selected
    assert selected.kind == "grid"
    assert selected.fids_by_bucket == ()
    assert selected.grid_axes is not None

    depth = [
        naming.name_depth_bucket(i, len(selected.grid_axes["depth"]))
        for i in range(len(selected.grid_axes["depth"]))
    ]
    lateral = [
        naming.name_lateral_bucket(i, len(selected.grid_axes["lateral"]))
        for i in range(len(selected.grid_axes["lateral"]))
    ]

    assert depth == ["GEO Downstage", "GEO Center", "GEO Upstage"]
    # 10 lateral buckets: the public API must handle 4+ on its own.
    assert len(lateral) == 10
    assert lateral[0] == "GEO Stage Right 5" and lateral[-1] == "GEO Stage Left 5"
    # design.md §4.3 — depth "Center" and lateral "Centerline" are distinct
    # symbols; the two axes must never name the same string.
    assert not set(depth) & set(lateral)


def test_seam_never_produces_rigging_hardware_names(grid_3x10, two_ring_concentric):
    """spec.md §D — coordinates cannot know a boom/FOH/ladder/torm exists.

    MUTATION: restore the `GEO SR Boom N` lateral fallback and this goes RED.
    """
    produced: list[str] = []
    for rig in (grid_3x10, two_ring_concentric):
        selected = classify(rig).selected
        if selected.grid_axes is not None:
            for axis, buckets in selected.grid_axes.items():
                namer = (
                    naming.name_depth_bucket if axis == "depth"
                    else naming.name_lateral_bucket
                )
                produced += [namer(i, len(buckets)) for i in range(len(buckets))]
        else:
            total = len(selected.fids_by_bucket)
            produced += [naming.name_concentric_bucket(i, total) for i in range(total)]

    assert produced, "non-vacuity: the seam sweep must actually produce names"
    for name in produced:
        for token in _RIGGING_HARDWARE_TOKENS:
            assert token not in name, (
                f"{name!r} claims rigging hardware {token!r} — spec.md §D "
                "forbids inferring hardware structure from coordinates"
            )


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 9, 10, 12])
def test_lateral_public_api_is_total_complete(count):
    """The grid seam needs 4+ lateral names from the PUBLIC surface.

    MUTATION: make name_lateral_bucket raise for 4+ again (deferring to a
    private helper) and every count >= 4 goes RED.
    """
    names = [naming.name_lateral_bucket(i, count) for i in range(count)]
    assert len(set(names)) == count, f"duplicate lateral names at total={count}"
    for name in names:
        assert name.startswith(naming.GEO_PREFIX)


def test_topology_result_type_invariant_holds_across_candidates(grid_3x10, two_ring_concentric):
    """design.md §2.2 — the M1/M2 cross contract, checked on every candidate."""
    for rig in (grid_3x10, two_ring_concentric):
        classification = classify(rig)
        for result in (*classification.candidates, classification.selected):
            if result.kind == "grid":
                assert result.grid_axes is not None
                assert result.fids_by_bucket == ()
            else:
                assert result.grid_axes is None
