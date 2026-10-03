from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from server.concept.mib import live_move_note
from server.concept.resolver import MOVE_SECONDS, SETTLE_SECONDS
from server.design.energy import AxisBudget, axis_budget, beats_to_seconds
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
from server.looks.section_intent import intent_for_label
from server.looks.section_vocab import ROW_CHORUS
from server.looks.songcue import LADDER_BLINDER_OR_FLASH, climax_cap_beats, darkness_target

__all__ = [
    "CardRequeryRequirement",
    "CueColorData",
    "CueDimmerData",
    "CueFxData",
    "ARC_BLINDER_GROUP_ABSENT",
    "ARC_BLINDER_ROW_ABSENT",
    "CueAccentFixtureData",
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

CueKind = Literal["section", "mib_premove", "climax_return"]
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
    """SPEC-LDRENDER-001 M3 — ``role_pct``는 ``key_pct``/``back_pct``(결함 6,
    하위호환으로 유지)를 역할 어휘(``rig.RIG_LAYER_ROLES``) 전체로 일반화한
    매핑이다. 이 시점(M3)에 실제로 채워지는 키는 ``key``/``back`` 뿐이다 —
    side/wash/mover 의 퍼센트 산출 규칙은 아직 정본 어디에도 없어(코드 판독
    + `docs/proposals/song-lighting-design-standard.md` §4a I1·§4b C1 전수
    확인, M3.md §미해결 참조) 지어내지 않는다. 비어 있는 역할은 단순히
    ``role_pct``에 없고, 렌더러(``song_cue_render._role_dimmer_value_lines``)는
    없는 역할의 줄을 내지 않는다 — 발명이 아니라 생략이다."""

    key_pct: float | None
    back_pct: float | None
    budget_range_pct: tuple[float, float]
    blackout: bool = False
    role_pct: Mapping[str, float] = dataclasses.field(default_factory=dict)

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
        role_pct = dict(self.role_pct)
        for role, pct in role_pct.items():
            if not isinstance(role, str) or not role.strip():
                raise SongCueComposerError(f"role_pct key must be a non-empty string, got {role!r}")
            _validate_percent(f"role_pct[{role!r}]", pct)
        object.__setattr__(self, "role_pct", MappingProxyType(role_pct))

    def to_dict(self) -> dict[str, object]:
        return {
            "key_pct": self.key_pct,
            "back_pct": self.back_pct,
            "budget_range_pct": list(self.budget_range_pct),
            "blackout": self.blackout,
            "role_pct": dict(self.role_pct),
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
    #: 카드 t471 — 사전이동 큐가 나간 뒤 켜지는 큐까지의 시간(초). 두 큐 중
    #: 하나라도 시각이 없으면 ``None``(재지 못함 — 「문제없음」이 아니다).
    dark_window_seconds: float | None = None
    #: 카드 t471 — 위 시간이 이동+정착(``resolver.MOVE_SECONDS +
    #: SETTLE_SECONDS``)보다 짧으면 ``True``. 어둠은 늘리지 않고 경고만 한다.
    live_move: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.premove, bool) or not isinstance(self.inserted, bool):
            raise SongCueComposerError("MIB flags must be bool values")
        if not isinstance(self.live_move, bool):
            raise SongCueComposerError("MIB live_move must be a bool value")
        if self.reason is not None and not self.reason.strip():
            raise SongCueComposerError("MIB reason must be non-empty or None")

    def to_dict(self) -> dict[str, object]:
        return {
            "premove": self.premove,
            "inserted": self.inserted,
            "reason": self.reason,
            "source_cue_number": self.source_cue_number,
            "dark_window_seconds": self.dark_window_seconds,
            "live_move": self.live_move,
        }


#: 카드 t462 — 절정 액센트를 블라인더로 못 낸 사유(``SongCueBundle.arc_notes``).
ARC_BLINDER_GROUP_ABSENT = "blinder_group_absent"
ARC_BLINDER_ROW_ABSENT = "blinder_six_row_absent"

#: 대화 길이 스스로 붙이는 절정 액센트 이름표 중 블라인더로 내보내는 것
#: (``server.web.session._occurrence_accent_label`` · ``_accent_decision``).
#: 「moving position hit」은 블라인더가 아니므로 여기 없다.
_BLINDER_ACCENT_PREFIXES = ("white flash", "climax accent")


@dataclass(frozen=True)
class CueAccentFixtureData:
    """이 큐가 켜는 블라인더 그룹과 밝기 (카드 t462).

    ``rung`` 과 ``dimmer_pct`` 는 업로드 길(``server/looks/songcue.py``)의 값을
    그대로 쓴다 — 칸 이름은 :data:`LADDER_BLINDER_OR_FLASH`, 밝기는 그 구간 §6
    행의 아래끝(B 의 ``_accent_fixture_commands`` 가 고르는 첫 값)이다.
    """

    rung: str
    group_no: int
    dimmer_pct: float

    def __post_init__(self) -> None:
        if isinstance(self.group_no, bool) or not isinstance(self.group_no, int):
            raise SongCueComposerError(f"group_no must be an int, got {self.group_no!r}")
        _validate_percent("dimmer_pct", self.dimmer_pct)

    def to_dict(self) -> dict[str, object]:
        return {"rung": self.rung, "group_no": self.group_no, "dimmer_pct": self.dimmer_pct}


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
    #: 카드 t462 — 이 큐가 켜는 블라인더(없으면 ``None``).
    accent_fixture: CueAccentFixtureData | None = None
    #: 카드 t462 — 드롭 앞 어둠이 내리기 **전** 밝기(안 내렸으면 ``None``).
    pre_drop_from: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("section", "mib_premove", "climax_return"):
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
            "accent_fixture": (
                self.accent_fixture.to_dict() if self.accent_fixture is not None else None
            ),
            "pre_drop_from": self.pre_drop_from,
        }


