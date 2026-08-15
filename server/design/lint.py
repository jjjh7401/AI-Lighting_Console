"""Cue-sheet lint — mechanical L1-L14 checks against a cue-sheet draft
(SPEC-COPILOT-SONGSTD-001 M1, REQ R3, docs/proposals/song-lighting-design-
standard.md §9).

The standard's own framing (§9): "린트는 차단이 아니라 보고다 — 연출은
규칙을 의도적으로 깰 수 있고, 그 결정은 운영자가 카드에서 내린다." This
module never blocks and never mutates a sheet; :func:`lint_sheet` only reads
a caller-supplied draft and reports what it finds.

Two structural input types are owned by this module — :class:`LintSection`
and :class:`LintCue` — narrow, plain, and independent of any console
transport or of ``energy.py`` (R2, not yet built). A cue sheet is whatever
the caller says it is: a tuple of sections and a tuple of cues, each cue
naming the section it belongs to and the handful of axis values the L1-L14
checks actually read (D level, key/back dimmer, fade seconds, position label
and width tier, palette colors, effect axis count and speed, and the
accent/blackout/audience-or-blinder flags §9's rules name).

RG1 (rig.py) governs which layer-conditioned checks may run at all: L6 and
L7 depend on the rig actually having a mapped key/back layer distinction
(``RigProfile.layer_rules_active()``); on a single-layer rig they are
INACTIVE, and that fact is reported as a :class:`DisabledRuleNote` — never as
a silent zero-violations result, which would read identically to "checked
and clean" (the same false-violation-report hazard rig.py's own docstring
names, mirrored here as a false-*clean*-report hazard). L11 similarly
disables itself — with its own note — when the song's BPM was never
declared and only fell back to :data:`server.design.profile.DEFAULT_BPM`
(spec.md R3's R clause: "L11 ... 은 BPM 있는 경우만"); grid-checking an
effect's speed against a tempo the song never actually stated would be a
different shape of the same false-violation hazard.

Every other L1-L14 check runs unconditionally — nothing else in §9 depends
on rig layer state or on BPM being declared, so gating them would itself be
an unsupported guess.

A cue may carry ``tags`` naming rule IDs it deliberately violates (spec.md
R3's R clause: "태그(의도적 위반 선언)가 있으면 해당 규칙 억제") — that
cue's finding for exactly that rule is suppressed; every other rule (and
every other cue) is unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.profile import MusicProfile
from server.design.rig import RigProfile

__all__ = [
    "LINT_RULE_IDS",
    "POSITION_WIDTH_TIERS",
    "DisabledRuleNote",
    "LintCue",
    "LintFinding",
    "LintReport",
    "LintSection",
    "LintSheet",
    "LintSheetError",
    "lint_sheet",
]


class LintSheetError(ValueError):
    """A lint input (a :class:`LintCue`, a :class:`LintSection`, or the
    :class:`LintSheet` they form together) is malformed."""


#: The standard's closed §9 rule-ID vocabulary — used to validate every
#: ``tags`` entry a cue declares, so a typo in an intentional-violation tag
#: fails loudly instead of silently suppressing nothing.
LINT_RULE_IDS: tuple[str, ...] = tuple(f"L{n}" for n in range(1, 15))

#: The four position-width tiers §3's "포지션 폭" row names (좁음/중간/넓음/
#: 최대), in narrow-to-wide order — the ordering L4 compares D-ascending
#: cue pairs against.
POSITION_WIDTH_TIERS: tuple[str, ...] = ("narrow", "medium", "wide", "max")

#: §3's "디머(키층 기준 %)" row, D1-D5, verbatim (min, max) per level. Kept
#: local to this module rather than imported from the not-yet-built
#: ``energy.py`` — the same "read the same source table, don't duplicate a
#: neighbour module's own re-derivation of it" pattern
#: ``profile.py``'s ``_D_LEVEL_AND_COLOR_BY_LABEL`` already uses. L2 uses
#: this to catch a cue whose dimmer sits outside its own D level's budget —
#: the shape of the Seq 114 defect (every cue at 100%, including D2/D3
#: sections whose budget tops out at 60%/80%) that a bare adjacent-pair
#: non-decrease check would miss, since a flat value never "decreases".
_D_LEVEL_DIMMER_RANGE_PCT: dict[int, tuple[float, float]] = {
    1: (20.0, 40.0),
    2: (40.0, 60.0),
    3: (60.0, 80.0),
    4: (80.0, 100.0),
    5: (100.0, 100.0),
}

#: §3's "이펙트 밀도" row, D1-D5, upper bound of each level's simultaneous-
#: axis count (F3's budget). L10 reads this directly; L3's headroom check
#: reuses the D5 upper bound (2) as the documented stand-in for "이펙트
#: 최대" — see :func:`_lint_l3` for why speed itself isn't used.
_D_LEVEL_EFFECT_AXIS_CEILING: dict[int, int] = {
    1: 0,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
}

#: L3's headroom check ("이펙트 최대") stand-in — the D5 row's effect-axis
#: ceiling from :data:`_D_LEVEL_EFFECT_AXIS_CEILING`.
_MAX_EFFECT_AXIS_COUNT = _D_LEVEL_EFFECT_AXIS_CEILING[5]

#: L11's BPM-multiple grid (F2 + §3's "이펙트 속도" row): ¼박·½박·1박·2박·
#: 4~8박 — every beat-multiple the standard names anywhere, collected once.
_EFFECT_SPEED_GRID_BEATS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)

#: L11's tolerance band around the nearest grid value (spec.md R3: "Speed
#: BPM 배수 ±10%").
_EFFECT_SPEED_GRID_TOLERANCE = 0.10

#: L8's blackout-count budget (I4: "곡당 예산 2~3회") — the conservative end
#: of the stated range, matching acceptance.md's ">3회" phrasing for L8.
_BLACKOUT_BUDGET = 3

#: L13's "동일 3중 조합 연속" run length (V2) before a repeat is a violation.
_REPEAT_COMBO_STREAK_LIMIT = 3

#: L14's Audience/블라인더 per-song budget (P4 + X1: "곡당 예산 1~2회").
_AUDIENCE_OR_BLINDER_BUDGET = 2

#: L14's D level Audience/블라인더 is reserved for (P4: "D5 전용").
_AUDIENCE_OR_BLINDER_D_LEVEL = 5


@dataclass(frozen=True)
class LintSection:
    """One timeline section — just enough for L1 (§9: "구간당 큐 ≥1")."""

    index: int
    name: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise LintSheetError(f"section index must be >= 0, got {self.index!r}")
        if not self.name.strip():
            raise LintSheetError("section name must be non-empty")


@dataclass(frozen=True)
class LintCue:
    """One cue-sheet line — exactly the axis values §9's L1-L14 checks read,
    nothing a console transport or a look pipeline would additionally need.

    ``cue_no`` follows the standard's own numbering (§2 T2): a section cue
    is an integer, an inserted cue (accent/MIB) is a fraction (``k.5``).
    ``section_index`` names which :class:`LintSection` this cue belongs to —
    independent of ``cue_no``'s integer part, since a section may carry more
    than one cue.

    ``key_dimmer_pct``/``back_dimmer_pct`` are ``None`` when this cue simply
    has no value for that layer (never inferred as zero) — L2/L6/L7 skip a
    cue whose relevant dimmer is unset rather than treat absence as "off".
    ``position_width`` is one of :data:`POSITION_WIDTH_TIERS`. ``tags``
    names the rule IDs (a subset of :data:`LINT_RULE_IDS`) this cue's
    designer has declared an intentional violation of (spec.md R3's R
    clause) — every other rule and every other cue is unaffected.
    """

    cue_no: float
    section_index: int
    d_level: int
    fade_seconds: float
    key_dimmer_pct: float | None = None
    back_dimmer_pct: float | None = None
    position_label: str | None = None
    position_width: str | None = None
    palette_colors: tuple[str, ...] = ()
    effect_axis_count: int = 0
    effect_speed_beats: float | None = None
    is_accent: bool = False
    is_blackout: bool = False
    is_audience_or_blinder: bool = False
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.cue_no < 0:
            raise LintSheetError(f"cue_no must be >= 0, got {self.cue_no!r}")
        if self.section_index < 0:
            raise LintSheetError(f"section_index must be >= 0, got {self.section_index!r}")
        if self.d_level not in (1, 2, 3, 4, 5):
            raise LintSheetError(f"d_level must be 1-5, got {self.d_level!r}")
        if self.fade_seconds < 0:
            raise LintSheetError(f"fade_seconds must be >= 0, got {self.fade_seconds!r}")
        for name, value in (
            ("key_dimmer_pct", self.key_dimmer_pct),
            ("back_dimmer_pct", self.back_dimmer_pct),
        ):
            if value is not None and not (0.0 <= value <= 100.0):
                raise LintSheetError(f"{name} must be within 0-100, got {value!r}")
        if self.position_width is not None and self.position_width not in POSITION_WIDTH_TIERS:
            raise LintSheetError(
                f"position_width must be one of {POSITION_WIDTH_TIERS}, got {self.position_width!r}"
            )
        if self.effect_axis_count < 0:
            raise LintSheetError(f"effect_axis_count must be >= 0, got {self.effect_axis_count!r}")
        if self.effect_speed_beats is not None and self.effect_speed_beats <= 0:
            raise LintSheetError(f"effect_speed_beats must be > 0, got {self.effect_speed_beats!r}")
        unknown_tags = self.tags - set(LINT_RULE_IDS)
        if unknown_tags:
            raise LintSheetError(
                f"unknown rule tag(s) {sorted(unknown_tags)}; must be in {LINT_RULE_IDS}"
            )


@dataclass(frozen=True)
class LintSheet:
    """A cue-sheet draft: its sections, and its cues in timeline order
    (ascending ``cue_no`` — validated below, since L2/L4/L12/L13 all compare
    adjacent cues and a caller-supplied misordering would silently corrupt
    every one of them)."""

    sections: tuple[LintSection, ...]
    cues: tuple[LintCue, ...]

    def __post_init__(self) -> None:
        for cue in self.cues:
            if cue.section_index >= len(self.sections):
                raise LintSheetError(
                    f"cue {cue.cue_no} references section_index {cue.section_index}, "
                    f"but only {len(self.sections)} section(s) exist"
                )
        cue_numbers = [cue.cue_no for cue in self.cues]
        if cue_numbers != sorted(cue_numbers):
            raise LintSheetError("cues must be given in ascending cue_no (timeline) order")


@dataclass(frozen=True)
class LintFinding:
    """One §9 violation: which rule, which cue, and why — never a block, per
    the module docstring."""

    rule_id: str
    cue_number: float
    description: str


@dataclass(frozen=True)
class DisabledRuleNote:
    """A §9 rule this call did NOT evaluate, and why — RG1's "거짓 위반
    보고 금지" read the other way round: an inactive rule reported as zero
    findings would look identical to "checked and clean". This makes the
    inactivity itself explicit instead."""

    rule_id: str
    reason: str


@dataclass(frozen=True)
class LintReport:
    """:func:`lint_sheet`'s result: the violations it found, plus the rules
    it deliberately did not evaluate this call."""

    findings: tuple[LintFinding, ...]
    disabled_rules: tuple[DisabledRuleNote, ...]


def _suppressed(rule_id: str, cue: LintCue) -> bool:
    return rule_id in cue.tags


def _lint_l1(sheet: LintSheet) -> list[LintFinding]:
    """L1: 구간당 큐 ≥1 (T1)."""
    counts = {section.index: 0 for section in sheet.sections}
    for cue in sheet.cues:
        counts[cue.section_index] += 1
    findings = []
    for section in sheet.sections:
        if counts[section.index] == 0:
            findings.append(
                LintFinding(
                    rule_id="L1",
                    cue_number=float(section.index),
                    description=f"section {section.name!r} has no cue (T1: 구간당 큐 ≥1)",
                )
            )
    return findings


def _lint_l2(sheet: LintSheet) -> list[LintFinding]:
    """L2: D 단조성 — D↑인데 키층 디머↓ (E1), plus a per-cue range-budget
    check against :data:`_D_LEVEL_DIMMER_RANGE_PCT` so a flat, undifferentiated
    curve (Seq 114: every cue at 100%) is caught even though it never
    literally *decreases* between D-ascending cues."""
    findings = []
    for cue in sheet.cues:
        if cue.key_dimmer_pct is None or _suppressed("L2", cue):
            continue
        low, high = _D_LEVEL_DIMMER_RANGE_PCT[cue.d_level]
        if not (low <= cue.key_dimmer_pct <= high):
            findings.append(
                LintFinding(
                    rule_id="L2",
                    cue_number=cue.cue_no,
                    description=(
                        f"D{cue.d_level} key dimmer {cue.key_dimmer_pct}% is outside its "
                        f"budget range {low}-{high}% (E4: 다이내믹스는 값이다)"
                    ),
                )
            )
    prior = None
    for cue in sheet.cues:
        if (
            cue.key_dimmer_pct is not None
            and prior is not None
            and prior.key_dimmer_pct is not None
            and prior.d_level < cue.d_level
            and prior.key_dimmer_pct > cue.key_dimmer_pct
            and not _suppressed("L2", cue)
        ):
            findings.append(
                LintFinding(
                    rule_id="L2",
                    cue_number=cue.cue_no,
                    description=(
                        f"D rose ({prior.d_level}->{cue.d_level}) but key dimmer fell "
                        f"({prior.key_dimmer_pct}%->{cue.key_dimmer_pct}%) (E1)"
                    ),
                )
            )
        if cue.key_dimmer_pct is not None:
            prior = cue
    return findings


def _lint_l3(sheet: LintSheet) -> list[LintFinding]:
    """L3: 헤드룸 — D5 이전 전축(디머·이펙트·포지션폭) 최대 동시 사용 금지
    (E2, V4). "이펙트 최대"는 F2의 speed 단위 표기가 (¼박=긴 주기, 1~2박=
    더블타임 허용) 처럼 D레벨을 관통하는 단조 척도가 아니라서, 대신 §3
    이펙트 밀도 열의 상한(:data:`_MAX_EFFECT_AXIS_COUNT`, D5=2축)을 "이펙트
    최대"의 근거 있는 대리 지표로 쓴다."""
    findings = []
    for cue in sheet.cues:
        if cue.d_level >= 5 or _suppressed("L3", cue):
            continue
        maxed_dimmer = cue.key_dimmer_pct is not None and cue.key_dimmer_pct >= 100.0
        maxed_width = cue.position_width == POSITION_WIDTH_TIERS[-1]
        maxed_effect = cue.effect_axis_count >= _MAX_EFFECT_AXIS_COUNT
        if maxed_dimmer and maxed_width and maxed_effect:
            findings.append(
                LintFinding(
                    rule_id="L3",
                    cue_number=cue.cue_no,
                    description=(
                        f"D{cue.d_level} (pre-D5) uses max dimmer, max position width, and "
                        f">= {_MAX_EFFECT_AXIS_COUNT} effect axes simultaneously — no headroom (E2)"
                    ),
                )
            )
    return findings


