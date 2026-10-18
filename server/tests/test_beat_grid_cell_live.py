"""칸 편집을 콘솔에 바로 반영할 때 쓰는 순수 규칙 시험 — 옮기기 (SPEC-LDRHYTHM-001).

콘솔 접촉 0건. 시험이 재는 것:

1. 범위 — 필요한 범위가 허락한 범위 안에 들 때만 덮는다.
2. 소유 타임코드 — 소유 기록의 주 타임코드 다음에 추가 타임코드를 적힌 순서대로, 중복 없이 낸다.
   주 번호가 없거나 정수가 아니면 거절한다.
3. 트랙 번호 — 상태 자식 1 은 마커라서 트랙은 2 부터이고, 명령에 쓰는 번호는 자리 - 1 이다.
4. 그룹 -> 콘솔 트랙 — 읽은 트랙 TARGET 을 시퀀스 번호로 풀어 그룹의 시퀀스와 맞춘다. 정확히
   하나면 대응시키고, 없으면 그 그룹을 뺀다. 둘 이상이면 어느 쪽인지 정할 수 없어 거절한다.
5. 이벤트 시각 — 유한하고 0 이상인 수만 받는다.
6. 허용 목록 — 명령 줄이 정해진 한 꼴(소유한 타임코드·트랙의 이벤트 시각 고치기)과 글자 하나까지
   같을 때만 통과한다. 하나라도 어긋나면 번들 전체를 거절한다. ';'·줄바꿈으로 이은 줄은 꼴 검사에도
   걸리지만 따로 사유를 대고 거절하므로, 시험은 사유 문자열까지 가려서 본다(가리지 않으면 그 검사를
   빼도 시험이 그대로 통과한다).
7. 거절 메시지는 감독에게 보여도 되는 한국어 사유이고, 이 모듈은 웹·안전 계층과 입출력 모듈을
   import 하지 않는다.
8. 소유 기록 갱신 — 옮긴 칸의 마디 열쇠만 바뀌고 큐 번호는 그대로이며, 나머지는 입력과 같다. 입력은
   고치지 않고 깊게 복사한 새 기록을 낸다. 서로 자리를 비켜 주는 옮김은 허용하고, 줄이 없거나 옛
   마디가 없거나 새 마디에 다른 칸이 남아 있거나 옮김끼리 겹치면 거절한다.
9. 칸 기록(스냅샷) 갱신 — 있는 열쇠만 새 마디로 옮기고(칸 사전의 ``bar`` 도 함께), 없는 열쇠는
   만들지 않는다. 부분 기록은 부분 기록으로 남는다. 입력은 고치지 않고, 겹치면 거절한다.
"""

from __future__ import annotations

import ast
import copy
import inspect
import re

import pytest

from server.design import beat_grid_cell_live as cell_live_module
from server.design.beat_grid_cell_live import (
    SCOPE_CREATE_DELETE,
    SCOPE_MOVE,
    CellLiveRefused,
    command_track_index,
    console_tracks_for_groups,
    move_bundle_allowed,
    move_record_tracks,
    move_snapshot_keys,
    owned_timecode_numbers,
    parse_event_seconds,
    scope_covers,
)
from server.design.beat_grid_send import PartialCellSnapshot

HANGUL = re.compile(r"[가-힣]")

#: 이 곡이 쓰는 타임코드 5 의 트랙 2 하나만 소유한 상태, 그리고 그 트랙에 허용되는 명령 한 줄.
_OWNED = {5: frozenset({2})}
_GOOD = "Set Timecode 5.1.2.1.1.10 Property 'Time' 82.142"


def _record() -> dict:
    """시험용 소유 기록 — 줄 이름은 일반 문자열이고 시퀀스 번호·이름은 기록 모양 그대로다."""
    return {
        "timecode_number": 5,
        "tracks": {
            "KEY": {"sequence_number": 1, "sequence_name": "LDBEAT KEY"},
            "FOH": {"sequence_number": 2, "sequence_name": "LDBEAT FOH"},
        },
    }


# == 범위 =============================================================================


