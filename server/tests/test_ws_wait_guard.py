"""`recv_frame` 이 실제로 상한을 거는지 잰다 (t52).

이 파일이 없으면 승격은 **아무것도 안 지킨다**. 옮긴 것과 지키는 것은 다른
작업이고, 상한을 지우면 실패가 아니라 **정지**로 나타나므로 평범한 테스트로는
안 잡힌다 — 그래서 「안 끝나는 것」을 바깥에서 재는 형태가 필요하다.
"""

from __future__ import annotations

import ast
import threading
import time
from pathlib import Path

import pytest

from .conftest import drain_until, recv_frame


class _NeverAnswers:
    """`receive_json` 이 영영 돌아오지 않는 소켓 — 사건의 모양 그대로."""

    def __init__(self) -> None:
        self.entered = threading.Event()

    def receive_json(self):
        self.entered.set()
        while True:  # 상한은 recv_frame 쪽에 있어야 한다
            time.sleep(0.05)


class _AnswersWrongForever:
    """계속 답하되 **원하는 종류는 영영 안 주는** 소켓."""

    def receive_json(self):
        return dict(type="status")


def test_recv_frame_fails_instead_of_hanging_when_no_frame_arrives():
    ws = _NeverAnswers()
    started = time.monotonic()
    with pytest.raises(AssertionError) as caught:
        recv_frame(ws, timeout=0.3)
    elapsed = time.monotonic() - started

    assert ws.entered.is_set(), "수신을 시도하지도 않았다면 이 테스트는 공허하다"
    assert "no websocket frame within 0.3s" in str(caught.value)
    assert elapsed < 5.0, "상한이 안 걸렸다: " + str(round(elapsed, 1)) + "s"


def test_drain_until_stops_on_the_frame_count_when_frames_keep_arriving():
    """프레임은 오는데 원하는 종류가 안 오는 경우 — 회수 상한이 끊는다."""
    with pytest.raises(AssertionError) as caught:
        drain_until(_AnswersWrongForever(), "chat_response", limit=3)
    assert "within 3 frames" in str(caught.value)
    assert "status" in str(caught.value), "무엇을 봤는지 보고해야 진단이 된다"


# --------------------------------------------------------------------------
# 직접 호출 트립와이어 (t56)
#
# t54 가 66자리를 `recv_frame` 으로 옮겼지만 「새로 직접 호출을 쓰지 마라」는
# 강제되지 않았다. 이관이 끝난 순간부터 새 자리가 **조용히** 다시 는다 —
# 직접 호출은 시간 상한이 없어 실패가 아니라 **정지**로 나타나고, 정지는
# 리뷰에서 안 보인다.
#
# 🔴 왜 문자열이 아니라 AST 인가 — 실측(t56, base 023c5a8):
#     AST 기준 호출 자리        1  (conftest 의 승격 헬퍼)
#     문자열 'receive_json'     7줄
# 나머지 6줄은 독스트링 2 + **가짜 소켓의 def receive_json 4**다. 가짜 소켓은
# 이 파일에도 둘 있고 **있어야 하는 것**이다. 문자열로 재면 정당한 가짜 소켓을
# 하나 더 만들 때마다 빨개지고, 그러면 다음 사람이 검사를 끈다.
# --------------------------------------------------------------------------

#: 직접 호출이 허용되는 **자리** — 승격 헬퍼 안 한 곳뿐이다.
#:
#: 개수(== 1)로 적지 않는다. 개수는 옛 자리가 사라지고 새 자리가 생기면 그대로
#: 통과한다 — 이 저장소는 len(REGISTRY) == 2 류를 이미 한 번 조건 검사로 바꿨다.
#: 재는 것은 「몇 개인가」가 아니라 **「허용 밖이 있는가」**다.
#:
#: 자리 이름이 recv_frame 이 아니라 recv_frame.pump 인 것은 실측이다 — 그 호출은
#: recv_frame **안의 중첩 함수**(수신 스레드의 target)에 있다. 스캐너가 가장 안쪽
#: 함수에 귀속하므로 중첩 경로를 그대로 적는다. recv_frame 으로 적었더니 빨간불이
#: 났고, 그 빨간불이 이 키의 모양을 알려 줬다.
_ALLOWED_DIRECT_RECEIVE = frozenset([("conftest.py", "recv_frame.pump")])


def _direct_receive_json_calls(source: str) -> set:
    """`.receive_json(` **호출** 자리 — (감싼 함수 이름, 줄).

    정의(``def receive_json``)와 독스트링 언급은 세지 않는다. 가장 안쪽 함수에
    귀속하므로 중첩 함수 안의 호출이 바깥 함수 이름으로 잘못 붙지 않는다.
    """
    found = set()
    stack = []

    class _Visitor(ast.NodeVisitor):
        def _enter_function(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()

        visit_FunctionDef = _enter_function
        visit_AsyncFunctionDef = _enter_function

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "receive_json":
                found.add((".".join(stack) if stack else "<module>", node.lineno))
            self.generic_visit(node)

    _Visitor().visit(ast.parse(source))
    return found


class TestDirectReceiveJsonDoesNotGrow:
    """승격이 지켜지는가 — 옮긴 것과 지키는 것은 다른 작업이다."""

    def test_no_direct_call_outside_the_promoted_helper(self):
        tests_dir = Path(__file__).parent
        scanned = 0
        found = set()

        for path in sorted(tests_dir.rglob("*.py")):
            scanned += 1
            for function, _line in _direct_receive_json_calls(path.read_text(encoding="utf-8")):
                found.add((path.name, function))

        # 비공허성 — 훑은 파일이 0이면 아래 단언은 아무 뜻이 없다.
        assert scanned > 10, "훑은 파일이 " + str(scanned) + "개뿐이다 — 스캔이 안 돌았다"

        offenders = found - _ALLOWED_DIRECT_RECEIVE
        assert offenders == set(), (
            "승격 헬퍼 밖에서 ws.receive_json() 을 직접 부른다 — 그 자리에는 시간 "
            "상한이 없어 실패가 아니라 정지로 나타난다. conftest 의 recv_frame 을 "
            "써라: " + str(sorted(offenders))
        )

    def test_the_scanner_catches_a_planted_call(self):
        """날조 대조군 — 안 잡으면 위 검사는 그물이 아니라 장식이다."""
        planted = "def somewhere(ws):\n    return ws.receive_json()\n"

        assert _direct_receive_json_calls(planted) == set([("somewhere", 2)])

    def test_the_scanner_ignores_definitions_and_prose(self):
        """정의와 산문은 위반이 아니다 — 가짜 소켓은 있어야 하는 것이다.

        이 검사가 없으면 스캐너를 문자열 매칭으로 되돌려도 위 둘이 통과한다.
        그 되돌림이 바로 이 트립와이어가 피하려는 형태다.
        """
        not_a_call = (
            "class Fake:\n"
            '    """recv_frame 은 ws.receive_json() 만 부른다."""\n'
            "\n"
            "    def receive_json(self):\n"
            "        return dict(type='status')\n"
        )

        assert _direct_receive_json_calls(not_a_call) == set()