def _lint_l4(sheet: LintSheet) -> list[LintFinding]:
    """L4: 포지션 폭이 D 상승 경계에서 축소 (태그 없이) (E3)."""
    findings = []
    prior: LintCue | None = None
    for cue in sheet.cues:
        if (
            prior is not None
            and prior.position_width is not None
            and cue.position_width is not None
            and prior.d_level < cue.d_level
            and not _suppressed("L4", cue)
        ):
            prior_index = POSITION_WIDTH_TIERS.index(prior.position_width)
            cue_index = POSITION_WIDTH_TIERS.index(cue.position_width)
            if cue_index < prior_index:
                findings.append(
                    LintFinding(
                        rule_id="L4",
                        cue_number=cue.cue_no,
                        description=(
                            f"D rose ({prior.d_level}->{cue.d_level}) but position width "
                            f"narrowed ({prior.position_width}->{cue.position_width}) (E3)"
                        ),
                    )
                )
        prior = cue
    return findings


def _lint_l5(sheet: LintSheet, profile: MusicProfile) -> list[LintFinding]:
    """L5: 팔레트 크기 > 5 또는 곡 중 팔레트 이탈 (C1). Both halves read
    ``profile.palette`` — an undeclared (empty) palette means nothing to
    check against, so neither half can fire (not a rule disablement: there
    is simply no declared palette for a cue to deviate from)."""
    findings = []
    if not profile.palette:
        return findings
    if len(profile.palette) > 5:
        findings.append(
            LintFinding(
                rule_id="L5",
                cue_number=0.0,
                description=(
                    f"palette declares {len(profile.palette)} colors, standard caps at 5 (C1)"
                ),
            )
        )
    allowed = set(profile.palette)
    for cue in sheet.cues:
        if _suppressed("L5", cue):
            continue
        off_palette = [color for color in cue.palette_colors if color not in allowed]
        if off_palette:
            findings.append(
                LintFinding(
                    rule_id="L5",
                    cue_number=cue.cue_no,
                    description=(
                        f"color(s) {off_palette} are outside the declared palette "
                        f"{profile.palette} (C1)"
                    ),
                )
            )
    return findings


