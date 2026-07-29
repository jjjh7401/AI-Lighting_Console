from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.looks.busking import looks_for_genre
from server.looks.matching import DYNAMICS_TERMS, resolve_dynamics
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
