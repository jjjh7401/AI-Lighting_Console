"""The song design standard engine (SPEC-COPILOT-SONGSTD-001) — pure functions
that turn a song's musical identity, the rig's equipment, and the director's
intent into standard-compliant cue-sheet parameters. No console handle, no
port, no transport reference anywhere in this package.

M1 ships :mod:`server.design.rig` (the equipment/design layer, R1b) only.
``profile.py`` (R1), ``energy.py`` (R2), ``lint.py`` (R3) and
``interview.py`` (R1c) land in later milestones and are intentionally not
imported here yet — this module re-exports only what already exists.
"""

from __future__ import annotations

from server.design.rig import (
    RG6_FULL_BUDGET_FIXTURE_COUNT,
    RIG_LAYER_ROLES,
    RIG_LAYER_SOURCE_DECLARED,
    RIG_LAYER_SOURCE_GROUP_HEURISTIC,
    RIG_LAYER_SOURCE_SINGLE_LAYER,
    RigFixtureRecord,
    RigGeometry,
    RigInventory,
    RigLayers,
    RigProfile,
    RigProfileError,
    RigScale,
    build_rig_profile,
    rig_fixture_record_from_record,
)

__all__ = [
    "RG6_FULL_BUDGET_FIXTURE_COUNT",
    "RIG_LAYER_ROLES",
    "RIG_LAYER_SOURCE_DECLARED",
    "RIG_LAYER_SOURCE_GROUP_HEURISTIC",
    "RIG_LAYER_SOURCE_SINGLE_LAYER",
    "RigFixtureRecord",
    "RigGeometry",
    "RigInventory",
    "RigLayers",
    "RigProfile",
    "RigProfileError",
    "RigScale",
    "build_rig_profile",
    "rig_fixture_record_from_record",
]