def _lint_l6(sheet: LintSheet) -> list[LintFinding]:
    """L6 (RG1-gated by the caller — see :func:`lint_sheet`): 키층 소등 +
    보컬 중심 구간 (D1~D2) (I3)."""
    findings = []
    for cue in sheet.cues:
        if cue.d_level not in (1, 2) or _suppressed("L6", cue):
            continue
        if cue.key_dimmer_pct == 0.0:
            findings.append(
                LintFinding(
                    rule_id="L6",
                    cue_number=cue.cue_no,
                    description=f"D{cue.d_level} (vocal-centric) key layer is off (I3)",
                )
            )
    return findings


def _lint_l7(sheet: LintSheet) -> list[LintFinding]:
    """L7 (RG1-gated by the caller — see :func:`lint_sheet`): 백층 > 키층
    (실루엣 태그 없이) (I2)."""
    findings = []
    for cue in sheet.cues:
        if cue.key_dimmer_pct is None or cue.back_dimmer_pct is None or _suppressed("L7", cue):
            continue
        if cue.back_dimmer_pct > cue.key_dimmer_pct:
            findings.append(
                LintFinding(
                    rule_id="L7",
                    cue_number=cue.cue_no,
                    description=(
                        f"back layer ({cue.back_dimmer_pct}%) exceeds key layer "
                        f"({cue.key_dimmer_pct}%) without a silhouette tag (I2)"
                    ),
                )
            )
    return findings


