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
"""

from __future__ import annotations

import ast
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
    owned_timecode_numbers,
    parse_event_seconds,
    scope_covers,
)

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
        imported = _imported_modules(inspect.getsource(cell_live_module))
        pure = {"__future__", "collections.abc", "math", "re", "typing"}
        assert imported <= pure | {"server.design.beat_grid_send"}
