from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.looks.busking import VALUE_LINE_COLLISION, looks_for_genre
from server.looks.instantiate import _values_line
from server.looks.matching import DYNAMICS_TERMS, resolve_dynamics
from server.looks.resolver import GroupCandidate, UnmappedRole, resolve_roles
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN, Look, LookLibrary

_MILLISECONDS_PER_SECOND = Decimal("1000")
_SECONDS_PER_MINUTE = Decimal("60")
_MILLISECONDS_PER_MINUTE = 60_000
_MMSS_PATTERN = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})(?P<fraction>\.\d{1,3})?$")
_SECONDS_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
_NAME_KEYS = ("name", "section", "label")
_START_KEYS = ("start", "start_time", "time")
EXPLICIT_DYNAMICS_REQUIRED = "explicit_dynamics_required"
UNMAPPED_LOOK = "unmapped_look"
SEQUENCE_UNAVAILABLE = "sequence_unavailable"
SEQUENCE_TRUNCATED = "sequence_truncated"
SEQUENCE_NUMBER_UNAVAILABLE = "sequence_number_unavailable"
EMPTY_SECTIONS = "empty_sections"
ROLE_UNMAPPED = "role_unmapped"
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_IMPLICIT_SYSTEM_CUE_COUNT = 2
TIMECODE_DESCOPE = "timecode_descope"
AUTO_ADVANCE_DESCOPE = "auto_advance_descope"
TRIGGER_TYPE_TIME = "Time"


@dataclass(frozen=True)
class SongCueSection:
    name: str
    start_ms: int
    index: int
    dynamics: tuple[int, ...] | None
    requires_explicit_dynamics: bool


@dataclass(frozen=True)
class SongCueLookSelection:
    section: SongCueSection
    requested_dynamics: tuple[int, ...]
    look: Look | None = None
    reason: str | None = None


@dataclass(frozen=True)
class SongCueSkippedSection:
    section: SongCueSection
    cue_number: int
    reason: str
    detail: str = ""
    collides_with_section_index: int | None = None
    collides_with_cue_number: int | None = None


@dataclass(frozen=True)
class SongCueSectionBundle:
    section: SongCueSection
    cue_number: int
    cue_name: str
    selection: SongCueLookSelection
    commands: tuple[str, ...] = ()
    skipped: tuple[SongCueSkippedSection, ...] = ()
    unmapped: tuple[UnmappedRole, ...] = ()
    bound: Mapping[str, tuple[GroupCandidate, ...]] | None = None


@dataclass(frozen=True)
class SongCueBundle:
    song_title: str
    sequence_number: int
    sequence_name: str
    commands: tuple[str, ...]
    sections: tuple[SongCueSectionBundle, ...]
    is_error: bool = False
    reason: str | None = None

    @property
    def skipped(self) -> tuple[SongCueSkippedSection, ...]:
        return tuple(skipped for section in self.sections for skipped in section.skipped)

    @property
    def stored_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.commands)


@dataclass(frozen=True)
class SongCueTimingAxes:
    timecode_go: bool = True
    auto_advance_go: bool = True
    timecode_skip_reason: str = "ASSUMPTION-20 is GO in M4; DESCOPE branch retained for future rerun"
    auto_advance_skip_reason: str = "ASSUMPTION-22 is GO in M4; DESCOPE branch retained for future rerun"


@dataclass(frozen=True)
class SongCueTimingSkip:
    axis: str
    reason: str


@dataclass(frozen=True)
class SongCueTimingPlan:
    commands: tuple[str, ...]
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped_axes: tuple[SongCueTimingSkip, ...] = ()


class SectionTimeError(ValueError):
    def __init__(
        self,
        *,
        index: int,
        reason: str,
        previous_start_ms: int | None,
        start_ms: int,
        sections: Sequence[SongCueSection],
    ) -> None:
        self.index = index
        self.reason = reason
        self.previous_start_ms = previous_start_ms
        self.start_ms = start_ms
        self.sections = tuple(sections)
        super().__init__(
            f"section index {index} {reason}: start_ms={start_ms}, "
            f"previous_start_ms={previous_start_ms}"
        )


class SequenceNumberError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SongCueBundleError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class _RawSection(NamedTuple):
    name: str
    start: object