class TestScope:
    def test_the_scope_words_are_fixed(self) -> None:
        assert SCOPE_MOVE == "move"
        assert SCOPE_CREATE_DELETE == "create_delete"

    def test_a_granted_scope_covers_itself_but_not_another(self) -> None:
        granted = frozenset({SCOPE_MOVE})
        assert scope_covers(granted, frozenset({SCOPE_MOVE}))
        assert not scope_covers(granted, frozenset({SCOPE_CREATE_DELETE}))

    def test_needing_more_than_was_granted_is_not_covered(self) -> None:
        both = frozenset({SCOPE_MOVE, SCOPE_CREATE_DELETE})
        assert not scope_covers(frozenset({SCOPE_MOVE}), both)

    def test_a_wider_grant_covers_a_narrower_need(self) -> None:
        both = frozenset({SCOPE_MOVE, SCOPE_CREATE_DELETE})
        assert scope_covers(both, frozenset({SCOPE_MOVE}))

    def test_needing_nothing_is_always_covered(self) -> None:
        assert scope_covers(frozenset(), frozenset())
        assert scope_covers(frozenset({SCOPE_MOVE}), frozenset())


# == 소유 타임코드 ======================================================================


class TestOwnedTimecodeNumbers:
    def test_the_main_timecode_comes_first_then_the_extras(self) -> None:
        record = {"timecode_number": 5, "extra_timecodes": [{"timecode_number": 6}]}
        assert owned_timecode_numbers(record) == (5, 6)

    def test_a_record_without_extras_owns_only_the_main_timecode(self) -> None:
        assert owned_timecode_numbers({"timecode_number": 5}) == (5,)

    def test_duplicates_are_dropped_and_the_written_order_is_kept(self) -> None:
        record = {
            "timecode_number": 5,
            "extra_timecodes": [
                {"timecode_number": 7},
                {"timecode_number": 5},
                {"timecode_number": 7},
                {"timecode_number": 6},
            ],
        }
        assert owned_timecode_numbers(record) == (5, 7, 6)

    def test_an_extra_without_a_usable_number_is_skipped(self) -> None:
        record = {
            "timecode_number": 5,
            "extra_timecodes": [
                "junk",
                {"timecode_name": "no number"},
                {"timecode_number": "6"},
                {"timecode_number": True},
                {"timecode_number": 7},
            ],
        }
        assert owned_timecode_numbers(record) == (5, 7)

    @pytest.mark.parametrize(
        "record",
        [
            pytest.param({}, id="no-main-number"),
            pytest.param({"timecode_number": None}, id="none"),
            pytest.param({"timecode_number": "5"}, id="text"),
            pytest.param({"timecode_number": 5.0}, id="float"),
            pytest.param({"timecode_number": True}, id="bool"),
            pytest.param({"extra_timecodes": [{"timecode_number": 6}]}, id="extras-only"),
        ],
    )
    def test_a_missing_or_non_integer_main_number_is_refused(self, record: dict) -> None:
        with pytest.raises(CellLiveRefused):
            owned_timecode_numbers(record)


# == 트랙 번호 ==========================================================================


class TestCommandTrackIndex:
    @pytest.mark.parametrize(("state_index", "expected"), [(2, 1), (3, 2), (10, 9)])
    def test_the_command_number_is_one_less_than_the_state_position(
        self, state_index: int, expected: int
    ) -> None:
        assert command_track_index(state_index) == expected

    @pytest.mark.parametrize("state_index", [1, 0, -1])
    def test_the_marker_position_and_below_are_not_tracks(self, state_index: int) -> None:
        with pytest.raises(CellLiveRefused):
            command_track_index(state_index)


# == 그룹 -> 콘솔 트랙 ===================================================================


