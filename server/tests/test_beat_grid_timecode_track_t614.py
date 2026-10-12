"""카드 t614 — 박자 격자 에미터: 타임코드 배정 줄은 트랙 주소 ``<타임코드>.1.<k>`` 로 낸다.

실기 근거(t608 v2 S1b ``.moai/reports/t608/v2/run-S1b.jsonl`` index 3·6): 맨 꼴
``Assign Sequence 702 At Timecode 70`` 은 ``OK`` 였고, 같은 타임코드의 둘째 맨 꼴
``Assign Sequence 703 At Timecode 70`` 은 ``Illegal object`` 로 거절됐다. 실기 선례는
``Store Timecode N.1`` 로 트랙 그룹을 만든 뒤 ``Assign Sequence S At Timecode N.1.k``
(``k`` = 그 타임코드에서 실제로 배정된 트랙의 1부터 센 순번)다 — t520
``live_write_b2/steps.jsonl`` 564~570행 · t506 ``live_write/steps.jsonl`` 9행 · t553
``approval_t553.txt`` 5~9행.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import pytest

from server.design.beat_grid_emit import BeatGridEmitResult, emit_beat_grid_write_bundle
from server.tests.test_beat_grid_emit_t549 import _ALL_M1_PASS, _TIMING, _position_cue, _track

#: 옛 맨 꼴 배정 줄의 끝 — ``... At Timecode 30`` (트랙 주소 점이 없다).
_BARE_ASSIGN = re.compile(r"At Timecode \d+$")
#: 새 꼴 배정 줄 전체 — ``Assign Sequence 300 At Timecode 30.1.1``.
_TRACK_ASSIGN = re.compile(r"^Assign Sequence \d+ At Timecode \d+\.1\.\d+$")


def _emit(
    tracks: Sequence[Mapping[str, object]],
    *,
    sequence_numbers: Mapping[str, int],
    timecode_numbers: Mapping[str, int],
    held_cells: Mapping[tuple[str, int], str] | None = None,
) -> BeatGridEmitResult:
    return emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers=sequence_numbers,
        timecode_numbers=timecode_numbers,
        dimmer_attributes={},
        probe_results=_ALL_M1_PASS,
        held_cells=held_cells,
    )


def _two_tracks_on_one_timecode() -> BeatGridEmitResult:
    # 카드 t615 — 배정은 저장 큐가 있는 트랙만 낸다. 두 트랙 모두 칸을 하나씩 가진다.
    return _emit(
        [
            _track("FOH", 3, [_position_cue(3, position_preset_no="1.1")]),
            _track("BLIND", 14, [_position_cue(3, position_preset_no="1.2")]),
        ],
        sequence_numbers={"FOH": 300, "BLIND": 301},
        timecode_numbers={"FOH": 30, "BLIND": 30},
    )


class TestAssignLineIsATrackAddress:
    def test_two_tracks_on_one_timecode_get_consecutive_track_indexes(self) -> None:
        # 실기: 같은 타임코드의 둘째 트랙 맨 꼴 배정이 Illegal object 로 거절됐다.
        first, second = _two_tracks_on_one_timecode().tracks
        assert first.assign_timecode_commands == ("Assign Sequence 300 At Timecode 30.1.1",)
        assert second.assign_timecode_commands == ("Assign Sequence 301 At Timecode 30.1.2",)

    def test_a_single_track_alone_on_its_timecode_gets_index_one(self) -> None:
        result = _emit(
            [_track("FOH", 3, [_position_cue(3, position_preset_no="1.1")])],
            sequence_numbers={"FOH": 300},
            timecode_numbers={"FOH": 30},
        )
        (track,) = result.tracks
        assert track.assign_timecode_commands == ("Assign Sequence 300 At Timecode 30.1.1",)

    def test_no_assign_line_is_in_the_bare_form(self) -> None:
        # 칸이 있는 두 트랙 모두 — 어느 경로로도 맨 꼴이 나가면 안 된다.
        tracks = [
            _track("FOH", 3, [_position_cue(18, position_preset_no="2.1")]),
            _track("BLIND", 14, [_position_cue(18, position_preset_no="2.2")]),
        ]
        result = _emit(
            tracks,
            sequence_numbers={"FOH": 300, "BLIND": 301},
            timecode_numbers={"FOH": 30, "BLIND": 30},
        )
        assigns = [line for line in result.commands if line.startswith("Assign Sequence ")]
        assert len(assigns) == 2
        assert not [line for line in result.commands if _BARE_ASSIGN.search(line)]
        assert all(_TRACK_ASSIGN.match(line) for line in assigns)


class TestBlockedTrackDoesNotConsumeAnIndex:
    @pytest.mark.parametrize(
        ("middle", "middle_sequence"),
        [
            pytest.param(_track("MYSTERY", None, [], confirmed=False), 301, id="unconfirmed-group"),
            pytest.param(_track("MYSTERY", 7, []), None, id="no-sequence-number"),
        ],
    )
    def test_next_assigned_track_takes_the_next_index(
        self, middle: dict, middle_sequence: int | None
    ) -> None:
        # 가운데 트랙이 막혀 배정 줄 구성에 닿지 못하면 순번을 쓰지 않는다 — 뒤 트랙이 .1.2 다.
        sequence_numbers = {"FOH": 300, "BLIND": 302}
        if middle_sequence is not None:
            sequence_numbers["MYSTERY"] = middle_sequence
        result = _emit(
            [
                _track("FOH", 3, [_position_cue(3, position_preset_no="1.1")]),
                middle,
                _track("BLIND", 14, [_position_cue(3, position_preset_no="1.2")]),
            ],
            sequence_numbers=sequence_numbers,
            timecode_numbers={"FOH": 30, "MYSTERY": 30, "BLIND": 30},
        )
        foh, mystery, blind = result.tracks
        assert mystery.blocked_reason is not None
        assert mystery.assign_timecode_commands == ()
        assert foh.assign_timecode_commands == ("Assign Sequence 300 At Timecode 30.1.1",)
        assert blind.assign_timecode_commands == ("Assign Sequence 302 At Timecode 30.1.2",)

    def test_a_held_cell_blocks_the_cell_not_the_track_so_the_track_keeps_its_index(self) -> None:
        # 보류 칸은 그 칸의 명령만 막는다. 트랙에 보낼 칸이 남아 있으면 배정되어 순번을 쓴다.
        tracks = [
            _track(
                "FOH",
                3,
                [
                    _position_cue(18, position_preset_no="2.1"),
                    _position_cue(20, position_preset_no="2.2"),
                ],
            ),
            _track("BLIND", 14, [_position_cue(3, position_preset_no="1.2")]),
        ]
        result = _emit(
            tracks,
            sequence_numbers={"FOH": 300, "BLIND": 301},
            timecode_numbers={"FOH": 30, "BLIND": 30},
            held_cells={("FOH", 18): "빈 프리셋 — 송신 보류"},
        )
        foh, blind = result.tracks
        assert foh.cues[0].commands == ()
        assert foh.cues[0].blocked_reason is not None
        assert foh.assign_timecode_commands == ("Assign Sequence 300 At Timecode 30.1.1",)
        assert blind.assign_timecode_commands == ("Assign Sequence 301 At Timecode 30.1.2",)


class TestTimecodeSetupStoresTheTrackGroup:
    def test_store_timecode_dot_one_comes_once_after_the_name_line(self) -> None:
        result = _two_tracks_on_one_timecode()
        setup = result.timecode_setup_commands
        assert setup.count("Store Timecode 30.1") == 1
        assert result.commands.count("Store Timecode 30.1") == 1
        name_index = next(
            index
            for index, line in enumerate(setup)
            if line.startswith("Set Timecode 30 Property 'Name'")
        )
        assert setup.index("Store Timecode 30") < name_index < setup.index("Store Timecode 30.1")
        # 트랙 그룹은 첫 배정 줄보다 먼저 만들어져야 한다(실기 선례 t520 순서).
        commands = result.commands
        first_assign = next(
            index for index, line in enumerate(commands) if line.startswith("Assign Sequence ")
        )
        assert commands.index("Store Timecode 30.1") < first_assign

    def test_track_index_counts_per_timecode_and_each_used_timecode_stores_its_group(self) -> None:
        result = _emit(
            [
                _track("FOH", 3, [_position_cue(3, position_preset_no="1.1")]),
                _track("BLIND", 14, [_position_cue(3, position_preset_no="1.2")]),
                _track("BACK", 4, [_position_cue(3, position_preset_no="1.3")]),
            ],
            sequence_numbers={"FOH": 300, "BLIND": 301, "BACK": 302},
            timecode_numbers={"FOH": 30, "BLIND": 31, "BACK": 30},
        )
        assert [track.assign_timecode_commands for track in result.tracks] == [
            ("Assign Sequence 300 At Timecode 30.1.1",),
            ("Assign Sequence 301 At Timecode 31.1.1",),
            ("Assign Sequence 302 At Timecode 30.1.2",),
        ]
        # 타임코드마다 정확히 한 번, 자기 Store 바로 뒤(이름 줄만 건너뛰고).
        stores = [line for line in result.timecode_setup_commands if line.startswith("Store ")]
        assert stores == [
            "Store Timecode 30",
            "Store Timecode 30.1",
            "Store Timecode 31",
            "Store Timecode 31.1",
        ]
