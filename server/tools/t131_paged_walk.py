"""페이징 루프를 **실기 응답기에 대고** 끝까지 걸어 완전성을 재는 프로브 (t131).

t131 첫 회차는 두 창(19+18=37)까지만 보고 「창이 전진한다」를 확인했다. 남은
질문은 하나였다 — **끝까지 걸으면 childCount 만큼 모이는가.** 그것을 여기서 잰다.

판정은 `truncated` 플래그가 아니라 **`len(모은 자식) == node.childCount`** 다.
「안 잘렸다」와 「이어 붙였다」는 다른 말이고, 첫 창만 쓰고 플래그만 지우는
구현도 앞의 단언은 통과한다.

읽기 전용이다. 실행 경로(`exec`)를 쓰지 않으며 콘솔 상태를 바꾸지 않는다.
"""

from __future__ import annotations

import argparse
import sys

from server.rig.paging import paged_children
from server.safety.bootstrap import build_console_stack
from server.safety.console import StateQueryError
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)


class _Counting:
    """포트를 감싸 요청한 offset 을 기록한다 — 창 크기가 증거의 일부다."""

    def __init__(self, port) -> None:
        self._port = port
        self.offsets: list[int] = []

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.offsets.append(offset)
        return self._port.query_state(path, offset=offset)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", required=True, help="걸어 볼 오브젝트 경로.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-host", default="127.0.0.1")
    add_listen_port_argument(parser)
    parser.add_argument("--timeout-seconds", type=float, default=6.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_host=args.listen_host,
        receive_port=args.listen_port,
        attempt_session_backup=False,
    )
    port = _Counting(stack.gate.state_port)
    try:
        first = port.query_state(args.path)
    except StateQueryError as exc:
        print("state failed: " + str(exc), file=sys.stderr)
        return 1
    node = first.get("node") or dict()
    total = node.get("childCount")
    children, truncated = paged_children(port, args.path, first)

    print("path          : " + args.path)
    print("childCount    : " + str(total))
    print("collected     : " + str(len(children)))
    print("truncated     : " + str(truncated))
    print("offsets sent  : " + str(port.offsets))
    print("window sizes  : " + str(_window_sizes(port.offsets, len(children))))
    complete = isinstance(total, int) and not isinstance(total, bool) and len(children) == total
    print("VERDICT       : " + ("COMPLETE" if complete else "INCOMPLETE"))
    if not complete:
        print("  -- 모은 개수가 childCount 와 다르다. 부분을 전체로 읽지 마라.")
    return 0 if complete else 2


def _window_sizes(offsets: list[int], collected: int) -> list[int]:
    """요청 오프셋의 차분 — 창 크기가 회차마다 변하는지 그 자리에서 읽힌다."""
    marks = offsets + [collected]
    return [b - a for a, b in zip(marks, marks[1:], strict=False)] or [collected]


if __name__ == "__main__":
    raise SystemExit(main())