class TestConsoleTracksForGroups:
    def test_each_group_maps_to_the_track_that_targets_its_sequence(self) -> None:
        # 세 번째 읽기는 어느 그룹의 시퀀스도 아니라서 어디에도 대응하지 않는다.
        reads = [(5, 2, 1), (5, 3, 2), (5, 4, 3)]
        assert console_tracks_for_groups(_record(), reads) == {"KEY": (5, 1), "FOH": (5, 2)}

    def test_a_group_with_no_matching_track_is_left_out(self) -> None:
        assert console_tracks_for_groups(_record(), [(5, 2, 1)]) == {"KEY": (5, 1)}

    def test_no_reads_map_nothing(self) -> None:
        assert console_tracks_for_groups(_record(), []) == {}

    def test_a_track_on_an_extra_timecode_maps_with_that_timecode(self) -> None:
        reads = [(5, 2, 1), (6, 2, 2)]
        assert console_tracks_for_groups(_record(), reads) == {"KEY": (5, 1), "FOH": (6, 1)}

    @pytest.mark.parametrize("raw", [1, "1", "Sequence 1", "LDBEAT KEY"])
    def test_the_target_may_be_a_number_a_sequence_word_or_the_name(self, raw: object) -> None:
        assert console_tracks_for_groups(_record(), [(5, 2, raw)]) == {"KEY": (5, 1)}

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param(None, id="unread"),
            pytest.param("", id="empty"),
            pytest.param("KEY", id="group-name-is-not-a-sequence-name"),
            pytest.param(True, id="bool"),
            pytest.param(7, id="another-sequence"),
        ],
    )
    def test_an_unreadable_or_foreign_target_matches_no_group(self, raw: object) -> None:
        assert console_tracks_for_groups(_record(), [(5, 2, raw)]) == {}

    @pytest.mark.parametrize(
        "reads",
        [
            pytest.param([(5, 2, 1), (5, 3, 1)], id="same-timecode"),
            pytest.param([(5, 2, 1), (6, 2, 1)], id="two-timecodes"),
            pytest.param([(5, 2, 1), (5, 3, "Sequence 1")], id="written-differently"),
            pytest.param([(5, 2, 1), (5, 3, 2), (5, 4, "LDBEAT KEY")], id="three-reads"),
        ],
    )
    def test_two_tracks_on_one_sequence_are_refused(self, reads: list) -> None:
        with pytest.raises(CellLiveRefused, match="KEY"):
            console_tracks_for_groups(_record(), reads)

    def test_a_matching_track_at_the_marker_position_is_refused(self) -> None:
        with pytest.raises(CellLiveRefused):
            console_tracks_for_groups(_record(), [(5, 1, 1)])

    def test_a_group_without_a_sequence_number_is_left_out(self) -> None:
        record = {
            "timecode_number": 5,
            "tracks": {
                "KEY": {"sequence_name": "LDBEAT KEY"},
                "FOH": {"sequence_number": 2, "sequence_name": "LDBEAT FOH"},
            },
        }
        reads = [(5, 2, 1), (5, 3, 2)]
        assert console_tracks_for_groups(record, reads) == {"FOH": (5, 2)}

    def test_a_record_without_tracks_maps_nothing(self) -> None:
        assert console_tracks_for_groups({"timecode_number": 5}, [(5, 2, 1)]) == {}


# == 이벤트 시각 ========================================================================


class TestParseEventSeconds:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param("83.784000", 83.784, id="console-text"),
            pytest.param(81.642, 81.642, id="float"),
            pytest.param("0", 0.0, id="zero-text"),
            pytest.param(0, 0.0, id="zero-int"),
            pytest.param(12, 12.0, id="int"),
            pytest.param("12", 12.0, id="int-text"),
        ],
    )
    def test_a_finite_non_negative_time_is_accepted(self, value: object, expected: float) -> None:
        assert parse_event_seconds(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("-1", id="negative-text"),
            pytest.param(-1, id="negative-int"),
            pytest.param(-0.001, id="negative-float"),
            pytest.param("nan", id="nan-text"),
            pytest.param(float("nan"), id="nan"),
            pytest.param("inf", id="inf-text"),
            pytest.param(float("inf"), id="inf"),
            pytest.param("-inf", id="minus-inf-text"),
            pytest.param("", id="empty"),
            pytest.param("abc", id="not-a-number"),
            pytest.param("1,5", id="comma"),
            pytest.param(None, id="none"),
            pytest.param(True, id="bool"),
            pytest.param([83.0], id="list"),
            pytest.param(10**400, id="int-too-large-for-a-float"),
        ],
    )
    def test_anything_else_is_refused(self, value: object) -> None:
        with pytest.raises(CellLiveRefused):
            parse_event_seconds(value)


