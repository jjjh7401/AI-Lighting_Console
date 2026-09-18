"""SPEC-LDSEND-001 M3~M4 · REQ-LDSEND-007/008/009/010/011/012/014 — 로컬 관측 도구.

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

## M4 — 시나리오 배선

세 시나리오 모두 스크래치 destination 에 ``Store Sequence <N> Cue 1
/Merge`` 를 채우는 것으로 시작한다(§2.0-라 plan.md 1단계와 같은 형태).

- **021**: 채움 bundle 하나 → readback(``state_port.query_state``)으로
  object-existence 를 확인한다(REQ-LDSEND-010).
- **024**: 채움 bundle → 같은 destination 에 재시도하는 실패 유발
  bundle(REQ-LDSEND-002/024) → **다른** scratch destination 에 쓰려는
  세 번째 bundle(전혀 나가지 않아야 한다) → readback 이 채운 destination
  은 존재를, 안 쓴 destination 은 부재를 확인한다. 실패 유발 명령은 M4a 가
  실기로 확정해야 하므로(plan.md §2.0-라), ``--confirmed-failure-command``
  없이는 ``--execute`` 를 거부한다 — dry-run 은 두 후보를 그대로 보여준다.
- **032**: 024 와 같은 메커니즘으로 원본 apply 를 의도적으로 partial 로
  만든 뒤(recovery 대상이 partial/unknown 이어야 한다, ``ApplyCoordinator``
  M6 docstring), **새** 승인 + ``recovery_of`` 로 **다른** scratch
  destination 에 recovery apply 를 낸다 — 원본 destination 은 partial
  이후에도 create-only 예약이 풀리지 않으므로(``ExecutionJournal.
  _reserve_destination_locked``), 같은 자리를 재사용하는 recovery 는 이
  SPEC 이 정하지 않은 release 절차가 필요하다(이 설계 결정은 M5 에서
  재확인한다). 024 와 같은 이유로 ``--confirmed-failure-command`` 가
  필요하다.

destination 점유 확인(REQ-LDSEND-008)은 시나리오 하나가 **처음** 쓰려는
destination 에만 적용된다 — 024 의 두 번째 bundle 이 자기 자신이 이미 채운
destination 을 다시 쓰는 것은 "첫 쓰기" 가 아니므로 이 가드의 대상이
아니다(D12, plan.md §2.0-마 항목6).

backup 선행조건(REQ-LDSEND-014)은 held(블랙리스트) 명령이 있을 때만
``execute_preapproved()`` 안에서 검사된다 — 이 도구의 모든 시나리오
명령(``Store Sequence ...``)이 held 이므로(blacklist.yaml v9) 매 apply 마다
관측된다. 실패하면 ``ApplyCoordinator.apply()`` 가 ``GATE_REJECTED`` 로
거부하고, 이 도구는 그 신호를 readback 판정과 구분된 필드에 기록한다 —
apply 가 콘솔에 아무것도 보내지 못했으므로 readback 은 시도하지 않는다.

Usage(dry-run, 콘솔로는 아무것도 안 나간다)::

    uv run python -m server.tools.director_apply_observe 021 --listen-port 9005

Usage(실행 — 세션 시작 백업(SaveShow) 포함, 콘솔에 실제로 씀)::

    uv run python -m server.tools.director_apply_observe 021 --listen-port 9005 --execute

Usage(024/032 — M4a 가 확정한 실패 유발 명령을 명시해야 --execute 가능)::

    uv run python -m server.tools.director_apply_observe 024 --listen-port 9005 \\
        --execute --confirmed-failure-command "Store Sequence {n}"

This is a DEV TOOL, not a production execution path — exempt from the
REQ-MVP-029 single-chokepoint rule the same way ``responder_roundtrip``/
``busking_e2e`` are (the M4 import-boundary test whitelists ``server.tools``).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from server.director.approvals import ApprovalBinding, ApprovalRegistry, ContextRef, ValidationRef
from server.director.execution import ApplyCoordinator, ExecutionJournal, run_director_apply
from server.director.models import ExchangeError
from server.director.service import OUTCOME_READY
from server.director.store import DirectorStore
from server.orchestrator.bundle_sender import GateBundleSender
from server.safety.bootstrap import build_console_stack
from server.safety.console import ConsoleSilentError, StateQueryError
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

#: M4a 실기 탐색이 아직 확정하지 않은 실패 유발 명령에 의존하는 시나리오
#: (plan.md §2.0-라) — ``--confirmed-failure-command`` 없이는 --execute 를
#: 거부한다.
_REQUIRES_CONFIRMED_FAILURE_COMMAND = frozenset({"024", "032"})

#: plan.md §2.0-라 두 후보 — ``{n}`` 은 destination sequence 번호로
#: 치환된다. 후보 자체의 실측 확정은 M4a 의 몫이다.
AC024_CANDIDATES: dict[str, str] = {
    "candidate_1_recommended": "Store Sequence {n}",
    "candidate_2_unverified": "Copy Sequence <source> At {n}",
}

#: 채움 명령 — 세 시나리오 모두 이 형태로 스크래치 destination 을 먼저
#: 채운다(§2.0-라 plan.md 1단계와 같은 형태).
_FILL_COMMAND_TEMPLATE = "Store Sequence {n} Cue 1 /Merge"

#: 시나리오별 스크래치 destination 오프셋 — 여러 named slot 을 갖는
#: 시나리오도 있다(024 의 "채우는" 자리와 "절대 안 쓰이는" 자리, 032 의
#: 원본과 recovery 자리). 서로 겹치지 않게 미리 나눈다.
_DESTINATION_OFFSETS: dict[str, dict[str, int]] = {
    "021": {"primary": 0},
    "024": {"primary": 1, "never_written": 2},
    "032": {"primary": 3, "recovery": 4},
}


@dataclass(frozen=True)
class ScenarioPlan:
    """시나리오 하나의 계획 — dry-run 이 그대로 출력하는 대상."""

    scenario: str
    description: str
    destinations: dict[str, dict[str, str]]
    bundles: list[dict[str, Any]]
    recovery_bundles: list[dict[str, Any]] | None = None
    notes: list[str] = field(default_factory=list)


def _destinations_for(scenario: str, sequence_range_start: int) -> dict[str, dict[str, str]]:
    return {
        name: {"show_id": "1", "sequence_id": str(sequence_range_start + offset)}
        for name, offset in _DESTINATION_OFFSETS[scenario].items()
    }


def _fill_bundle(bundle_id: str, sequence_id: str) -> dict[str, Any]:
    return {"bundle_id": bundle_id, "commands": [_FILL_COMMAND_TEMPLATE.format(n=sequence_id)]}


def _candidate_notes(sequence_id: str) -> list[str]:
    return [
        "AC-024 실패 유발 명령은 M4a 가 실기로 확정한다(plan.md §2.0-라) — "
        "아래 두 후보 중 하나가 채택된다:",
        f"  candidate_1(권장): {AC024_CANDIDATES['candidate_1_recommended'].format(n=sequence_id)}",
        f"  candidate_2(미검증): {AC024_CANDIDATES['candidate_2_unverified']}",
    ]


def _plan_for_scenario(
    scenario: str,
    *,
    sequence_range_start: int,
    confirmed_failure_command: str | None = None,
) -> ScenarioPlan:
    """시나리오 하나의 계획을 만든다.

    ``confirmed_failure_command`` 가 없으면(dry-run 기본) 024/032 는 채움
    bundle 만 완성하고, 아직 확정 안 된 부분은 ``notes`` 에 두 후보로만
    보여준다(REQ-LDSEND-009 안전 — 콘솔에 무엇을 보낼지 정해지지 않은
    상태로 계획을 완성하지 않는다).
    """
    if scenario not in SCENARIOS:
        raise ValueError(
            f"알 수 없는 시나리오: {scenario!r} — {sorted(SCENARIOS)} 중 하나여야 한다."
        )

    destinations = _destinations_for(scenario, sequence_range_start)

    if scenario == "021":
        n = destinations["primary"]["sequence_id"]
        bundles = [_fill_bundle("ldsend-observe-021-bundle-1-fill", n)]
        return ScenarioPlan(scenario, SCENARIOS[scenario], destinations, bundles)

    if scenario == "024":
        n = destinations["primary"]["sequence_id"]
        never = destinations["never_written"]["sequence_id"]
        notes = _candidate_notes(n)
        bundles = [_fill_bundle("ldsend-observe-024-bundle-1-fill", n)]
        if confirmed_failure_command is not None:
            bundles.append(
                {
                    "bundle_id": "ldsend-observe-024-bundle-2-fail-trigger",
                    "commands": [confirmed_failure_command.format(n=n)],
                }
            )
            bundles.append(_fill_bundle("ldsend-observe-024-bundle-3-never-sent", never))
        else:
            notes.append(
                "--confirmed-failure-command 없이는 bundle 2/3 을 아직 만들지 "
                "않는다(REQ-LDSEND-009 안전) — --execute 도 거부한다."
            )
        return ScenarioPlan(scenario, SCENARIOS[scenario], destinations, bundles, notes=notes)

    # scenario == "032"
    n = destinations["primary"]["sequence_id"]
    recovery_n = destinations["recovery"]["sequence_id"]
    notes = _candidate_notes(n)
    notes.append(
        "원본 apply 를 의도적으로 partial 로 만들기 위해 024 와 같은 확정 "
        "대기 실패 유발 명령을 재사용한다. recovery apply 는 원본과 다른 "
        "scratch destination 을 새로 쓴다 — 원본 destination 은 partial "
        "이후에도 예약이 풀리지 않는다(create-only, ExecutionJournal."
        "_reserve_destination_locked) — 같은 자리를 재사용하려면 이 SPEC 이 "
        "정하지 않은 release 절차가 필요하다. 이 설계 결정은 M5 에서 "
        "재확인한다."
    )
    bundles = [_fill_bundle("ldsend-observe-032-bundle-1-fill", n)]
    recovery_bundles: list[dict[str, Any]] | None = None
    if confirmed_failure_command is not None:
        bundles.append(
            {
                "bundle_id": "ldsend-observe-032-bundle-2-fail-trigger",
                "commands": [confirmed_failure_command.format(n=n)],
            }
        )
        recovery_bundles = [_fill_bundle("ldsend-observe-032-recovery-bundle-1", recovery_n)]
    else:
        notes.append(
            "--confirmed-failure-command 없이는 원본을 partial 로 만들 수 "
            "없다 — recovery 배선도 아직 만들지 않는다(REQ-LDSEND-009 안전) "
            "— --execute 도 거부한다."
        )
    return ScenarioPlan(
        scenario, SCENARIOS[scenario], destinations, bundles, recovery_bundles, notes
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


class DestinationOccupiedError(RuntimeError):
    """REQ-LDSEND-008 — 첫 쓰기 대상 destination 이 이미 점유돼 있어
    거부한다(server-selected create-only, overwrite·재선택 없음)."""


@dataclass(frozen=True)
class DestinationCheck:
    """REQ-LDSEND-008/010 — 콘솔에 물어 확인한 destination 상태.

    ``empty`` 는 destination-occupancy 가드(REQ-008)의 진행 여부를, readback
    (REQ-010)에서는 반대 극성(``exists = not empty``)으로 읽힌다 — 같은 질의가
    두 용도를 겸한다.
    """

    #: ``None`` = 판독 불가(콘솔 무응답) — 비었다고도 찼다고도 말할 수 없다.
    empty: bool | None
    response_shape: str
    raw: Any


def _check_destination_empty(state_port: Any, path: str) -> DestinationCheck:
    """destination 이 비어 있는지 콘솔에 물어 확인한다.

    존재/부재 응답 모양은 아직 실기로 확정되지 않았다(plan.md §2.0-다) — 두
    후보 모두 "비어있음"으로 받아들인다: (1) ``StateQueryError``(``ok:false``)
    (2) ``ok:true`` + 빈/부재 ``node``·``children``. 그 밖의 모든 경우(콘솔이
    실제 내용이 있는 node 를 돌려줌)는 점유로 보고 거부한다 — 모호하면 쓰지
    않는다(보수적 기본값). M5 가 이 도구의 dry-run/--execute 관측 기록에서
    실제로 관측된 응답 모양을 확정한다.
    """
    try:
        payload = state_port.query_state(path)
    except ConsoleSilentError as error:
        # 무응답은 「없다」는 답이 아니다(console.py t313) — 판독 자체가 성립하지
        # 않았다. ``empty=None``(모름): 점유 확인은 쓰기를 거부하고, readback 은
        # 「없음」으로 단정하지 않는다.
        return DestinationCheck(
            empty=None,
            response_shape=f"ConsoleSilentError (무응답): {error} — 판독 불가",
            raw=None,
        )
    except StateQueryError as error:
        return DestinationCheck(
            empty=True,
            response_shape=(f"StateQueryError (ok:false): {error} — §2.0-다 후보 1, M5 확인 필요"),
            raw=None,
        )
    node = payload.get("node")
    children = payload.get("children") or []
    if not node and not children:
        return DestinationCheck(
            empty=True,
            response_shape=(
                f"ok:true, node/children 비어있음: {payload!r} — §2.0-다 후보 2, M5 확인 필요"
            ),
            raw=payload,
        )
    return DestinationCheck(
        empty=False,
        response_shape=f"ok:true, node={node!r} children={len(children)}개 — 점유",
        raw=payload,
    )


def _require_destination_empty(state_port: Any, destination: Mapping[str, str]) -> DestinationCheck:
    """REQ-LDSEND-008 — 첫 쓰기 전 destination 이 비어 있는지 확인하고,
    점유돼 있으면 거부한다."""
    path = f"DataPool/Sequences/{destination['sequence_id']}"
    check = _check_destination_empty(state_port, path)
    if check.empty is None:
        raise DestinationOccupiedError(
            f"destination {dict(destination)!r} 의 점유 여부를 판독할 수 없습니다 — "
            f"쓰기를 거부합니다({check.response_shape})."
        )
    if not check.empty:
        raise DestinationOccupiedError(
            f"destination {dict(destination)!r} 이 이미 점유돼 있습니다 — 쓰기를 "
            f"거부합니다({check.response_shape})."
        )
    return check


@dataclass(frozen=True)
class ReadbackResult:
    """REQ-LDSEND-010 — ``BundleSender`` 반환값이 아니라 이 별도 조회
    결과로 apply 여부를 보고한다."""

    path: str
    #: ``None`` = 판독 불가(콘솔 무응답).
    exists: bool | None
    response_shape: str
    raw: Any


def _readback_object_existence(state_port: Any, destination: Mapping[str, str]) -> ReadbackResult:
    path = f"DataPool/Sequences/{destination['sequence_id']}"
    check = _check_destination_empty(state_port, path)
    return ReadbackResult(
        path=path,
        exists=None if check.empty is None else not check.empty,
        response_shape=check.response_shape,
        raw=check.raw,
    )


def _backup_failure_detail(error: ExchangeError) -> str | None:
    """REQ-LDSEND-014 — gate 거부 예외가 backup 실패 때문인지 판별한다.

    ``execute_preapproved()`` 가 ``_backup.before_risky_execution()`` 에서
    ``BackupError`` 를 잡으면 ``ScreenDecision(status="blocked_backup_failed",
    notice=f"showfile backup failed ...")`` 를 만들고, ``ApplyCoordinator.
    apply()`` 는 그 decision 을 ``_gate_rejected()`` 로 감싸
    ``ExchangeError(code="GATE_REJECTED", details=(Detail("", decision.notice
    or decision.status),))`` 를 던진다(``execution.py`` ``_gate_rejected``/
    ``ApplyCoordinator.apply`` 947-976행). 이 함수는 그 신호를 역으로 읽어
    "backup 이 실패해서 거부됐다"를 다른 GATE_REJECTED 사유(문법/분류/
    health/lock)와 구분한다. backup 실패가 아니면 ``None`` 을 돌려준다 —
    호출자는 그 예외를 그대로 재전파해야 한다.
    """
    if error.code != "GATE_REJECTED":
        return None
    for detail in error.details:
        if "backup failed" in detail.message:
            return detail.message
    if "backup failed" in error.message:
        return error.message
    return None


def _apply_bundles(
    *,
    stack: Any,
    store: DirectorStore,
    journal: ExecutionJournal,
    approvals: ApprovalRegistry,
    project_id: str,
    plan_id: str,
    destination: Mapping[str, str],
    bundles: list[dict[str, Any]],
    recovery_of: str | None = None,
) -> dict[str, Any]:
    """승인 하나를 발급하고 ``run_director_apply()`` 를 한 번 호출한다.

    REQ-LDSEND-014 — backup 선행조건이 실패하면(``ExchangeError`` code
    ``GATE_REJECTED`` + backup 실패 신호) 그 사실을 ``backup_precondition``
    필드에 구분해 기록하고 전파하지 않는다 — apply 가 콘솔에 아무것도 보내지
    못했으므로 호출자는 readback 을 시도하지 않는다. 그 밖의 예외(backup
    실패가 아닌 GATE_REJECTED 포함)는 그대로 전파한다.
    """
    binding = _build_local_approval(
        store=store,
        approvals=approvals,
        project_id=project_id,
        plan_id=plan_id,
        destination=destination,
    )
    coordinator = ApplyCoordinator(
        journal=journal, approvals=approvals, store=store, gate=stack.gate
    )
    body: dict[str, Any] = {
        "approval_id": binding.approval_id,
        "idempotency_key": f"{plan_id}-apply",
        "destination": dict(destination),
        "bundles": [dict(bundle) for bundle in bundles],
        "compiled_digest": binding.compiled_digest,
    }
    if recovery_of is not None:
        body["recovery_of"] = recovery_of

    try:
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
    except ExchangeError as error:
        backup_detail = _backup_failure_detail(error)
        if backup_detail is None:
            raise
        return {
            "approval_id": binding.approval_id,
            "response_body": None,
            "response_status": None,
            "backup_precondition": "failed",
            "backup_precondition_detail": backup_detail,
        }

    return {
        "approval_id": binding.approval_id,
        "response_body": response_body,
        "response_status": response_status,
        "backup_precondition": "ok",
        "backup_precondition_detail": None,
    }


def _run_scenario(
    *,
    scenario: str,
    stack: Any,
    sequence_range_start: int,
    confirmed_failure_command: str | None = None,
) -> dict[str, Any]:
    """시나리오 하나를 ``run_director_apply()`` 로 실제로 구동한다.

    도구 자신의 로컬 ``DirectorStore``/``ExecutionJournal``/
    ``ApprovalRegistry`` 를 process 수명(이 함수 호출) 동안만 만들고,
    ``ApplyCoordinator`` 는 그 로컬 셋과 **진짜** ``stack.gate`` 를 섞어
    구성한다(§2.0-마 plan.md 항목 3) — ``gate`` 만 운영과 같은 진짜
    ``SafetyGate`` 다.

    처리 순서: (1) REQ-LDSEND-008 — primary destination 이 비어 있는지
    확인, 점유돼 있으면 즉시 거부(아무것도 쓰지 않는다). (2) 원본 apply —
    backup 실패면 readback 을 건너뛰고 반환(REQ-LDSEND-014). (3) 성공하면
    readback(REQ-LDSEND-010) — 021/024 는 primary(+024 는 never_written 도),
    032 는 원본 destination 은 readback 하지 않고 recovery apply 로 이어간다.
    (4) 032 만 — recovery apply(새 승인, ``recovery_of`` 링크) → 성공하면
    recovery destination 을 readback.

    032 의 원본 destination readback 을 생략하는 이유: 원본은 partial 로
    끝나도록 설계됐고(§2.0-라 재사용), 그 destination 은 이미 bundle1 이
    채웠다는 사실이 024 시나리오로 이미 관측되므로, 032 의 관측 초점은
    recovery 가 실제로 적용됐는가(AC-LDPLUGIN-032)에 있다.
    """
    if scenario in _REQUIRES_CONFIRMED_FAILURE_COMMAND and confirmed_failure_command is None:
        raise ValueError(
            f"시나리오 {scenario} 는 --confirmed-failure-command 없이 실행할 수 "
            "없습니다(M4a 미확정, plan.md §2.0-라)."
        )

    plan = _plan_for_scenario(
        scenario,
        sequence_range_start=sequence_range_start,
        confirmed_failure_command=confirmed_failure_command,
    )
    project_id = "ldsend-observe"

    with tempfile.TemporaryDirectory(prefix="ldsend-observe-") as tmp:
        tmp_path = Path(tmp)
        store = DirectorStore(tmp_path / "director.sqlite3")
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        approvals = ApprovalRegistry()
        try:
            destination_check = _require_destination_empty(
                stack.gate.state_port, plan.destinations["primary"]
            )

            outcome = _apply_bundles(
                stack=stack,
                store=store,
                journal=journal,
                approvals=approvals,
                project_id=project_id,
                plan_id=f"ldsend-observe-{scenario}",
                destination=plan.destinations["primary"],
                bundles=plan.bundles,
            )

            result: dict[str, Any] = {
                "scenario": scenario,
                "plan": plan,
                "destination_check": destination_check,
                **outcome,
            }

            if outcome["backup_precondition"] != "ok":
                return result

            readback: dict[str, ReadbackResult] = {
                "primary": _readback_object_existence(
                    stack.gate.state_port, plan.destinations["primary"]
                )
            }
            if scenario == "024":
                readback["never_written"] = _readback_object_existence(
                    stack.gate.state_port, plan.destinations["never_written"]
                )
            result["readback"] = readback

            if scenario == "032" and plan.recovery_bundles:
                original_execution_id = (outcome["response_body"] or {}).get("execution_id")
                recovery_outcome = _apply_bundles(
                    stack=stack,
                    store=store,
                    journal=journal,
                    approvals=approvals,
                    project_id=project_id,
                    plan_id=f"ldsend-observe-{scenario}-recovery",
                    destination=plan.destinations["recovery"],
                    bundles=plan.recovery_bundles,
                    recovery_of=original_execution_id,
                )
                result["recovery"] = recovery_outcome
                if recovery_outcome["backup_precondition"] == "ok":
                    result["readback"]["recovery"] = _readback_object_existence(
                        stack.gate.state_port, plan.destinations["recovery"]
                    )
        finally:
            journal.close()
            store.close()

    return result


def _cleanup_commands(destination: Mapping[str, Any]) -> list[str]:
    """REQ-LDSEND-011 — 이 도구는 이 명령을 콘솔로 보내지 않는다. 표준출력에
    문자열만 낸다. 사람이 직접 콘솔에 실행한다."""
    return [f"Delete Sequence {destination['sequence_id']}"]


def _print_plan(plan: ScenarioPlan, *, execute: bool) -> None:
    print(f"# scenario {plan.scenario} — {plan.description}")
    for name, destination in plan.destinations.items():
        print(f"destination[{name}]: {destination}")
    print("commands:")
    for bundle in plan.bundles:
        for command in bundle["commands"]:
            print(f"  {command}")
    if plan.recovery_bundles:
        print("recovery commands (원본 apply 뒤, recovery_of 로 연결된 2차 apply):")
        for bundle in plan.recovery_bundles:
            for command in bundle["commands"]:
                print(f"  {command}")
    for note in plan.notes:
        print(f"# {note}")
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
    print(f"backup_precondition: {result['backup_precondition']}")
    if result["backup_precondition"] == "failed":
        print(f"backup_precondition_detail: {result['backup_precondition_detail']}")
        print(
            "readback 은 시도하지 않았다 — backup 선행조건 실패로 apply 가 "
            "콘솔에 아무것도 보내지 못했다(REQ-LDSEND-014, 이 사실을 readback "
            "판정과 구분해 기록한다)."
        )
        return
    print(f"response_status: {result['response_status']}")
    print(f"response_body: {result['response_body']}")
    for name, readback in (result.get("readback") or {}).items():
        print(
            f"readback[{name}]: exists={readback.exists} path={readback.path} "
            f"shape={readback.response_shape}"
        )
    if "recovery" in result:
        recovery = result["recovery"]
        print(f"recovery.backup_precondition: {recovery['backup_precondition']}")
        if recovery["backup_precondition"] == "failed":
            print(f"recovery.backup_precondition_detail: {recovery['backup_precondition_detail']}")
        else:
            print(f"recovery.response_status: {recovery['response_status']}")
            print(f"recovery.response_body: {recovery['response_body']}")


def _print_cleanup(destination: Mapping[str, Any]) -> None:
    print(
        "# cleanup — 아래 명령은 이 도구가 콘솔로 보내지 않는다. 사람이 "
        "직접 콘솔에 실행한다(REQ-LDSEND-011)."
    )
    for command in _cleanup_commands(destination):
        print(command)


def _print_cleanup_all(destinations: Sequence[Mapping[str, Any]]) -> None:
    """REQ-LDSEND-011 — 이 실행이 만들 수 있는 모든 scratch destination 에
    대해 ``Delete Sequence <N>`` 를 출력한다(단일 destination 시나리오는
    :func:`_print_cleanup` 과 동일)."""
    for destination in destinations:
        _print_cleanup(destination)


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
            "9900) — 쓰기 전 비어 있는지 확인한다(REQ-LDSEND-008)."
        ),
    )
    parser.add_argument(
        "--confirmed-failure-command",
        default=None,
        help=(
            "M4a 가 실기로 확정한 024/032 실패 유발 명령 — {n} 이 destination "
            "sequence 번호로 치환된다(예: 'Store Sequence {n}'). 024/032 는 "
            "이 값 없이는 --execute 를 거부한다(plan.md §2.0-라 HALT 조건)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # REQ-LDSEND-009/D11 — 인자 파싱을 먼저 끝내고(--execute 여부 확정), 그
    # 뒤에야 스택을 구성한다(dry-run 이면 attempt_session_backup=False).
    args = build_arg_parser().parse_args(argv)
    plan = _plan_for_scenario(
        args.scenario,
        sequence_range_start=args.sequence_range_start,
        confirmed_failure_command=args.confirmed_failure_command,
    )

    # M4a HALT 조건(plan.md §2.0-라) — 024/032 의 실패 유발 명령이 아직
    # 실기로 확정되지 않았으면 --execute 를 거부한다. 콘솔 스택 자체를
    # 만들기 전에 거부해야 세션 시작 백업(SaveShow)조차 나가지 않는다.
    refused_for_m4a = (
        args.execute
        and args.scenario in _REQUIRES_CONFIRMED_FAILURE_COMMAND
        and args.confirmed_failure_command is None
    )
    _print_plan(plan, execute=(args.execute and not refused_for_m4a))
    if refused_for_m4a:
        print(
            f"거부 — 시나리오 {args.scenario} 는 M4a 가 실기로 확정한 실패 유발 "
            "명령이 필요합니다(plan.md §2.0-라 HALT 조건). "
            "--confirmed-failure-command 로 명시적으로 넘기지 않으면 --execute "
            "를 거부합니다 — 콘솔로는 아무것도 보내지 않았습니다(세션 시작 "
            "백업 포함)."
        )
        return 1

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
                confirmed_failure_command=args.confirmed_failure_command,
            )
        except Exception as error:  # noqa: BLE001 — 실패도 사람이 읽을 형태로 보고한다
            print(f"실행 실패: {error!r}")
            return 1
        finally:
            # REQ-LDSEND-011 — 성공이든 실패든 cleanup 명령은 항상 출력한다.
            # M4a 게이트를 지났다는 것은(위에서 return 하지 않았다는 것은)
            # 이 시나리오의 전체 destination 목록이 확정돼 있다는 뜻이다.
            _print_cleanup_all(list(plan.destinations.values()))
        _print_result(result)
        return 0
    finally:
        stack.stop()


if __name__ == "__main__":
    sys.exit(main())