def _lint_l8(sheet: LintSheet) -> list[LintFinding]:
    """L8: 블랙아웃 > 3회 (I4). Each blackout past the budget is its own
    finding, at that blackout's own cue number."""
    findings = []
    seen = 0
    for cue in sheet.cues:
        if not cue.is_blackout:
            continue
        seen += 1
        if seen > _BLACKOUT_BUDGET and not _suppressed("L8", cue):
            findings.append(
                LintFinding(
                    rule_id="L8",
                    cue_number=cue.cue_no,
                    description=(
                        f"blackout #{seen} exceeds the per-song budget of {_BLACKOUT_BUDGET} (I4)"
                    ),
                )
            )
    return findings


def _lint_l9(sheet: LintSheet) -> list[LintFinding]:
    """L9: 스냅(0s)이 히트/드롭/버튼 외 위치 (G1)."""
    findings = []
    for cue in sheet.cues:
        if cue.fade_seconds == 0.0 and not cue.is_accent and not _suppressed("L9", cue):
            findings.append(
                LintFinding(
                    rule_id="L9",
                    cue_number=cue.cue_no,
                    description="snap fade (0s) used outside an accent/hit/drop/button cue (G1)",
                )
            )
    return findings


def _lint_l10(sheet: LintSheet) -> list[LintFinding]:
    """L10: 동시 이펙트 축 수 > D레벨 예산 (F3)."""
    findings = []
    for cue in sheet.cues:
        if _suppressed("L10", cue):
            continue
        ceiling = _D_LEVEL_EFFECT_AXIS_CEILING[cue.d_level]
        if cue.effect_axis_count > ceiling:
            findings.append(
                LintFinding(
                    rule_id="L10",
                    cue_number=cue.cue_no,
                    description=(
                        f"D{cue.d_level} uses {cue.effect_axis_count} simultaneous effect axes, "
                        f"budget is {ceiling} (F3)"
                    ),
                )
            )
    return findings


