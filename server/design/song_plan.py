from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from server.design.profile import MusicProfile
from server.design.rig import RigProfile

__all__ = [
    "ACCENT_AXIS",
    "APPROVAL_APPROVED",
    "APPROVAL_DRAFT",
    "APPROVAL_PENDING",
    "APPROVAL_REJECTED",
    "D_AXIS",
    "FX_AXIS",
    "MANUAL_GO",
    "PALETTE_AXIS",
    "POSITION_AXIS",
    "TEXTURE_AXIS",
    "TIMECODE",
    "TRIG_TIME",
    "AccentDecision",
    "ApprovalState",
    "CuePayload",
    "CueTimingPayload",
    "DecisionAxis",
    "DirectorDecision",
    "DisabledNote",
    "DLevelDecision",
    "FxDecision",
    "PaletteDecision",
    "PositionDecision",
    "SectionDecision",
    "SongPlanError",
    "TextureDecision",
    "TimingMode",
    "TimingPlan",
    "TimestampedSection",
    "MusicProfile",
    "RigProfile",
    "UnifiedSongLightingPlan",
    "UnresolvedNote",
]

DecisionAxis = Literal["d", "palette", "position", "texture", "fx", "accent"]
TimingMode = Literal["manual_go", "trig_time", "timecode"]
ApprovalStatus = Literal["draft", "pending_review", "approved", "rejected"]

D_AXIS = "d"
PALETTE_AXIS = "palette"
POSITION_AXIS = "position"
TEXTURE_AXIS = "texture"
FX_AXIS = "fx"
ACCENT_AXIS = "accent"

MANUAL_GO = "manual_go"
TRIG_TIME = "trig_time"
TIMECODE = "timecode"

APPROVAL_DRAFT = "draft"
APPROVAL_PENDING = "pending_review"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"

_AXES: frozenset[str] = frozenset(
    (D_AXIS, PALETTE_AXIS, POSITION_AXIS, TEXTURE_AXIS, FX_AXIS, ACCENT_AXIS)
)
_TIMING_MODES: frozenset[str] = frozenset((MANUAL_GO, TRIG_TIME, TIMECODE))
_APPROVAL_STATUSES: frozenset[str] = frozenset(
    (APPROVAL_DRAFT, APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED)
)


class SongPlanError(ValueError):
    pass


def _validate_int(name: str, value: int, *, minimum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SongPlanError(f"{name} must be an int, got {value!r}")
    if minimum is not None and value < minimum:
        raise SongPlanError(f"{name} must be >= {minimum}, got {value!r}")


def _tuple_of_str(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise SongPlanError(f"{name} must be a sequence of strings, got {values!r}")
    items = tuple(values)
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise SongPlanError(f"{name} entries must be non-empty strings, got {item!r}")
    return items


def _dict_tuple(
    name: str, values: tuple[Mapping[str, object], ...] | list[Mapping[str, object]]
) -> tuple[Mapping[str, object], ...]:
    if isinstance(values, Mapping):
        raise SongPlanError(f"{name} must be a sequence of mappings, got {values!r}")
    rows: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise SongPlanError(f"{name} entries must be mappings, got {value!r}")
        rows.append(MappingProxyType(dict(value)))
    return tuple(rows)


def _validate_axis(axis: str) -> None:
    if axis not in _AXES:
        raise SongPlanError(f"axis must be one of {sorted(_AXES)}, got {axis!r}")


def _jsonable(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
            if not field.name.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class TimestampedSection:
    index: int
    label: str
    start_ms: int
    end_ms: int | None = None
    source: str = "song_timeline"

    def __post_init__(self) -> None:
        _validate_int("index", self.index, minimum=1)
        if not isinstance(self.label, str) or not self.label.strip():
            raise SongPlanError(f"label must be a non-empty string, got {self.label!r}")
        _validate_int("start_ms", self.start_ms, minimum=0)
        if self.end_ms is not None:
            _validate_int("end_ms", self.end_ms, minimum=0)
            if self.end_ms <= self.start_ms:
                raise SongPlanError("end_ms must be greater than start_ms")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    @property
    def start_seconds(self) -> float:
        return self.start_ms / 1000.0

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "label": self.label,
            "start_ms": self.start_ms,
            "start_seconds": self.start_seconds,
            "end_ms": self.end_ms,
            "source": self.source,
        }


@dataclass(frozen=True)
class DLevelDecision:
    level: int
    source: str
    reason: str | None = None

    def __post_init__(self) -> None:
        _validate_int("D level", self.level, minimum=1)
        if self.level > 5:
            raise SongPlanError(f"D level must be 1-5, got {self.level!r}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    def to_dict(self) -> dict[str, object]:
        return {"level": self.level, "source": self.source, "reason": self.reason}


@dataclass(frozen=True)
class PaletteDecision:
    colors: tuple[str, ...]
    source: str
    palette_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "colors", _tuple_of_str("colors", self.colors))
        if not self.colors:
            raise SongPlanError("palette must contain at least one color")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    def to_dict(self) -> dict[str, object]:
        return {"colors": list(self.colors), "source": self.source, "palette_id": self.palette_id}


@dataclass(frozen=True)
class PositionDecision:
    preset: str
    source: str
    candidates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.preset, str) or not self.preset.strip():
            raise SongPlanError(f"preset must be a non-empty string, got {self.preset!r}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")
        object.__setattr__(self, "candidates", _tuple_of_str("candidates", self.candidates))

    def to_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset,
            "source": self.source,
            "candidates": list(self.candidates),
        }


