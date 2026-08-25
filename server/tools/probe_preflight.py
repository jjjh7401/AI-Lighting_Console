"""프로브 도구 공용 프리플라이트 — 침묵을 **진단으로** 바꾼다.

이 모듈이 푸는 문제는 포트 숫자가 아니라 **침묵의 모호성**이다.

응답 포트를 틀리게 잡고 쏘면 아무 회신도 안 온다. 그런데 응답기가 죽어 있어도
아무 회신이 안 온다. **두 침묵이 구분되지 않는다.** 그래서 조작자는 멀쩡한
포트 설정을 의심하거나, 죽은 응답기를 두고 포트를 만진다.

`--listen-port` 를 필수 인자로 만드는 것은 **절반짜리 처방이다.** 조용히
기본값으로 틀리는 것은 막지만, 사람이 틀린 값을 **명시하면** 침묵은 똑같이
모호하다. 나머지 절반이 이 프리플라이트다.

기전은 새로 짓지 않는다 — `server/web/reply_discovery.py` 가 앱 런타임을 위해
이미 지어 놨고(같은 사고를 독스트링에 적어 뒀다: *"the settings screen would say
9000 while the runtime listened on 9005"*), 도구들이 그것을 안 쓰고 있었을 뿐이다.
그 모듈의 네 가지 경계(보고만 하고 채택 안 함 · 송신은 게이트 하나 · 콘솔 입력
포트는 절대 바인드 안 함 · 링크가 죽었을 때만)를 그대로 물려받는다.
"""

from __future__ import annotations

import argparse

from server.safety.monitor import HealthMonitor
from server.tools.tree_identity import assert_same_tree
from server.web.reply_discovery import discover_reply_port

assert_same_tree(__file__)

#: 현장 실측값. **기본값으로 쓰지 않는다** — 도구는 말하게 한다(아래 참조).
#: 도움말에만 실어 조작자가 무엇을 적어야 할지 알게 한다.
SITE_LISTEN_PORT = 9005

_HELP = (
    "회신 수신 포트. **기본값 없음** — 이 저장소의 하네스들이 9005 와 9000 으로 "
    "갈려 있었고(t61), 기본값에 기대면 틀린 포트로 조용히 쏜 뒤 그 침묵을 "
    "「응답기가 죽었다」로 오독한다. 현장 실측값은 " + str(SITE_LISTEN_PORT) + "."
)


def add_listen_port_argument(parser: argparse.ArgumentParser) -> None:
    """모든 콘솔 접촉 도구가 쓰는 단 하나의 `--listen-port` 선언.

    도구마다 따로 선언하면 기본값이 다시 갈린다 — t61 이 정확히 그렇게 났다
    (17개 중 9005 셋 · 9000 셋 · 손수 파싱한 침묵 기본값 다섯).
    `test_probe_port_discipline.py` 가 이 함수를 **쓰는지**가 아니라 도구에
    기본값이 **없는지**를 전수로 재므로, 우회해도 걸린다.
    """
    parser.add_argument("--listen-port", type=int, required=True, help=_HELP)


def preflight(gate, *, receive_host: str, receive_port: int, console_port: int) -> dict:
    """응답기가 답하는지 보고, 안 답하면 **왜 안 답하는지**까지 말한다.

    반환하는 `verdict` 는 셋 중 하나다.

    * `responder_ok` — 하트비트가 돌아왔다. 발견 비용 0.
    * `port_mismatch` — 설정한 포트로는 조용한데 **다른 후보로 회신이 왔다.**
      그 포트 번호를 이름으로 댄다. 채택하지는 않는다(REQ-DEPLOY-026 —
      조용히 바꾸는 것이 같은 병의 부호 반대다).
    * `responder_silent` — **들을 수 있었던 후보 전부**에 안 왔다. 포트 문제가
      아니다.
    * `discovery_incomplete` — 후보 중 못 바인드한 것이 있고 회신도 못 봤다.
      **위 둘 중 어느 판정도 못 한다.**

    넷째를 셋째로 접지 않는 것이 이 함수의 요점이다. 「아무 데도 없다」와
    「다 못 봐서 못 찾았다」는 다른 사건인데 결과가 같아 보인다 — 접으면 이
    카드가 없애려던 모호성을 다른 자리로 옮기는 것이다. `reply_discovery` 가
    `unbindable` 을 접지 않고 따로 보고하는 이유가 그것이고, 여기서도 접지
    않는다.
    """
    state = gate.heartbeat()
    if state == HealthMonitor.ONLINE:
        return dict(verdict="responder_ok", health=str(state), configured_port=receive_port)

    result = discover_reply_port(
        send_ping=gate.heartbeat,
        receive_host=receive_host,
        receive_port=receive_port,
        console_port=console_port,
    )
    mismatch = result.mismatch
    report = dict(
        health=str(state),
        configured_port=result.configured_port,
        candidates=list(result.candidates),
        listened=list(result.listened),
        unbindable=list(result.unbindable),
        observed_port=result.observed_port,
        send_error=result.send_error,
    )
    if mismatch is not None:
        report["verdict"] = "port_mismatch"
        report["detail"] = (
            "설정한 포트 "
            + str(mismatch.configured)
            + " 으로는 회신이 없고 "
            + str(mismatch.observed)
            + " 으로 왔다. 응답기는 살아 있다 — 포트를 맞춰라. "
            "이 도구는 포트를 바꾸지 않는다"
        )
        return report
    if result.unbindable:
        report["verdict"] = "discovery_incomplete"
        report["detail"] = (
            "후보 "
            + str(len(result.unbindable))
            + "개를 못 들었다("
            + ", ".join(str(port) for port in result.unbindable)
            + "). 회신도 못 봤지만 **그것을 「응답기가 안 답한다」로 읽으면 안 된다** "
            "— 안 들은 포트로 왔을 수 있다. 그 포트를 쥔 프로세스를 정리하고 다시 재라"
        )
        return report
    report["verdict"] = "responder_silent"
    report["detail"] = (
        "후보 포트 전부를 들었고 어디에도 회신이 없다. 포트 불일치가 아니라 "
        "응답기가 안 답하는 것이다"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    """프리플라이트만 단독으로 돌린다 — `ping` 하나 외에 아무것도 안 쏜다.

    도구에 붙이기 전에 **이것부터 재라.** 틀린 포트와 맞는 포트로 각각 한 번씩
    돌려 **서로 다른 이름의 진단**이 나오는지 보는 것이 이 기능의 비공허성
    검사다. 둘 다 같은 답이 나오면 아무것도 안 가른 것이다.
    """
    import json

    from server.safety.bootstrap import build_console_stack

    parser = argparse.ArgumentParser(description="응답 포트 프리플라이트 (ping 전용)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    args = parser.parse_args(argv)

    stack = build_console_stack(
        send_host=args.host, send_port=args.port, receive_port=args.listen_port
    )
    try:
        report = preflight(
            stack.gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
    finally:
        stack.stop()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