# == 옮기기 허용 목록 =====================================================================


class TestMoveBundleAllowed:
    def test_the_one_allowed_shape_passes(self) -> None:
        assert move_bundle_allowed([_GOOD], _OWNED) is None

    def test_an_empty_bundle_passes(self) -> None:
        assert move_bundle_allowed([], _OWNED) is None

    def test_several_allowed_lines_pass_with_whole_and_fractional_seconds(self) -> None:
        lines = [
            _GOOD,
            "Set Timecode 5.1.2.1.1.3 Property 'Time' 7",
            "Set Timecode 5.1.2.1.1.12 Property 'Time' 0.5",
        ]
        move_bundle_allowed(lines, _OWNED)

    def test_every_owned_timecode_and_track_pair_passes(self) -> None:
        owned = {5: frozenset({1, 2}), 6: frozenset({1})}
        lines = [
            "Set Timecode 5.1.1.1.1.3 Property 'Time' 1.5",
            "Set Timecode 5.1.2.1.1.3 Property 'Time' 1.5",
            "Set Timecode 6.1.1.1.1.3 Property 'Time' 1.5",
        ]
        move_bundle_allowed(lines, owned)

    def test_a_timecode_the_song_does_not_own_is_refused(self) -> None:
        line = "Set Timecode 3.1.2.1.1.10 Property 'Time' 82.142"
        with pytest.raises(CellLiveRefused, match="타임코드 3"):
            move_bundle_allowed([line], _OWNED)

    def test_a_track_the_song_does_not_own_is_refused(self) -> None:
        line = "Set Timecode 5.1.4.1.1.10 Property 'Time' 82.142"
        with pytest.raises(CellLiveRefused, match="트랙 4"):
            move_bundle_allowed([line], _OWNED)

    def test_a_track_owned_on_another_timecode_is_refused(self) -> None:
        owned = {5: frozenset({2}), 6: frozenset({1})}
        line = "Set Timecode 5.1.1.1.1.10 Property 'Time' 82.142"
        with pytest.raises(CellLiveRefused, match="트랙 1"):
            move_bundle_allowed([line], owned)

    @pytest.mark.parametrize(
        "line",
        [
            pytest.param("Delete Timecode 5.1.2.1.1.10", id="delete"),
            pytest.param("Store Property 'Time' 81.642 'AbsTime' 81.642 'Token' 'Go+'", id="store"),
            pytest.param("cd root", id="cd-root"),
            pytest.param("cd Timecode 5.1.2.1.1", id="cd-container"),
            pytest.param("Assign Sequence 5", id="other-verb"),
            pytest.param("", id="empty-line"),
            pytest.param(" " + _GOOD, id="leading-space"),
            pytest.param(_GOOD + " ", id="trailing-space"),
            pytest.param(_GOOD.replace("Set ", "set "), id="lower-case-verb"),
            pytest.param(_GOOD.replace("'Time'", "'AbsTime'"), id="other-property"),
            pytest.param(_GOOD + " /NoConfirm", id="extra-option"),
            pytest.param(_GOOD + " Property 'Time' 83", id="two-properties"),
            pytest.param(_GOOD.replace(" Property", "  Property"), id="double-space"),
            pytest.param(_GOOD.replace("82.142", "-82.142"), id="negative-time"),
            pytest.param(_GOOD.replace("82.142", "82.142.5"), id="two-fractions"),
            pytest.param(_GOOD.replace("82.142", "82."), id="empty-fraction"),
            pytest.param(_GOOD.replace("82.142", ".5"), id="no-whole-part"),
            pytest.param(_GOOD.replace("82.142", "1e3"), id="exponent"),
            pytest.param(_GOOD.replace("82.142", "82,142"), id="comma"),
            pytest.param(_GOOD.replace("82.142", "abc"), id="word-for-time"),
            pytest.param(_GOOD.replace(" 82.142", ""), id="no-time"),
            pytest.param(_GOOD.replace("82.142", "٨٢.142"), id="non-ascii-digit-in-time"),
            pytest.param(_GOOD.replace(".10 ", ".١٠ "), id="non-ascii-digit-in-event"),
            pytest.param(_GOOD.replace(".1.1.10", ".1.1."), id="no-event-number"),
            pytest.param(_GOOD.replace(".1.1.10", ".1.1.x"), id="word-for-event-number"),
            pytest.param(_GOOD.replace(".1.1.10", ".1.1.10.3"), id="extra-segment"),
            pytest.param(_GOOD.replace(".1.1.10", ".1.1"), id="container-not-event"),
            pytest.param(_GOOD.replace("5.1.2.1.1", "5.2.2.1.1"), id="second-part-not-one"),
            pytest.param(_GOOD.replace("5.1.2.1.1", "5.1.2.2.1"), id="fourth-part-not-one"),
            pytest.param(_GOOD.replace("5.1.2.1.1", "5.1.2.1.2"), id="fifth-part-not-one"),
            pytest.param(_GOOD.replace("5.1.2", "05.1.2"), id="leading-zero-timecode"),
            pytest.param(_GOOD.replace("5.1.2", "5.1.02"), id="leading-zero-track"),
        ],
    )
    def test_any_other_line_is_refused(self, line: str) -> None:
        with pytest.raises(CellLiveRefused):
            move_bundle_allowed([line], _OWNED)

    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(_GOOD + "; Delete Timecode 5.1.2.1.1.10", id="semicolon-then-delete"),
            pytest.param(_GOOD + "\nDelete Timecode 5.1.2.1.1.10", id="newline-then-delete"),
            pytest.param(_GOOD + ";", id="trailing-semicolon"),
            pytest.param(_GOOD + "\n", id="trailing-newline"),
            pytest.param(_GOOD + "\r", id="carriage-return"),
            pytest.param("\n" + _GOOD, id="leading-newline"),
        ],
    )
    def test_a_line_that_chains_commands_is_refused_for_that_reason(self, line: str) -> None:
        with pytest.raises(CellLiveRefused, match="명령 하나만"):
            move_bundle_allowed([line], _OWNED)

    def test_one_bad_line_refuses_the_whole_bundle_and_is_named(self) -> None:
        bad = "Delete Timecode 5.1.2.1.1.10"
        with pytest.raises(CellLiveRefused) as caught:
            move_bundle_allowed([_GOOD, bad], _OWNED)
        assert bad in str(caught.value)

    def test_the_first_offending_line_is_the_one_named(self) -> None:
        first, second = "cd root", "Delete Timecode 5.1.2.1.1.10"
        with pytest.raises(CellLiveRefused) as caught:
            move_bundle_allowed([_GOOD, first, second], _OWNED)
        assert first in str(caught.value)
        assert second not in str(caught.value)

    def test_a_line_that_is_not_text_is_refused(self) -> None:
        with pytest.raises(CellLiveRefused):
            move_bundle_allowed([_GOOD, None], _OWNED)  # type: ignore[list-item]