@dataclass(frozen=True)
class TextureDecision:
    label: str
    source: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise SongPlanError(f"label must be a non-empty string, got {self.label!r}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")
        object.__setattr__(self, "notes", _tuple_of_str("notes", self.notes))

    def to_dict(self) -> dict[str, object]:
        return {"label": self.label, "source": self.source, "notes": list(self.notes)}


@dataclass(frozen=True)
class FxDecision:
    allowed: tuple[str, ...] = ()
    source: str = "standard"
    disabled: tuple[str, ...] = ()
    density: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed", _tuple_of_str("allowed", self.allowed))
        object.__setattr__(self, "disabled", _tuple_of_str("disabled", self.disabled))
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")
        _validate_int("density", self.density, minimum=0)

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": list(self.allowed),
            "source": self.source,
            "disabled": list(self.disabled),
            "density": self.density,
        }


@dataclass(frozen=True)
class AccentDecision:
    accents: tuple[str, ...] = ()
    source: str = "standard"
    hits: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "accents", _tuple_of_str("accents", self.accents))
        object.__setattr__(self, "hits", _dict_tuple("hits", self.hits))
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    def to_dict(self) -> dict[str, object]:
        return {
            "accents": list(self.accents),
            "source": self.source,
            "hits": [dict(hit) for hit in self.hits],
        }


@dataclass(frozen=True)
class SectionDecision:
    section: TimestampedSection
    d: DLevelDecision
    palette: PaletteDecision
    position: PositionDecision
    texture: TextureDecision
    fx: FxDecision
    accent: AccentDecision
    cue_number: int | None = None
    #: A director's explicit PLAN-stage fade for this cue (seconds). None =
    #: derive from the D-level axis budget as before.
    fade_override: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.section, TimestampedSection):
            raise SongPlanError("section must be a TimestampedSection")
        if not isinstance(self.d, DLevelDecision):
            raise SongPlanError("d must be a DLevelDecision")
        if not isinstance(self.palette, PaletteDecision):
            raise SongPlanError("palette must be a PaletteDecision")
        if not isinstance(self.position, PositionDecision):
            raise SongPlanError("position must be a PositionDecision")
        if not isinstance(self.texture, TextureDecision):
            raise SongPlanError("texture must be a TextureDecision")
        if not isinstance(self.fx, FxDecision):
            raise SongPlanError("fx must be an FxDecision")
        if not isinstance(self.accent, AccentDecision):
            raise SongPlanError("accent must be an AccentDecision")
        if self.cue_number is not None:
            _validate_int("cue_number", self.cue_number, minimum=1)
        if self.fade_override is not None and (
            not isinstance(self.fade_override, (int, float))
            or isinstance(self.fade_override, bool)
            or self.fade_override < 0
        ):
            raise SongPlanError(
                f"fade_override must be a non-negative number, got {self.fade_override!r}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "section": self.section.to_dict(),
            "decisions": {
                D_AXIS: self.d.to_dict(),
                PALETTE_AXIS: self.palette.to_dict(),
                POSITION_AXIS: self.position.to_dict(),
                TEXTURE_AXIS: self.texture.to_dict(),
                FX_AXIS: self.fx.to_dict(),
                ACCENT_AXIS: self.accent.to_dict(),
            },
            "cue_number": self.cue_number,
            "fade_override": self.fade_override,
        }


