"""SPEC-LDSEND-001 M3~M4 · REQ-LDSEND-007/008/009/011/012 — 로컬 관측 도구 골격.

AC-LDPLUGIN-021(승격부)·024(관측부)·032(실행부) 세 콘솔 게이트 항목을 로컬
checkout 에서 실기로 관측하기 위한 하네스다(spec.md §1). 이 도구는 판단(어떤
명령을 보낼지)도 승인(누가 허락했는지)도 하지 않는다 — 그 결정은 이미
``SPEC-LDRECV-001`` 의 ``ApplyCoordinator``/``ApprovalRegistry`` 가 끝냈다.

## 진입점은 공유 함수 하나뿐이다(REQ-LDSEND-007/015, §2.0-마 plan.md)

이 도구는 ``server.director.execution.run_director_apply()`` 만 호출한다 —
``server.director.director_api``(``fastapi`` 의존)는 import 하지 않는다.
콘솔 접근은 오직 ``server.safety.bootstrap.build_console_stack`` 으로만
구성한다 — ``server.bridge`` 를 직접 열지 않는다.

## 로컬 승인 — 운영 승인이 아니다(REQ-LDSEND-012)

이 도구가 시나리오 구동을 위해 만드는 ``ApprovalBinding`` 은 도구 자신의
로컬 ``DirectorStore``/``ApprovalRegistry`` 인스턴스(``server/web/serve.py``
운영 조립과 무관, 별도 프로세스 수명)에서 공개 API
``ApprovalRegistry.approve()`` 로만 발급된다 — ``principal_id`` 는 고정
문자열 ``ldsend-observe-harness`` 로 로컬 관측 하네스 산출물임을 표시한다.

## 이 마일스톤(M3)의 범위

이 파일은 **골격**이다 — 인자 파싱, dry-run 기본값, 로컬 plan/승인 구성
헬퍼, cleanup 출력, ``run_director_apply()`` 배선까지만 M3 의 범위다. 시나리오
본문(021 의 실제 큐 내용, 024 의 M4a 가 확정할 실패 유발 명령, 032 의
recovery 배선, REQ-LDSEND-008 의 destination 점유 확인, REQ-LDSEND-010 의
readback 확인, REQ-LDSEND-014 의 백업 선행조건 관측)은 전부 ``@MX:TODO`` 로
표시된 M3~M4 자리표시자다 — 실제 로직은 M4 가 채운다(plan.md §4 M3~M4).

Usage(dry-run, 콘솔로는 아무것도 안 나간다)::

    uv run python -m server.tools.director_apply_observe 021 --listen-port 9005

Usage(실행 — 세션 시작 백업(SaveShow) 포함, 콘솔에 실제로 씀)::

    uv run python -m server.tools.director_apply_observe 021 --listen-port 9005 --execute

This is a DEV TOOL, not a production execution path — exempt from the
REQ-MVP-029 single-chokepoint rule the same way ``responder_roundtrip``/
``busking_e2e`` are (the M4 import-boundary test whitelists ``server.tools``).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.director.approvals import ApprovalBinding, ApprovalRegistry, ContextRef, ValidationRef
from server.director.execution import ApplyCoordinator, ExecutionJournal, run_director_apply
from server.director.service import OUTCOME_READY
from server.director.store import DirectorStore
from server.orchestrator.bundle_sender import GateBundleSender
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

#: REQ-LDSEND-012 — 이 도구가 만드는 모든 ApprovalBinding 을 표시하는 고정
#: 문자열. 이 값이 로컬 관측 하네스 산출물이라는 구분자다(운영 principal
#: 이름과 절대 겹치지 않는다).
HARNESS_PRINCIPAL_ID = "ldsend-observe-harness"

#: 이 도구가 로컬로 구성하는 context/compiled digest — 실제 LDCOMPILE
#: manifest 와 무관한, 도구 자신의 로컬 plan/승인 쌍에서만 쓰는 값이다.
_HARNESS_CONTEXT_DIGEST = "ldsend-observe-context-digest-1"

#: spec.md §5 go-table 이 관측하겠다고 약속한 세 콘솔 게이트 항목.
SCENARIOS: dict[str, str] = {
    "021": "AC-LDPLUGIN-021 승격부 — apply 가 실제로 콘솔에 적용됐는가",
    "024": "AC-LDPLUGIN-024 관측부 — 실패 뒤 후속 bundle 이 실기에서도 안 갔는가",
    "032": "AC-LDPLUGIN-032 실행부 — recovery apply 가 실제로 적용됐는가",
}

#: 시나리오마다 스크래치 destination 을 다른 Sequence 번호로 나눈다(같은
#: --sequence-range-start 로 여러 시나리오를 돌려도 서로 덮어쓰지 않도록).
_SEQUENCE_OFFSETS: dict[str, int] = {"021": 0, "024": 1, "032": 2}


@dataclass(frozen=True)
class ScenarioPlan:
    """시나리오 하나의 계획 — dry-run 이 그대로 출력하는 대상."""

    scenario: str
    description: str
    destination: dict[str, str]
    bundles: list[dict[str, Any]]


def _plan_for_scenario(scenario: str, *, sequence_range_start: int) -> ScenarioPlan:
    """시나리오 하나의 계획을 만든다.

    @MX:TODO M4 가 채운다 — 021 의 실제 큐 내용, 024 의 M4a 가 실기로 확정할
    실패 유발 명령(plan.md §2.0-라 두 후보), 032 의 recovery 배선(``body``
    의 ``recovery_of``)은 이 마일스톤의 범위가 아니다. 지금 이 함수는
    ``run_director_apply()`` 를 실제로 한 번 타게 하는 최소 자리표시자
    bundle 만 만든다(plan.md §4 M3~M4 1단계) — 명령은 이미 이 코드베이스
    전체가 안전 대조군으로 쓰는 ``"Fixture 901 At 50"``(예: ``server/tests/
    test_director_ops_lifecycle.py``)이다. blacklist 계열(``Store
    Sequence``/``Store Cue``)로 바뀌면 REQ-LDSEND-014 의 백업 선행조건
    관측도 함께 배선해야 한다 — 그 배선은 M4 의 몫이다(spec.md §1 규범표).
    """
    if scenario not in SCENARIOS:
        raise ValueError(
            f"알 수 없는 시나리오: {scenario!r} — {sorted(SCENARIOS)} 중 하나여야 한다."
        )

    sequence_id = sequence_range_start + _SEQUENCE_OFFSETS[scenario]
    destination = {"show_id": "1", "sequence_id": str(sequence_id)}
    bundles: list[dict[str, Any]] = [
        {
            "bundle_id": f"ldsend-observe-{scenario}-bundle-1",
            # @MX:TODO M4 확정 — 자리표시자 명령. 위 함수 docstring 참고.
            "commands": ["Fixture 901 At 50"],
        }
    ]
    return ScenarioPlan(
        scenario=scenario,
        description=SCENARIOS[scenario],
        destination=destination,
        bundles=bundles,
    )


def _build_local_approval(
    *,
    store: DirectorStore,
    approvals: ApprovalRegistry,
    project_id: str,
    plan_id: str,
    destination: Mapping[str, str],
) -> ApprovalBinding:
    """도구 자신의 로컬 ``DirectorStore``/``ApprovalRegistry`` 인스턴스에서
    공개 API ``ApprovalRegistry.approve()`` 로 진짜 ``ApprovalBinding`` 을
    발급한다(§2.0-마 plan.md, REQ-LDSEND-012).

    ``server/tests/test_director_ops_lifecycle.py`` 가 쓰는 ``_register()``
    private dict 지름길은 쓰지 않는다 — 그건 시험 전용이고, 이 도구는 시험이
    아니라 운영에 가까운 하네스다(plan.md §2.0-마 항목 2).
    """
    record = store.submit(
        plan={
            "project_id": project_id,
            "plan_id": plan_id,
            "base_revision": 0,
            "body": {"destination": dict(destination)},
        },
        expected_revision=0,
        principal_id=HARNESS_PRINCIPAL_ID,
        operation="PUT plan (ldsend-observe)",
        idempotency_key=f"{plan_id}-submit",
    )

    compiled_digest = _compiled_digest_for(plan_id)
    expires_at = "2099-01-01T00:00:00Z"
    validation = ValidationRef(
        validation_id=f"{plan_id}-validation",
        plan_digest=record.plan_digest,
        context_digest=_HARNESS_CONTEXT_DIGEST,
        compiled_digest=compiled_digest,
        expires_at=expires_at,
        outcome=OUTCOME_READY,
    )
    context = ContextRef(
        context_digest=_HARNESS_CONTEXT_DIGEST,
        expires_at=expires_at,
        console_id="ldsend-observe-console",
        session_id="ldsend-observe-session",
        safety_policy_revision=1,
    )
    return approvals.approve(
        store=store,
        project_id=project_id,
        plan_id=plan_id,
        revision=record.revision,
        principal_id=HARNESS_PRINCIPAL_ID,
        validation=validation,
        context=context,
        body={
            "idempotency_key": f"{plan_id}-approve",
            "validation_id": validation.validation_id,
            "plan_digest": record.plan_digest,
            "context_digest": _HARNESS_CONTEXT_DIGEST,
            "compiled_digest": compiled_digest,
        },
        operation="POST plan approval (ldsend-observe)",
    )


def _compiled_digest_for(plan_id: str) -> str:
    """``_build_local_approval`` 이 발급하는 승인과 apply 요청 본문이 같은
    ``compiled_digest`` 를 참조하도록 결정론적으로 계산한다 — 실제
    LDCOMPILE manifest digest 가 아니라, 이 도구의 로컬 plan/승인 쌍
    안에서만 일관되면 되는 값이다(``check_validity`` 가 이 값의 동등성만
    비교한다, approvals.py)."""
    return f"ldsend-observe-compiled-digest-{plan_id}"


def _run_scenario(*, scenario: str, stack: Any, sequence_range_start: int) -> dict[str, Any]:
    """시나리오 하나를 ``run_director_apply()`` 로 실제로 구동한다.

    도구 자신의 로컬 ``DirectorStore``/``ExecutionJournal``/
    ``ApprovalRegistry`` 를 process 수명(이 함수 호출) 동안만 만들고,
    ``ApplyCoordinator`` 는 그 로컬 셋과 **진짜** ``stack.gate`` 를 섞어
    구성한다(§2.0-마 plan.md 항목 3) — ``gate`` 만 운영과 같은 진짜
    ``SafetyGate`` 다.

    @MX:TODO M4 가 채운다 — REQ-LDSEND-008(destination 점유 확인),
    REQ-LDSEND-010(readback 재확인), REQ-LDSEND-014(백업 선행조건 관측)
    로직은 아직 여기 없다. 이 함수는 ``run_director_apply()`` 호출 경로
    자체(REQ-LDSEND-007)만 실제로 탄다.
    """
    plan = _plan_for_scenario(scenario, sequence_range_start=sequence_range_start)
    project_id = "ldsend-observe"
    plan_id = f"ldsend-observe-{scenario}"

    with tempfile.TemporaryDirectory(prefix="ldsend-observe-") as tmp:
        tmp_path = Path(tmp)
        store = DirectorStore(tmp_path / "director.sqlite3")
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        approvals = ApprovalRegistry()
        try:
            binding = _build_local_approval(
                store=store,
                approvals=approvals,
                project_id=project_id,
                plan_id=plan_id,
                destination=plan.destination,
            )
            coordinator = ApplyCoordinator(
                journal=journal, approvals=approvals, store=store, gate=stack.gate
            )
            body: dict[str, Any] = {
                "approval_id": binding.approval_id,
                "idempotency_key": f"{plan_id}-apply",
                "destination": dict(plan.destination),
                "bundles": [dict(bundle) for bundle in plan.bundles],
                "compiled_digest": binding.compiled_digest,
            }
            response_body, response_status = run_director_apply(
                coordinator=coordinator,
                journal=journal,
                bundle_sender=GateBundleSender(stack.gate.execution_port),
                interference=None,
                project_id=project_id,
                plan_id=plan_id,
                revision=binding.plan_revision,
                principal_id=HARNESS_PRINCIPAL_ID,
                operation=f"POST plan {plan_id} apply (ldsend-observe)",
                current_context_digest=_HARNESS_CONTEXT_DIGEST,
                body=body,
            )
        finally:
            journal.close()
            store.close()

    return {
        "scenario": scenario,
        "plan": plan,
        "approval_id": binding.approval_id,
        "response_body": response_body,
        "response_status": response_status,
    }


def _cleanup_commands(destination: Mapping[str, Any]) -> list[str]:
    """REQ-LDSEND-011 — 이 도구는 이 명령을 콘솔로 보내지 않는다. 표준출력에
    문자열만 낸다. 사람이 직접 콘솔에 실행한다."""
    return [f"Delete Sequence {destination['sequence_id']}"]


def _print_plan(plan: ScenarioPlan, *, execute: bool) -> None:
    print(f"# scenario {plan.scenario} — {plan.description}")
    print(f"destination: {plan.destination}")
    print("commands:")
    for bundle in plan.bundles:
        for command in bundle["commands"]:
            print(f"  {command}")
    if execute:
        print(
            "--execute — 이 실행은 세션 시작 시 실제 콘솔 백업(SaveShow)을 "
            "보냅니다(D11, bootstrap.py attempt_session_backup=True)."
        )
    else:
        print(
            "dry-run — 콘솔로는 아무것도 보내지 않습니다(세션 시작 백업 "
            "포함, D11 — build_console_stack(attempt_session_backup=False))."
        )


def _print_result(result: dict[str, Any]) -> None:
    print(f"approval_id: {result['approval_id']}")
    print(f"response_status: {result['response_status']}")
    print(f"response_body: {result['response_body']}")
    print(
        "readback 재확인은 아직 없다(REQ-LDSEND-010, M4 의 몫) — 위 결과는 "
        "BundleSender 가 돌려준 상태만 담는다."
    )


def _print_cleanup(destination: Mapping[str, Any]) -> None:
    print(
        "# cleanup — 아래 명령은 이 도구가 콘솔로 보내지 않는다. 사람이 "
        "직접 콘솔에 실행한다(REQ-LDSEND-011)."
    )
    for command in _cleanup_commands(destination):
        print(command)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="director_apply_observe",
        description=(
            "SPEC-LDSEND-001 M3~M4 로컬 관측 도구 — director-apply 경로"
            "(AC-LDPLUGIN-021/024/032)를 실기로 관측한다."
        ),
    )
    parser.add_argument(
        "scenario",
        choices=sorted(SCENARIOS),
        help=(
            "관측할 시나리오 — 021(승격부)/024(관측부)/032(실행부). "
            "1회 실행(run) = 시나리오 1개(REQ-LDSEND-008 D12)."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="콘솔 OSC 송신 목적지 host.")
    parser.add_argument("--port", type=int, default=8000, help="콘솔 OSC 송신 목적지 port.")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help=(
            "명시하지 않으면 dry-run(계획만 출력, 콘솔로 아무것도 보내지 "
            "않음 — 세션 시작 백업 포함, REQ-LDSEND-009). 지정하면 실제로 "
            "콘솔에 쓴다."
        ),
    )
    parser.add_argument(
        "--sequence-range-start",
        type=int,
        default=9900,
        help=(
            "스크래치 destination 으로 쓸 Sequence 번호대의 시작값(기본 "
            "9900) — 쓰기 전 비어 있는지 확인한다(REQ-LDSEND-008, 확인 "
            "로직 자체는 M4)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # REQ-LDSEND-009/D11 — 인자 파싱을 먼저 끝내고(--execute 여부 확정), 그
    # 뒤에야 스택을 구성한다(dry-run 이면 attempt_session_backup=False).
    args = build_arg_parser().parse_args(argv)
    plan = _plan_for_scenario(args.scenario, sequence_range_start=args.sequence_range_start)
    _print_plan(plan, execute=args.execute)

    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        attempt_session_backup=args.execute,
    )
    try:
        if not args.execute:
            return 0
        try:
            result = _run_scenario(
                scenario=args.scenario,
                stack=stack,
                sequence_range_start=args.sequence_range_start,
            )
        except Exception as error:  # noqa: BLE001 — 실패도 사람이 읽을 형태로 보고한다
            print(f"실행 실패: {error!r}")
            return 1
        finally:
            # REQ-LDSEND-011 — 성공이든 실패든 cleanup 명령은 항상 출력한다.
            _print_cleanup(plan.destination)
        _print_result(result)
        return 0
    finally:
        stack.stop()


if __name__ == "__main__":
    sys.exit(main())