def normalise_start_ms(raw: object) -> int:
    if isinstance(raw, str):
        value = raw.strip()
        match = _MMSS_PATTERN.fullmatch(value)
        if match is not None:
            minutes = int(match.group("minutes"))
            seconds = Decimal(match.group("seconds") + (match.group("fraction") or ""))
            if seconds >= _SECONDS_PER_MINUTE:
                raise ValueError(f"section seconds out of range: {raw!r}")
            return (minutes * _MILLISECONDS_PER_MINUTE) + _seconds_to_milliseconds(seconds)
        if _SECONDS_PATTERN.fullmatch(value):
            return _seconds_to_milliseconds(_decimal_from(value, raw))
        raise ValueError(f"unsupported section time format: {raw!r}")

    if isinstance(raw, bool):
        raise ValueError(f"unsupported section time format: {raw!r}")
    if isinstance(raw, int | float | Decimal):
        return _seconds_to_milliseconds(_decimal_from(str(raw), raw))

    raise ValueError(f"unsupported section time format: {raw!r}")


def parse_sections(raw_sections: Iterable[Mapping[str, object] | Sequence[object]]) -> tuple[SongCueSection, ...]:
    sections = tuple(_parse_section(raw, index) for index, raw in enumerate(raw_sections))
    previous: SongCueSection | None = None
    for section in sections:
        if previous is not None:
            if section.start_ms < previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="starts_before_previous",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
            if section.start_ms == previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="duplicates_previous_start",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
        previous = section
    return sections


def map_sections_to_looks(
    sections: Iterable[SongCueSection],
    library: LookLibrary,
    genre: str,
    explicit_dynamics: Mapping[int, int] | None = None,
) -> tuple[SongCueLookSelection, ...]:
    ordered_looks = looks_for_genre(library, genre)
    return tuple(
        _map_section_to_look(
            section=section,
            ordered_looks=ordered_looks,
            explicit_dynamics=_explicit_dynamics_for(section, explicit_dynamics),
        )
        for section in sections
    )


def build_songcue_bundle(
    song_title: str,
    selections: Iterable[SongCueLookSelection],
    *,
    sequences_section: Mapping[str, object],
    groups_section: Mapping[str, object],
) -> SongCueBundle:
    ordered = tuple(selections)
    if not ordered:
        raise SongCueBundleError(EMPTY_SECTIONS)

    sequence_number = select_sequence_number(sequences_section)
    sequence_name = _ascii_label(song_title, fallback=f"Song {sequence_number}")
    resolution = resolve_roles(groups_section)
    cue_names = _cue_names(tuple(selection.section for selection in ordered))
    commands: list[str] = [_DESTINATION]
    section_bundles: list[SongCueSectionBundle] = []
    emitted: dict[str, tuple[int, int, str]] = dict()
    sequence_labelled = False
    cue_number = 0
    for selection, cue_name in zip(ordered, cue_names, strict=True):
        cue_number += 1
        section_bundle = _section_bundle(
            selection=selection,
            cue_number=cue_number,
            cue_name=cue_name,
            sequence_number=sequence_number,
            resolution=resolution,
            emitted=emitted,
        )
        if section_bundle.commands:
            commands.extend(section_bundle.commands)
            if not sequence_labelled:
                store_index = _first_store_index(commands, sequence_number, cue_number)
                commands.insert(store_index + 1, f"Label Sequence {sequence_number} '{sequence_name}'")
                section_bundle = replace(section_bundle, commands=tuple(commands[-len(section_bundle.commands) - 1 :]))
                sequence_labelled = True
        section_bundles.append(section_bundle)

    stored_commands = tuple(commands) if len(commands) > 1 else ()
    return SongCueBundle(
        song_title=song_title,
        sequence_number=sequence_number,
        sequence_name=sequence_name,
        commands=stored_commands,
        sections=tuple(section_bundles),
    )


def render_songcue_report(bundle: SongCueBundle) -> str:
    parts = [bundle.song_title, bundle.sequence_name]
    parts.extend(section.section.name for section in bundle.sections)
    parts.extend(skipped.detail for skipped in bundle.skipped)
    return "\n".join(part for part in parts if part)


def select_sequence_number(sequences_section: Mapping[str, object]) -> int:
    unavailable = sequences_section.get("reason")
    if isinstance(unavailable, str) or sequences_section.get("ok") is False:
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    if sequences_section.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    occupied = _sequence_numbers(sequences_section)
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


def observed_user_cue_count(sequence_payload: Mapping[str, object]) -> int:
    if sequence_payload.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    node = sequence_payload.get("node")
    child_count = node.get("childCount") if isinstance(node, Mapping) else None
    if not isinstance(child_count, int):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    return max(0, child_count - _IMPLICIT_SYSTEM_CUE_COUNT)