def _nearest_grid_deviation(speed_beats: float) -> float:
    """The relative distance from ``speed_beats`` to the nearest entry in
    :data:`_EFFECT_SPEED_GRID_BEATS` — 0.0 exactly on-grid."""
    nearest = min(_EFFECT_SPEED_GRID_BEATS, key=lambda grid: abs(grid - speed_beats))
    return abs(speed_beats - nearest) / nearest


def _lint_l11(sheet: LintSheet) -> list[LintFinding]:
    """L11 (BPM-declared-gated by the caller — see :func:`lint_sheet`):
    이펙트 Speed가 BPM 배수 격자 밖 (±10%) (F2)."""
    findings = []
    for cue in sheet.cues:
        if cue.effect_speed_beats is None or _suppressed("L11", cue):
            continue
        deviation = _nearest_grid_deviation(cue.effect_speed_beats)
        if deviation > _EFFECT_SPEED_GRID_TOLERANCE:
            findings.append(
                LintFinding(
                    rule_id="L11",
                    cue_number=cue.cue_no,
                    description=(
                        f"effect speed {cue.effect_speed_beats} beats/cycle is "
                        f"{deviation:.0%} off the BPM-multiple grid {_EFFECT_SPEED_GRID_BEATS} "
                        f"(F2 tolerance is ±{_EFFECT_SPEED_GRID_TOLERANCE:.0%})"
                    ),
                )
            )
    return findings


