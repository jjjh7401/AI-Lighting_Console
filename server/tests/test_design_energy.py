"""Tests for server/design/energy.py (SPEC-COPILOT-SONGSTD-001, M1, R2).

Scenarios per spec.md R2 §S: BPM 60 vs 180 gives a 3x fade-seconds ratio,
D-ascending dimmer stays monotonic, D5 is the only level that reaches full
headroom on every axis at once (E2/V4), rig capable-fixture count scales the
effect-axis budget (RG6), and a rig with no declared effect capability gets
zero effect axes regardless of D level.
"""

from __future__ import annotations

import pytest

from server.design.energy import (
    EFFECT_AXIS_CAPABILITY,
    EnergyModelError,
    axis_budget,
    beats_to_seconds,
)
from server.design.profile import MusicProfile
from server.design.rig import RigProfile, build_rig_profile


def _patch(*, count: int, capability: str | None = None) -> list[dict[str, object]]:
    """``count`` fixtures of one type; ``capability`` declared on all of them
    when given (never inferred — mirrors test_design_rig.py's helper)."""
    return [
        {
            "fid": fid,
            "type_name": "Sharpy",
            "capabilities": [capability] if capability else [],
        }
        for fid in range(1, count + 1)
    ]


def _rig(*, count: int, capability: str | None = None) -> RigProfile:
    return build_rig_profile(patch=_patch(count=count, capability=capability), groups={}, coords=[])


# ---------------------------------------------------------------------------
# beats_to_seconds — R2 S clause: BPM 60 vs 180 -> 3x fade seconds
# ---------------------------------------------------------------------------


def test_beats_to_seconds_60_vs_180_bpm_is_threefold() -> None:
    slow = beats_to_seconds(4.0, 60.0)
    fast = beats_to_seconds(4.0, 180.0)
    assert slow == pytest.approx(4.0)
    assert fast == pytest.approx(4.0 / 3.0)
    assert slow == pytest.approx(3.0 * fast)


def test_beats_to_seconds_rejects_nonpositive_bpm() -> None:
    with pytest.raises(EnergyModelError):
        beats_to_seconds(4.0, 0.0)


def test_beats_to_seconds_rejects_negative_beats() -> None:
    with pytest.raises(EnergyModelError):
        beats_to_seconds(-1.0, 120.0)


# ---------------------------------------------------------------------------
# E1 — dimmer monotonicity across the D-ascending ladder
# ---------------------------------------------------------------------------


def test_dimmer_is_monotonic_non_decreasing_across_d_levels() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    budgets = [axis_budget(d, profile, rig) for d in range(1, 6)]

    for lower, higher in zip(budgets, budgets[1:], strict=False):
        assert lower.dimmer_pct[0] <= higher.dimmer_pct[0]
        assert lower.dimmer_pct[1] <= higher.dimmer_pct[1]


def test_position_width_is_monotonic_narrow_to_wide() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    widths = [axis_budget(d, profile, rig).position_width for d in range(1, 6)]
    assert widths == sorted(widths)
    assert widths[0] == 0.0
    assert widths[-1] == 1.0


# ---------------------------------------------------------------------------
# E2/V4 — D5 is the sole all-axis peak; D1-D4 keep headroom
# ---------------------------------------------------------------------------


def test_d5_is_the_only_level_at_full_dimmer_and_full_position_width() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)

    for d in range(1, 5):
        budget = axis_budget(d, profile, rig)
        assert budget.headroom_reserved is True
        at_peak_dimmer = budget.dimmer_pct[1] == 100.0
        at_peak_width = budget.position_width == 1.0
        # E2: dimmer 100% + max position width never coincide before D5.
        assert not (at_peak_dimmer and at_peak_width)

    peak = axis_budget(5, profile, rig)
    assert peak.headroom_reserved is False
    assert peak.dimmer_pct == (100.0, 100.0)
    assert peak.position_width == 1.0