def build_songcue_timing(
    bundle: SongCueBundle,
    *,
    timecode_number: int,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan:
    if isinstance(timecode_number, bool) or timecode_number < 1:
        raise ValueError(f"timecode_number must be positive: {timecode_number!r}")
    selected_axes = axes or SongCueTimingAxes()
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped: list[SongCueTimingSkip] = []
    if selected_axes.timecode_go:
        timecode_commands = _timecode_commands(bundle, timecode_number)
    else:
        skipped.append(SongCueTimingSkip(axis=TIMECODE_DESCOPE, reason=selected_axes.timecode_skip_reason))
    if selected_axes.auto_advance_go:
        auto_advance_commands = _auto_advance_commands(bundle)
    else:
        skipped.append(
            SongCueTimingSkip(axis=AUTO_ADVANCE_DESCOPE, reason=selected_axes.auto_advance_skip_reason)
        )
    return SongCueTimingPlan(
        commands=timecode_commands + auto_advance_commands,
        timecode_commands=timecode_commands,
        auto_advance_commands=auto_advance_commands,
        skipped_axes=tuple(skipped),
    )


def _parse_section(raw: Mapping[str, object] | Sequence[object], index: int) -> SongCueSection:
    section = _raw_section(raw)
    name = section.name.strip()
    if not name:
        raise ValueError(f"section index {index} has an empty name")
    dynamics = _section_dynamics(name)
    return SongCueSection(
        name=name,
        start_ms=normalise_start_ms(section.start),
        index=index,
        dynamics=dynamics,
        requires_explicit_dynamics=dynamics is None,
    )


def _map_section_to_look(
    *,
    section: SongCueSection,
    ordered_looks: Sequence[Look],
    explicit_dynamics: int | None,
) -> SongCueLookSelection:
    if explicit_dynamics is not None:
        requested_dynamics = (_validated_dynamics(explicit_dynamics, section.index),)
    elif section.dynamics is None:
        return SongCueLookSelection(section=section, requested_dynamics=(), reason=EXPLICIT_DYNAMICS_REQUIRED)
    else:
        requested_dynamics = section.dynamics

    for look in ordered_looks:
        if look.dynamics in requested_dynamics:
            return SongCueLookSelection(section=section, requested_dynamics=requested_dynamics, look=look)
    return SongCueLookSelection(section=section, requested_dynamics=requested_dynamics, reason=UNMAPPED_LOOK)


def _section_bundle(
    *,
    selection: SongCueLookSelection,
    cue_number: int,
    cue_name: str,
    sequence_number: int,
    resolution,
    emitted: dict[str, tuple[int, int, str]],
) -> SongCueSectionBundle:
    if selection.look is None:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=selection.reason or UNMAPPED_LOOK,
            detail=selection.reason or UNMAPPED_LOOK,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
        )

    look = selection.look
    bound: dict[str, tuple[GroupCandidate, ...]] = dict()
    unmapped: list[UnmappedRole] = []
    for role in look.roles:
        candidates = resolution.groups_for(role)
        if candidates:
            bound[role] = candidates
            continue
        entry = resolution.unmapped_for(role)
        if entry is not None:
            unmapped.append(entry)
    groups = _selected_groups(bound)
    if not groups:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=ROLE_UNMAPPED,
            detail="; ".join(entry.reason for entry in unmapped),
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            unmapped=tuple(unmapped),
            bound=bound,
        )

    values = _values_line(look.attributes)
    previous = emitted.get(values)
    if previous is not None:
        previous_section, previous_cue, previous_look = previous
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=VALUE_LINE_COLLISION,
            detail=f"value line matches section {previous_section} cue {previous_cue} look {previous_look}",
            collides_with_section_index=previous_section,
            collides_with_cue_number=previous_cue,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            bound=bound,
        )
    emitted[values] = (selection.section.index, cue_number, look.look_id)
    commands = (
        _CLEAR,
        _selection_line(groups),
        values,
        f"Store Sequence {sequence_number} Cue {cue_number} '{cue_name}'",
        _CLEAR,
    )
    return SongCueSectionBundle(
        section=selection.section,
        cue_number=cue_number,
        cue_name=cue_name,
        selection=selection,
        commands=commands,
        bound=bound,
    )


def _timecode_commands(bundle: SongCueBundle, timecode_number: int) -> tuple[str, ...]:
    timecode_name = _ascii_label(f"{bundle.sequence_name} Timecode", fallback=f"Timecode {timecode_number}")
    return (
        f"Store Timecode {timecode_number}",
        f"Set Timecode {timecode_number} Property 'Name' '{timecode_name}'",
        f"Assign Sequence {bundle.sequence_number} At Timecode {timecode_number}",
    )


