"""Energy model — D1-D5 as the budget for every axis (SPEC-COPILOT-SONGSTD-001
M1, REQ R2, docs/proposals/song-lighting-design-standard.md §3).

The standard's §3 table is the fix for a measured defect: "다이내믹스가 룩
선택 인덱스에 불과해 벌스와 후렴의 디머가 같다(실측: Seq 114 전 큐 100%)".
:func:`axis_budget` turns a bare D level into the table's per-axis budget —
key-layer dimmer %, fade-in (beats, then converted to seconds via the song's
own BPM), position width, color saturation, effect-axis density, and effect
speed — so a D level is a value the standard's E1-E4 rules constrain, never
just a look-selection index (E4).

Two upstream layers this module reads but never mutates:

* :class:`server.design.profile.MusicProfile` supplies the BPM
  (:attr:`MusicProfile.effective_bpm`) that :func:`beats_to_seconds` converts
  the table's beat counts against, and the genre (§7) that
  :func:`axis_budget` may use to override a default.
* :class:`server.design.rig.RigProfile` supplies the capability/count
  helpers (``has_capability``, ``capable_fixture_count``,
  ``budget_scale_factor``) that scale §3's F3 effect-axis budget down to
  what the rig actually has (RG6: "4대 리그의 블라인더 예산 ≠ 40대 리그").

Three guarantees the standard's R2 acceptance clause names are enforced by
construction, not by extra runtime checks, because the §3 table itself is
built that way:

* **E1 (디머 단조성)** — the per-D-level dimmer range is a fixed table
  (:data:`_D_LEVEL_ROWS`) whose floor and ceiling both increase (or hold) as
  D rises; :func:`axis_budget` never derives a value that could break that
  order.
* **E2 (헤드룸)** — only D5's row reaches ``position_width == 1.0`` (표의
  "최대"). Every D1-D4 row's dimmer ceiling may reach 100% (D4) but its
  position width stays below the D5 ceiling, so at least one axis always
  keeps headroom below D1-D4's row — exactly V4's "피크 유일성" claim, that
  the all-axis peak is reserved for D5 alone.
* **E3 (좁음→넓음)** — :data:`_D_LEVEL_ROWS`' ``position_width`` column is
  the table's own 좁음→최대 ordinal progression rescaled to ``[0.0, 1.0]``
  (``(d_level - 1) / 4``); it is monotonically non-decreasing in D by
  construction, never computed from anything the caller supplies.

G2 (전환 비대칭: "D 상승 전환은 짧게, D 하강 전환은 길게") is likewise an
emergent property of the same table rather than a second code path: §3's
fade-in column is monotonically non-increasing in D, so a transition into a
higher D level always lands on a shorter fade-in than a transition into a
lower one — this module needs no separate rising/falling branch to satisfy
it.

Genre overrides (§7) are applied ONLY where §7 states a concrete number this
module already computes — see :data:`_BALLAD_GENRE` below. §7's other
per-genre notes (스냅 위주, 히트 정밀 타이밍, 하드 스냅 등) describe cueing
texture and palette, not a §3 axis this module owns, so they are left alone
here (profile.py's ``GENRE_DEFAULT_TABLE`` already owns the palette column).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.profile import MusicProfile
from server.design.rig import RigProfile

__all__ = [
    "EFFECT_AXIS_CAPABILITY",
    "AxisBudget",
    "EnergyModelError",
    "axis_budget",
    "beats_to_seconds",
]


class EnergyModelError(ValueError):
    """An energy-model input (D level, BPM, or beat count) is malformed."""


#: The single rig capability name §3's F3/RG6 effect-axis budget is gated
#: on for this M1 foundation. The standard's §3 table budgets "이펙트
#: 밀도"/"이펙트 속도" as one undifferentiated axis count per D level — it
#: does not yet split the budget by effect kind (moving sweep vs. dimmer
#: chase vs. color chase, per §4d F1's per-axis-use table) — so this module
#: gates the whole budget on one declared capability rather than inventing a
#: per-kind split the standard hasn't specified. A later milestone that adds
#: F1's per-axis vocabulary can widen this to one capability per effect
#: kind without changing :func:`axis_budget`'s signature.
EFFECT_AXIS_CAPABILITY = "effect"

#: D5 is the only level the standard names as the all-axis peak (V4: "피크
#: 유일성"); every row below it must keep at least one axis short of its own
#: ceiling (E2).
_PEAK_D_LEVEL = 5

#: §7 발라드 row's "긴 페이드(5s+)" is the one genre note phrased as a
#: concrete number for an axis this module computes (fade-in seconds) — see
#: the module docstring for why the rest of §7's per-genre notes are left to
#: other layers.
_BALLAD_GENRE = "발라드"
_BALLAD_FADE_IN_FLOOR_SECONDS = 5.0


@dataclass(frozen=True)
class _DLevelRow:
    """One row of the §3 table, pre-BPM-conversion and pre-rig-scaling."""

    dimmer_pct: tuple[float, float]
    fade_beats: tuple[float, float]
    position_width: float
    fx_axes_budget: int
    fx_speed_mult: tuple[float, float]
    saturation: str
    headroom_reserved: bool


#: §3 table, transcribed one row per D level. Every cell below is the exact
#: figure the table states; ranges stay ranges rather than being collapsed
#: to an invented single number.
#:
#: * ``dimmer_pct`` — "디머(키층 기준 %)" row.
#: * ``fade_beats`` — "페이드 인 (박 기준)" row; 마디 values are read as
#:   4/4 bars (2마디=8박, 1마디=4박), matching ``MusicProfile.meter``'s
#:   "4/4" default.
#: * ``position_width`` — "포지션 폭" row's 좁음→최대 ordinal rescaled to
#:   ``[0.0, 1.0]`` per ``(d_level - 1) / 4`` (E3; see module docstring).
#: * ``fx_axes_budget`` — "이펙트 밀도" row's upper bound (F3: "동시 이펙트
#:   축 수 = D레벨 예산"); D5's "+ 순간 액션" clause is X-territory (§4e)
#:   and out of this module's scope.
#: * ``fx_speed_mult`` — "이펙트 속도" row, as a fraction-of-a-beat
#:   multiplier (F2: "속도는 BPM의 배수"); D1 has no rung ("—") so its own
#:   row carries ``(0.0, 0.0)`` (이펙트 밀도 0 makes the speed moot).
#: * ``saturation`` — "컬러 채도" row's label, verbatim.
#: * ``headroom_reserved`` — True for every row except D5 (E2/V4).
_D_LEVEL_ROWS: dict[int, _DLevelRow] = {
    1: _DLevelRow(
        dimmer_pct=(20.0, 40.0),
        fade_beats=(8.0, 8.0),
        position_width=0.00,
        fx_axes_budget=0,
        fx_speed_mult=(0.0, 0.0),
        saturation="낮음(파스텔·화이트 혼합)",
        headroom_reserved=True,
    ),
    2: _DLevelRow(
        dimmer_pct=(40.0, 60.0),
        fade_beats=(4.0, 4.0),
        position_width=0.25,
        fx_axes_budget=1,
        fx_speed_mult=(0.0, 0.25),
        saturation="중간",
        headroom_reserved=True,
    ),
    3: _DLevelRow(
        dimmer_pct=(60.0, 80.0),
        fade_beats=(2.0, 4.0),
        position_width=0.50,
        fx_axes_budget=1,
        fx_speed_mult=(0.5, 1.0),
        saturation="중간~높음",
        headroom_reserved=True,
    ),
    4: _DLevelRow(
        dimmer_pct=(80.0, 100.0),
        fade_beats=(1.0, 2.0),
        position_width=0.75,
        fx_axes_budget=2,
        fx_speed_mult=(1.0, 1.0),
        saturation="높음",
        headroom_reserved=True,
    ),
    5: _DLevelRow(
        dimmer_pct=(100.0, 100.0),
        fade_beats=(0.0, 1.0),
        position_width=1.00,
        fx_axes_budget=2,
        fx_speed_mult=(1.0, 2.0),
        saturation="최대(단색 볼드)",
        headroom_reserved=False,
    ),
}


@dataclass(frozen=True)
class AxisBudget:
    """One D level's resolved per-axis budget (spec.md R2's A clause) —
    the standard's §3 row, BPM-converted and rig-scaled for one song and
    one rig. Immutable: a budget describes one (D level, profile, rig)
    triple and has no field that should mutate in place.
    """

    d_level: int
    dimmer_pct: tuple[float, float]
    fade_beats: tuple[float, float]
    fade_seconds: tuple[float, float]
    position_width: float
    saturation: str
    fx_axes_budget: int
    fx_axes: int
    fx_speed_mult: tuple[float, float]
    headroom_reserved: bool
    genre_notes: tuple[str, ...] = ()


def _validate_d_level(d_level: int) -> None:
    if isinstance(d_level, bool) or not isinstance(d_level, int):
        raise EnergyModelError(f"d_level must be an int, got {d_level!r}")
    if d_level not in _D_LEVEL_ROWS:
        raise EnergyModelError(f"d_level must be 1-5, got {d_level!r}")


def _validate_bpm(bpm: float) -> None:
    if isinstance(bpm, bool) or not isinstance(bpm, int | float):
        raise EnergyModelError(f"bpm must be a number, got {bpm!r}")
    if bpm <= 0:
        raise EnergyModelError(f"bpm must be positive, got {bpm!r}")


def _validate_beats(beats: float) -> None:
    if isinstance(beats, bool) or not isinstance(beats, int | float):
        raise EnergyModelError(f"beats must be a number, got {beats!r}")
    if beats < 0:
        raise EnergyModelError(f"beats must be non-negative, got {beats!r}")


def beats_to_seconds(beats: float, bpm: float) -> float:
    """Convert a beat count to seconds at ``bpm`` (F2: "속도는 곡 BPM에
    정렬" — the same beat-length arithmetic backs both the fade-in
    conversion here and the BPM-multiple effect speeds §3 names).

    One beat lasts ``60 / bpm`` seconds regardless of meter, so doubling the
    tempo halves the seconds a fixed beat count takes — spec.md R2's S
    clause: "BPM 60 vs 180 입력 시 페이드 초가 3배 차이" (60 BPM's beat is
    3x as long as 180 BPM's).
    """
    _validate_beats(beats)
    _validate_bpm(bpm)
    return beats * (60.0 / bpm)


def _apply_genre_overrides(
    d_level: int, fade_seconds: tuple[float, float], profile: MusicProfile
) -> tuple[tuple[float, float], tuple[str, ...]]:
    if profile.genre is None:
        return fade_seconds, ()
    if profile.genre.strip().casefold() != _BALLAD_GENRE.casefold():
        return fade_seconds, ()
    if d_level >= _PEAK_D_LEVEL:
        # D5's "0~1박 (스냅 허용)" is an explicit standard carve-out (§3 D5
        # row; §6 G1: "스냅(0s)은 히트/드롭/버튼 한정") that even a ballad
        # song keeps — a genre texture override must not clobber it.
        return fade_seconds, ()
    low, high = fade_seconds
    if low >= _BALLAD_FADE_IN_FLOOR_SECONDS:
        return fade_seconds, ()
    floored = (
        max(low, _BALLAD_FADE_IN_FLOOR_SECONDS),
        max(high, _BALLAD_FADE_IN_FLOOR_SECONDS),
    )
    note = (
        f"§7 {_BALLAD_GENRE}: 기본 페이드 최소 {_BALLAD_FADE_IN_FLOOR_SECONDS:g}초 적용 "
        "(히트 큐는 컷 허용)"
    )
    return floored, (note,)


def _fx_axes(fx_axes_budget: int, rig: RigProfile) -> int:
    """F3 × RG6: the §3 simultaneous-effect-axis ceiling, scaled down to
    what the rig actually has capable fixtures for. Zero when the rig
    declares no ``EFFECT_AXIS_CAPABILITY`` fixture at all — RG2 already
    gates the vocabulary shut in that case, and this budget must agree
    rather than silently handing out a nonzero count anyway."""
    if fx_axes_budget <= 0:
        return 0
    if not rig.has_capability(EFFECT_AXIS_CAPABILITY):
        return 0
    scale = rig.budget_scale_factor(EFFECT_AXIS_CAPABILITY)
    return int(fx_axes_budget * scale)


def axis_budget(d_level: int, profile: MusicProfile, rig: RigProfile) -> AxisBudget:
    """Resolve one D level's per-axis budget (spec.md R2's A clause) for
    ``profile``'s BPM and ``rig``'s capability/count.

    Pure — no console handle, no port, no transport import (matching
    ``profile.py``/``rig.py``). Never mutates ``profile`` or ``rig``.
    """
    _validate_d_level(d_level)
    row = _D_LEVEL_ROWS[d_level]
    bpm = profile.effective_bpm
    fade_seconds = (
        beats_to_seconds(row.fade_beats[0], bpm),
        beats_to_seconds(row.fade_beats[1], bpm),
    )
    fade_seconds, genre_notes = _apply_genre_overrides(d_level, fade_seconds, profile)
    return AxisBudget(
        d_level=d_level,
        dimmer_pct=row.dimmer_pct,
        fade_beats=row.fade_beats,
        fade_seconds=fade_seconds,
        position_width=row.position_width,
        saturation=row.saturation,
        fx_axes_budget=row.fx_axes_budget,
        fx_axes=_fx_axes(row.fx_axes_budget, rig),
        fx_speed_mult=row.fx_speed_mult,
        headroom_reserved=row.headroom_reserved,
        genre_notes=genre_notes,
    )