# == 칸 옮기기 — 소유 기록 갱신 ===========================================================


def _owned_record() -> dict:
    """옮기기 시험용 소유 기록 — 줄마다 {마디: 큐 번호} 가 있고 추가 타임코드도 있다.
    마디 열쇠는 파일에 JSON 으로 저장되는 값이라 글자다."""
    return {
        "timecode_number": 5,
        "timecode_name": "LDBEAT Timecode 5",
        "extra_timecodes": [{"timecode_number": 6, "timecode_name": "LDBEAT Timecode 6"}],
        "tracks": {
            "KEY": {
                "sequence_number": 1,
                "sequence_name": "LDBEAT KEY",
                "cues": {"3": 1, "5": 2, "9": 3},
            },
            "FOH": {
                "sequence_number": 2,
                "sequence_name": "LDBEAT FOH",
                "cues": {"3": 1, "7": 2},
            },
        },
    }


class TestMoveRecordTracks:
    def test_the_bar_key_moves_and_the_cue_number_stays(self) -> None:
        moved = move_record_tracks(_owned_record(), [("KEY", 5, 6)])
        assert moved["tracks"]["KEY"]["cues"] == {"3": 1, "6": 2, "9": 3}

    def test_nothing_but_the_moved_cue_keys_changes(self) -> None:
        expected = _owned_record()
        expected["tracks"]["KEY"]["cues"] = {"3": 1, "6": 2, "9": 3}
        assert move_record_tracks(_owned_record(), [("KEY", 5, 6)]) == expected

    def test_moves_in_several_groups_apply_together(self) -> None:
        moved = move_record_tracks(_owned_record(), [("KEY", 3, 4), ("FOH", 7, 8), ("KEY", 9, 11)])
        assert moved["tracks"]["KEY"]["cues"] == {"4": 1, "5": 2, "11": 3}
        assert moved["tracks"]["FOH"]["cues"] == {"3": 1, "8": 2}

    def test_cells_that_make_room_for_each_other_move_together(self) -> None:
        # 5→7 과 7→9: 7마디는 옮기는 칸이 비켜 주므로 겹치지 않는다(격자의 여럿 옮기기와 같은 판정).
        record = _owned_record()
        record["tracks"]["KEY"]["cues"] = {"5": 1, "7": 2}
        moved = move_record_tracks(record, [("KEY", 5, 7), ("KEY", 7, 9)])
        assert moved["tracks"]["KEY"]["cues"] == {"7": 1, "9": 2}

    def test_no_moves_gives_an_equal_copy(self) -> None:
        record = _owned_record()
        moved = move_record_tracks(record, [])
        assert moved == record
        assert moved is not record

    def test_the_input_record_is_left_alone(self) -> None:
        record = _owned_record()
        before = copy.deepcopy(record)
        move_record_tracks(record, [("KEY", 5, 6)])
        assert record == before

    def test_the_result_shares_nothing_with_the_input(self) -> None:
        record = _owned_record()
        before = copy.deepcopy(record)
        moved = move_record_tracks(record, [("KEY", 5, 6)])
        moved["extra_timecodes"][0]["timecode_number"] = 99
        moved["tracks"]["FOH"]["cues"]["3"] = 99
        moved["tracks"]["KEY"]["sequence_name"] = "바뀜"
        assert record == before

    @pytest.mark.parametrize(
        ("moves", "message"),
        [
            pytest.param([("NOPE", 5, 6)], "NOPE", id="group-not-in-the-record"),
            pytest.param([("KEY", 4, 6)], "4마디", id="no-cue-at-the-old-bar"),
            pytest.param([("KEY", 5, 9)], "9마디", id="another-cue-already-at-the-new-bar"),
            pytest.param([("KEY", 3, 4), ("KEY", 5, 4)], "4마디", id="two-cues-to-one-bar"),
            pytest.param([("KEY", 5, 6), ("KEY", 5, 7)], "5마디", id="one-cue-moved-twice"),
            pytest.param([("KEY", 3, 4), ("NOPE", 5, 6)], "NOPE", id="one-bad-move-spoils-all"),
        ],
    )
    def test_a_move_the_record_cannot_follow_is_refused(self, moves: list, message: str) -> None:
        record = _owned_record()
        before = copy.deepcopy(record)
        with pytest.raises(CellLiveRefused, match=message):
            move_record_tracks(record, moves)
        assert record == before

    def test_a_record_without_tracks_is_refused(self) -> None:
        with pytest.raises(CellLiveRefused, match="KEY"):
            move_record_tracks({"timecode_number": 5}, [("KEY", 5, 6)])

    def test_a_group_without_cue_numbers_has_no_cue_to_move(self) -> None:
        record = {"timecode_number": 5, "tracks": {"KEY": {"sequence_number": 1}}}
        with pytest.raises(CellLiveRefused, match="5마디"):
            move_record_tracks(record, [("KEY", 5, 6)])