def _auto_advance_commands(bundle: SongCueBundle) -> tuple[str, ...]:
    commands: list[str] = []
    for section in bundle.stored_sections:
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigType' '{TRIGGER_TYPE_TIME}'"
        )
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigTime' {_format_seconds(section.section.start_ms)}"
        )
    return tuple(commands)


def _format_seconds(start_ms: int) -> str:
    seconds = Decimal(start_ms) / _MILLISECONDS_PER_SECOND
    if seconds == seconds.to_integral_value():
        return str(int(seconds))
    return format(seconds.normalize(), "f")


def _selected_groups(bound: Mapping[str, tuple[GroupCandidate, ...]]) -> tuple[GroupCandidate, ...]:
    selected = sorted({group.number: group for groups in bound.values() for group in groups}.items())
    return tuple(group for _number, group in selected)


def _selection_line(groups: Sequence[GroupCandidate]) -> str:
    return "Group " + " + ".join(str(group.number) for group in groups)


def _first_store_index(commands: Sequence[str], sequence_number: int, cue_number: int) -> int:
    prefix = f"Store Sequence {sequence_number} Cue {cue_number} "
    for index, command in enumerate(commands):
        if command.startswith(prefix):
            return index
    raise SongCueBundleError(SEQUENCE_UNAVAILABLE)


def _sequence_numbers(sequences_section: Mapping[str, object]) -> set[int]:
    listed = sequences_section.get("objects")
    if not isinstance(listed, list):
        listed = sequences_section.get("children")
    if not isinstance(listed, list):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    occupied: set[int] = set()
    for entry in listed:
        if not isinstance(entry, Mapping):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        number = entry.get("no", entry.get("i"))
        if not isinstance(number, int):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        occupied.add(number)
    return occupied


def _cue_names(sections: Sequence[SongCueSection]) -> tuple[str, ...]:
    totals: dict[str, int] = dict()
    for section in sections:
        totals[section.name] = totals.get(section.name, 0) + 1
    seen: dict[str, int] = dict()
    names: list[str] = []
    for section in sections:
        seen[section.name] = seen.get(section.name, 0) + 1
        fallback = f"Section {section.index + 1}"
        base = _ascii_label(section.name, fallback=fallback)
        if totals[section.name] > 1:
            base = f"{base} {seen[section.name]}"
        names.append(base)
    return tuple(names)


def _ascii_label(value: str, *, fallback: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^0-9A-Za-z _.-]+", " ", ascii_text.replace("'", " "))
    label = " ".join(cleaned.split())
    return label or fallback


def _explicit_dynamics_for(section: SongCueSection, explicit_dynamics: Mapping[int, int] | None) -> int | None:
    if explicit_dynamics is None:
        return None
    return explicit_dynamics.get(section.index)


def _validated_dynamics(value: int, index: int) -> int:
    if isinstance(value, bool) or value < DYNAMICS_MIN or value > DYNAMICS_MAX:
        raise ValueError(
            f"section index {index} explicit dynamics must be "
            f"between {DYNAMICS_MIN} and {DYNAMICS_MAX}: {value!r}"
        )
    return value


def _raw_section(raw: Mapping[str, object] | Sequence[object]) -> _RawSection:
    if isinstance(raw, Mapping):
        return _RawSection(name=str(_first_present(raw, _NAME_KEYS)), start=_first_present(raw, _START_KEYS))
    if isinstance(raw, str):
        raise ValueError("section entries must provide both name and start time")
    if len(raw) != 2:
        raise ValueError("section entries must provide exactly two values")
    name, start = raw
    return _RawSection(name=str(name), start=start)


def _first_present(values: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        if key in values:
            return values[key]
    raise ValueError(f"section entry is missing one of {keys!r}")


def _section_dynamics(name: str) -> tuple[int, ...] | None:
    if not DYNAMICS_TERMS:
        raise RuntimeError("matching dynamics vocabulary is empty")
    return resolve_dynamics(name)


def _decimal_from(value: str, raw: object) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"unsupported section time format: {raw!r}") from exc


def _seconds_to_milliseconds(seconds: Decimal) -> int:
    if seconds < 0:
        raise ValueError(f"section time must be non-negative: {seconds}")
    milliseconds = seconds * _MILLISECONDS_PER_SECOND
    if milliseconds != milliseconds.to_integral_value():
        raise ValueError(f"section time must resolve to a whole millisecond: {seconds}")
    return int(milliseconds)
