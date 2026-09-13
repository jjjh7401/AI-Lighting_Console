from __future__ import annotations

import inspect
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
    plan_prepare_songcue_timing,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

_TIMECODE_COMMANDS = (
    re.compile(r"^Store Timecode \d+$"),
    re.compile(r"^Set Timecode \d+ Property 'Name' '[ -~]+'$"),
    re.compile(r"^Assign Sequence \d+ At Timecode \d+$"),
)
_TRIG_TYPE_RE = re.compile(r"^Set Cue \d+ Sequence \d+ Property 'TrigType' 'Time'$")
_TRIG_TIME_RE = re.compile(
    r"^Set Cue (?P<cue>\d+) Sequence (?P<sequence>\d+) Property 'TrigTime' (?P<time>\d+(?:\.\d+)?)$"
)


class TestBundleAloneCarriesNoTiming:
    """카드 t380 — 현장 스크립트가 반복한 그 착시를 회귀로 고정한다.

    `reports/onsite-round-20260912/{diag,real_song_cues}.py` 는 둘 다
    `build_songcue_bundle(...)` 만 부르고 `build_songcue_timing` 은 부르지
    않았다. 그 결과 발사된 90줄에 `Timecode`/`TrigTime`/`Follow` 가 0건이었고,
    이것이 "곡이 리듬에 안 맞는다" 관측의 진짜 원인이었다 — 자동 진행 기능이
    없어서가 아니라, 그 기능을 켜는 별도 호출을 진단 스크립트가 하지 않아서다.

    `build_songcue_bundle` 혼자서는 타이밍 축을 절대 안 낸다는 것을,
    그리고 `build_songcue_timing` 과 합치면 저장된 큐마다 정확히 한 쌍씩
    나온다는 것을 여기서 기계로 고정한다 — 다음에 같은 착시가 재발하지
    않도록.
    """

    def test_bundle_commands_alone_have_zero_sync_lines(self):
        bundle = _bundle()

        assert not _commands_matching(bundle.commands, r"Timecode|TrigTime|TrigType|Follow")

    def test_combining_with_build_songcue_timing_yields_one_pair_per_stored_cue(self):
        bundle = _bundle()
        timing = build_songcue_timing(bundle, timecode_number=7)
        combined = bundle.commands + timing.commands

        trig_type_lines = _commands_matching(combined, r"Property 'TrigType' 'Time'$")
        trig_time_lines = _commands_matching(combined, r"Property 'TrigTime' ")

        assert len(trig_type_lines) == len(bundle.stored_sections)
        assert len(trig_time_lines) == len(bundle.stored_sections)


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
    assert all(
        _TRIG_TYPE_RE.fullmatch(command) or _TRIG_TIME_RE.fullmatch(command)
        for command in plan.auto_advance_commands
    )
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


def test_prepare_songcue_timing_plan_preserves_existing_command_formation():
    bundle = _bundle()
    request = {
        "song_title": "테스트 곡",
        "genre": "록",
        "timecode_number": 7,
        "sections": [{"name": "Chorus", "start": "0:10"}],
    }

    plan = plan_prepare_songcue_timing(bundle, request)

    assert plan == build_songcue_timing(bundle, timecode_number=7)
    assert plan.timecode_commands == (
        "Store Timecode 7",
        f"Set Timecode 7 Property 'Name' '{bundle.sequence_name} Timecode'",
        f"Assign Sequence {bundle.sequence_number} At Timecode 7",
    )
    assert plan.auto_advance_commands == (
        f"Set Cue 1 Sequence {bundle.sequence_number} Property 'TrigType' 'Time'",
        f"Set Cue 1 Sequence {bundle.sequence_number} Property 'TrigTime' 10",
        f"Set Cue 2 Sequence {bundle.sequence_number} Property 'TrigType' 'Time'",
        f"Set Cue 2 Sequence {bundle.sequence_number} Property 'TrigTime' 14",
    )


@pytest.mark.parametrize(
    "request_payload",
    (
        {},
        {"timecode": 7},
        {"timecode_number": 0},
        {"timecode_number": True},
        {"timecode_number": "7"},
        {"timecode_number": 7.0},
    ),
)
def test_prepare_songcue_timing_plan_rejects_non_prepare_songcue_timecode_grammar(
    request_payload,
):
    with pytest.raises(
        ValueError,
        match=re.escape("'timecode_number' must be a positive integer"),
    ):
        plan_prepare_songcue_timing(_bundle(), request_payload)


def test_prepare_songcue_timing_plan_has_no_console_io_surface():
    parameters = set(inspect.signature(plan_prepare_songcue_timing).parameters)

    assert parameters == {"bundle", "request", "axes"}


@pytest.mark.skip(reason="ASSUMPTION-20 is GO in M4; DESCOPE branch retained for a future rerun")
def test_axis1_timecode_descope_branch_retains_required_reason():
    bundle = _bundle()
    plan = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=True),
    )

    assert plan.timecode_commands == ()
    assert any(
        skip.axis == TIMECODE_DESCOPE and "ASSUMPTION-20" in skip.reason
        for skip in plan.skipped_axes
    )


@pytest.mark.skip(reason="ASSUMPTION-22 is GO in M4; DESCOPE branch retained for a future rerun")
def test_axis2_auto_advance_descope_branch_retains_required_reason():
    bundle = _bundle()
    plan = build_songcue_timing(
        bundle,
        timecode_number=7,
        axes=SongCueTimingAxes(timecode_go=True, auto_advance_go=False),
    )

    assert plan.auto_advance_commands == ()
    assert any(
        skip.axis == AUTO_ADVANCE_DESCOPE and "ASSUMPTION-22" in skip.reason
        for skip in plan.skipped_axes
    )


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
    return [
        match.group("time") for command in commands if (match := _TRIG_TIME_RE.fullmatch(command))
    ]


def _skip_axes(plan) -> set[str]:
    return {skip.axis for skip in plan.skipped_axes}
