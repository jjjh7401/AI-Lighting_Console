from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.looks.matching import DYNAMICS_TERMS, resolve_dynamics

_MILLISECONDS_PER_SECOND = Decimal("1000")
_SECONDS_PER_MINUTE = Decimal("60")
_MILLISECONDS_PER_MINUTE = 60_000
_MMSS_PATTERN = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})(?P<fraction>\.\d{1,3})?$")
_SECONDS_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
_NAME_KEYS = ("name", "section", "label")
_START_KEYS = ("start", "start_time", "time")


@dataclass(frozen=True)
class SongCueSection:
    name: str
    start_ms: int
    index: int
    dynamics: tuple[int, ...] | None
    requires_explicit_dynamics: bool


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
