"""WebSocket 프로토콜 v1 — 칸 옮기기 메시지 ``beat_grid_cell_edit`` (SPEC-LDRHYTHM-001 TC5).

이 버전은 옮기기(``"move"``) 하나만 받는다. 만들기·지우기가 같은 메시지로 올 날이 있어도 지금은
거절한다. 파서가 한 번에 받는 항목은 ``BEAT_GRID_CELL_EDIT_OPS_MAX`` 개까지다.

거절 시험은 **사유까지** 가려서 본다. 타입 자체가 허용 목록에 없을 때도 ``ProtocolError`` 가
나므로, 사유를 보지 않으면 파서가 없어도 거절 시험이 통과해 버린다(공허한 통과).
"""

from __future__ import annotations

import json

import pytest

from server.web.messages import (
    CLIENT_MESSAGE_TYPES,
    PROTOCOL_VERSION,
    ProtocolError,
    parse_client_message,
)

_TYPE = "beat_grid_cell_edit"
#: 옮기기 말고 다른 일을 보냈을 때 대는 사유 — 문장 그대로 정해진 한국어다.
_MOVE_ONLY = "이 버전은 칸 옮기기만 지원합니다"
_NOT_A_LIST = r"beat_grid_cell_edit\.ops must be a non-empty list"


def _raw(**fields) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


def _move(**overrides) -> dict:
    """유효한 옮기기 항목 하나 — 시험마다 고칠 칸만 ``overrides`` 로 바꾼다."""
    return {"op": "move", "group_name": "BACK", "bar": 3, "to_bar": 5, **overrides}


def _refused(ops: object, reason: str) -> None:
    with pytest.raises(ProtocolError, match=reason):
        parse_client_message(_raw(type=_TYPE, ops=ops))


class TestParse:
    def test_the_type_is_on_the_client_allowlist_exactly_once(self) -> None:
        assert CLIENT_MESSAGE_TYPES.count(_TYPE) == 1

    def test_a_single_move_parses(self) -> None:
        message = parse_client_message(_raw(type=_TYPE, ops=[_move()]))
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": _TYPE,
            "ops": [{"op": "move", "group_name": "BACK", "bar": 3, "to_bar": 5}],
        }

    def test_a_group_of_two_moves_parses_in_order(self) -> None:
        first = _move(group_name="BACK", bar=3, to_bar=5)
        second = _move(group_name="SIDE", bar=7, to_bar=2)
        message = parse_client_message(_raw(type=_TYPE, ops=[first, second]))
        assert message["ops"] == [first, second]

    def test_the_most_a_frame_may_carry_still_parses(self) -> None:
        ops = [_move(bar=number) for number in range(1, 65)]
        assert parse_client_message(_raw(type=_TYPE, ops=ops))["ops"] == ops


class TestOnlyMovesAreAccepted:
    @pytest.mark.parametrize(
        "entry",
        [
            pytest.param({"op": "create", "group_name": "BACK", "bar": 3}, id="create"),
            pytest.param({"op": "delete", "group_name": "BACK", "bar": 3}, id="delete"),
            pytest.param(
                {"op": "create", "group_name": "BACK", "bar": 3, "preset": 7},
                id="create-with-a-key-this-version-does-not-know",
            ),
            pytest.param({"group_name": "BACK", "bar": 3, "to_bar": 5}, id="op-missing"),
            pytest.param(_move(op="MOVE"), id="op-in-capitals"),
            pytest.param(_move(op=None), id="op-null"),
        ],
    )
    def test_any_other_op_is_refused_with_the_version_reason(self, entry: dict) -> None:
        _refused([entry], _MOVE_ONLY)

    def test_one_bad_op_refuses_the_whole_group(self) -> None:
        _refused([_move(), {"op": "delete", "group_name": "BACK", "bar": 3}], _MOVE_ONLY)


class TestOpsShape:
    def test_ops_missing_is_refused(self) -> None:
        with pytest.raises(ProtocolError, match=_NOT_A_LIST):
            parse_client_message(_raw(type=_TYPE))

    @pytest.mark.parametrize(
        "ops",
        [
            pytest.param([], id="empty-list"),
            pytest.param(None, id="null"),
            pytest.param("move", id="string"),
            pytest.param({"op": "move"}, id="object"),
            pytest.param(5, id="number"),
        ],
    )
    def test_ops_must_be_a_non_empty_list(self, ops: object) -> None:
        _refused(ops, _NOT_A_LIST)

    def test_one_more_than_the_most_is_refused(self) -> None:
        # 항목이 모두 유효해도 개수만으로 거절된다.
        _refused([_move(bar=number) for number in range(1, 66)], r"ops must have at most 64 items")

    @pytest.mark.parametrize(
        "entry",
        [
            pytest.param("move", id="string"),
            pytest.param(5, id="number"),
            pytest.param(None, id="null"),
            pytest.param(["move", "BACK", 3, 5], id="list"),
        ],
    )
    def test_an_entry_must_be_an_object(self, entry: object) -> None:
        _refused([entry], r"ops\[0\] must be an object")


class TestEntryFields:
    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            pytest.param({"group_name": ""}, "group_name", id="group-name-empty"),
            pytest.param({"group_name": "   "}, "group_name", id="group-name-blank"),
            pytest.param({"group_name": 5}, "group_name", id="group-name-number"),
            pytest.param({"bar": 0}, "bar", id="bar-zero"),
            pytest.param({"bar": -1}, "bar", id="bar-negative"),
            pytest.param({"bar": True}, "bar", id="bar-bool"),
            pytest.param({"bar": "5"}, "bar", id="bar-string"),
            pytest.param({"bar": 3.0}, "bar", id="bar-float"),
            pytest.param({"to_bar": 0}, "to_bar", id="to-bar-zero"),
            pytest.param({"to_bar": True}, "to_bar", id="to-bar-bool"),
            pytest.param({"to_bar": "5"}, "to_bar", id="to-bar-string"),
        ],
    )
    def test_a_bad_field_is_refused_and_named_by_position(
        self, overrides: dict, field: str
    ) -> None:
        # 나쁜 항목을 두 번째에 둔다 — 앞의 유효한 항목이 가리지 않고, 사유가 자리(1)를 댄다.
        _refused([_move(), _move(**overrides)], rf"ops\[1\]\.{field}")

    @pytest.mark.parametrize("field", ["group_name", "bar", "to_bar"])
    def test_a_missing_field_is_refused(self, field: str) -> None:
        entry = _move()
        del entry[field]
        _refused([entry], rf"ops\[0\]\.{field}")

    def test_an_unknown_key_is_refused(self) -> None:
        _refused([_move(evidence="x")], r"ops\[0\] has unknown keys")
