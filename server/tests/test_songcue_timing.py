from __future__ import annotations

import re

import pytest

from server.looks.songcue import (
    AUTO_ADVANCE_DESCOPE,
    TIMECODE_DESCOPE,
    SongCueBundle,
    SongCueLookSelection,
    SongCueSectionBundle,
    SongCueTimingAxes,
    build_songcue_timing,
    parse_sections,
)

# 카드 t480 D3 — 룩 라이브러리 조립기(``build_songcue_bundle``)가 은퇴했다. 이 파일이
# 지키는 것은 **타이밍 명령 생성**(``build_songcue_timing``, 대화 길·업로드 길이 함께
# 쓴다)이므로 시험 재료를 조립기 대신 손으로 만든 번들로 바꿨다(``_bundle``). 은퇴한
# 두 부분 — 「조립기 번들 혼자서는 타이밍이 없다」와 ``plan_prepare_songcue_timing``
# (생산 호출처 0) — 의 시험은 뺐다.

_TIMECODE_COMMANDS = (
    re.compile(r"^Store Timecode \d+$"),
    re.compile(r"^Set Timecode \d+ Property 'Name' '[ -~]+'$"),
    re.compile(r"^Assign Sequence \d+ At Timecode \d+$"),
)
_TRIG_TYPE_RE = re.compile(r"^Set Cue \d+ Sequence \d+ Property 'TrigType' 'Time'$")
_TRIG_TIME_RE = re.compile(
    r"^Set Cue (?P<cue>\d+) Sequence (?P<sequence>\d+) Property 'TrigTime' (?P<time>\d+(?:\.\d+)?)$"
)


class TestTimingPairsPerStoredCue:
    """카드 t380 — ``build_songcue_timing`` 은 저장된 큐마다 정확히 한 쌍을 낸다."""

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


def _bundle() -> SongCueBundle:
    """저장된 큐 둘(Chorus 0:10 · Drop 0:14)을 가진 번들 — 타이밍 함수가 읽는 것만 채운다.

    예전에는 은퇴한 조립기로 만들었다(한국어 제목 → ``Song 3``, 빈 시퀀스 3). 타이밍 함수는
    시퀀스 번호·이름과 **명령이 있는**(저장된) 구간의 시작 시각만 읽으므로 같은 값을
    손으로 싣는다. 대화 길(``song_cue_render.reviewed_song_timing``)도 같은 방식으로 번들을
    짓는다.
    """
    sections = parse_sections((("Chorus", "0:10"), ("Drop", "0:14")))
    stored = tuple(
        SongCueSectionBundle(
            section=section,
            cue_number=number,
            cue_name=section.name,
            selection=SongCueLookSelection(section=section, requested_dynamics=(4,)),
            commands=("stored",),
        )
        for number, section in enumerate(sections, start=1)
    )
    return SongCueBundle(
        song_title="테스트 곡",
        sequence_number=3,
        sequence_name="Song 3",
        commands=("stored",),
        sections=stored,
    )


def _commands_matching(commands: tuple[str, ...], pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [command for command in commands if regex.search(command)]


def _trig_times(commands: tuple[str, ...]) -> list[str]:
    return [
        match.group("time") for command in commands if (match := _TRIG_TIME_RE.fullmatch(command))
    ]


def _skip_axes(plan) -> set[str]:
    return {skip.axis for skip in plan.skipped_axes}
