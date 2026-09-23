"""R4: the standard-engine position cue sheet — M1's profile+rig over T3's draft.

SPEC-COPILOT-SONGSTD-001 M2. This module is the design-layer HOME of the
standard path that briefly lived inside
:mod:`server.spatial.position_cuesheet` — moved here so the spatial analysis
layer stays stdlib + intra-spatial (AC-SPATIAL-013,
``test_the_package_has_no_third_party_imports_at_all``). The dependency
direction matches the rest of this package (:mod:`server.design.profile` and
:mod:`server.design.rig` already import ``server.spatial``, never the
reverse): the engine derives each lit section's (dimmer %, fade seconds)
pair from its own D level and hands the finished numbers DOWN to the pure
builder via its ``lit_dimmer_fade`` parameter.

The finished sheet carries a :func:`server.design.lint.lint_sheet` audit —
reported on :attr:`StandardPositionCueSheet.lint_report`, never used to
block generation (§9: "린트는 차단이 아니라 보고다"). MIB pre-moves, the
alternative-rotation, and the pre-move ``Follow`` trigger are exactly the
pure builder's — none of them read the dimmer/fade values this path changes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.design.energy import axis_budget
from server.design.lint import LintCue, LintReport, LintSection, LintSheet, lint_sheet
from server.design.profile import (
    GLOBAL_DEFAULT_D_LEVEL,
    MusicProfile,
    UnresolvedMood,
    resolve_section,
)
from server.design.rig import RigProfile
from server.spatial.position_cuesheet import (
    PositionCueSheet,
    PositionSheetSection,
    build_position_cue_sheet,
)

__all__ = [
    "StandardPositionCueSheet",
    "build_standard_position_cue_sheet",
]


@dataclass(frozen=True)
class StandardPositionCueSheet(PositionCueSheet):
    """The pure draft plus the standard engine's non-blocking lint audit."""

    lint_report: LintReport


def _standard_axis_values(
    mood_text: str, profile: MusicProfile, rig: RigProfile
) -> tuple[int, float, float]:
    """R4: the D level + (dimmer %, fade seconds) M1's engine derives for one
    lit section — midpoint of the D level's budget range, so the value is
    always strictly inside its own D-level range (a fixed L2-pass point,
    never the flat all-100% shape the standard's Seq 114 defect names) while
    still rising/shortening monotonically with D (E1/G2).

    A section whose mood-word ties or otherwise fails
    :func:`server.design.profile.resolve_section` (measured: never observed
    for a mood that already matched
    :func:`server.spatial.position_moods.match_position_mood`, since both
    read the same table) falls back to
    :data:`server.design.profile.GLOBAL_DEFAULT_D_LEVEL` rather than raising
    — the position for this cue is already decided by the builder's own
    matcher; refusing the cue over its D level alone would be a difference
    in strictness this module chooses not to enforce twice.
    """
    resolution = resolve_section(mood_text, profile)
    d_level = (
        GLOBAL_DEFAULT_D_LEVEL if isinstance(resolution, UnresolvedMood) else resolution.d_level
    )
    budget = axis_budget(d_level, profile, rig)
    dimmer = sum(budget.dimmer_pct) / 2.0
    fade = sum(budget.fade_seconds) / 2.0
    return d_level, dimmer, fade


def build_standard_position_cue_sheet(
    sections: Sequence[PositionSheetSection],
    *,
    sequence_no: int,
    preset_numbers: Mapping[str, int],
    fids: Sequence[int],
    fade_seconds: float = 3.0,
    move_seconds: float = 1.0,
    profile: MusicProfile,
    rig: RigProfile,
) -> StandardPositionCueSheet:
    """The T3 draft with every lit cue's dimmer/fade D-budget-driven (R4).

    Same contract as :func:`server.spatial.position_cuesheet.
    build_position_cue_sheet` — blackout/skip rules, MIB pre-moves, the
    alternative-rotation, and every refusal are the pure builder's own —
    except each lit section's dimmer % and fade seconds come from its D
    level via :func:`server.design.energy.axis_budget` instead of the flat
    100%/``fade_seconds`` pair, and the result carries the sheet-level lint
    audit. ``profile`` and ``rig`` are both REQUIRED keywords: the old
    optional-pair runtime check ("supplied together") became structural
    when the standard path moved into this layer.
    """
    axis_values = [_standard_axis_values(section.mood, profile, rig) for section in sections]
    sheet = build_position_cue_sheet(
        sections,
        sequence_no=sequence_no,
        preset_numbers=preset_numbers,
        fids=fids,
        fade_seconds=fade_seconds,
        move_seconds=move_seconds,
        lit_dimmer_fade=[(dimmer, fade) for _d_level, dimmer, fade in axis_values],
    )
    # Rebuild the lint inputs from the draft's own audit lines: one
    # LintSection per song section (resolutions are appended per section, in
    # order), one LintCue per stored cue — skipped sections consumed a cue
    # number but stored nothing, so they lint nothing; MIB pre-moves are
    # dark positioning moves, not designed looks, so they are not linted.
    lint_sections: list[LintSection] = []
    lint_cues: list[LintCue] = []
    for index, res in enumerate(sheet.resolutions):
        lint_sections.append(LintSection(index=index, name=res.section.name))
        if res.blackout:
            lint_cues.append(
                LintCue(
                    cue_no=float(res.cue_no),
                    section_index=index,
                    d_level=GLOBAL_DEFAULT_D_LEVEL,
                    fade_seconds=fade_seconds,
                    key_dimmer_pct=0.0,
                    is_blackout=True,
                )
            )
            continue
        if res.skipped_reason is not None:
            continue
        d_level, dimmer, fade = axis_values[index]
        lint_cues.append(
            LintCue(
                cue_no=float(res.cue_no),
                section_index=index,
                d_level=d_level,
                fade_seconds=fade,
                key_dimmer_pct=dimmer,
                position_label=res.look_label,
                is_audience_or_blinder=(res.look_label == "Audience"),
            )
        )
    report = lint_sheet(
        LintSheet(sections=tuple(lint_sections), cues=tuple(lint_cues)), profile, rig
    )
    return StandardPositionCueSheet(
        sequence_no=sheet.sequence_no,
        resolutions=sheet.resolutions,
        plans=sheet.plans,
        bundles=sheet.bundles,
        lint_report=report,
    )