@dataclass(frozen=True)
class TimingPlan:
    mode: TimingMode
    timecode_number: int | None = None
    source: str = "operator"

    def __post_init__(self) -> None:
        if self.mode not in _TIMING_MODES:
            raise SongPlanError(f"timing mode must be one of {sorted(_TIMING_MODES)}")
        if self.timecode_number is not None:
            _validate_int("timecode_number", self.timecode_number, minimum=1)
        if self.mode != TIMECODE and self.timecode_number is not None:
            raise SongPlanError("timecode_number is only valid for timecode timing")
        if self.mode == TIMECODE and self.timecode_number is None:
            raise SongPlanError("timecode timing requires timecode_number")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    @classmethod
    def manual_go(cls, *, source: str = "operator") -> TimingPlan:
        return cls(mode=MANUAL_GO, source=source)

    @classmethod
    def trig_time(cls, *, source: str = "operator") -> TimingPlan:
        return cls(mode=TRIG_TIME, source=source)

    @classmethod
    def timecode(cls, timecode_number: int, *, source: str = "operator") -> TimingPlan:
        return cls(mode=TIMECODE, timecode_number=timecode_number, source=source)

    @property
    def uses_trig_time(self) -> bool:
        return self.mode in (TRIG_TIME, TIMECODE)

    @property
    def uses_timecode(self) -> bool:
        return self.mode == TIMECODE

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "uses_trig_time": self.uses_trig_time,
            "uses_timecode": self.uses_timecode,
            "timecode_number": self.timecode_number,
            "source": self.source,
        }


@dataclass(frozen=True)
class UnresolvedNote:
    axis: DecisionAxis
    reason: str
    section_index: int | None = None
    prompt: str | None = None

    def __post_init__(self) -> None:
        _validate_axis(self.axis)
        if self.section_index is not None:
            _validate_int("section_index", self.section_index, minimum=1)
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise SongPlanError(f"reason must be a non-empty string, got {self.reason!r}")

    def to_dict(self) -> dict[str, object]:
        return {
            "axis": self.axis,
            "section_index": self.section_index,
            "reason": self.reason,
            "prompt": self.prompt,
        }


@dataclass(frozen=True)
class DisabledNote:
    axis: DecisionAxis
    reason: str
    section_index: int | None = None

    def __post_init__(self) -> None:
        _validate_axis(self.axis)
        if self.section_index is not None:
            _validate_int("section_index", self.section_index, minimum=1)
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise SongPlanError(f"reason must be a non-empty string, got {self.reason!r}")

    def to_dict(self) -> dict[str, object]:
        return {"axis": self.axis, "section_index": self.section_index, "reason": self.reason}


