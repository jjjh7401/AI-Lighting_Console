"""SPEC-LDSEND-001 M2 · REQ-LDSEND-001/002/003/004.

``server.director.execution.BundleSender`` 프로토콜의 실물 구현체. 이 층은
판단(어떤 명령을 보낼지)도 승인(누가 허락했는지)도 하지 않는다 — 그 결정은
이미 ``SPEC-LDRECV-001`` 의 ``ApplyCoordinator``/``ApprovalRegistry`` 가
끝냈다. 이 모듈이 만드는 것은 승인된 명령을 공유 ``SafetyGate`` 를 통해
실제로 보내고, 결과를 정직하게 분류해 돌려주는 한 단계뿐이다(spec.md §1).

명령은 오직 공유 ``SafetyGate.execution_port``(명령 하나를 보내고
``ExecutionResult`` 를 반환하는 실행 포트)로만 보낸다 — ``server.bridge`` 를
이 모듈은 직접 import 하지 않는다(REQ-LDSEND-001).

.. note::
   ``server/director`` 경계 시험(``test_director_boundary.py``,
   SPEC-LDSTORE-001)이 이 패키지 전체에서 실행 포트 타입 이름을 문자열로
   금지한다 — 그래서 이 모듈은 그 타입을 이름으로 import 하지 않고, 구조적
   타이핑(로컬 ``Protocol``)으로만 그 모양을 표현한다. 런타임 동작은
   동일하다 — 어차피 ``gate.execution_port`` 는 덕타이핑으로 소비된다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from server.director.execution import STATE_ACKNOWLEDGED, STATE_FAILED, STATE_UNKNOWN
from server.orchestrator.ports import ExecutionResult


class _ExecutionPort(Protocol):
    """``execution_port`` 가 만족해야 하는 구조적 타입 — 명령 하나를 보내고
    ``ExecutionResult`` 를 반환한다. 실물 ``server.safety.gate.SafetyGate.
    execution_port`` 가 이 타입을 구조적으로 만족한다(상속 불필요)."""

    def execute(self, command: str) -> ExecutionResult: ...


class GateBundleSender:
    """``BundleSender`` 프로토콜의 실물 구현 — 공유 ``execution_port`` 로만 보낸다.

    클리어런스 회수(REQ-LDSEND-005/006)는 이 클래스의 책임이 아니다 —
    ``server.director.execution.run_director_apply()`` 가
    ``execute_bundles()`` 반환 직후(성공이든 예외든) 처리한다(§2.0-나/마
    plan.md). ``send()`` 는 ``execution_port.execute()`` 만 부르고 그 밖의
    부수 효과를 일으키지 않는다.
    """

    def __init__(self, execution_port: _ExecutionPort) -> None:
        self._execution_port = execution_port

    def send(self, bundle: Mapping[str, Any]) -> str:
        """``bundle["commands"]`` 를 순서대로 보내고, 확인되지 않은(ok 가 아닌)
        첫 결과 뒤로는 같은 번들의 남은 명령을 보내지 않는다(REQ-LDSEND-002).

        번들 판정 표(plan.md §4 M2, REQ-LDSEND-003 의 구체화):

        - 모든 명령이 확인됨(ok) → ``STATE_ACKNOWLEDGED``.
        - 첫 명령부터 명시적 실패, 그 전 확인된 명령 없음 → ``STATE_FAILED``.
        - 어떤 명령이든 미확인(timeout) → ``STATE_UNKNOWN``.
        - 앞서 확인된 명령이 있는 상태에서 뒤 명령이 명시적 실패(부분 완료)
          → ``STATE_UNKNOWN`` (계약 "atomic OSC rollback 을 주장하지
          않는다"의 구체화 — 콘솔에 이미 일부가 도달했으므로 ``failed`` 로
          부를 수 없고, 전부가 확인된 것도 아니므로 ``ACKNOWLEDGED`` 도
          아니다).
        - 콘솔 링크 호출이 예외를 던짐 → 그 명령을 unconfirmed 로 취급하고
          번들 전체 ``STATE_UNKNOWN``(REQ-LDSEND-004 — 예외가 ``send()``
          밖으로 전파되지 않는다).

        ``STATE_SENT`` 는 반환하지 않는다 — ``ConsoleLink.execute()`` 자체가
        확인 또는 timeout 까지 블록하므로, "보냈지만 아직 확인 대기 중"이라는
        중간 상태가 ``send()`` 반환 시점에는 존재하지 않는다.
        """
        confirmed_any = False
        for command in bundle["commands"]:
            try:
                result = self._execution_port.execute(command)
            except Exception:  # noqa: BLE001 — REQ-LDSEND-004: 예외를 unconfirmed 로 흡수
                return STATE_UNKNOWN

            if result.outcome == "ok":
                confirmed_any = True
                continue

            if result.outcome == "failed" and not confirmed_any:
                return STATE_FAILED

            # unconfirmed, 또는 확인된 명령 뒤의 명시적 실패(부분 완료) —
            # 둘 다 "불확실하면 unknown 이다" 로 접는다.
            return STATE_UNKNOWN

        return STATE_ACKNOWLEDGED
