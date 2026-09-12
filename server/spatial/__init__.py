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
from server.spatial.pointing import (
    POINTING_TILT_LIMIT_DEGREES,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    pointing_commands,
)
from server.spatial.preflight import (
    CHAIN_ORDER_VERDICTS,
    SPLIT_MODES,
    SPLIT_VERDICTS,
    ChainDivergence,
    ChainOrderCheck,
    SplitCheck,
    check_chain_order,
    check_split,
)
from server.spatial.presets import (
    EXPLICIT_ENTRY_KEYS,
    EXPLICIT_PRESET_NAME,
    SPATIAL_PRESET_DECIMALS,
    SPATIAL_PRESET_DEFAULTS,
    SPATIAL_PRESET_MAX_ABS,
    SPATIAL_PRESET_ORIENTATIONS,
    SPATIAL_PRESETS,
    SpatialPlacement,
    SpatialPresetError,
    SpatialPresetPlan,
    explicit_placements,
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
    "CHAIN_ORDER_VERDICTS",
    "EXPLICIT_ENTRY_KEYS",
    "EXPLICIT_PRESET_NAME",
    "POINTING_TILT_LIMIT_DEGREES",
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
    "SPLIT_MODES",
    "SPLIT_VERDICTS",
    "SPATIAL_WAVE_ATTRIBUTE",
    "SPATIAL_WAVE_DEFAULT_SPEED",
    "SPATIAL_WAVE_HIGH",
    "SPATIAL_WAVE_LOW",
    "SPATIAL_WAVE_PHASE_SPAN",
    "ChainDivergence",
    "ChainOrderCheck",
    "PointingTarget",
    "SplitCheck",
    "SpatialAnalysis",
    "SpatialAnalysisError",
    "SpatialFixture",
    "SpatialGapProfile",
    "SpatialPlacement",
    "SpatialPointingError",
    "SpatialPresetError",
    "SpatialPresetPlan",
    "SpatialQualifierMatch",
    "SpatialRow",
    "aim_pan_tilt",
    "analyze_spatial_records",
    "analyze_spatial_rows",
    "build_spatial_selection_chain",
    "build_spatial_wave_commands",
    "check_chain_order",
    "check_split",
    "match_spatial_qualifier",
    "pointing_commands",
    "resolve_spatial_sort",
    "spatial_analysis_to_dict",
    "spatial_fixture_from_record",
    "spatial_fixtures_from_records",
    "explicit_placements",
    "spatial_placements_to_records",
    "spatial_preset_placements",
    "spatial_sorted_fids",
    "spatial_sorted_fixtures",
]