# == 칸 옮기기 — 칸 기록(스냅샷) 갱신 =====================================================


def _cell(bar: int, preset: str) -> dict:
    """칸 기록의 값 하나 — ``beat_grid_cell_snapshot`` 이 담는 칸 사전처럼 ``bar`` 를 품고 있다."""
    return {"bar": bar, "position_preset_no": preset, "entry": {"trigger_beat": None}}


def _snapshot() -> dict:
    return {
        ("KEY", 3): _cell(3, "1.1"),
        ("KEY", 5): _cell(5, "1.2"),
        ("FOH", 3): _cell(3, "2.1"),
    }


class TestMoveSnapshotKeys:
    def test_the_key_moves_and_the_cell_body_follows_the_new_bar(self) -> None:
        moved = move_snapshot_keys(_snapshot(), [("KEY", 5, 6)])
        assert moved == {
            ("KEY", 3): _cell(3, "1.1"),
            ("KEY", 6): _cell(6, "1.2"),
            ("FOH", 3): _cell(3, "2.1"),
        }

    def test_another_groups_cell_at_the_same_bar_stays(self) -> None:
        moved = move_snapshot_keys(_snapshot(), [("KEY", 3, 4)])
        assert ("FOH", 3) in moved
        assert ("KEY", 3) not in moved
        assert ("KEY", 4) in moved

    def test_a_key_the_snapshot_does_not_have_stays_absent(self) -> None:
        moved = move_snapshot_keys(_snapshot(), [("KEY", 4, 6)])
        assert moved == _snapshot()
        assert ("KEY", 6) not in moved

    def test_moves_may_mix_present_and_absent_keys(self) -> None:
        moved = move_snapshot_keys(_snapshot(), [("KEY", 5, 6), ("KEY", 4, 7)])
        assert set(moved) == {("KEY", 3), ("KEY", 6), ("FOH", 3)}

    def test_an_unknown_old_cell_leaves_a_known_new_bar_alone(self) -> None:
        # 옮길 칸을 기록이 모르면 아무것도 옮기지 않는다 — 새 마디에 있던 기록을 덮어쓰지 않는다.
        known = PartialCellSnapshot({("KEY", 7): _cell(7, "1.1")})
        assert move_snapshot_keys(known, [("KEY", 5, 7)]) == known

    def test_cells_that_make_room_for_each_other_move_together(self) -> None:
        snapshot = {("KEY", 5): _cell(5, "1.1"), ("KEY", 7): _cell(7, "1.2")}
        moved = move_snapshot_keys(snapshot, [("KEY", 5, 7), ("KEY", 7, 9)])
        assert moved == {("KEY", 7): _cell(7, "1.1"), ("KEY", 9): _cell(9, "1.2")}

    def test_no_moves_gives_an_equal_new_snapshot(self) -> None:
        snapshot = _snapshot()
        moved = move_snapshot_keys(snapshot, [])
        assert moved == snapshot
        assert moved is not snapshot

    def test_the_input_snapshot_is_left_alone(self) -> None:
        snapshot = _snapshot()
        before = copy.deepcopy(snapshot)
        moved = move_snapshot_keys(snapshot, [("KEY", 5, 6)])
        moved[("KEY", 6)]["position_preset_no"] = "바뀜"
        assert snapshot == before

    def test_a_body_that_is_not_a_cell_dictionary_is_carried_as_it_is(self) -> None:
        moved = move_snapshot_keys({("KEY", 5): "opaque"}, [("KEY", 5, 6)])
        assert moved == {("KEY", 6): "opaque"}

    def test_a_partial_snapshot_stays_partial(self) -> None:
        # 부분 기록이 일반 사전이 되면 기록에 없는 칸이 전부 「미반영」으로 세어진다.
        moved = move_snapshot_keys(PartialCellSnapshot(_snapshot()), [("KEY", 5, 6)])
        assert isinstance(moved, PartialCellSnapshot)
        assert set(moved) == {("KEY", 3), ("KEY", 6), ("FOH", 3)}

    def test_a_whole_snapshot_stays_whole(self) -> None:
        moved = move_snapshot_keys(_snapshot(), [("KEY", 5, 6)])
        assert not isinstance(moved, PartialCellSnapshot)

    @pytest.mark.parametrize(
        ("moves", "message"),
        [
            pytest.param([("KEY", 5, 3)], "3마디", id="another-cell-already-at-the-new-bar"),
            pytest.param([("KEY", 3, 4), ("KEY", 5, 4)], "4마디", id="two-cells-to-one-bar"),
            pytest.param([("KEY", 5, 6), ("KEY", 5, 7)], "5마디", id="one-cell-moved-twice"),
        ],
    )
    def test_a_move_that_would_land_on_another_cell_is_refused(
        self, moves: list, message: str
    ) -> None:
        snapshot = _snapshot()
        before = copy.deepcopy(snapshot)
        with pytest.raises(CellLiveRefused, match=message):
            move_snapshot_keys(snapshot, moves)
        assert snapshot == before


