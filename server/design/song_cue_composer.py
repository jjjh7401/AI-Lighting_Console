from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Literal

from server.design.energy import AxisBudget, axis_budget
from server.design.lint import (
    POSITION_WIDTH_TIERS,
    DisabledRuleNote,
    LintCue,
    LintFinding,
    LintSection,
    LintSheet,
    lint_sheet,
)
from server.design.song_plan import (
    MANUAL_GO,
    POSITION_AXIS,
    TIMECODE,
    TRIG_TIME,
    CueTimingPayload,
    DecisionAxis,
    DisabledNote,
    SectionDecision,
    TimingMode,
    UnifiedSongLightingPlan,
)

__all__ = [
    "CardRequeryRequirement",
    "CueColorData",
    "CueDimmerData",
    "CueFxData",
    "CueMibData",
    "CuePositionData",
    "CueTimingData",
    "ComposedCue",
    "SongCueBundle",
    "SongCueComposerError",
    "position_axis_disabled",
    "SongCueCompositionResult",
    "build_song_cue_bundle",
    "compose_song_cue_bundle",
]

CueKind = Literal["section", "mib_premove"]
CueTrigger = Literal["manual_go", "trig_time", "timecode", "follow_previous"]

_POSITION_WIDTH_FROM_ENERGY: tuple[tuple[float, str], ...] = (
    (0.25, POSITION_WIDTH_TIERS[0]),
    (0.50, POSITION_WIDTH_TIERS[1]),
    (0.99, POSITION_WIDTH_TIERS[2]),
    (math.inf, POSITION_WIDTH_TIERS[3]),
)
_BLACKOUT_TOKENS = frozenset(("blackout", "black out", "amjeon", "암전", "블랙아웃"))
_AUDIENCE_TOKENS = frozenset(("audience", "blinder", "blind", "객석", "블라인더"))


class SongCueComposerError(ValueError):
    pass


