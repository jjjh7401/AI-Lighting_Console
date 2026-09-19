"""운영 중단·recovery (SPEC-LDRECV-001 M6 · REQ-LDPLUGIN-032).

release/운영 중단 결정이 내려졌을 때 시스템이 정확히 무엇을 하는지만 다룬다 —
그 결정 자체(사람이 "이 principal 을 내린다"고 판단하는 것)는 이 모듈의 범위
밖이다(spec.md §2 "운영 중단·recovery는 사람 확인(H)이 섞인 기준이다 ... 결정
자체를 자동화하지 마라").

## 신규 apply 차단은 별도 플래그가 아니라 인증 철회의 구조적 귀결이다

`director_api.py` 의 모든 route(POST apply 포함)는 `auth.authenticate()` 를
가장 먼저 거친다(`auth.py` `@MX:ANCHOR` — "모든 director HTTP route 가 이
함수 하나를 거친다"). 그래서 이 모듈이 하는 유일한 일은 "해당 principal 의
모든 credential 을 철회한다"이며, 그 뒤로는 그 principal 의 어떤 route
호출도(apply 포함) `authenticate()` 단계에서 즉시 `UNAUTHENTICATED` 로
막힌다 — 뒤 단계(승인 재조회·LiveLock·SafetyGate)에는 도달조차 하지 않는다.
apply 전용 차단 플래그를 별도로 추가하면 두 메커니즘이 어긋날 여지(철회는
됐는데 차단 플래그를 세우는 걸 잊는 경우)가 생긴다 — 기존 인증 경계 하나를
재사용해 그 여지 자체를 없앤다(Enforce Simplicity).

## journal 보존은 "아무것도 안 한다"가 증거다

이 모듈은 `ExecutionJournal` 에 삭제/수정 API 를 추가하지 않았고, 이 함수도
`ExecutionJournal` 을 인자로 받지 않는다 — 운영 중단이 journal 을 건드릴
방법 자체가 코드 시그니처 수준에서 없다. recovery 흐름(:meth:`server.director
.execution.ApplyCoordinator.apply` 의 `recovery_of` 확장)은 원본 execution
행을 고치지 않고 새 execution + 별도 링크 테이블(`execution_recovery_links`,
migrations/003)만 추가한다 — 이 모듈은 그 recovery 흐름 자체도 새로 만들지
않는다(기존 apply 경로를 그대로 재사용한다, `execution.py` 모듈 docstring).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.director.auth import CredentialRegistry


@dataclass(frozen=True, slots=True)
class DecommissionResult:
    """운영 중단 실행 결과 — 철회된 credential id 전부(감사 근거).

    비어 있는 ``revoked_credential_ids`` 도 유효한 결과다(해당 principal 에게
    애초에 credential 이 없었던 경우) — 예외를 던지지 않는다.
    """

    project_id: str
    principal_id: str
    revoked_credential_ids: tuple[str, ...]


def decommission_principal(
    *, registry: CredentialRegistry, project_id: str, principal_id: str
) -> DecommissionResult:
    """해당 principal 의 MCP/human credential 을 즉시 전부 철회한다 (REQ-032).

    한 principal 이 MCP credential 과 human credential 을 동시에 가질 수
    있으므로(계약 §5 LD-AUTH-001 — 두 축은 서로 다른 자격이지 배타적 소유가
    아니다), 이 함수는 그 principal 이 가진 **모든** credential(어느
    audience 든)을 :meth:`CredentialRegistry.for_principal` 로 찾아 전부
    철회한다.

    다른 project 의 같은 principal_id, 또는 같은 project 의 다른 principal_id
    는 대상이 아니다 — ``for_principal`` 이 (project_id, principal_id) 정확히
    일치하는 credential 만 돌려준다.

    두 번 호출해도 안전하다(``CredentialRegistry.revoke`` 는 멱등 — 이미
    철회된 credential 을 다시 철회해도 예외를 던지지 않는다) — 운영자가 같은
    결정을 재시도해도 문제가 없다.
    """
    targets = registry.for_principal(project_id=project_id, principal_id=principal_id)
    for credential in targets:
        registry.revoke(credential.credential_id)
    return DecommissionResult(
        project_id=project_id,
        principal_id=principal_id,
        revoked_credential_ids=tuple(credential.credential_id for credential in targets),
    )
