"""TC5 칸 하나를 콘솔에서 고치는 명령 꼴 — 시각으로 이벤트 번호 찾기 (SPEC-LDRHYTHM-001).

콘솔 접촉 0건. 순수 함수만 부른다. 아래 문자열은 실콘솔 실측 기록(레인 1)에서 옮긴 정확한 꼴이다
(트랙 3 · 이벤트 10 · 81.642 초 → 82.142 초). 시험이 재는 것:

1. 컨테이너 주소 — 타임코드 번호와 트랙 순번이 ``Timecode 5.1.<트랙>.1.1`` 꼴이 된다.
2. 만들기 — ``cd`` 로 컨테이너에 들어가 ``Store Property 'Time' … 'Token' 'Go+'`` 한 줄을 넣고
   ``cd root`` 로 나온다.
3. 옮기기·지우기 — 이벤트 번호는 상수가 아니다. 방금 읽은 (번호, 시각) 목록에서 시각이 맞는
   이벤트를 찾아 쓴다. 지우거나 만들면 번호가 밀리므로 같은 시각의 번호가 읽을 때마다 달라진다.
4. 못 찾거나(0개) 모호하면(2개 이상) ``TcCellIndexError`` — 엉뚱한 이벤트를 건드리느니 거절한다.
5. 모르는 동작·빠진 시각은 ``TcCellIndexError`` 가 아닌 그냥 ``ValueError`` 다 — 사유가 섞이지
   않는다.
6. 초 문자열은 에미터(``beat_grid_emit``)가 쓰는 것과 같은 꼴이다 — 정수 초는 ``82``, 짧은 소수는
   ``82.5``. ``.3f`` 같은 두 번째 포매터는 ``82.142`` 에서는 티가 안 나므로 따로 잰다.
7. 시각이 NaN·무한대·음수이면 문자열로 만들거나 이벤트를 찾기 전에 거절한다 — 번호 찾기 실패가
   아닌 그냥 ``ValueError`` 이고, 메시지에 동작과 값이 나온다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_tc_cell import (
    TcCellIndexError,
    plan_tc_cell_commands,
    tc_track_container,
)

#: 실콘솔 실측 기록의 트랙 3 컨테이너(타임코드 5).
CONTAINER = "Timecode 5.1.3.1.1"


def test_create_emits_cd_store_and_cd_root_lines_in_order() -> None:
    commands = plan_tc_cell_commands("create", CONTAINER, [], to_seconds=81.642)

    assert commands == [
        "cd Timecode 5.1.3.1.1",
        "Store Property 'Time' 81.642 'AbsTime' 81.642 'Token' 'Go+'",
        "cd root",
    ]


def test_move_resolves_the_index_from_a_shifted_read() -> None:
    # 앞쪽 이벤트가 바뀌어 81.642 초의 번호가 22 로 밀린 읽기 — 10 이 아니라 22 를 써야 한다.
    events = [(9, 80.0), (10, 83.784), (22, 81.642)]

    commands = plan_tc_cell_commands(
        "move", CONTAINER, events, from_seconds=81.642, to_seconds=82.142
    )

    assert commands == ["Set Timecode 5.1.3.1.1.22 Property 'Time' 82.142"]


def test_move_resolves_the_index_from_the_original_numbering() -> None:
    events = [(9, 80.0), (10, 81.642), (11, 82.0)]

    commands = plan_tc_cell_commands(
        "move", CONTAINER, events, from_seconds=81.642, to_seconds=82.142
    )

    assert commands == ["Set Timecode 5.1.3.1.1.10 Property 'Time' 82.142"]


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ([(10, 81.642)], "Delete Timecode 5.1.3.1.1.10"),
        # 번호가 밀린 읽기 — 지우기도 상수 10 이 아니라 읽은 번호를 쓴다.
        ([(9, 80.0), (22, 81.642)], "Delete Timecode 5.1.3.1.1.22"),
    ],
    ids=["original-numbering", "shifted-numbering"],
)
def test_delete_resolves_the_index_from_the_time(
    events: list[tuple[int, float]], expected: str
) -> None:
    commands = plan_tc_cell_commands("delete", CONTAINER, events, from_seconds=81.642)

    assert commands == [expected]


@pytest.mark.parametrize("op", ["move", "delete"])
@pytest.mark.parametrize(
    "events",
    [[], [(9, 80.0), (10, 83.784)]],
    ids=["no-events", "only-far-events"],
)
def test_no_event_near_the_time_is_refused(op: str, events: list[tuple[int, float]]) -> None:
    with pytest.raises(TcCellIndexError):
        plan_tc_cell_commands(op, CONTAINER, events, from_seconds=81.642, to_seconds=82.142)


@pytest.mark.parametrize("op", ["move", "delete"])
@pytest.mark.parametrize(
    "events",
    [
        [(9, 80.0), (10, 81.642), (11, 81.642)],
        # 오차 안에 든 두 이벤트도 같은 시각으로 묶이므로 모호하다.
        [(10, 81.642), (11, 81.645)],
    ],
    ids=["same-time", "within-tolerance"],
)
def test_two_events_at_the_time_are_refused(op: str, events: list[tuple[int, float]]) -> None:
    with pytest.raises(TcCellIndexError):
        plan_tc_cell_commands(op, CONTAINER, events, from_seconds=81.642, to_seconds=82.142)


def test_tc_cell_index_error_is_a_value_error() -> None:
    assert issubclass(TcCellIndexError, ValueError)


def test_unknown_op_raises_a_plain_value_error() -> None:
    with pytest.raises(ValueError) as caught:
        plan_tc_cell_commands("rename", CONTAINER, [(10, 81.642)], from_seconds=81.642)

    # TcCellIndexError 도 ValueError 라서, 번호 찾기 실패로 뭉개지지 않았는지 따로 본다.
    assert not isinstance(caught.value, TcCellIndexError)
    assert "rename" in str(caught.value)


def test_tolerance_accepts_half_a_millisecond_but_not_eighteen() -> None:
    # 81.6425 는 81.642 와 0.0005 초 차이 — 같은 시각이다.
    near = plan_tc_cell_commands("delete", CONTAINER, [(10, 81.6425)], from_seconds=81.642)
    assert near == ["Delete Timecode 5.1.3.1.1.10"]

    # 81.66 은 0.018 초 차이 — 다른 이벤트이므로 못 찾는다.
    with pytest.raises(TcCellIndexError):
        plan_tc_cell_commands("delete", CONTAINER, [(10, 81.66)], from_seconds=81.642)


def test_track_container_is_timecode_dot_one_dot_track_dot_one_dot_one() -> None:
    assert tc_track_container(5, 3) == "Timecode 5.1.3.1.1"
    assert tc_track_container(5, 4) == "Timecode 5.1.4.1.1"


@pytest.mark.parametrize(
    ("op", "kwargs"),
    [
        ("create", {}),
        ("move", {"from_seconds": 81.642}),
        ("move", {"to_seconds": 82.142}),
        ("delete", {}),
    ],
    ids=["create-no-to", "move-no-to", "move-no-from", "delete-no-from"],
)
def test_missing_required_seconds_is_a_plain_value_error(op: str, kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError) as caught:
        plan_tc_cell_commands(op, CONTAINER, [(10, 81.642)], **kwargs)

    assert not isinstance(caught.value, TcCellIndexError)


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(82.0, "82"), (82.5, "82.5"), (0.001, "0.001")],
    ids=["whole-seconds", "one-decimal", "one-millisecond"],
)
def test_seconds_are_written_like_the_emitter_writes_them(seconds: float, text: str) -> None:
    created = plan_tc_cell_commands("create", CONTAINER, [], to_seconds=seconds)
    moved = plan_tc_cell_commands(
        "move", CONTAINER, [(10, 81.642)], from_seconds=81.642, to_seconds=seconds
    )

    assert created[1] == f"Store Property 'Time' {text} 'AbsTime' {text} 'Token' 'Go+'"
    assert moved == [f"Set Timecode 5.1.3.1.1.10 Property 'Time' {text}"]


@pytest.mark.parametrize(
    ("op", "events", "kwargs", "bad_name"),
    [
        ("create", [], {"to_seconds": -1.0}, "to_seconds"),
        ("create", [], {"to_seconds": float("nan")}, "to_seconds"),
        ("create", [], {"to_seconds": float("inf")}, "to_seconds"),
        # 옮기기: 찾을 시각은 멀쩡하고 옮겨 갈 시각만 음수다.
        ("move", [(10, 81.642)], {"from_seconds": 81.642, "to_seconds": -0.5}, "to_seconds"),
        # 지우기: 찾을 시각이 NaN 이다 — "맞는 이벤트 0개" 라는 엉뚱한 사유로 뭉개지면 안 된다.
        ("delete", [(10, 81.642)], {"from_seconds": float("nan")}, "from_seconds"),
    ],
    ids=["create-negative", "create-nan", "create-inf", "move-negative-to", "delete-nan-from"],
)
def test_non_finite_or_negative_seconds_are_a_plain_value_error(
    op: str,
    events: list[tuple[int, float]],
    kwargs: dict[str, float],
    bad_name: str,
) -> None:
    # 콘솔로 나가는 시각은 유한하고 0 이상이어야 한다 — 문자열로 만들거나 이벤트를 찾기
    # 전에 거절한다. 검사가 없어도 NaN 은 우연히 ValueError 로 끝나므로(만들기는 round(nan),
    # 지우기는 "맞는 이벤트 0개" 인 TcCellIndexError = ValueError) ValueError 만 봐서는
    # 모자라다. 그래서 사유(시각 자체가 틀림)를 따로 잰다.
    with pytest.raises(ValueError) as caught:
        plan_tc_cell_commands(op, CONTAINER, events, **kwargs)

    message = str(caught.value)
    # 번호 찾기 실패로 뭉개지지 않고, 어느 동작의 어느 시각이 무슨 값이라 틀렸는지 나온다.
    assert not isinstance(caught.value, TcCellIndexError)
    assert op in message
    assert bad_name in message
    assert str(kwargs[bad_name]) in message