def _cue_signature(cue: LintCue) -> tuple[str | None, frozenset[str], int, float | None]:
    """The (position, palette, effect) axes L12/L13 compare between cues —
    a single hashable summary of "what does this cue look like"."""
    return (
        cue.position_label,
        frozenset(cue.palette_colors),
        cue.effect_axis_count,
        cue.effect_speed_beats,
    )


def _lint_l12(sheet: LintSheet) -> list[LintFinding]:
    """L12: 인접 큐 변화 축 > 2, 구간 리셋이 아닌 경우 (V1). A reset — D
    급변 ≥2 또는 블랙아웃 경유 — legitimately changes every axis at once."""
    findings = []
    prior: LintCue | None = None
    for cue in sheet.cues:
        if prior is not None and not _suppressed("L12", cue):
            is_reset = abs(cue.d_level - prior.d_level) >= 2 or prior.is_blackout
            if not is_reset:
                changed = sum(
                    1
                    for a, b in zip(_cue_signature(prior), _cue_signature(cue), strict=True)
                    if a != b
                )
                if changed > 2:
                    findings.append(
                        LintFinding(
                            rule_id="L12",
                            cue_number=cue.cue_no,
                            description=(
                                f"{changed} axes changed from the prior cue outside a reset (V1)"
                            ),
                        )
                    )
        prior = cue
    return findings


