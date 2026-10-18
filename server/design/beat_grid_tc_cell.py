"""TC5 칸 하나를 콘솔에서 고치는 명령 꼴 — 시각으로 이벤트 번호를 찾아 쓴다 (SPEC-LDRHYTHM-001).

이 파일은 순수 함수다. 콘솔에 아무것도 쓰지 않고 읽지도 않는다 — 호출자가 방금 읽은 이벤트 목록
``(번호, 시각)`` 을 넘기면, 이 파일은 보낼 명령 줄만 돌려준다.

타임코드 한 트랙의 이벤트는 ``Timecode <tc>.1.<트랙>.1.1`` 컨테이너에 담기고, 이벤트 ``N`` 은
``<컨테이너>.<N>`` 으로 부른다. 명령 꼴은 실콘솔 실측 기록(레인 1)에서 그대로 옮겼다.

- 만들기: ``cd <컨테이너>`` → ``Store Property 'Time' T 'AbsTime' T 'Token' 'Go+'`` → ``cd root``
- 옮기기: ``Set <컨테이너>.<N> Property 'Time' T``
- 지우기: ``Delete <컨테이너>.<N>``

**이벤트 번호는 상수가 아니다.** 이벤트를 지우거나 만들면 뒤 번호가 밀린다(실측). 그래서 번호는
언제나 방금 읽은 목록에서 **시각으로** 찾는다. 시각이 맞는 이벤트가 정확히 하나가 아니면(없거나
모호하면) 엉뚱한 이벤트를 건드리지 않도록 ``TcCellIndexError`` 로 거절한다.

초 문자열은 에미터(``beat_grid_emit``)와 같은 ``songcue._format_seconds`` 로 만든다 — 포매터를
둘로 나누지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from server.looks.songcue import _format_seconds

__all__ = ["TcCellIndexError", "plan_tc_cell_commands", "tc_track_container"]

#: 이벤트 시각이 같다고 보는 오차(초, 절대값). 콘솔이 읽어 주는 시각은 소수 여섯 자리
#: (``83.784000``)이고 명령에 쓰는 초는 세 자리(``82.142``)라서, 그 반올림 차이만
#: 같은 시각으로 묶는다.
_TIME_MATCH_TOLERANCE_SECONDS = 0.01


class TcCellIndexError(ValueError):
    """시각으로 이벤트 번호를 하나로 정하지 못했다 — 맞는 이벤트가 없거나(0개) 모호하다(2개 이상).

    메시지는 감독에게 그대로 보여도 되는 한국어 사유다
    (`beat_grid_edit.BeatGridEditError`와 같은 계약).
    """


def tc_track_container(timecode_number: int, track_index: int) -> str:
    """타임코드 ``timecode_number`` 의 ``track_index`` 번째 트랙(1부터)의 이벤트 컨테이너 주소."""
    return f"Timecode {timecode_number}.1.{track_index}.1.1"


# @MX:NOTE: [AUTO] 이벤트 번호는 상수도 이전 읽기의 값도 아니다 — 지우기·만들기 뒤 번호가 밀리므로
#   ``events``(호출 직전에 읽은 목록)에서만 시각으로 찾는다. 콘솔을 읽거나 쓰지 않는 순수 함수다.
def plan_tc_cell_commands(
    op: str,
    container: str,
    events: Sequence[tuple[int, float]],
    *,
    from_seconds: float | None = None,
    to_seconds: float | None = None,
) -> list[str]:
    """칸 하나를 만들거나(``create``) 옮기거나(``move``) 지우는(``delete``) 명령 줄들.

    ``events`` 는 그 컨테이너를 방금 읽은 ``(이벤트 번호, 시각 초)`` 목록이다. ``create`` 는
    번호가 필요 없어 읽지 않는다. ``move``·``delete`` 는 ``from_seconds`` 와 오차
    0.01 초 안에서 맞는 이벤트가 **정확히 하나**일 때만 그 번호를 쓴다 — 없거나 둘 이상이면
    ``TcCellIndexError``. 모르는 ``op`` 나 빠진 시각은 그냥 ``ValueError`` 다.
    """
    if op == "create":
        seconds = _seconds_text(_required(to_seconds, "to_seconds", op))
        return [
            f"cd {container}",
            f"Store Property 'Time' {seconds} 'AbsTime' {seconds} 'Token' 'Go+'",
            "cd root",
        ]
    if op == "move":
        found_at = _required(from_seconds, "from_seconds", op)
        seconds = _seconds_text(_required(to_seconds, "to_seconds", op))
        index = _resolve_event_index(events, found_at)
        return [f"Set {container}.{index} Property 'Time' {seconds}"]
    if op == "delete":
        index = _resolve_event_index(events, _required(from_seconds, "from_seconds", op))
        return [f"Delete {container}.{index}"]
    raise ValueError(f"알 수 없는 동작입니다: {op!r} — create · move · delete 중 하나여야 합니다")


def _required(value: float | None, name: str, op: str) -> float:
    if value is None:
        raise ValueError(f"{op} 에는 {name} 가 필요합니다")
    return value


def _seconds_text(seconds: float) -> str:
    """초를 에미터와 같은 문자열로 — 밀리초 정수로 환산해 ``_format_seconds`` 에 넘긴다."""
    return _format_seconds(round(seconds * 1000))


def _resolve_event_index(events: Sequence[tuple[int, float]], seconds: float) -> int:
    """``seconds`` 와 오차 안에서 맞는 이벤트의 번호. 정확히 하나가 아니면 ``TcCellIndexError``."""
    matches = [
        index
        for index, event_seconds in events
        if abs(event_seconds - seconds) <= _TIME_MATCH_TOLERANCE_SECONDS
    ]
    if len(matches) != 1:
        raise TcCellIndexError(
            f"시각 {seconds} 초에 맞는 이벤트가 {len(matches)}개입니다"
            " — 하나여야 해서 건드리지 않습니다"
        )
    return matches[0]