def _tuple_of_str(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise SongCueComposerError(f"{name} must be a sequence of strings, got {values!r}")
    items = tuple(values)
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise SongCueComposerError(f"{name} entries must be non-empty strings")
    return items


def _tuple_of_findings(values: tuple[LintFinding, ...]) -> tuple[LintFinding, ...]:
    items = tuple(values)
    if not all(isinstance(item, LintFinding) for item in items):
        raise SongCueComposerError("lint_findings must contain LintFinding values")
    return items


def _tuple_of_disabled_rules(
    values: tuple[DisabledRuleNote, ...],
) -> tuple[DisabledRuleNote, ...]:
    items = tuple(values)
    if not all(isinstance(item, DisabledRuleNote) for item in items):
        raise SongCueComposerError("disabled_rule_notes must contain DisabledRuleNote values")
    return items


def _tuple_of_disabled_notes(values: tuple[DisabledNote, ...]) -> tuple[DisabledNote, ...]:
    items = tuple(values)
    if not all(isinstance(item, DisabledNote) for item in items):
        raise SongCueComposerError("disabled_plan_notes must contain DisabledNote values")
    return items


def _validate_percent(name: str, value: float | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SongCueComposerError(f"{name} must be numeric or None, got {value!r}")
    if not 0.0 <= float(value) <= 100.0:
        raise SongCueComposerError(f"{name} must be within 0-100, got {value!r}")


def _validate_nonnegative(name: str, value: float | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SongCueComposerError(f"{name} must be numeric or None, got {value!r}")
    if float(value) < 0.0:
        raise SongCueComposerError(f"{name} must be non-negative, got {value!r}")


@dataclass(frozen=True)
class CardRequeryRequirement:
    axis: DecisionAxis
    reason: str
    prompt: str
    source: str
    section_index: int | None = None
    step: str | None = None
    choice_label: str | None = None
    free_text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise SongCueComposerError("requery reason must be non-empty")
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise SongCueComposerError("requery prompt must be non-empty")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongCueComposerError("requery source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "axis": self.axis,
            "section_index": self.section_index,
            "reason": self.reason,
            "prompt": self.prompt,
            "source": self.source,
            "step": self.step,
            "choice_label": self.choice_label,
            "free_text": self.free_text,
        }


@dataclass(frozen=True)
class CueDimmerData:
    key_pct: float | None
    back_pct: float | None
    budget_range_pct: tuple[float, float]
    blackout: bool = False

    def __post_init__(self) -> None:
        _validate_percent("key_pct", self.key_pct)
        _validate_percent("back_pct", self.back_pct)
        if len(self.budget_range_pct) != 2:
            raise SongCueComposerError("budget_range_pct must have exactly two values")
        low, high = self.budget_range_pct
        _validate_percent("budget_range_pct low", low)
        _validate_percent("budget_range_pct high", high)
        if low > high:
            raise SongCueComposerError("budget_range_pct must be ordered low to high")
        object.__setattr__(self, "budget_range_pct", (float(low), float(high)))

    def to_dict(self) -> dict[str, object]:
        return {
            "key_pct": self.key_pct,
            "back_pct": self.back_pct,
            "budget_range_pct": list(self.budget_range_pct),
            "blackout": self.blackout,
        }


@dataclass(frozen=True)
class CueColorData:
    palette: tuple[str, ...]
    saturation: str
    palette_id: str | None = None
    source: str = "plan_palette"

    def __post_init__(self) -> None:
        object.__setattr__(self, "palette", _tuple_of_str("palette", self.palette))
        if not isinstance(self.saturation, str) or not self.saturation.strip():
            raise SongCueComposerError("saturation must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongCueComposerError("color source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "palette": list(self.palette),
            "saturation": self.saturation,
            "palette_id": self.palette_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class CuePositionData:
    requested: str | None
    stored: str | None
    width_tier: str | None
    source: str
    mib_premoved_by: float | None = None

    def __post_init__(self) -> None:
        for name in ("requested", "stored"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise SongCueComposerError(f"position {name} must be non-empty or None")
        if self.width_tier is not None and self.width_tier not in POSITION_WIDTH_TIERS:
            raise SongCueComposerError(f"position width_tier must be one of {POSITION_WIDTH_TIERS}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongCueComposerError("position source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "requested": self.requested,
            "stored": self.stored,
            "width_tier": self.width_tier,
            "source": self.source,
            "mib_premoved_by": self.mib_premoved_by,
        }


@dataclass(frozen=True)
class CueFxData:
    requested: tuple[str, ...]
    permitted: tuple[str, ...]
    disabled: tuple[str, ...]
    density: int
    axis_budget: int
    speed_beats: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", _tuple_of_str("requested", self.requested))
        object.__setattr__(self, "permitted", _tuple_of_str("permitted", self.permitted))
        object.__setattr__(self, "disabled", _tuple_of_str("disabled", self.disabled))
        if isinstance(self.density, bool) or not isinstance(self.density, int):
            raise SongCueComposerError(f"density must be an int, got {self.density!r}")
        if self.density < 0:
            raise SongCueComposerError(f"density must be non-negative, got {self.density!r}")
        if isinstance(self.axis_budget, bool) or not isinstance(self.axis_budget, int):
            raise SongCueComposerError(f"axis_budget must be an int, got {self.axis_budget!r}")
        if self.axis_budget < 0:
            raise SongCueComposerError(
                f"axis_budget must be non-negative, got {self.axis_budget!r}"
            )
        _validate_nonnegative("speed_beats", self.speed_beats)

    def to_dict(self) -> dict[str, object]:
        return {
            "requested": list(self.requested),
            "permitted": list(self.permitted),
            "disabled": list(self.disabled),
            "density": self.density,
            "axis_budget": self.axis_budget,
            "speed_beats": self.speed_beats,
        }


@dataclass(frozen=True)
class CueMibData:
    premove: bool = False
    inserted: bool = False
    reason: str | None = None
    source_cue_number: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.premove, bool) or not isinstance(self.inserted, bool):
            raise SongCueComposerError("MIB flags must be bool values")
        if self.reason is not None and not self.reason.strip():
            raise SongCueComposerError("MIB reason must be non-empty or None")

    def to_dict(self) -> dict[str, object]:
        return {
            "premove": self.premove,
            "inserted": self.inserted,
            "reason": self.reason,
            "source_cue_number": self.source_cue_number,
        }


@dataclass(frozen=True)
class CueTimingData:
    mode: TimingMode
    trigger: CueTrigger
    start_ms: int | None
    trig_time_seconds: float | None = None
    timecode_number: int | None = None
    follows_cue_number: float | None = None

    def __post_init__(self) -> None:
        if self.mode not in (MANUAL_GO, TRIG_TIME, TIMECODE):
            raise SongCueComposerError(f"unknown timing mode {self.mode!r}")
        if self.trigger not in ("manual_go", "trig_time", "timecode", "follow_previous"):
            raise SongCueComposerError(f"unknown timing trigger {self.trigger!r}")
        if self.trigger == "follow_previous":
            if self.follows_cue_number is None:
                raise SongCueComposerError("follow_previous timing requires follows_cue_number")
            if self.start_ms is not None or self.trig_time_seconds is not None:
                raise SongCueComposerError("follow_previous timing must be relative only")
            return
        if self.start_ms is None:
            raise SongCueComposerError("section timing requires start_ms")
        if self.start_ms < 0:
            raise SongCueComposerError(f"start_ms must be non-negative, got {self.start_ms!r}")
        if self.trigger == "manual_go" and self.mode != MANUAL_GO:
            raise SongCueComposerError("manual_go trigger must match manual_go mode")
        if self.trigger == "trig_time" and self.mode != TRIG_TIME:
            raise SongCueComposerError("trig_time trigger must match trig_time mode")
        if self.trigger == "timecode" and self.mode != TIMECODE:
            raise SongCueComposerError("timecode trigger must match timecode mode")

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "trigger": self.trigger,
            "start_ms": self.start_ms,
            "trig_time_seconds": self.trig_time_seconds,
            "timecode_number": self.timecode_number,
            "follows_cue_number": self.follows_cue_number,
        }


@dataclass(frozen=True)
class ComposedCue:
    kind: CueKind
    section_index: int
    cue_number: float
    cue_name: str
    d_level: int
    fade_seconds: float
    position: CuePositionData
    dimmer: CueDimmerData
    color: CueColorData
    fx: CueFxData
    accents: tuple[str, ...]
    mib: CueMibData
    timing: CueTimingData

    def __post_init__(self) -> None:
        if self.kind not in ("section", "mib_premove"):
            raise SongCueComposerError(f"unknown cue kind {self.kind!r}")
        if isinstance(self.section_index, bool) or not isinstance(self.section_index, int):
            raise SongCueComposerError(f"section_index must be an int, got {self.section_index!r}")
        if self.section_index < 1:
            raise SongCueComposerError(f"section_index must be >= 1, got {self.section_index!r}")
        if not isinstance(self.cue_number, int | float) or self.cue_number <= 0:
            raise SongCueComposerError(f"cue_number must be positive, got {self.cue_number!r}")
        if not isinstance(self.cue_name, str) or not self.cue_name.strip():
            raise SongCueComposerError("cue_name must be non-empty")
        if self.d_level not in (1, 2, 3, 4, 5):
            raise SongCueComposerError(f"d_level must be 1-5, got {self.d_level!r}")
        _validate_nonnegative("fade_seconds", self.fade_seconds)
        if not isinstance(self.position, CuePositionData):
            raise SongCueComposerError("position must be CuePositionData")
        if not isinstance(self.dimmer, CueDimmerData):
            raise SongCueComposerError("dimmer must be CueDimmerData")
        if not isinstance(self.color, CueColorData):
            raise SongCueComposerError("color must be CueColorData")
        if not isinstance(self.fx, CueFxData):
            raise SongCueComposerError("fx must be CueFxData")
        object.__setattr__(self, "accents", _tuple_of_str("accents", self.accents))
        if not isinstance(self.mib, CueMibData):
            raise SongCueComposerError("mib must be CueMibData")
        if not isinstance(self.timing, CueTimingData):
            raise SongCueComposerError("timing must be CueTimingData")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "section_index": self.section_index,
            "cue_number": self.cue_number,
            "cue_name": self.cue_name,
            "d_level": self.d_level,
            "fade_seconds": self.fade_seconds,
            "position": self.position.to_dict(),
            "dimmer": self.dimmer.to_dict(),
            "color": self.color.to_dict(),
            "fx": self.fx.to_dict(),
            "accents": list(self.accents),
            "mib": self.mib.to_dict(),
            "timing": self.timing.to_dict(),
        }


@dataclass(frozen=True)
class SongCueBundle:
    song_title: str
    sequence_name: str | None
    cues: tuple[ComposedCue, ...]
    lint_findings: tuple[LintFinding, ...] = ()
    disabled_rule_notes: tuple[DisabledRuleNote, ...] = ()
    disabled_plan_notes: tuple[DisabledNote, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.song_title, str) or not self.song_title.strip():
            raise SongCueComposerError("song_title must be non-empty")
        cues = tuple(self.cues)
        if not cues:
            raise SongCueComposerError("a composed bundle must contain at least one cue")
        if not all(isinstance(cue, ComposedCue) for cue in cues):
            raise SongCueComposerError("cues must contain ComposedCue values")
        cue_numbers = [cue.cue_number for cue in cues]
        if cue_numbers != sorted(cue_numbers):
            raise SongCueComposerError("cues must be ordered by cue_number")
        object.__setattr__(self, "cues", cues)
        object.__setattr__(self, "lint_findings", _tuple_of_findings(self.lint_findings))
        object.__setattr__(
            self,
            "disabled_rule_notes",
            _tuple_of_disabled_rules(self.disabled_rule_notes),
        )
        object.__setattr__(
            self,
            "disabled_plan_notes",
            _tuple_of_disabled_notes(self.disabled_plan_notes),
        )

    @property
    def section_cues(self) -> tuple[ComposedCue, ...]:
        return tuple(cue for cue in self.cues if cue.kind == "section")

    def to_dict(self) -> dict[str, object]:
        return {
            "song_title": self.song_title,
            "sequence_name": self.sequence_name,
            "cues": [cue.to_dict() for cue in self.cues],
            "lint_findings": [_lint_finding_dict(finding) for finding in self.lint_findings],
            "disabled_rule_notes": [_disabled_rule_dict(note) for note in self.disabled_rule_notes],
            "disabled_plan_notes": [note.to_dict() for note in self.disabled_plan_notes],
        }


@dataclass(frozen=True)
class SongCueCompositionResult:
    bundle: SongCueBundle | None
    requery_requirements: tuple[CardRequeryRequirement, ...] = ()
    lint_findings: tuple[LintFinding, ...] = ()
    disabled_rule_notes: tuple[DisabledRuleNote, ...] = ()
    disabled_plan_notes: tuple[DisabledNote, ...] = ()

    def __post_init__(self) -> None:
        if self.bundle is not None and not isinstance(self.bundle, SongCueBundle):
            raise SongCueComposerError("bundle must be SongCueBundle or None")
        requirements = tuple(self.requery_requirements)
        if not all(isinstance(item, CardRequeryRequirement) for item in requirements):
            raise SongCueComposerError(
                "requery_requirements must contain CardRequeryRequirement values"
            )
        if self.bundle is not None and requirements:
            raise SongCueComposerError("a successful bundle cannot also request re-query cards")
        object.__setattr__(self, "requery_requirements", requirements)
        object.__setattr__(self, "lint_findings", _tuple_of_findings(self.lint_findings))
        object.__setattr__(
            self,
            "disabled_rule_notes",
            _tuple_of_disabled_rules(self.disabled_rule_notes),
        )
        object.__setattr__(
            self,
            "disabled_plan_notes",
            _tuple_of_disabled_notes(self.disabled_plan_notes),
        )

    @property
    def complete(self) -> bool:
        return self.bundle is not None and not self.requery_requirements

    def to_dict(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "bundle": None if self.bundle is None else self.bundle.to_dict(),
            "requery_requirements": [
                requirement.to_dict() for requirement in self.requery_requirements
            ],
            "lint_findings": [_lint_finding_dict(finding) for finding in self.lint_findings],
            "disabled_rule_notes": [_disabled_rule_dict(note) for note in self.disabled_rule_notes],
            "disabled_plan_notes": [note.to_dict() for note in self.disabled_plan_notes],
        }


def compose_song_cue_bundle(plan: UnifiedSongLightingPlan) -> SongCueCompositionResult:
    if not isinstance(plan, UnifiedSongLightingPlan):
        raise SongCueComposerError("plan must be a UnifiedSongLightingPlan")

    disabled_plan_notes = tuple(plan.disabled)
    requery_requirements = _requery_requirements(plan)
    if requery_requirements:
        return SongCueCompositionResult(
            bundle=None,
            requery_requirements=requery_requirements,
            disabled_plan_notes=disabled_plan_notes,
        )

    cues = _apply_mib(
        tuple(
            _section_cue(plan, decision, payload)
            for decision, payload in zip(
                plan.sections,
                plan.cue_payloads(),
                strict=True,
            )
        )
    )
    lint_report = _lint_report(plan, cues)
    bundle = SongCueBundle(
        song_title=plan.song_title,
        sequence_name=plan.sequence_name,
        cues=cues,
        lint_findings=lint_report.findings,
        disabled_rule_notes=lint_report.disabled_rules,
        disabled_plan_notes=disabled_plan_notes,
    )
    return SongCueCompositionResult(
        bundle=bundle,
        lint_findings=lint_report.findings,
        disabled_rule_notes=lint_report.disabled_rules,
        disabled_plan_notes=disabled_plan_notes,
    )


build_song_cue_bundle = compose_song_cue_bundle


def _requery_requirements(plan: UnifiedSongLightingPlan) -> tuple[CardRequeryRequirement, ...]:
    requirements: list[CardRequeryRequirement] = []
    for note in plan.unresolved:
        prompt = note.prompt or _default_prompt(note.axis, note.section_index)
        requirements.append(
            CardRequeryRequirement(
                axis=note.axis,
                section_index=note.section_index,
                reason=note.reason,
                prompt=prompt,
                source="unresolved_plan_input",
            )
        )
    for decision in plan.director_decisions:
        if decision.confirmed:
            continue
        requirements.append(
            CardRequeryRequirement(
                axis=decision.axis,
                section_index=decision.section_index,
                reason="director answer is not confirmed",
                prompt=_director_prompt(decision),
                source=decision.source,
                step=decision.step,
                choice_label=decision.choice_label,
                free_text=decision.free_text,
            )
        )
    return tuple(requirements)


def _default_prompt(axis: DecisionAxis, section_index: int | None) -> str:
    target = "the whole song" if section_index is None else f"section {section_index}"
    return f"Re-ask the {axis} card for {target}."


def _director_prompt(decision) -> str:
    target = (
        "the whole song" if decision.section_index is None else f"section {decision.section_index}"
    )
    return f"Re-ask {decision.step} for {target} and require an explicit confirmation."


def position_axis_disabled(plan: UnifiedSongLightingPlan) -> bool:
    """전곡 포지션 축이 꺼져 있는가 (카드 t311).

    좌표를 못 읽은 리그에는 프리셋을 불러 앉힐 장비 자체가 없다. 그때
    ``stored`` 를 비우는 것이 이 함수의 전부다 — 없는 포지션을 지어내는 대신
    **빈 칸**을 남기고, 사유는 같은 노트가 들고 있어 리뷰·타임라인이 읽는다.
    구간 노트(``section_index`` 가 있는 것)는 여기서 보지 않는다: 축을 통째로
    끄는 것은 전곡 노트뿐이다.
    """
    return any(note.axis == POSITION_AXIS and note.section_index is None for note in plan.disabled)


def _section_cue(
    plan: UnifiedSongLightingPlan,
    decision: SectionDecision,
    payload,
) -> ComposedCue:
    budget = axis_budget(decision.d.level, plan.music_profile, plan.rig_profile)
    blackout = _is_blackout(decision)
    dimmer = _dimmer_data(budget, plan, blackout=blackout)
    fx = _fx_data_for_role(decision, budget)
    fade_seconds = (
        float(decision.fade_override)
        if decision.fade_override is not None
        else _fade_seconds_for_role(budget, decision, plan)
    )
    position_label = None if blackout or position_axis_disabled(plan) else decision.position.preset
    return ComposedCue(
        kind="section",
        section_index=decision.section.index,
        cue_number=float(payload.cue_number),
        cue_name=payload.cue_name,
        d_level=decision.d.level,
        fade_seconds=fade_seconds,
        position=CuePositionData(
            requested=decision.position.preset,
            stored=position_label,
            width_tier=_position_width_for_role(decision, budget),
            source=decision.position.source,
        ),
        dimmer=dimmer,
        color=CueColorData(
            palette=decision.palette.colors,
            saturation=budget.saturation,
            palette_id=decision.palette.palette_id,
            source=decision.palette.source,
        ),
        fx=fx,
        accents=decision.accent.accents,
        mib=CueMibData(),
        timing=_timing_data(payload.timing),
    )


def _dimmer_data(
    budget: AxisBudget,
    plan: UnifiedSongLightingPlan,
    *,
    blackout: bool,
) -> CueDimmerData:
    low, high = budget.dimmer_pct
    if blackout:
        return CueDimmerData(
            key_pct=0.0,
            back_pct=0.0 if plan.rig_profile.has_layer("back") else None,
            budget_range_pct=budget.dimmer_pct,
            blackout=True,
        )
    key_pct = (low + high) / 2.0
    back_pct = key_pct * 0.8 if plan.rig_profile.has_layer("back") else None
    return CueDimmerData(
        key_pct=key_pct,
        back_pct=back_pct,
        budget_range_pct=budget.dimmer_pct,
    )


def _fx_data(decision: SectionDecision, budget: AxisBudget) -> CueFxData:
    requested = decision.fx.allowed
    permitted = requested[: budget.fx_axes]
    disabled = (*decision.fx.disabled, *requested[budget.fx_axes :])
    speed_beats = _effect_speed_beats(budget, permitted)
    return CueFxData(
        requested=requested,
        permitted=permitted,
        disabled=disabled,
        density=decision.fx.density,
        axis_budget=budget.fx_axes,
        speed_beats=speed_beats,
    )


#: 카드 t394 — 정본 §6 "breakdown · bridge → 밝기 20~35% · 무빙·이펙트 정지".
#: `_ARC_D_LEVEL`(session.py) 은 bridge 를 D2 고정으로 주지만, 이 예산은
#: `axis_budget(decision.d.level, ...)` 로 D 레벨마다 다시 계산되므로 D2·D3
#: 에서는 `('slow tilt',)` 가 permit 된다(실측: D2 fx_permitted=('slow
#: tilt',) density=1 speed_beats=0.25 — 정지가 아니다). §6 은 밝기(D 레벨)와
#: 별개로 role 하나만 조건으로 건다 — D1 에서 우연히 permitted 가 비었던 것과
#: 같은 결과를 D 레벨과 무관하게 강제한다. 밝기·페이드는 이 축이 아니므로
#: 건드리지 않는다(`_fade_seconds_for_role` 과 같은 분리 원칙).
_BRIDGE_ROLE = "bridge"


def _fx_data_for_role(decision: SectionDecision, budget: AxisBudget) -> CueFxData:
    if decision.role != _BRIDGE_ROLE:
        return _fx_data(decision, budget)
    requested = decision.fx.allowed
    return CueFxData(
        requested=requested,
        permitted=(),
        disabled=(*decision.fx.disabled, *requested),
        density=0,
        axis_budget=budget.fx_axes,
        speed_beats=None,
    )


def _position_width_for_role(decision: SectionDecision, budget: AxisBudget) -> str:
    if decision.role != _BRIDGE_ROLE:
        return _position_width_tier(budget.position_width)
    return _position_width_tier(0.0)


def _effect_speed_beats(budget: AxisBudget, permitted: tuple[str, ...]) -> float | None:
    if not permitted:
        return None
    low, high = budget.fx_speed_mult
    if high > 0.0:
        return high
    if low > 0.0:
        return low
    return None


def _fade_seconds(budget: AxisBudget) -> float:
    low, high = budget.fade_seconds
    return (low + high) / 2.0


#: 카드 t386 — 연출 기준 §6 "outro → 느린 페이드 1회". `_ARC_D_LEVEL` 은
#: finale 도 chorus 와 같은 D5 를 준다(`session.py`) — 두 역할이 밝기는
#: 같아야 맞지만, D5 의 페이드 표(§3)는 chorus 히트용 하프비트짜리라
#: finale 이 그대로 받으면 곡이 뚝 끊기듯 끝난다. D 레벨(밝기)은 그대로
#: 두고 페이드(전환 속도)만 D1 행(§3 의 가장 느린 페이드)으로 바꾼다 —
#: 두 축을 분리해 놓은 §3 표의 구조를 그대로 이용한 것이라 새 숫자를
#: 지어내지 않는다.
_OUTRO_ROLE = "finale"
_OUTRO_FADE_D_LEVEL = 1


def _fade_seconds_for_role(
    budget: AxisBudget, decision: SectionDecision, plan: UnifiedSongLightingPlan
) -> float:
    if decision.role != _OUTRO_ROLE:
        return _fade_seconds(budget)
    outro_budget = axis_budget(_OUTRO_FADE_D_LEVEL, plan.music_profile, plan.rig_profile)
    return _fade_seconds(outro_budget)


def _position_width_tier(width: float) -> str:
    for ceiling, label in _POSITION_WIDTH_FROM_ENERGY:
        if width <= ceiling:
            return label
    raise SongCueComposerError(f"unsupported position width {width!r}")


def _timing_data(timing: CueTimingPayload) -> CueTimingData:
    if not isinstance(timing, CueTimingPayload):
        raise SongCueComposerError("timing payload must be a CueTimingPayload")
    if timing.mode == MANUAL_GO:
        trigger: CueTrigger = "manual_go"
    elif timing.mode == TRIG_TIME:
        trigger = "trig_time"
    elif timing.mode == TIMECODE:
        trigger = "timecode"
    else:
        raise SongCueComposerError(f"unknown timing mode {timing.mode!r}")
    return CueTimingData(
        mode=timing.mode,
        trigger=trigger,
        start_ms=timing.start_ms,
        trig_time_seconds=timing.trig_time_seconds,
        timecode_number=timing.timecode_number,
    )


def _apply_mib(cues: tuple[ComposedCue, ...]) -> tuple[ComposedCue, ...]:
    if not cues:
        return ()
    result: list[ComposedCue] = []
    dark = False
    parked_position: str | None = None
    previous_cue_number: float | None = None
    for cue in cues:
        stored_position = cue.position.stored
        key_pct = cue.dimmer.key_pct
        fires = (
            dark
            and previous_cue_number is not None
            and stored_position is not None
            and stored_position != parked_position
            and key_pct is not None
            and key_pct > 0.0
        )
        if fires:
            midpoint = (previous_cue_number + cue.cue_number) / 2.0
            result.append(_mib_premove(cue, cue_number=midpoint, follows=previous_cue_number))
            result.append(_mib_reveal(cue, premove_cue_number=midpoint))
        else:
            result.append(cue)
        if stored_position is not None:
            parked_position = stored_position
        if key_pct is not None:
            dark = key_pct == 0.0
        previous_cue_number = cue.cue_number
    return tuple(result)


def _mib_premove(reveal: ComposedCue, *, cue_number: float, follows: float) -> ComposedCue:
    return ComposedCue(
        kind="mib_premove",
        section_index=reveal.section_index,
        cue_number=cue_number,
        cue_name=f"{reveal.cue_name} Move",
        d_level=reveal.d_level,
        fade_seconds=1.0,
        position=CuePositionData(
            requested=reveal.position.requested,
            stored=reveal.position.stored,
            width_tier=reveal.position.width_tier,
            source="mib",
        ),
        dimmer=CueDimmerData(
            key_pct=None,
            back_pct=None,
            budget_range_pct=reveal.dimmer.budget_range_pct,
        ),
        color=CueColorData(
            palette=(),
            saturation=reveal.color.saturation,
            palette_id=reveal.color.palette_id,
            source="mib",
        ),
        fx=CueFxData(
            requested=(),
            permitted=(),
            disabled=(),
            density=0,
            axis_budget=0,
        ),
        accents=(),
        mib=CueMibData(
            premove=True,
            inserted=True,
            reason="dark reveal moves before intensity",
            source_cue_number=reveal.cue_number,
        ),
        timing=CueTimingData(
            mode=reveal.timing.mode,
            trigger="follow_previous",
            start_ms=None,
            follows_cue_number=follows,
        ),
    )


def _mib_reveal(reveal: ComposedCue, *, premove_cue_number: float) -> ComposedCue:
    return dataclasses.replace(
        reveal,
        position=dataclasses.replace(
            reveal.position,
            stored=None,
            mib_premoved_by=premove_cue_number,
        ),
        mib=CueMibData(
            premove=False,
            inserted=True,
            reason="position carried by preceding dark pre-move",
            source_cue_number=premove_cue_number,
        ),
    )


def _lint_report(plan: UnifiedSongLightingPlan, cues: tuple[ComposedCue, ...]):
    section_ordinals = {
        decision.section.index: ordinal for ordinal, decision in enumerate(plan.sections)
    }
    sheet = LintSheet(
        sections=tuple(
            LintSection(index=ordinal, name=decision.section.label)
            for ordinal, decision in enumerate(plan.sections)
        ),
        cues=tuple(_lint_cue(cue, section_ordinals[cue.section_index]) for cue in cues),
    )
    return lint_sheet(sheet, plan.music_profile, plan.rig_profile)


def _lint_cue(cue: ComposedCue, section_ordinal: int) -> LintCue:
    return LintCue(
        cue_no=cue.cue_number,
        section_index=section_ordinal,
        d_level=cue.d_level,
        fade_seconds=cue.fade_seconds,
        key_dimmer_pct=cue.dimmer.key_pct,
        back_dimmer_pct=cue.dimmer.back_pct,
        position_label=cue.position.stored,
        position_width=cue.position.width_tier,
        palette_colors=cue.color.palette,
        palette_source=cue.color.source,
        effect_axis_count=len(cue.fx.permitted),
        effect_speed_beats=cue.fx.speed_beats,
        is_accent=bool(cue.accents),
        is_blackout=cue.dimmer.blackout,
        is_audience_or_blinder=_contains_any(
            (*cue.accents, *cue.fx.permitted),
            _AUDIENCE_TOKENS,
        ),
    )


def _is_blackout(decision: SectionDecision) -> bool:
    return _contains_any(
        (
            decision.section.label,
            decision.position.preset,
            decision.texture.label,
            *decision.texture.notes,
            *decision.fx.allowed,
            *decision.accent.accents,
        ),
        _BLACKOUT_TOKENS,
    )


def _contains_any(values: tuple[str, ...], tokens: frozenset[str]) -> bool:
    for value in values:
        folded = value.strip().casefold()
        if folded in tokens:
            return True
        if any(token in folded for token in tokens):
            return True
    return False


def _lint_finding_dict(finding: LintFinding) -> dict[str, object]:
    return {
        "rule_id": finding.rule_id,
        "cue_number": finding.cue_number,
        "description": finding.description,
    }


def _disabled_rule_dict(note: DisabledRuleNote) -> dict[str, object]:
    return {"rule_id": note.rule_id, "reason": note.reason}
