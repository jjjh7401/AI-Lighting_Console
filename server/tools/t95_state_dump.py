"""프리셋 **값** 판독 채널 조사용 원시 state 덤프 (t95).

한 경로의 `state` 회신을 **해석 없이** 그대로 찍는다. 기존 도구들은 요약만
출력해서(childCount·PASS/FAIL) 「값이 실려 오는가」를 판정할 수 없다 — 이 조사는
자식 목록과 필드가 실제로 무엇을 담는지를 봐야 하므로 원문이 필요하다.

읽기 전용이다. 실행 경로(`exec`)를 쓰지 않으며 콘솔 상태를 바꾸지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys

from server.safety.bootstrap import build_console_stack
from server.safety.console import StateQueryError
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", required=True, help="조회할 오브젝트 경로.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-host", default="127.0.0.1")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help=(
            "children 창의 0-기반 시작점 (PROTOCOL.md 4.2). 기본 0 은 토큰 없는 "
            "역사적 요청 바이트를 그대로 보낸다. 응답기가 페이징을 알면 회신에 "
            "offset 을 되돌려 준다 — 에코가 없으면 「진전 없음」이지 「끝」이 아니다."
        ),
    )
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
    try:
        payload = stack.gate.state_port.query_state(args.path, offset=args.offset)
    except StateQueryError as exc:
        # 거절은 예외로 온다 — 그 문면이 곧 증거다.
        print(f"state failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