@dataclass(frozen=True)
class DirectorDecision:
    step: str
    axis: DecisionAxis
    value: object
    confirmed: bool
    source: str
    section_index: int | None = None
    free_text: str | None = None
    choice_label: str | None = None

    def __post_init__(self) -> None:
        _validate_axis(self.axis)
        if not isinstance(self.step, str) or not self.step.strip():
            raise SongPlanError(f"step must be a non-empty string, got {self.step!r}")
        if self.section_index is not None:
            _validate_int("section_index", self.section_index, minimum=1)
        if not isinstance(self.confirmed, bool):
            raise SongPlanError(f"confirmed must be bool, got {self.confirmed!r}")
        if not isinstance(self.source, str) or not self.source.strip():
            raise SongPlanError(f"source must be a non-empty string, got {self.source!r}")

    @classmethod
    def from_audit_record(
        cls,
        record: object,
        *,
        axis: DecisionAxis,
        section_index: int | None = None,
    ) -> DirectorDecision:
        choice = getattr(record, "choice", None)
        choice_label = getattr(choice, "label", None)
        return cls(
            step=record.step,
            axis=axis,
            value=record.value,
            confirmed=record.confirmed,
            source=record.source,
            section_index=section_index,
            free_text=getattr(record, "free_text", None),
            choice_label=choice_label if isinstance(choice_label, str) else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "step": self.step,
            "axis": self.axis,
            "section_index": self.section_index,
            "value": _jsonable(self.value),
            "confirmed": self.confirmed,
            "source": self.source,
            "free_text": self.free_text,
            "choice_label": self.choice_label,
        }


@dataclass(frozen=True)
class ApprovalState:
    status: ApprovalStatus = APPROVAL_DRAFT
    reviewer: str | None = None
    decided_at: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _APPROVAL_STATUSES:
            raise SongPlanError(f"approval status must be one of {sorted(_APPROVAL_STATUSES)}")
        if self.status == APPROVAL_APPROVED and not self.reviewer:
            raise SongPlanError("approved plans must record a reviewer")
        if self.status == APPROVAL_REJECTED and not self.reason:
            raise SongPlanError("rejected plans must record a reason")

    @classmethod
    def draft(cls) -> ApprovalState:
        return cls(status=APPROVAL_DRAFT)

    @classmethod
    def pending(cls, *, reviewer: str | None = None) -> ApprovalState:
        return cls(status=APPROVAL_PENDING, reviewer=reviewer)

    @classmethod
    def approved(cls, *, reviewer: str, decided_at: str | None = None) -> ApprovalState:
        return cls(status=APPROVAL_APPROVED, reviewer=reviewer, decided_at=decided_at)

    @classmethod
    def rejected(
        cls, *, reviewer: str | None = None, decided_at: str | None = None, reason: str
    ) -> ApprovalState:
        return cls(
            status=APPROVAL_REJECTED,
            reviewer=reviewer,
            decided_at=decided_at,
            reason=reason,
        )

    @property
    def is_approved(self) -> bool:
        return self.status == APPROVAL_APPROVED

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at,
            "reason": self.reason,
            "is_approved": self.is_approved,
        }


@dataclass(frozen=True)
class CueTimingPayload:
    mode: TimingMode
    start_ms: int
    manual_go: bool
    trig_time_seconds: float | None = None
    timecode_number: int | None = None

    def __post_init__(self) -> None:
        if self.mode not in _TIMING_MODES:
            raise SongPlanError(f"timing mode must be one of {sorted(_TIMING_MODES)}")
        _validate_int("start_ms", self.start_ms, minimum=0)
        if not isinstance(self.manual_go, bool):
            raise SongPlanError(f"manual_go must be bool, got {self.manual_go!r}")
        if self.manual_go != (self.mode == MANUAL_GO):
            raise SongPlanError("manual_go must match the timing mode")
        if self.trig_time_seconds is not None and not isinstance(
            self.trig_time_seconds, int | float
        ):
            raise SongPlanError(
                f"trig_time_seconds must be numeric or None, got {self.trig_time_seconds!r}"
            )
        if self.mode == MANUAL_GO and self.trig_time_seconds is not None:
            raise SongPlanError("manual_go timing cannot carry TrigTime seconds")
        if self.mode in (TRIG_TIME, TIMECODE) and self.trig_time_seconds is None:
            raise SongPlanError("TrigTime and Timecode timing require TrigTime seconds")
        if self.mode != TIMECODE and self.timecode_number is not None:
            raise SongPlanError("timecode_number is only valid for timecode timing")
        if self.mode == TIMECODE and self.timecode_number is None:
            raise SongPlanError("timecode timing requires timecode_number")
        if self.timecode_number is not None:
            _validate_int("timecode_number", self.timecode_number, minimum=1)

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "start_ms": self.start_ms,
            "manual_go": self.manual_go,
            "trig_time_seconds": self.trig_time_seconds,
            "timecode_number": self.timecode_number,
        }


