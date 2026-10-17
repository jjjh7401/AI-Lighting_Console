"""타임코드 트랙 이벤트 — 카드 tc-events (SPEC-LDRHYTHM-001).

실기 판별(tc4-play-probe): ``Store Timecode`` 만 낸 타임코드는 Duration 0 · 빈 트랙이라
``Go Timecode`` 가 아무것도 재생하지 않는다. t520 레시피대로 Duration, 트랙별 CmdSubTrack,
큐 TrigTime 마다 ``Go+`` 이벤트를 내는지, 다시 반영할 때 앱 소유 타임코드를 먼저 지우는지 본다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import BeatGridEmitResult, emit_beat_grid_write_bundle
from server.design.beat_grid_send import (
    clear_app_timecode_before_rebuild,
    song_end_seconds_from_bar_map,
)
from server.tests.test_beat_grid_emit_t549 import _ALL_M1_PASS, _TIMING, _position_cue, _track


def _emit(song_end_seconds: float | None = 60.0) -> BeatGridEmitResult:
    return emit_beat_grid_write_bundle(
        [
            _track(
                "FOH",
                3,
                [
                    _position_cue(1, position_preset_no="1.1"),
                    _position_cue(3, position_preset_no="1.2"),
                ],
            ),
            _track("BLIND", 14, [_position_cue(2, position_preset_no="1.3")]),
        ],
        timing=_TIMING,
        sequence_numbers={"FOH": 300, "BLIND": 301},
        timecode_numbers={"FOH": 30, "BLIND": 30},
        dimmer_attributes={},
        probe_results=_ALL_M1_PASS,
        song_end_seconds=song_end_seconds,
    )


def _trig_seconds(result: BeatGridEmitResult, sequence: int) -> list[str]:
    out = []
    for line in result.commands:
        prefix = "Set Cue "
        if line.startswith(prefix) and f"Sequence {sequence} Property 'TrigTime'" in line:
            out.append(line.rsplit(" ", 1)[1])
    return out


class TestTimecodeEvents:
    def test_duration_line_follows_name_and_disables_autostop(self) -> None:
        setup = _emit(60.0).timecode_setup_commands
        assert "Set Timecode 30 Property 'Duration' 60 'AutoStop' 0" in setup
        assert setup.index("Set Timecode 30 Property 'Duration' 60 'AutoStop' 0") == 2

    def test_no_duration_line_when_song_length_unknown(self) -> None:
        assert not any("'Duration'" in line for line in _emit(None).commands)

    def test_one_cmd_subtrack_per_assigned_track(self) -> None:
        commands = list(_emit().commands)
        assert "Store Type 'CmdSubTrack' Timecode 30.1.1.1" in commands
        assert "Store Type 'CmdSubTrack' Timecode 30.1.2.1" in commands
        # 하위 트랙은 이벤트 줄보다 먼저, 배정 줄보다 나중에 만든다.
        assert commands.index("Assign Sequence 301 At Timecode 30.1.2") < commands.index(
            "Store Type 'CmdSubTrack' Timecode 30.1.1.1"
        )
        assert commands.index("Store Type 'CmdSubTrack' Timecode 30.1.2.1") < commands.index(
            "cd Timecode 30.1.1.1.1"
        )

    def test_go_plus_event_per_cue_at_the_absolute_trig_time(self) -> None:
        result = _emit()
        commands = list(result.commands)
        start = commands.index("cd Timecode 30.1.1.1.1")
        end = commands.index("cd root", start)
        events = commands[start + 1 : end]
        expected = _trig_seconds(result, 300)
        assert len(events) == 2 == len(expected)
        for line, seconds in zip(events, expected, strict=True):
            assert line == f"Store Property 'Time' {seconds} 'AbsTime' {seconds} 'Token' 'Go+'"
        second = commands.index("cd Timecode 30.1.2.1.1")
        blind_events = commands[second + 1 : commands.index("cd root", second)]
        assert list(blind_events) == [
            f"Store Property 'Time' {s} 'AbsTime' {s} 'Token' 'Go+'"
            for s in _trig_seconds(result, 301)
        ]

    def test_blocked_track_gets_no_subtrack(self) -> None:
        result = emit_beat_grid_write_bundle(
            [_track("FOH", 3, [_position_cue(1, position_preset_no="1.1")])],
            timing=_TIMING,
            sequence_numbers={},
            timecode_numbers={"FOH": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
            song_end_seconds=60,
        )
        assert result.timecode_event_commands == ()


class TestClearBeforeRebuild:
    def test_delete_is_first_and_targets_only_that_number(self) -> None:
        cleared = clear_app_timecode_before_rebuild(_emit(), 30)
        commands = list(cleared.commands)
        # 재실행 4 — 타임코드 지우기는 큐를 다 쓴 뒤, 타임코드 설정의 첫 줄이다.
        delete_at = commands.index("Delete Timecode 30 /NoConfirm")
        assert cleared.timecode_setup_commands[0] == "Delete Timecode 30 /NoConfirm"
        assert all(not line.startswith("Store Sequence ") for line in commands[delete_at:])
        assert sum(1 for line in commands if line.startswith("Delete ")) == 1
        assert commands.index("Store Timecode 30") == delete_at + 1

    def test_no_delete_when_timecode_is_not_rebuilt(self) -> None:
        result = _emit()
        assert clear_app_timecode_before_rebuild(result, 99) is result


class TestSongEnd:
    def test_last_bar_end_from_bar_map(self) -> None:
        bar_map = {
            "bpm": 120.0,
            "time_signature": [4, 4],
            "bars": [
                {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [0]} for n in range(1, 4)
            ],
        }
        assert song_end_seconds_from_bar_map(bar_map) == 7.0

    def test_missing_bar_map_is_none(self) -> None:
        assert song_end_seconds_from_bar_map(None) is None