# ---------------------------------------------------------------------------
# RG6 — effect-axis budget scales with rig capable-fixture count
# ---------------------------------------------------------------------------


def test_rig_with_forty_capable_fixtures_gets_more_fx_axes_than_four() -> None:
    profile = MusicProfile(bpm=120.0)
    small_rig = _rig(count=4, capability=EFFECT_AXIS_CAPABILITY)
    large_rig = _rig(count=40, capability=EFFECT_AXIS_CAPABILITY)

    small_budget = axis_budget(4, profile, small_rig)
    large_budget = axis_budget(4, profile, large_rig)

    assert small_budget.fx_axes_budget == large_budget.fx_axes_budget == 2
    assert small_budget.fx_axes < large_budget.fx_axes
    assert large_budget.fx_axes == large_budget.fx_axes_budget


def test_no_declared_capability_means_no_effect_axes_at_any_d_level() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=40)  # no capability declared on any fixture

    for d in range(1, 6):
        assert axis_budget(d, profile, rig).fx_axes == 0


# ---------------------------------------------------------------------------
# Fade beats -> seconds, via the profile's own BPM
# ---------------------------------------------------------------------------


def test_fade_seconds_uses_profile_effective_bpm() -> None:
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    slow_profile = MusicProfile(bpm=60.0)
    fast_profile = MusicProfile(bpm=180.0)

    slow_budget = axis_budget(3, slow_profile, rig)
    fast_budget = axis_budget(3, fast_profile, rig)

    assert slow_budget.fade_beats == fast_budget.fade_beats  # same table row
    assert slow_budget.fade_seconds[0] == pytest.approx(3.0 * fast_budget.fade_seconds[0])
    assert slow_budget.fade_seconds[1] == pytest.approx(3.0 * fast_budget.fade_seconds[1])


def test_fade_seconds_falls_back_to_default_bpm_when_unset() -> None:
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    profile = MusicProfile()
    assert profile.bpm_is_default is True
    budget = axis_budget(2, profile, rig)
    # D2 row: fade_beats=(4.0, 4.0), DEFAULT_BPM=120.0 -> 2s
    assert budget.fade_seconds == pytest.approx((2.0, 2.0))


# ---------------------------------------------------------------------------
# §7 genre overrides — applied ONLY where §7 states a concrete number
# ---------------------------------------------------------------------------


def test_ballad_genre_floors_fade_seconds_at_five_below_peak() -> None:
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    profile = MusicProfile(bpm=120.0, genre="발라드")

    budget = axis_budget(1, profile, rig)  # D1 fade would be 4s at 120 BPM
    assert budget.fade_seconds == pytest.approx((5.0, 5.0))
    assert budget.genre_notes  # override is disclosed, not silent


def test_ballad_genre_does_not_override_d5_snap_allowance() -> None:
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    profile = MusicProfile(bpm=120.0, genre="발라드")

    budget = axis_budget(5, profile, rig)
    assert budget.fade_seconds == pytest.approx((0.0, 0.5))
    assert budget.genre_notes == ()


def test_non_ballad_genre_leaves_fade_seconds_untouched() -> None:
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    profile = MusicProfile(bpm=120.0, genre="록")

    budget = axis_budget(1, profile, rig)
    assert budget.fade_seconds == pytest.approx((4.0, 4.0))
    assert budget.genre_notes == ()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_axis_budget_rejects_out_of_range_d_level() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    with pytest.raises(EnergyModelError):
        axis_budget(0, profile, rig)
    with pytest.raises(EnergyModelError):
        axis_budget(6, profile, rig)


def test_axis_budget_rejects_non_int_d_level() -> None:
    profile = MusicProfile(bpm=120.0)
    rig = _rig(count=8, capability=EFFECT_AXIS_CAPABILITY)
    with pytest.raises(EnergyModelError):
        axis_budget(3.5, profile, rig)  # type: ignore[arg-type]