# == 거절 메시지 · 모듈 경계 ===========================================================

_REFUSALS = [
    pytest.param(lambda: owned_timecode_numbers({}), id="owned-without-main"),
    pytest.param(lambda: command_track_index(1), id="marker-position"),
    pytest.param(
        lambda: console_tracks_for_groups(_record(), [(5, 2, 1), (5, 3, 1)]),
        id="two-tracks-one-sequence",
    ),
    pytest.param(lambda: parse_event_seconds("-1"), id="negative-time"),
    pytest.param(lambda: parse_event_seconds("nan"), id="nan-time"),
    pytest.param(lambda: parse_event_seconds(""), id="empty-time"),
    pytest.param(lambda: move_bundle_allowed(["cd root"], _OWNED), id="bundle-foreign-verb"),
    pytest.param(lambda: move_bundle_allowed([_GOOD + "; cd root"], _OWNED), id="bundle-chained"),
    pytest.param(
        lambda: move_bundle_allowed([_GOOD.replace("5.1.2", "3.1.2")], _OWNED),
        id="bundle-foreign-timecode",
    ),
    pytest.param(
        lambda: move_bundle_allowed([_GOOD.replace("5.1.2", "5.1.4")], _OWNED),
        id="bundle-foreign-track",
    ),
    pytest.param(lambda: move_bundle_allowed([None], _OWNED), id="bundle-not-text"),
    pytest.param(
        lambda: move_record_tracks(_owned_record(), [("NOPE", 5, 6)]),
        id="record-group-missing",
    ),
    pytest.param(
        lambda: move_record_tracks(_owned_record(), [("KEY", 4, 6)]),
        id="record-old-bar-missing",
    ),
    pytest.param(
        lambda: move_record_tracks(_owned_record(), [("KEY", 5, 9)]),
        id="record-new-bar-taken",
    ),
    pytest.param(
        lambda: move_record_tracks(_owned_record(), [("KEY", 3, 4), ("KEY", 5, 4)]),
        id="record-moves-collide",
    ),
    pytest.param(
        lambda: move_record_tracks(_owned_record(), [("KEY", 5, 6), ("KEY", 5, 7)]),
        id="record-cue-moved-twice",
    ),
    pytest.param(
        lambda: move_snapshot_keys(_snapshot(), [("KEY", 5, 3)]),
        id="snapshot-new-bar-taken",
    ),
    pytest.param(
        lambda: move_snapshot_keys(_snapshot(), [("KEY", 3, 4), ("KEY", 5, 4)]),
        id="snapshot-moves-collide",
    ),
    pytest.param(
        lambda: move_snapshot_keys(_snapshot(), [("KEY", 5, 6), ("KEY", 5, 7)]),
        id="snapshot-cell-moved-twice",
    ),
]


def _imported_modules(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TestContract:
    def test_the_error_is_a_value_error(self) -> None:
        assert issubclass(CellLiveRefused, ValueError)

    @pytest.mark.parametrize("refuse", _REFUSALS)
    def test_every_refusal_is_a_korean_sentence_for_the_operator(self, refuse) -> None:
        with pytest.raises(CellLiveRefused) as caught:
            refuse()
        assert HANGUL.search(str(caught.value))

    def test_the_module_reaches_neither_web_nor_safety(self) -> None:
        imported = _imported_modules(inspect.getsource(cell_live_module))
        assert not [name for name in imported if name.startswith(("server.web", "server.safety"))]

    def test_the_module_imports_only_pure_standard_library_and_the_target_parser(self) -> None:
        # 입출력 모듈(os·socket·subprocess·pathlib·json …)이 슬그머니 들어오면 여기서 걸린다.
        # ``copy`` 는 소유 기록을 깊게 복사하려고 들어왔다 — 입출력이 없는 표준 라이브러리다.
        imported = _imported_modules(inspect.getsource(cell_live_module))
        pure = {"__future__", "collections.abc", "copy", "math", "re", "typing"}
        assert imported <= pure | {"server.design.beat_grid_send"}
