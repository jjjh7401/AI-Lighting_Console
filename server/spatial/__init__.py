"""Spatial analysis — where the rig IS, turned into an order to fire it in
(SPEC-COPILOT-SPATIAL-001, REQ-SPATIAL-009).

Two operations, both pure: detect rows from fixture coordinates (y-axis gap
clustering) and order the fixtures within that structure by one of four closed
sort names. Nothing else. The point of the layer is that the SAME instruction
produces a different chain on a 1x30 bar than on a 3x10 grid, and that the
difference is machine-readable (REQ-SPATIAL-011).

Pure data + pure functions. This package never touches the console: it holds no
OSC surface, imports no transport and imports no gate surface
(REQ-SPATIAL-013). It also has ZERO third-party imports — row detection is
standard-library arithmetic, never a clustering library (design.md §3.1). The
one path that reaches a console is the spatial read tool, a caller of the
existing ``run_commands`` -> ``gate.screen()`` chokepoint.

Not to be confused with EXECUTOR layout (``server/looks/layout.py``,
``server/orchestrator/layout_occupancy.py``), which is sequence-to-executor
wiring. Different axis, shared English word — every identifier here carries the
``spatial`` prefix so the two never blur (spec.md §A.2).
"""

from __future__ import annotations

from server.spatial.choreography import (
    SPATIAL_QUALIFIER_AMBIGUOUS,
    SPATIAL_QUALIFIER_EMPTY,
    SPATIAL_QUALIFIER_NO_MATCH,
    SPATIAL_QUALIFIER_REASONS,
    SPATIAL_WAVE_ATTRIBUTE,
    SPATIAL_WAVE_DEFAULT_SPEED,
    SPATIAL_WAVE_HIGH,
    SPATIAL_WAVE_LOW,
    SPATIAL_WAVE_PHASE_SPAN,
    SpatialQualifierMatch,
    build_spatial_selection_chain,
    build_spatial_wave_commands,
    match_spatial_qualifier,
    resolve_spatial_sort,
)
from server.spatial.presets import (
    SPATIAL_PRESET_DECIMALS,
    SPATIAL_PRESET_DEFAULTS,
    SPATIAL_PRESET_MAX_ABS,
    SPATIAL_PRESET_ORIENTATIONS,
    SPATIAL_PRESETS,
    SpatialPlacement,
    SpatialPresetError,
    SpatialPresetPlan,
    spatial_placements_to_records,
    spatial_preset_placements,
)
from server.spatial.rows import (
    SPATIAL_ROW_GAP_RATIO,
    SPATIAL_ROW_NOISE_SPAN,
    analyze_spatial_records,
    analyze_spatial_rows,
)
from server.spatial.schema import (
    SPATIAL_LOW_CONFIDENCE_REASONS,
    SPATIAL_ROW_ORDER,
    SPATIAL_SORTS,
    SpatialAnalysis,
    SpatialAnalysisError,
    SpatialFixture,
    SpatialGapProfile,
    SpatialRow,
    spatial_analysis_to_dict,
    spatial_fixture_from_record,
    spatial_fixtures_from_records,
)
from server.spatial.sorting import spatial_sorted_fids, spatial_sorted_fixtures

__all__ = [
    "SPATIAL_LOW_CONFIDENCE_REASONS",
    "SPATIAL_PRESETS",
    "SPATIAL_PRESET_DECIMALS",
    "SPATIAL_PRESET_DEFAULTS",
    "SPATIAL_PRESET_MAX_ABS",
    "SPATIAL_PRESET_ORIENTATIONS",
    "SPATIAL_QUALIFIER_AMBIGUOUS",
    "SPATIAL_QUALIFIER_EMPTY",
    "SPATIAL_QUALIFIER_NO_MATCH",
    "SPATIAL_QUALIFIER_REASONS",
    "SPATIAL_ROW_GAP_RATIO",
    "SPATIAL_ROW_NOISE_SPAN",
    "SPATIAL_ROW_ORDER",
    "SPATIAL_SORTS",
    "SPATIAL_WAVE_ATTRIBUTE",
    "SPATIAL_WAVE_DEFAULT_SPEED",
    "SPATIAL_WAVE_HIGH",
    "SPATIAL_WAVE_LOW",
    "SPATIAL_WAVE_PHASE_SPAN",
    "SpatialAnalysis",
    "SpatialAnalysisError",
    "SpatialFixture",
    "SpatialGapProfile",
    "SpatialPlacement",
    "SpatialPresetError",
    "SpatialPresetPlan",
    "SpatialQualifierMatch",
    "SpatialRow",
    "analyze_spatial_records",
    "analyze_spatial_rows",
    "build_spatial_selection_chain",
    "build_spatial_wave_commands",
    "match_spatial_qualifier",
    "resolve_spatial_sort",
    "spatial_analysis_to_dict",
    "spatial_fixture_from_record",
    "spatial_fixtures_from_records",
    "spatial_placements_to_records",
    "spatial_preset_placements",
    "spatial_sorted_fids",
    "spatial_sorted_fixtures",
]
