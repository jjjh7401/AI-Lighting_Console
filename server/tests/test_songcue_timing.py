from __future__ import annotations

import re

import pytest

from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    AUTO_ADVANCE_DESCOPE,
    TIMECODE_DESCOPE,
    SongCueLookSelection,
    SongCueTimingAxes,
    build_songcue_bundle,
    build_songcue_timing,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

_TIMECODE_COMMANDS = (
    re.compile(r"^Store Timecode \d+$"),
    re.compile(r"^Set Timecode \d+ Property 'Name' '[ -~]+'$"),
    re.compile(r"^Assign Sequence \d+ At Timecode \d+$"),
)
_TRIG_TYPE_RE = re.compile(r"^Set Cue \d+ Sequence \d+ Property 'TrigType' 'Time'$")
_TRIG_TIME_RE = re.compile(r"^Set Cue (?P<cue>\d+) Sequence (?P<sequence>\d+) Property 'TrigTime' (?P<time>\d+(?:\.\d+)?)$")


def test_axis1_timecode_go_emits_only_measured_command_forms():
    bundle = _bundle()
    plan = build_songcue_timing(bundle, timecode_number=7)

    assert plan.timecode_commands == (
        "Store Timecode 7",
        f"Set Timecode 7 Property 'Name' '{bundle.sequence_name} Timecode'",
        f"Assign Sequence {bundle.sequence_number} At Timecode 7",
    )
    assert plan.timecode_commands
    assert all(command.isascii() for command in plan.timecode_commands)
    assert all(
        any(pattern.fullmatch(command) for pattern in _TIMECODE_COMMANDS)
        for command in plan.timecode_commands
    )
    assert _commands_matching(plan.commands, r"\bTimecode\b") == list(plan.timecode_commands)


def test_axis2_auto_advance_go_uses_time_token_and_absolute_section_starts():
    bundle = _bundle()
    plan = build_songcue_timing(bundle, timecode_number=7)

    assert plan.auto_advance_commands == (
        f"Set Cue 1 Sequence {bundle.sequence_number} Property 'TrigType' 'Time'",
        f"Set Cue 1 Sequence {bundle.sequence_number} Property 'TrigTime' 10",
        f"Set Cue 2 Sequence {bundle.sequence_number} Property 'TrigType' 'Time'",
        f"Set Cue 2 Sequence {bundle.sequence_number} Property 'TrigTime' 14",
    )
    assert plan.auto_advance_commands
    assert all(_TRIG_TYPE_RE.fullmatch(command) or _TRIG_TIME_RE.fullmatch(command) for command in plan.auto_advance_commands)
    assert _trig_times(plan.auto_advance_commands) == ["10", "14"]
    assert _commands_matching(plan.auto_advance_commands, r"\b(Follow|Sound|BPM|Go)\b") == []
    assert _commands_matching(plan.auto_advance_commands, r"/trig\s*=") == []


def test_disabled_auto_axis_has_zero_trigger_commands_in_false_false_and_mixed():
    bundle = _bundle()
    disabled = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=False),
    )
    mixed = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=True, auto_advance_go=False),
    )

    assert disabled.auto_advance_commands == ()
    assert mixed.auto_advance_commands == ()
    assert mixed.timecode_commands
    assert _commands_matching(disabled.commands, r"Property 'Trig(?:Type|Time)'") == []
    assert _commands_matching(mixed.commands, r"Property 'Trig(?:Type|Time)'") == []
    assert _skip_axes(disabled) == {TIMECODE_DESCOPE, AUTO_ADVANCE_DESCOPE}
    assert AUTO_ADVANCE_DESCOPE in _skip_axes(mixed)


def test_disabled_timecode_axis_keeps_auto_advance_go_independent():
    bundle = _bundle()
    plan = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=True),
    )

    assert plan.timecode_commands == ()
    assert plan.auto_advance_commands
    assert _commands_matching(plan.commands, r"\bTimecode\b") == []
    assert _trig_times(plan.auto_advance_commands) == ["10", "14"]
    assert _skip_axes(plan) == {TIMECODE_DESCOPE}


@pytest.mark.skip(reason="ASSUMPTION-20 is GO in M4; DESCOPE branch retained for a future rerun")
def test_axis1_timecode_descope_branch_retains_required_reason():
    bundle = _bundle()
    plan = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=True),
    )

    assert plan.timecode_commands == ()
    assert any(skip.axis == TIMECODE_DESCOPE and "ASSUMPTION-20" in skip.reason for skip in plan.skipped_axes)


@pytest.mark.skip(reason="ASSUMPTION-22 is GO in M4; DESCOPE branch retained for a future rerun")
def test_axis2_auto_advance_descope_branch_retains_required_reason():
    bundle = _bundle()
    plan = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=True, auto_advance_go=False),
    )

    assert plan.auto_advance_commands == ()
    assert any(skip.axis == AUTO_ADVANCE_DESCOPE and "ASSUMPTION-22" in skip.reason for skip in plan.skipped_axes)


def _bundle():
    sections = parse_sections((("Chorus", "0:10"), ("Drop", "0:14")))
    selections = tuple(
        SongCueLookSelection(
            section=section,
            requested_dynamics=(look.dynamics,),
            look=look,
        )
        for section, look in zip(
            sections,
            (_look("chorus", dynamics=4, value=70), _look("drop", dynamics=5, value=90)),
            strict=True,
        )
    )
    return build_songcue_bundle(
        "테스트 곡",
        selections,
        sequences_section=_sequences(1, 2, 4),
        groups_section=_groups(*FULL_RIG),
    )


def _look(look_id: str, *, dynamics: int, value: float) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="rock",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(AttributeValue("Dimmer", value),),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _commands_matching(commands: tuple[str, ...], pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [command for command in commands if regex.search(command)]


def _trig_times(commands: tuple[str, ...]) -> list[str]:
    return [match.group("time") for command in commands if (match := _TRIG_TIME_RE.fullmatch(command))]


def _skip_axes(plan) -> set[str]:
    return {skip.axis for skip in plan.skipped_axes}