def _lint_l13(sheet: LintSheet) -> list[LintFinding]:
    """L13: 동일 (포지션, 팔레트, 이펙트) 3중 조합의 연속 큐 금지 (V2)."""
    findings = []
    streak_signature: tuple[str | None, frozenset[str], int, float | None] | None = None
    streak_len = 0
    for cue in sheet.cues:
        signature = _cue_signature(cue)
        if signature == streak_signature:
            streak_len += 1
        else:
            streak_signature = signature
            streak_len = 1
        if streak_len >= _REPEAT_COMBO_STREAK_LIMIT and not _suppressed("L13", cue):
            findings.append(
                LintFinding(
                    rule_id="L13",
                    cue_number=cue.cue_no,
                    description=(
                        f"identical (position, palette, effect) combo for {streak_len} "
                        "consecutive cues (V2)"
                    ),
                )
            )
    return findings


def _lint_l14(sheet: LintSheet) -> list[LintFinding]:
    """L14: Audience/블라인더 예산 초과 (>2회) 또는 D5 외 사용 (P4, X1)."""
    findings = []
    seen = 0
    for cue in sheet.cues:
        if not cue.is_audience_or_blinder:
            continue
        seen += 1
        if _suppressed("L14", cue):
            continue
        if cue.d_level != _AUDIENCE_OR_BLINDER_D_LEVEL:
            findings.append(
                LintFinding(
                    rule_id="L14",
                    cue_number=cue.cue_no,
                    description=(
                        f"audience/blinder action used at D{cue.d_level}, reserved for "
                        f"D{_AUDIENCE_OR_BLINDER_D_LEVEL} (P4)"
                    ),
                )
            )
        if seen > _AUDIENCE_OR_BLINDER_BUDGET:
            findings.append(
                LintFinding(
                    rule_id="L14",
                    cue_number=cue.cue_no,
                    description=(
                        f"audience/blinder action #{seen} exceeds the per-song budget of "
                        f"{_AUDIENCE_OR_BLINDER_BUDGET} (X1)"
                    ),
                )
            )
    return findings


def lint_sheet(sheet: LintSheet, profile: MusicProfile, rig: RigProfile) -> LintReport:
    """Run every L1-L14 check §9 defines against ``sheet``, reporting
    (never blocking) what it finds.

    L6 and L7 run only when ``rig.layer_rules_active()`` is true (RG1); L11
    runs only when ``profile.bpm_is_default`` is false (spec.md R3's R
    clause). Each skip is recorded as a :class:`DisabledRuleNote` instead of
    silently contributing zero findings, so an inactive rule is never
    mistaken for a rule that ran clean.
    """
    findings: list[LintFinding] = []
    disabled: list[DisabledRuleNote] = []

    findings.extend(_lint_l1(sheet))
    findings.extend(_lint_l2(sheet))
    findings.extend(_lint_l3(sheet))
    findings.extend(_lint_l4(sheet))
    findings.extend(_lint_l5(sheet, profile))

    if rig.layer_rules_active():
        findings.extend(_lint_l6(sheet))
        findings.extend(_lint_l7(sheet))
    else:
        disabled.append(
            DisabledRuleNote(
                rule_id="L6",
                reason="RG1: rig has no mapped key/back layer distinction (single-layer rig)",
            )
        )
        disabled.append(
            DisabledRuleNote(
                rule_id="L7",
                reason="RG1: rig has no mapped key/back layer distinction (single-layer rig)",
            )
        )

    findings.extend(_lint_l8(sheet))
    findings.extend(_lint_l9(sheet))
    findings.extend(_lint_l10(sheet))

    if not profile.bpm_is_default:
        findings.extend(_lint_l11(sheet))
    else:
        disabled.append(
            DisabledRuleNote(
                rule_id="L11",
                reason=(
                    "spec.md R3: BPM was not declared (defaulted) — no real tempo to "
                    "grid-check against"
                ),
            )
        )

    findings.extend(_lint_l12(sheet))
    findings.extend(_lint_l13(sheet))
    findings.extend(_lint_l14(sheet))

    return LintReport(findings=tuple(findings), disabled_rules=tuple(disabled))