@dataclass(frozen=True)
class SongCueBundle:
    song_title: str
    sequence_name: str | None
    cues: tuple[ComposedCue, ...]
    lint_findings: tuple[LintFinding, ...] = ()
    disabled_rule_notes: tuple[DisabledRuleNote, ...] = ()
    disabled_plan_notes: tuple[DisabledNote, ...] = ()
    #: 카드 t462 — 드롭 앞 어둠·블라인더·복귀 큐를 못 한 자리와 그 사유.
    arc_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.song_title, str) or not self.song_title.strip():
            raise SongCueComposerError("song_title must be non-empty")
        object.__setattr__(self, "arc_notes", _tuple_of_str("arc_notes", self.arc_notes))
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

    @property
    def timed_cues(self) -> tuple[ComposedCue, ...]:
        """시각을 갖고 콘솔 타이밍에 실리는 큐 — 구간 큐와 절정 복귀 큐(카드 t462).

        MIB 사전이동은 앞 큐를 따라가므로(``follow_previous``) 여기 없다.
        """
        return tuple(cue for cue in self.cues if cue.kind in ("section", "climax_return"))

    def to_dict(self) -> dict[str, object]:
        return {
            "song_title": self.song_title,
            "sequence_name": self.sequence_name,
            "cues": [cue.to_dict() for cue in self.cues],
            "lint_findings": [_lint_finding_dict(finding) for finding in self.lint_findings],
            "disabled_rule_notes": [_disabled_rule_dict(note) for note in self.disabled_rule_notes],
            "disabled_plan_notes": [note.to_dict() for note in self.disabled_plan_notes],
            "arc_notes": list(self.arc_notes),
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

    section_cues = tuple(
        _section_cue(plan, decision, payload)
        for decision, payload in zip(
            plan.sections,
            plan.cue_payloads(),
            strict=True,
        )
    )
    labels = {decision.section.index: decision.section.label for decision in plan.sections}
    # 카드 t462 — 업로드 길의 드롭 전 어둠·절정 길이 상한을 여기서도 건다. MIB 앞에
    # 둔다: MIB 는 「앞 큐가 어두운가」를 보는데, 어둠의 바닥(DARKNESS_FLOOR=20)은
    # 0 이 아니므로 MIB 판정을 바꾸지 않는다.
    darkened = _apply_pre_drop_darkness(plan, section_cues, labels)
    accented, arc_notes = _apply_blinder_accents(plan, darkened, labels)
    cues = _apply_mib(_apply_climax_returns(plan, accented))
    lint_report = _lint_report(plan, cues)
    bundle = SongCueBundle(
        song_title=plan.song_title,
        sequence_name=plan.sequence_name,
        cues=cues,
        lint_findings=lint_report.findings,
        disabled_rule_notes=lint_report.disabled_rules,
        disabled_plan_notes=disabled_plan_notes,
        arc_notes=arc_notes,
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


#: SPEC-LDRENDER-001 M3 완료(리드 결정, 카드 t501, 2026-10-01) — side/wash/
#: mover 의 퍼센트 산출 규칙은 정본 어디에도 없다(M3.md §미해결 6단계 검색
#: 표, back 전용 ``key_pct * 0.8``이 유일한 역할별 공식). 리드가 M3 블로커의
#: 옵션 (a)(back 비율 재사용)를 확정했다 — **새 숫자를 짓지 않고** back 과
#: 바이트 동일한 식을 side/wash/mover 에도 그대로 적용한다. 이 결정의 알려진
#: 결과(블로커 분석이 "치명적 결함"으로 적어 둔 것): side/wash/mover 가 back
#: 과 **같은 값**을 받으므로 ``ldrender_gate.layer_diversity``(상태값 기준
#: 버킷)에서 디머만으로는 새 버킷이 안 생긴다 — 층 간 밝기 대비는 R5(후속
#: SPEC)로 이월한다. 층 구분은 M4(이 SPEC 의 R2, `_song_color_value_lines`)
#: 가 역할별로 다른 색(back+mover=지배색, side+wash=보조색, key=중립)을 내는
#: 것으로 난다 — 디머 값이 같아도 색이 다르면 서로 다른 상태 버킷이다.
_BACK_RATIO_ROLES: tuple[str, ...] = ("back", "side", "wash", "mover")


def _role_pct_for(
    key_pct: float | None,
    back_pct: float | None,
    *,
    plan: UnifiedSongLightingPlan | None = None,
) -> dict[str, float]:
    """SPEC-LDRENDER-001 M3 — ``key``/``back``/``side``/``wash``/``mover`` 를
    채운다. ``effect``/``audience`` 는 여전히 **의도적으로 비운다**(이 SPEC
    범위 밖 — role_pct 비어 있음 = 아직 정본 산출 규칙이 없다는 뜻이지 0%
    라는 뜻이 아니다). side/wash/mover 는 리드 결정(위 ``_BACK_RATIO_ROLES``
    주석)대로 back 과 같은 ``key_pct * 0.8`` 식을 ``plan.rig_profile.
    has_layer(role)`` 가 참인 역할에만 채운다 — ``plan`` 이 없으면(과거
    호출부 호환) side/wash/mover 는 여전히 비운다. 이 함수를 ``_dimmer_data``
    와 ``_apply_pre_drop_darkness`` 양쪽이 공유해, 역할 집합이 두 자리에서
    갈라지는 것을 막는다."""
    role_pct: dict[str, float] = {}
    if key_pct is not None:
        role_pct["key"] = key_pct
    if back_pct is not None:
        role_pct["back"] = back_pct
    if plan is not None and key_pct is not None:
        for role in ("side", "wash", "mover"):
            if plan.rig_profile.has_layer(role):
                role_pct[role] = key_pct * 0.8
    return role_pct


def _dimmer_data(
    budget: AxisBudget,
    plan: UnifiedSongLightingPlan,
    *,
    blackout: bool,
) -> CueDimmerData:
    low, high = budget.dimmer_pct
    if blackout:
        back_pct = 0.0 if plan.rig_profile.has_layer("back") else None
        return CueDimmerData(
            key_pct=0.0,
            back_pct=back_pct,
            budget_range_pct=budget.dimmer_pct,
            blackout=True,
            role_pct=_role_pct_for(0.0, back_pct, plan=plan),
        )
    key_pct = (low + high) / 2.0
    back_pct = key_pct * 0.8 if plan.rig_profile.has_layer("back") else None
    return CueDimmerData(
        key_pct=key_pct,
        back_pct=back_pct,
        budget_range_pct=budget.dimmer_pct,
        role_pct=_role_pct_for(key_pct, back_pct, plan=plan),
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


def _is_drop_row(label: str) -> bool:
    """이 이름이 §6 표의 chorus · drop 행인가 — 업로드 길의 판정과 같은 표를 읽는다."""
    intent = intent_for_label(label)
    return intent is not None and intent.row == ROW_CHORUS


# @MX:NOTE: [AUTO] 드롭 앞 어둠(정본 §8) — 값은 업로드 길의 `darkness_target` 하나에서
#   온다(카드 t462). 형태는 B 와 같은 「줄인 워시」: 앞 큐의 밝기를 그 행의 바닥까지
#   내린다. 같은 행(후렴 뒤 후렴)·이미 어두운 큐·블랙아웃은 건드리지 않는다.
def _apply_pre_drop_darkness(
    plan: UnifiedSongLightingPlan,
    cues: tuple[ComposedCue, ...],
    labels: dict[int, str],
) -> tuple[ComposedCue, ...]:
    result = list(cues)
    for position in range(1, len(result)):
        if not _is_drop_row(labels[result[position].section_index]):
            continue
        previous = result[position - 1]
        intent = intent_for_label(labels[previous.section_index])
        if intent is None or intent.row == ROW_CHORUS:
            continue
        key_pct = previous.dimmer.key_pct
        target = float(darkness_target(intent))
        if key_pct is None or previous.dimmer.blackout or key_pct <= target:
            continue
        back_pct = previous.dimmer.back_pct
        new_back_pct = None if back_pct is None else target * 0.8
        # SPEC-LDRENDER-001 M3 — `role_pct`는 `dataclasses.replace`로는 저절로
        # 안 따라온다(지정 안 한 필드는 옛 값을 그대로 들고 온다). 여기서 다시
        # 계산하지 않으면 `back_pct` 필드는 내려갔는데 `role_pct["back"]`은
        # 드롭-앞-어둠 적용 전 값으로 남는 불일치가 생긴다. M3 완료(리드 결정,
        # 카드 t501) — `plan`을 넘겨 side/wash/mover 도 같은 비율로 같이
        # 내려간다(위 `_role_pct_for`/`_BACK_RATIO_ROLES` 주석 참조).
        result[position - 1] = dataclasses.replace(
            previous,
            dimmer=dataclasses.replace(
                previous.dimmer,
                key_pct=target,
                back_pct=new_back_pct,
                role_pct=_role_pct_for(target, new_back_pct, plan=plan),
            ),
            pre_drop_from=key_pct,
        )
    return tuple(result)


def _apply_blinder_accents(
    plan: UnifiedSongLightingPlan, cues: tuple[ComposedCue, ...], labels: dict[int, str]
) -> tuple[tuple[ComposedCue, ...], tuple[str, ...]]:
    """대화 길이 스스로 붙인 절정 액센트를 블라인더 그룹으로 낸다 (카드 t462).

    밝기는 그 구간 §6 행의 아래끝 — 업로드 길이 블라인더에 주는 첫 값과 같다.
    그룹이 없거나 행이 없으면 켜지 않고 사유를 남긴다(숫자를 지어내지 않는다).
    """
    result: list[ComposedCue] = []
    notes: list[str] = []
    for cue in cues:
        wants_blinder = any(
            accent.strip().casefold().startswith(_BLINDER_ACCENT_PREFIXES) for accent in cue.accents
        )
        if not wants_blinder:
            result.append(cue)
            continue
        where = f"Q{cue.cue_number:g} {cue.cue_name!r}"
        if plan.blinder_group_no is None:
            notes.append(
                f"{ARC_BLINDER_GROUP_ABSENT}: {where} 절정 액센트 — 콘솔에 BLIND/BLINDER "
                "그룹이 없어 블라인더를 켜지 않음"
            )
            result.append(cue)
            continue
        intent = intent_for_label(labels[cue.section_index])
        if intent is None:
            notes.append(
                f"{ARC_BLINDER_ROW_ABSENT}: {where} 절정 액센트 — 구간 이름이 §6 표의 한 행에 "
                "맞지 않아 블라인더 밝기를 정할 근거가 없음"
            )
            result.append(cue)
            continue
        result.append(
            dataclasses.replace(
                cue,
                accent_fixture=CueAccentFixtureData(
                    rung=LADDER_BLINDER_OR_FLASH,
                    group_no=plan.blinder_group_no,
                    dimmer_pct=float(intent.brightness[0]),
                ),
            )
        )
    return tuple(result), tuple(notes)


# @MX:NOTE: [AUTO] 절정 길이 상한(REQ-LDCLIMAX-006~009) — 박수는 업로드 길의
#   `climax_cap_beats` 하나에서 온다(카드 t462). BPM 이 없거나 수동 GO 면 박을 잴
#   시계가 없으므로 끼우지 않는다 — 수동 GO 에 복귀 큐를 끼우면 감독이 GO 를 한 번
#   더 눌러야 블라인더가 꺼진다.
def _apply_climax_returns(
    plan: UnifiedSongLightingPlan, cues: tuple[ComposedCue, ...]
) -> tuple[ComposedCue, ...]:
    bpm = plan.music_profile.bpm
    if bpm is None or plan.timing.mode == MANUAL_GO:
        return cues
    result: list[ComposedCue] = []
    for position, cue in enumerate(cues):
        result.append(cue)
        fixture = cue.accent_fixture
        if fixture is None or cue.timing.start_ms is None:
            continue
        cap_ms = cue.timing.start_ms + round(
            beats_to_seconds(climax_cap_beats(fixture.rung), bpm) * 1000
        )
        following = cues[position + 1] if position + 1 < len(cues) else None
        if (
            following is not None
            and following.timing.start_ms is not None
            and cap_ms >= following.timing.start_ms
        ):
            continue
        cue_number = (
            (cue.cue_number + following.cue_number) / 2.0
            if following is not None
            else cue.cue_number + 1
        )
        result.append(_climax_return(cue, cue_number=cue_number, cap_ms=cap_ms))
    return tuple(result)


def _climax_return(climax: ComposedCue, *, cue_number: float, cap_ms: int) -> ComposedCue:
    """블라인더를 끄고 절정 큐의 밝기로 돌아가는 큐 — 즉시 복귀(페이드 0).

    이 조립(compose) 층에서 포지션·색·디머는 다시 계산하지 않는다 —
    ``dataclasses.replace``가 교체 인자로 주지 않은 필드(``position``은
    ``stored=None``만 바꾸고, ``dimmer``/``color``는 아예 건드리지 않는다)는
    climax 큐 자신의 값을 바이트 동일하게 그대로 들고 간다. 효과(``fx``)만
    예외로, 명시적으로 빈 값으로 교체한다(복사가 아니다 — 블라인더가 꺼지는
    것 외에 새 효과가 없다는 뜻).

    **송신(render) 층의 재사용(SPEC-LDRENDER-001 M3 후속, t501)**: 포지션은
    송신기도 다시 싣지 않는다(``position.stored=None`` → ``preset_no=None``).
    디머·색은 다르다 — ``reviewed_song_commands``가 모든 저장 큐에 내는 전체
    기구 키 디머 줄이 climax_return 에도 kind 와 무관하게 나가 전체 기구를
    ``key_pct`` 하나로 되감으므로, 송신기(``song_cue_render._role_dimmer_
    value_lines``/``_song_color_value_lines``)가 이 climax_return 큐에도
    역할별 디머·색 줄을 **명시적으로 다시 내어** 그 되감김을 바로잡는다(콘솔
    트래킹에 맡기지 않는다 — `_ROLE_VALUE_LINE_KINDS` 참조). 낼 값은 이
    함수가 바이트 동일하게 들고 온 climax 큐 자신의 값이므로 새 값을
    발명하지 않는다.
    """
    return dataclasses.replace(
        climax,
        kind="climax_return",
        cue_number=cue_number,
        cue_name=f"{climax.cue_name} Return",
        fade_seconds=0.0,
        position=dataclasses.replace(climax.position, stored=None),
        fx=CueFxData(requested=(), permitted=(), disabled=(), density=0, axis_budget=0),
        accents=(),
        accent_fixture=None,
        pre_drop_from=None,
        mib=CueMibData(),
        timing=dataclasses.replace(
            climax.timing,
            start_ms=cap_ms,
            trig_time_seconds=(
                cap_ms / 1000.0 if climax.timing.trig_time_seconds is not None else None
            ),
        ),
    )


def _apply_mib(cues: tuple[ComposedCue, ...]) -> tuple[ComposedCue, ...]:
    if not cues:
        return ()
    result: list[ComposedCue] = []
    dark = False
    parked_position: str | None = None
    previous_cue_number: float | None = None
    previous_start_ms: int | None = None
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
            result.append(
                _mib_premove(
                    cue,
                    cue_number=midpoint,
                    follows=previous_cue_number,
                    dark_window_seconds=_premove_window_seconds(previous_start_ms, cue),
                )
            )
            result.append(_mib_reveal(cue, premove_cue_number=midpoint))
        else:
            result.append(cue)
        if stored_position is not None:
            parked_position = stored_position
        if key_pct is not None:
            dark = key_pct == 0.0
        previous_cue_number = cue.cue_number
        previous_start_ms = cue.timing.start_ms
    return tuple(result)


def _premove_window_seconds(previous_start_ms: int | None, reveal: ComposedCue) -> float | None:
    """카드 t471 — 사전이동 큐는 앞 큐를 따라 바로 나가므로(``follow_previous``),
    이동에 쓸 수 있는 시간은 앞 큐 시작부터 켜지는 큐 시작까지다. 둘 중 하나라도
    시각이 없으면 재지 못한 것으로 ``None`` 을 돌려준다."""
    if previous_start_ms is None or reveal.timing.start_ms is None:
        return None
    return round((reveal.timing.start_ms - previous_start_ms) / 1000.0, 3)


def _mib_premove(
    reveal: ComposedCue,
    *,
    cue_number: float,
    follows: float,
    dark_window_seconds: float | None,
) -> ComposedCue:
    # 카드 t471 — 컨셉 판정기(G12)와 같은 기준으로 어둠이 모자란지 본다.
    # 어둠은 음악이 정하므로 늘리지 않는다: 사전이동은 그대로 넣고 경고만 싣는다
    # (REQ-066 live_move). fade_seconds=1.0 은 이 큐 자체의 포지션 페이드이고,
    # 필요한 어둠 길이(MOVE_SECONDS)와는 다른 양이다.
    need_seconds = MOVE_SECONDS + SETTLE_SECONDS
    live_move = dark_window_seconds is not None and dark_window_seconds < need_seconds
    reason = (
        f"{live_move_note()} (어둠 {dark_window_seconds:g}초 < 필요 {need_seconds:g}초)"
        if live_move
        else "dark reveal moves before intensity"
    )
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
            reason=reason,
            source_cue_number=reveal.cue_number,
            dark_window_seconds=dark_window_seconds,
            live_move=live_move,
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
        # 카드 t462 — 드롭 앞 어둠은 D 레벨 예산(L2) 아래로 **일부러** 내린 값이다
        # (정본 §8). 린트의 의도적 위반 선언으로 그 한 규칙만 억제한다.
        tags=frozenset({"L2"}) if cue.pre_drop_from is not None else frozenset(),
        is_audience_or_blinder=cue.accent_fixture is not None
        or _contains_any(
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