@dataclass(frozen=True)
class CuePayload:
    section_index: int
    cue_number: int
    cue_name: str
    d_level: int
    palette: tuple[str, ...]
    position: str
    texture: str
    fx: tuple[str, ...]
    accents: tuple[str, ...]
    timing: CueTimingPayload

    def __post_init__(self) -> None:
        _validate_int("section_index", self.section_index, minimum=1)
        _validate_int("cue_number", self.cue_number, minimum=1)
        if not isinstance(self.cue_name, str) or not self.cue_name.strip():
            raise SongPlanError(f"cue_name must be a non-empty string, got {self.cue_name!r}")
        _validate_int("d_level", self.d_level, minimum=1)
        if self.d_level > 5:
            raise SongPlanError(f"d_level must be 1-5, got {self.d_level!r}")
        object.__setattr__(self, "palette", _tuple_of_str("palette", self.palette))
        if not isinstance(self.position, str) or not self.position.strip():
            raise SongPlanError(f"position must be a non-empty string, got {self.position!r}")
        if not isinstance(self.texture, str) or not self.texture.strip():
            raise SongPlanError(f"texture must be a non-empty string, got {self.texture!r}")
        object.__setattr__(self, "fx", _tuple_of_str("fx", self.fx))
        object.__setattr__(self, "accents", _tuple_of_str("accents", self.accents))
        if not isinstance(self.timing, CueTimingPayload):
            raise SongPlanError("timing must be a CueTimingPayload")

    def to_dict(self) -> dict[str, object]:
        return {
            "section_index": self.section_index,
            "cue_number": self.cue_number,
            "cue_name": self.cue_name,
            "d_level": self.d_level,
            "palette": list(self.palette),
            "position": self.position,
            "texture": self.texture,
            "fx": list(self.fx),
            "accents": list(self.accents),
            "timing": self.timing.to_dict(),
        }


@dataclass(frozen=True)
class UnifiedSongLightingPlan:
    song_title: str
    sections: tuple[SectionDecision, ...]
    timing: TimingPlan
    music_profile: MusicProfile
    rig_profile: RigProfile
    approval: ApprovalState = dataclasses.field(default_factory=ApprovalState.draft)
    director_decisions: tuple[DirectorDecision, ...] = ()
    unresolved: tuple[UnresolvedNote, ...] = ()
    disabled: tuple[DisabledNote, ...] = ()
    sequence_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.song_title, str) or not self.song_title.strip():
            raise SongPlanError(f"song_title must be a non-empty string, got {self.song_title!r}")
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "director_decisions", tuple(self.director_decisions))
        object.__setattr__(self, "unresolved", tuple(self.unresolved))
        object.__setattr__(self, "disabled", tuple(self.disabled))
        if not self.sections:
            raise SongPlanError("a song plan must contain at least one section")
        if not isinstance(self.timing, TimingPlan):
            raise SongPlanError("timing must be a TimingPlan")
        if not isinstance(self.approval, ApprovalState):
            raise SongPlanError("approval must be an ApprovalState")
        if not isinstance(self.music_profile, MusicProfile):
            raise SongPlanError("music_profile must be a MusicProfile")
        if not isinstance(self.rig_profile, RigProfile):
            raise SongPlanError("rig_profile must be a RigProfile")
        previous_start_ms = -1
        seen_indexes: set[int] = set()
        seen_cues: set[int] = set()
        for decision in self.sections:
            if not isinstance(decision, SectionDecision):
                raise SongPlanError("sections must contain only SectionDecision values")
            index = decision.section.index
            if index in seen_indexes:
                raise SongPlanError(f"duplicate section index {index}")
            seen_indexes.add(index)
            if decision.section.start_ms < previous_start_ms:
                raise SongPlanError("sections must be ordered by non-decreasing start_ms")
            previous_start_ms = decision.section.start_ms
            if decision.cue_number is not None:
                if decision.cue_number in seen_cues:
                    raise SongPlanError(f"duplicate cue number {decision.cue_number}")
                seen_cues.add(decision.cue_number)
        for decision in self.director_decisions:
            if not isinstance(decision, DirectorDecision):
                raise SongPlanError("director_decisions must contain DirectorDecision values")
        for note in self.unresolved:
            if not isinstance(note, UnresolvedNote):
                raise SongPlanError("unresolved must contain UnresolvedNote values")
        for note in self.disabled:
            if not isinstance(note, DisabledNote):
                raise SongPlanError("disabled must contain DisabledNote values")

    @property
    def has_unresolved(self) -> bool:
        return bool(self.unresolved)

    @property
    def has_unconfirmed_director_decisions(self) -> bool:
        return any(not decision.confirmed for decision in self.director_decisions)

    @property
    def ready_for_review(self) -> bool:
        return not self.has_unresolved

    @property
    def ready_for_commit(self) -> bool:
        return (
            self.approval.is_approved
            and not self.has_unresolved
            and not self.has_unconfirmed_director_decisions
        )

    def cue_payloads(self) -> tuple[CuePayload, ...]:
        return tuple(
            self._cue_payload(decision, fallback_cue_number=index)
            for index, decision in enumerate(self.sections, start=1)
        )

    def director_review_projection(self) -> dict[str, object]:
        return {
            "song_title": self.song_title,
            "sequence_name": self.sequence_name,
            "timing": self.timing.to_dict(),
            "approval": self.approval.to_dict(),
            "ready_for_review": self.ready_for_review,
            "ready_for_commit": self.ready_for_commit,
            "unresolved": [note.to_dict() for note in self.unresolved],
            "disabled": [note.to_dict() for note in self.disabled],
            "director_decisions": [decision.to_dict() for decision in self.director_decisions],
            "cue_payloads": [payload.to_dict() for payload in self.cue_payloads()],
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "song_title": self.song_title,
            "sequence_name": self.sequence_name,
            "music_profile": _jsonable(self.music_profile),
            "rig_profile": _jsonable(self.rig_profile),
            "sections": [section.to_dict() for section in self.sections],
            "timing": self.timing.to_dict(),
            "approval": self.approval.to_dict(),
            "unresolved": [note.to_dict() for note in self.unresolved],
            "disabled": [note.to_dict() for note in self.disabled],
            "director_decisions": [decision.to_dict() for decision in self.director_decisions],
            "cue_payloads": [payload.to_dict() for payload in self.cue_payloads()],
            "ready_for_review": self.ready_for_review,
            "ready_for_commit": self.ready_for_commit,
        }

    def _cue_payload(self, decision: SectionDecision, *, fallback_cue_number: int) -> CuePayload:
        section = decision.section
        timing_payload = CueTimingPayload(
            mode=self.timing.mode,
            start_ms=section.start_ms,
            manual_go=self.timing.mode == MANUAL_GO,
            trig_time_seconds=section.start_seconds if self.timing.uses_trig_time else None,
            timecode_number=self.timing.timecode_number if self.timing.uses_timecode else None,
        )
        return CuePayload(
            section_index=section.index,
            cue_number=decision.cue_number or fallback_cue_number,
            cue_name=section.label,
            d_level=decision.d.level,
            palette=decision.palette.colors,
            position=decision.position.preset,
            texture=decision.texture.label,
            fx=decision.fx.allowed,
            accents=decision.accent.accents,
            timing=timing_payload,
        )
