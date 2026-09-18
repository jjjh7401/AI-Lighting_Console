"""durable execution journal · idempotency · destination 예약 (SPEC-LDRECV-001 M4 ·
REQ-LDPLUGIN-023).

계약 §9.7·§10 이 단일 원본이다. 이 모듈이 담당하는 것:

- 첫 write(실제 socket 전송) 전에 **승인 소비·execution·bundle journal·idempotency
  fingerprint·destination 예약을 하나의 transaction** 으로 SQLite 에 커밋한다
  (:meth:`ExecutionJournal.begin_execution`).
- 같은 idempotency key + 같은 request fingerprint 재제출은 최초 status·body 를
  **그대로** replay 한다 — 재실행하지 않는다. 같은 key + 다른 request 는
  ``IDEMPOTENCY_CONFLICT``(409).
- socket send 뒤 결과 커밋 전 crash 는 ``unknown`` 이다 — blind 하게
  success/failed 로 확정하지 않는다 (:meth:`ExecutionJournal.status`).

## fingerprint 는 형제 LDSTORE 와 같은 알고리즘

``server.director.store.DirectorStore._fingerprint`` 가 이미 계약 §9.7 을 구현했다
(``sha256(JCS({operation,project_id,principal_id,request}))``). 이 모듈은 그
알고리즘을 새로 발명하지 않고 ``server.director.digest.canonical_digest`` 를 직접
재사용한다 — 계산 규칙이 문자 그대로 같아야 두 층의 fingerprint 가 어긋나지 않는다.

## journal state 와 crash → unknown 의 관계

계약 §10: *"journal에는 bundle planned→sending(디스크 commit)→sent/acknowledged/
failed/unknown과 시간·오류·evidence를 남긴다. OSC 전송과 DB commit을 원자
transaction이라고 주장하지 않는다. socket send 뒤 저장 전 crash는 unknown이다."*

이 모듈은 그 문장을 문자 그대로 접근 패턴으로 구현한다: :meth:`mark_sending` 이
"socket send 직전" 상태를 디스크에 커밋하고, 그 다음 실제 전송이 일어난 뒤
:meth:`finalize_execution` 이 결과를 커밋한다. 두 커밋 사이에 프로세스가 죽으면
(합성 테스트에서는 두 번째 호출을 하지 않는 것으로 재현한다) execution 은
``sending`` 에 멈춘 채로 남고, :meth:`status` 는 그 상태를 ``unknown`` 으로
읽는다 — "sending 에서 멈췄다" 는 "확정할 수 없다" 와 같은 뜻이기 때문이다.

## destination occupancy — design.md §3 채택안 B

`context.py`(형제 SPEC 소유, 불변 ``ContextSnapshot``)를 건드리지 않는다. destination
점유는 apply 실행의 부산물(가변 상태)이므로 이 execution journal 층에 독립 테이블로
둔다. create-only 다 — 이미 점유된 slot 위에 다른 execution 이 조용히 재선택하지
못한다(LD-TARGET-001).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from server.director.approvals import ApprovalRegistry, check_validity
from server.director.digest import canonical_digest
from server.director.models import Detail, ExchangeError
from server.director.store import DirectorStore
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

#: 계약 §10 의 execution journal state. `UNKNOWN` 은 이 모듈이 직접 쓰는 값이라기보다
#: `status()` 가 `SENDING` 에서 멈춘 행을 읽을 때 반환하는 값이다 — 다만 M5(간섭 감지)
#: 가 명시적으로 이 상태를 커밋하는 경로도 있을 수 있어 상수로 노출해 둔다.
STATE_PLANNED = "planned"
STATE_SENDING = "sending"
STATE_SENT = "sent"
STATE_ACKNOWLEDGED = "acknowledged"
STATE_FAILED = "failed"
STATE_UNKNOWN = "unknown"

#: destination_reservations.status (design.md §3).
RESERVATION_RESERVED = "reserved"
RESERVATION_RELEASED = "released"

#: bundle 레벨 상태 — 후속 bundle 이 아예 시도되지 않았음을 뜻한다
#: (AC-LDPLUGIN-024, "not_sent 로 receipt 에 보존").
STATE_NOT_SENT = "not_sent"

#: execution 전체(aggregate) 상태 — 일부 bundle 은 confirmed, 일부는
#: not_sent/failed. `unknown`/`failed`/`sent`(전부 confirmed) 와 나란히
#: :func:`execute_bundles` 만 계산해 쓰는 값이다.
STATE_PARTIAL = "partial"

#: 계약 §3 — 신규 생성 201.
_STATUS_CREATED = 201


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _idempotency_conflict() -> ExchangeError:
    return ExchangeError(
        "IDEMPOTENCY_CONFLICT",
        409,
        "같은 idempotency_key 에 다른 요청이 들어왔습니다.",
        (Detail("", "idempotency key reused with a different request"),),
    )


def _target_busy(
    message: str, *, pointer: str = "/destination", detail: str = "already reserved"
) -> ExchangeError:
    return ExchangeError("TARGET_BUSY", 409, message, (Detail(pointer, detail),))


def _not_found(message: str) -> ExchangeError:
    return ExchangeError("NOT_FOUND", 404, message)


def _approval_not_found(approval_id: str) -> ExchangeError:
    return ExchangeError(
        "APPROVAL_NOT_FOUND",
        404,
        f"승인 {approval_id} 을 찾을 수 없습니다.",
        (Detail("/approval_id", ""),),
    )


def _approval_stale(reasons: tuple[str, ...]) -> ExchangeError:
    """REQ-LDPLUGIN-021 재검사 — head 변경/context stale/만료된 승인 거부.

    ``reasons`` 는 :func:`server.director.approvals.check_validity` 가 돌려주는
    사유 어휘(``head_changed``/``context_changed``/``expired``)를 그대로 싣는다 —
    같은 무효화 판정을 M2(승인 재조회) 와 M5(apply 직전 재검사)가 공유한다.
    """
    return ExchangeError(
        "APPROVAL_STALE",
        409,
        f"승인이 더 이상 유효하지 않습니다: {', '.join(reasons)}",
        (Detail("/approval_id", ", ".join(reasons)),),
    )


def _live_lock_active() -> ExchangeError:
    return ExchangeError(
        "LIVE_LOCK_ACTIVE",
        423,
        "LiveLock 이 활성화되어 있어 apply 를 차단합니다.",
        (Detail("", "live lock active"),),
    )


def _gate_rejected(decision: Any) -> ExchangeError:
    return ExchangeError(
        "GATE_REJECTED",
        422,
        f"SafetyGate 가 이 bundle 을 거부했습니다: {decision.status}",
        (Detail("", decision.notice or decision.status),),
    )


def _schema_invalid(message: str, pointer: str = "") -> ExchangeError:
    return ExchangeError("SCHEMA_INVALID", 422, message, (Detail(pointer, ""),))


def _identity_mismatch(field_name: str, path_value: str, binding_value: str) -> ExchangeError:
    """`director_api.py` 의 ``_identity_mismatch`` 와 같은 패턴(계약 §3) — path/URL 이
    주장하는 식별자가 `ApprovalBinding` 이 실제로 가리키는 값과 다르면 422 다.

    ``director_api.py`` 는 project_id/plan_id 의 path-vs-body 불일치에 이 코드를
    쓴다; 이 모듈은 같은 코드를 plan_id/revision 의 path-vs-**binding** 불일치에
    재사용한다 — `director_api.py` 를 import 하지 않는 이유는 그쪽이 이미 이
    모듈(`execution.py`)을 import 하기 때문이다(순환 참조 방지, 값은 리터럴로
    복제해 두 자리가 갈라지지 않게 `test_director_apply_rejection.py` 가 대조한다).
    """
    return ExchangeError(
        "IDENTITY_MISMATCH",
        422,
        f"path 의 {field_name}({path_value!r})가 승인의 {field_name}({binding_value!r})와 "
        "다릅니다.",
        (Detail(f"/{field_name}", "path/approval identity mismatch"),),
    )


def _invalid_state(approval_id: str, execution_id: str) -> ExchangeError:
    """M5 다각도 검토 결함3 — 승인은 첫 execution allocation 시 소비된다(계약 §10).
    이미 소비된 approval_id 를 다른 idempotency_key 로 다시 apply 하면 여기로 온다.
    """
    return ExchangeError(
        "INVALID_STATE",
        409,
        f"승인 {approval_id} 은 이미 execution {execution_id} 에 의해 소비되었습니다 — "
        "같은 승인을 다른 idempotency_key 로 재사용할 수 없습니다.",
        (Detail("/approval_id", "approval already consumed"),),
    )


def _recovery_required(approval_id: str, execution_id: str) -> ExchangeError:
    """결함3 — 소비된 execution 이 partial/unknown(recovery_required=true) 이면
    ``INVALID_STATE`` 대신 이 코드로 recovery 흐름(새 approval+``recovery_of``)을
    가리킨다(계약 §10: "이후 다른 idempotency key로 같은 approval을 apply하면
    INVALID_STATE 또는 RECOVERY_REQUIRED다")."""
    return ExchangeError(
        "RECOVERY_REQUIRED",
        409,
        f"승인 {approval_id} 이 소비한 execution {execution_id} 은 partial/unknown "
        "상태입니다 — 새 승인과 recovery_of 로 recovery 흐름을 거쳐야 합니다.",
        (Detail("/approval_id", "recovery required"),),
    )


def _recovery_source_invalid(execution_id: str, status: str) -> ExchangeError:
    """M6 · REQ-LDPLUGIN-032 — recovery 는 partial/unknown execution 만 대상으로
    한다. 이미 confirmed(``sent``/``acknowledged``) 된 execution 을 recovery
    대상으로 삼으면 "이미 성공한 것을 왜 다시 보내는가"라는 의미가 불분명해지고,
    ``planned``/``sending``/``failed`` 는 recovery 가 아니라 각각 정상 진행 중이거나
    (M5 의 재검사 대상) 그냥 실패 재시도(이 SPEC 이 금지하는 blind retry, LD-EXEC-002)
    이지 recovery 가 아니다."""
    return ExchangeError(
        "RECOVERY_SOURCE_INVALID",
        409,
        f"execution {execution_id} 는 partial/unknown 상태가 아니어서({status}) "
        "recovery 대상이 될 수 없습니다.",
        (Detail("/recovery_of", status),),
    )


class GatePort(Protocol):
    """M5 가 ``SafetyGate`` 로부터 필요로 하는 표면만 — 전체 ``SafetyGate`` 타입에
    결합하지 않고 테스트에서 fake 로 대체할 수 있게 한다. 실제 운영 배선에서는
    ``server.safety.gate.SafetyGate`` 인스턴스가 이 Protocol 을 그대로 만족한다
    (구조적 타이핑 — 상속 불필요)."""

    @property
    def lock(self) -> Any: ...  # LiveLock — .is_active 만 읽는다

    def execute_preapproved(self, commands: Sequence[str]) -> Any: ...  # ScreenDecision

    def revoke_clearances(self) -> None:
        """SPEC-LDSEND-001 REQ-LDSEND-005/006 — 호출 세션 자신의 남은 클리어런스만
        비운다. fake gate 와 실물 :class:`server.safety.gate.SafetyGate` 양쪽이
        이 구조적 타입을 만족해야 한다."""
        ...


class BundleSender(Protocol):
    """실제 콘솔 송신 seam (spec.md §5 — apply 의 승격부는 콘솔 게이트다).

    이 SPEC 은 이 프로토콜의 실제 구현체(``server/bridge/osc.py`` 연결)를
    만들지 않는다 — PRESERVE 경계(§3 spec.md, §5 spec.md)가 그 층을 콘솔
    게이트로 명시하기 때문이다. 호출자(추후 SPEC 또는 운영 배선)가 진짜
    전송기를, 테스트는 fake 를 주입한다.
    """

    def send(self, bundle: Mapping[str, Any]) -> str:
        """``STATE_SENT``/``STATE_ACKNOWLEDGED``/``STATE_FAILED``/``STATE_UNKNOWN``
        중 하나를 반환한다."""
        ...


class InterferenceDetector(Protocol):
    """operator 개입(programmer 변경) 감지 seam. bundle 하나를 보내기 전마다
    호출되며, ``True`` 를 반환하면 진행 중이던 execution 을 ``unknown``+
    ``recovery_required`` 로 전환하고 후속 bundle 을 전송하지 않는다."""

    def check(self) -> bool: ...


def _fingerprint(
    *, operation: str, project_id: str, principal_id: str, request: Mapping[str, Any]
) -> str:
    """계약 §9.7 의 request fingerprint 를 `store.py`/`approvals.py` 와 동일하게 계산한다.

    ``sha256(JCS({operation, project_id, principal_id, request}))`` — ``request`` 는
    호출자가 이미 idempotency_key 를 제거한 객체를 넘긴다는 전제다(계약 §9.7: "request는
    HTTP body에서 idempotency_key만 제거한 객체다").
    """
    return canonical_digest(
        {
            "operation": operation,
            "project_id": project_id,
            "principal_id": principal_id,
            "request": dict(request),
        }
    )


def _default_execution_id() -> str:
    import secrets

    return f"execution-{secrets.token_urlsafe(16)}"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """:meth:`ExecutionJournal.begin_execution` 의 반환값."""

    execution_id: str
    status: str
    response_status: int
    response_body: dict[str, Any]
    replayed: bool


class ExecutionJournal:
    """durable execution journal · idempotency · destination occupancy 저장소.

    `server.director.store.DirectorStore` 와 같은 파일을 가리켜도 안전하다 — 두
    클래스 모두 자신의 마이그레이션을 ``IF NOT EXISTS`` 로 적용하므로 순서와 무관하게
    수렴한다. 이 클래스를 단독으로(``DirectorStore`` 없이) 열어도 001+002 가 모두
    적용되어 스키마가 완결된다.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    @property
    def path(self) -> Path:
        """이 저장소의 DB 파일. 같은 파일을 여는 다른 연결을 만들 때 쓴다."""
        return self._path

    def _migrate(self) -> None:
        """마이그레이션 파일을 **파일명 순서대로** 전부 적용한다 — 001 다음 002.

        `001_initial.sql` 을 다시 적용해도 전부 ``IF NOT EXISTS`` 라 안전하다. 이
        순차 적용이 이 SPEC 이 추가하는 유일한 신규 메커니즘이다 —
        `DirectorStore._migrate` 는 고정된 단일 파일만 적용하므로 재사용하지 않고,
        여기서 최소하게 새로 만든다.
        """
        for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            self._connection.executescript(migration.read_text(encoding="utf-8"))

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def _transaction(self) -> Generator[None, None, None]:
        """명시적 transaction 경계.

        이 연결은 ``isolation_level=None``(autocommit) 으로 연다 — `DirectorStore` 와
        같은 패턴이다. 그러나 실측(스크립트로 직접 확인)하면 ``isolation_level=None``
        에서는 Python `sqlite3` 모듈이 DML 문 앞에 묵시적 ``BEGIN`` 을 **전혀 발행하지
        않는다** — 즉 각 ``execute()`` 가 곧바로 커밋되고, 뒤이은 예외에서
        ``with self._connection:`` 이 부르는 ``rollback()`` 은 되돌릴 열린 transaction
        이 없어 아무 일도 하지 않는다. 이 SPEC 이 요구하는 "하나의 transaction"
        불변식(§ M4 docstring)은 그 위에서는 성립하지 않으므로, 여기서 ``BEGIN
        IMMEDIATE``/``COMMIT``/``ROLLBACK`` 을 직접 발행해 진짜 원자성을 만든다.
        """
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise
        else:
            self._connection.execute("COMMIT")

    # ------------------------------------------------------------ idempotent execution

    def begin_execution(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request: Mapping[str, Any],
        approval_id: str,
        bundles: list[Mapping[str, Any]],
        destination: Mapping[str, str] | None = None,
        allocate_execution_id: Callable[[], str] | None = None,
    ) -> ExecutionResult:
        """첫 write 전 승인 소비·execution·bundle journal·fingerprint·destination
        예약을 하나의 transaction 으로 커밋한다 (계약 §10).

        Raises:
            ExchangeError: ``IDEMPOTENCY_CONFLICT`` (같은 key 에 다른 request),
                ``TARGET_BUSY`` (``destination`` 이 이미 예약된 slot).
        """
        fingerprint = _fingerprint(
            operation=operation,
            project_id=project_id,
            principal_id=principal_id,
            request=request,
        )

        replayed = self._replay_or_none(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed

        execution_id = (allocate_execution_id or _default_execution_id)()
        created_at = _now()
        response_body: dict[str, Any] = {
            "execution_id": execution_id,
            "state": STATE_PLANNED,
            "bundles": [
                {"bundle_id": str(bundle["bundle_id"]), "state": STATE_PLANNED}
                for bundle in bundles
            ],
        }
        response_status = _STATUS_CREATED

        # 하나의 transaction — 승인 소비(approval_id 기록)·execution·bundle journal·
        # destination 예약·idempotency fingerprint 전부가 이 안에서 커밋되거나 전부
        # 롤백된다. destination 이 이미 점유돼 있으면(TARGET_BUSY) execution 행도
        # 남지 않는다.
        with self._transaction():
            self._connection.execute(
                "INSERT INTO executions "
                "(execution_id, project_id, principal_id, approval_id, operation, state, "
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    execution_id,
                    project_id,
                    principal_id,
                    approval_id,
                    operation,
                    STATE_PLANNED,
                    created_at,
                    created_at,
                ),
            )

            for index, bundle in enumerate(bundles):
                self._connection.execute(
                    "INSERT INTO execution_bundles "
                    "(execution_id, bundle_index, bundle_id, state, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (execution_id, index, str(bundle["bundle_id"]), STATE_PLANNED, created_at),
                )

            if destination is not None:
                self._reserve_destination_locked(
                    project_id=project_id,
                    show_id=str(destination["show_id"]),
                    sequence_id=str(destination["sequence_id"]),
                    execution_id=execution_id,
                    now=created_at,
                )

            self._connection.execute(
                "INSERT INTO idempotency_records "
                "(project_id, principal_id, operation, idempotency_key, request_fingerprint, "
                " result_execution_id, result_status, result_body, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    principal_id,
                    operation,
                    idempotency_key,
                    fingerprint,
                    execution_id,
                    response_status,
                    json.dumps(response_body, ensure_ascii=False),
                    created_at,
                ),
            )

        return ExecutionResult(
            execution_id=execution_id,
            status=STATE_PLANNED,
            response_status=response_status,
            response_body=response_body,
            replayed=False,
        )

    def _replay_or_none(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> ExecutionResult | None:
        """같은 key 가 이미 있으면 **최초 저장한 status·body 그대로** replay 한다.

        계약 §10: "동일 key+동일 request fingerprint는 최초 저장한 status와 body를
        그대로 replay한다." 현재 execution 의 최신 상태가 아니라 저장 시점의 응답
        body 를 그대로 돌려준다 — 최신 상태는 :meth:`status`(별도 GET)가 맡는다.
        """
        row = self._connection.execute(
            "SELECT * FROM idempotency_records WHERE project_id = ? AND principal_id = ? "
            "AND operation = ? AND idempotency_key = ?",
            (project_id, principal_id, operation, idempotency_key),
        ).fetchone()
        if row is None:
            return None

        if str(row["request_fingerprint"]) != fingerprint:
            raise _idempotency_conflict()

        stored_body = json.loads(str(row["result_body"]))
        return ExecutionResult(
            execution_id=str(row["result_execution_id"]),
            status=str(stored_body.get("state", STATE_PLANNED)),
            response_status=int(row["result_status"]),
            response_body=stored_body,
            replayed=True,
        )

    def replay_if_exists(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        request: Mapping[str, Any],
    ) -> ExecutionResult | None:
        """``begin_execution`` 을 실제로 커밋하기 전에 replay 여부만 먼저 본다.

        M5 의 apply 재검사(REQ-021 — 승인 신선도·LiveLock·destination occupancy)는
        idempotent replay 요청에는 적용되면 안 된다(계약 §9.7 — 동일 key+동일
        request 는 그 사이 상태가 무엇이든 최초 응답을 그대로 replay 한다).
        :class:`ApplyCoordinator` 가 재검사보다 먼저 이 메서드를 호출해
        replay 경로를 가른다.
        """
        fingerprint = _fingerprint(
            operation=operation,
            project_id=project_id,
            principal_id=principal_id,
            request=request,
        )
        return self._replay_or_none(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )

    # ------------------------------------------------------------ 전송 상태 전이

    def mark_sending(self, execution_id: str) -> None:
        """socket send 직전 — ``sending`` 으로 디스크에 커밋한다 (계약 §10:
        "planned→sending(디스크 commit)"). 이 커밋 이후 crash 하면 :meth:`status` 가
        ``unknown`` 을 반환한다."""
        with self._transaction():
            self._connection.execute(
                "UPDATE executions SET state = ?, updated_at = ? WHERE execution_id = ?",
                (STATE_SENDING, _now(), execution_id),
            )

    def finalize_execution(self, execution_id: str, state: str) -> None:
        """실제 전송 결과를 커밋한다 (``sent``/``acknowledged``/``failed``/``unknown``).

        socket send 와 이 호출 사이에 crash 가 나면(합성 시험에서는 이 호출을 하지
        않는 것으로 재현한다) execution 은 ``sending`` 에 멈춘 채 남고 :meth:`status`
        가 그것을 ``unknown`` 으로 읽는다.
        """
        with self._transaction():
            self._connection.execute(
                "UPDATE executions SET state = ?, updated_at = ? WHERE execution_id = ?",
                (state, _now(), execution_id),
            )

    def record_bundle_result(
        self, *, execution_id: str, bundle_index: int, state: str, error: str | None = None
    ) -> None:
        """bundle 하나의 결과를 커밋한다 (계약 §10 의 bundle journal)."""
        with self._transaction():
            self._connection.execute(
                "UPDATE execution_bundles SET state = ?, updated_at = ?, error = ? "
                "WHERE execution_id = ? AND bundle_index = ?",
                (state, _now(), error, execution_id, bundle_index),
            )

    def existing_execution_for_approval(self, approval_id: str) -> str | None:
        """이 ``approval_id`` 가 이미 어떤 execution 에 소비됐으면 그 execution_id,
        아니면 ``None`` (M5 다각도 검토 결함3 · 계약 §10 "승인은 첫 execution
        allocation 시 소비된다").

        ``executions_by_approval`` 인덱스(migrations/002)를 그대로 쓴다 — 이
        인덱스는 M4 부터 존재했지만 이 조회가 만들어지기 전까지는 아무도 쿼리하지
        않았다. 한 approval_id 는 정확히 하나의 execution 만 만들 수 있어야 하므로
        (`ApplyCoordinator.apply` 가 이 메서드로 먼저 재사용을 차단한다) 가장 이른
        행 하나만 돌려주면 충분하다.
        """
        row = self._connection.execute(
            "SELECT execution_id FROM executions WHERE approval_id = ? "
            "ORDER BY created_at ASC LIMIT 1",
            (approval_id,),
        ).fetchone()
        return None if row is None else str(row["execution_id"])

    def status(self, execution_id: str) -> str:
        """현재 관측 가능한 execution 상태.

        ``sending`` 에서 다음 상태로 전이하지 못한 채 남아 있으면 ``unknown`` 으로
        읽는다 — socket send 뒤 결과 커밋 전 crash 와 바이트 동일한 관측이다(계약
        §10: "socket send 뒤 저장 전 crash는 unknown이다"). ``planned``(아직 전송
        시도 전)는 unknown 이 아니다 — 전송을 시작조차 안 한 상태와 "전송했는데
        결과를 모르는" 상태는 다르다.

        Raises:
            ExchangeError: ``NOT_FOUND`` (해당 execution 이 없음).
        """
        row = self._connection.execute(
            "SELECT state FROM executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        if row is None:
            raise _not_found(f"execution {execution_id} 이 없습니다.")

        state = str(row["state"])
        if state == STATE_SENDING:
            return STATE_UNKNOWN
        return state

    # ------------------------------------------------------------ destination 예약

    def reserve_destination(
        self, *, project_id: str, show_id: str, sequence_id: str, execution_id: str
    ) -> None:
        """create-only 예약 (design.md §3, LD-TARGET-001).

        이미 ``reserved`` 인 slot 이면 조용히 다른 slot 으로 재선택하지 않고
        ``TARGET_BUSY`` 로 거부한다. ``released`` 였던 slot 은 재예약할 수 있다.

        Raises:
            ExchangeError: ``TARGET_BUSY``.
        """
        with self._transaction():
            self._reserve_destination_locked(
                project_id=project_id,
                show_id=show_id,
                sequence_id=sequence_id,
                execution_id=execution_id,
                now=_now(),
            )

    def _reserve_destination_locked(
        self, *, project_id: str, show_id: str, sequence_id: str, execution_id: str, now: str
    ) -> None:
        """``reserve_destination`` 의 본체 — 이미 열린 transaction 안에서 호출되도록
        커밋을 직접 하지 않는다(``begin_execution`` 이 같은 transaction 에서
        재사용한다)."""
        existing = self._connection.execute(
            "SELECT status, reserved_by_execution_id FROM destination_reservations "
            "WHERE project_id = ? AND show_id = ? AND sequence_id = ?",
            (project_id, show_id, sequence_id),
        ).fetchone()

        if existing is not None and str(existing["status"]) == RESERVATION_RESERVED:
            raise _target_busy(
                f"destination (show={show_id}, sequence={sequence_id}) 이 이미 "
                f"execution {existing['reserved_by_execution_id']} 에 의해 점유되어 "
                "있습니다 — create-only."
            )

        if existing is None:
            self._connection.execute(
                "INSERT INTO destination_reservations "
                "(project_id, show_id, sequence_id, reserved_by_execution_id, reserved_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, show_id, sequence_id, execution_id, now, RESERVATION_RESERVED),
            )
        else:
            self._connection.execute(
                "UPDATE destination_reservations "
                "SET reserved_by_execution_id = ?, reserved_at = ?, status = ? "
                "WHERE project_id = ? AND show_id = ? AND sequence_id = ?",
                (execution_id, now, RESERVATION_RESERVED, project_id, show_id, sequence_id),
            )

    def release_destination(self, *, project_id: str, show_id: str, sequence_id: str) -> None:
        """예약을 해제한다 — slot 은 이후 다시 ``reserve_destination`` 할 수 있다."""
        with self._transaction():
            self._connection.execute(
                "UPDATE destination_reservations SET status = ? "
                "WHERE project_id = ? AND show_id = ? AND sequence_id = ?",
                (RESERVATION_RELEASED, project_id, show_id, sequence_id),
            )

    def destination_status(
        self, *, project_id: str, show_id: str, sequence_id: str
    ) -> dict[str, Any] | None:
        """slot 하나의 현재 예약 상태. 아예 예약된 적 없으면 ``None``."""
        row = self._connection.execute(
            "SELECT reserved_by_execution_id, reserved_at, status FROM destination_reservations "
            "WHERE project_id = ? AND show_id = ? AND sequence_id = ?",
            (project_id, show_id, sequence_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "reserved_by_execution_id": str(row["reserved_by_execution_id"]),
            "reserved_at": str(row["reserved_at"]),
            "status": str(row["status"]),
        }

    # ------------------------------------------------------------ M6 — recovery 링크

    def record_recovery_link(
        self, *, recovery_execution_id: str, original_execution_id: str
    ) -> None:
        """recovery execution 이 어떤 원본의 recovery 인지 기록한다 (M6 · REQ-032).

        원본 execution 행(``executions`` 테이블)은 이 메서드가 전혀 건드리지
        않는다 — 별도 테이블(``execution_recovery_links``, migrations/003)에
        관계만 추가한다. 원본 기록이 "덮어써지지 않고 recovery_of 로만
        연결된다"는 AC-LDPLUGIN-032 항목4 의 요구를 스키마 수준에서 만족한다.
        """
        with self._transaction():
            self._connection.execute(
                "INSERT INTO execution_recovery_links "
                "(recovery_execution_id, original_execution_id, created_at) VALUES (?, ?, ?)",
                (recovery_execution_id, original_execution_id, _now()),
            )

    def recovery_of(self, execution_id: str) -> str | None:
        """``execution_id`` 가 recovery execution 이면 원본 execution_id, 아니면
        ``None``(recovery 가 아닌 일반 execution)."""
        row = self._connection.execute(
            "SELECT original_execution_id FROM execution_recovery_links "
            "WHERE recovery_execution_id = ?",
            (execution_id,),
        ).fetchone()
        return None if row is None else str(row["original_execution_id"])


# ---------------------------------------------------------------------------
# M5 — apply 직전 재검사 · SafetyGate 연결 (REQ-LDPLUGIN-021)
# ---------------------------------------------------------------------------


class ApplyCoordinator:
    """apply 직전 재검사(REQ-LDPLUGIN-021) + durable journal 커밋 + SafetyGate
    연결. 실제 bundle 전송·실패 분류(REQ-LDPLUGIN-024)는 :func:`execute_bundles`
    가 별도로 맡는다 — 이 클래스는 "lock 안에서 첫 write 직전" 재검사와 journal
    커밋, gate 로의 연결까지만 책임진다.

    이 클래스가 실제로 검사하는 순서(REQ-021 원문이 나열한 네 항목 — current
    bindings·target/destination occupancy·LiveLock·승인 — 은 검사 **대상**의
    열거이지 순서 규정이 아니다; acceptance.md AC-021 항목 1 은 각 조건이
    "하나라도" 위반되면 차단됨을 요구할 뿐, 순서 자체를 시험하지 않는다):

    0. idempotent replay(같은 key+같은 request) 여부 — 그 사이 상태가 무엇이든
       최초 응답을 그대로 돌려준다(계약 §9.7). 아래 재검사보다 먼저 확인한다.
    1. path identity — URL 의 ``plan_id``/``revision`` 이 실제로 승인이
       가리키는 ``ApprovalBinding.plan_id``/``plan_revision`` 과 같은지
       (``director_api.py`` 의 project_id/plan_id path-vs-body
       ``IDENTITY_MISMATCH`` 패턴을 plan_id/revision 의 path-vs-**binding**
       불일치에 재사용한다 — M5 다각도 검토 결함4·5. 같은 프로젝트의 다른
       plan 이 우연히 같은 revision 숫자를 가지면 승인이 잘못된 plan 에
       쓰일 수 있다는 결함5 의 시나리오를 이 검사가 막는다).
    2. 승인 단일 소비 — 이 ``approval_id`` 로 이미 만들어진 execution 이
       있으면(:meth:`ExecutionJournal.existing_execution_for_approval`)
       ``INVALID_STATE``/``RECOVERY_REQUIRED`` 로 거부한다(계약 §10: "승인은
       첫 execution allocation 시 소비된다" — M5 다각도 검토 결함3).
       ``recovery_of`` 흐름은 항상 **새** approval_id 를 쓰므로(plan.md M6:
       "새 revision→검증→승인→apply") 이 검사와 부딪히지 않는다.
    3. 승인 조회 + 신선도(head 변경/context stale/compiled_digest 변경/만료) —
       :func:`server.director.approvals.check_validity` ("current bindings" +
       "승인"). ``compiled_digest`` 는 apply 요청이 되풀이해 제출해야 하는
       값이다 — 이 층은 ``bundles`` 로부터 그 값을 재계산하지 않는다(계약
       §209 — `compiled_digest` 는 compiler_id/compiler_version/
       compiler_build_digest/target/playback 까지 묶은 manifest 전체의
       digest 이고, 이 필드들은 이 층에 전달되지 않는다 — M5 다각도 검토
       결함1+2 잔여 위험: 클라이언트가 실제로는 다른 bundles 를 보내면서
       예전 compiled_digest 를 그대로 재전송하면 이 비교만으로는 잡지
       못한다; 결함3 수정이 같은 승인의 반복 소비는 막지만 **최초** apply
       요청의 bundles 내용 자체를 manifest 와 대조하려면 이 모듈에 없는
       compiled manifest 접근(LDCOMPILE `ValidationProvider`)이 필요하다).
    4. LiveLock 활성 여부 — ``gate.lock.is_active``.
    5. destination occupancy — :meth:`ExecutionJournal.begin_execution` 이
       같은 transaction 안에서 create-only 로 예약한다(design.md §3). 이미
       점유돼 있으면 ``TARGET_BUSY`` 로 거부하고 **다른 slot 으로 조용히
       재선택하지 않는다**.
    6. SafetyGate 연결 — ``gate.execute_preapproved(commands)``. grammar/
       classify/backup/health/audit 는 우회하지 않는다(§2.0-가, design.md §1).
       중재자 lock 충돌(``status=="blocked_target_busy"``)은 재시도 가능
       신호를 보존하기 위해 ``GATE_REJECTED`` 가 아니라 ``TARGET_BUSY`` 로
       분기한다(M5 다각도 검토 결함6). 이 단계에서 거부되면(``GATE_REJECTED``
       든 이 ``TARGET_BUSY`` 든) 아직 콘솔에 아무것도 보내지 않았다는 것이
       확정되므로, execution 을 ``failed`` 로 닫는 동시에 destination
       예약도 즉시 해제한다(결함7) — ``STATE_PARTIAL``/``STATE_UNKNOWN`` 으로
       끝나는 :func:`execute_bundles` 의 실패 경로는 별도이며 이 즉시 해제
       대상이 아니다(그 상태들은 콘솔에 무엇이 도달했는지 불확실하므로
       recovery 흐름을 거쳐야 한다).

    M6(REQ-LDPLUGIN-032) 의 recovery 흐름도 이 클래스를 그대로 재사용한다 —
    별도 "recovery apply" 메서드를 만들지 않는다. 호출자가 body 에
    ``recovery_of``(원본 execution_id)를 실으면, 위 재검사를 전부 통과한
    **새** execution 이 만들어지고 :meth:`ExecutionJournal.record_recovery_link`
    로 원본과 연결된다 — 원본 execution 행 자체는 건드리지 않는다(plan.md
    M6 이 명시한 "새 revision→검증→승인→apply(recovery_of)").
    """

    def __init__(
        self,
        *,
        journal: ExecutionJournal,
        approvals: ApprovalRegistry,
        store: DirectorStore,
        gate: GatePort,
    ) -> None:
        self._journal = journal
        self._approvals = approvals
        self._store = store
        self._gate = gate

    def apply(
        self,
        *,
        project_id: str,
        plan_id: str,
        revision: int,
        principal_id: str,
        operation: str,
        current_context_digest: str,
        body: Mapping[str, Any],
    ) -> ExecutionResult:
        """``POST .../apply`` 판정.

        Raises:
            ExchangeError: ``SCHEMA_INVALID`` (필수 필드 누락),
                ``IDENTITY_MISMATCH`` (URL 의 plan_id/revision 이 승인이
                가리키는 plan_id/plan_revision 과 다름 — 결함4·5),
                ``APPROVAL_NOT_FOUND`` (approval_id 가 없음),
                ``INVALID_STATE``/``RECOVERY_REQUIRED`` (이 approval_id 가
                이미 다른 execution 을 만듦 — 결함3),
                ``APPROVAL_STALE`` (head 변경/context stale/compiled_digest
                변경/만료), ``LIVE_LOCK_ACTIVE``, ``TARGET_BUSY``
                (destination 이미 점유·create-only, 또는 SafetyGate 중재자
                lock 충돌 — 결함6), ``IDEMPOTENCY_CONFLICT``, ``GATE_REJECTED``
                (SafetyGate 가 grammar/classify/backup/health 중 하나에서
                거부), ``RECOVERY_SOURCE_INVALID`` (``recovery_of`` 가 가리키는
                원본 execution 이 partial/unknown 상태가 아님 — M6).
        """
        approval_id = body.get("approval_id")
        idempotency_key = body.get("idempotency_key")
        destination = body.get("destination")
        bundles = body.get("bundles")
        compiled_digest = body.get("compiled_digest")
        recovery_of = body.get("recovery_of")
        if not isinstance(approval_id, str) or not approval_id:
            raise _schema_invalid("approval_id 가 필요합니다.", "/approval_id")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise _schema_invalid("idempotency_key 가 필요합니다.", "/idempotency_key")
        if not isinstance(destination, Mapping):
            raise _schema_invalid("destination 이 필요합니다.", "/destination")
        if not isinstance(bundles, list) or not bundles:
            raise _schema_invalid("bundles 가 필요합니다.", "/bundles")
        if not isinstance(compiled_digest, str) or not compiled_digest:
            # M5 다각도 검토 결함1+2 — 이 apply 가 향하는 compiled artifact 를
            # 밝히지 않으면 애초에 승인과 대조할 것이 없다. check_validity 가
            # 이 값을 binding.compiled_digest 와 비교한다(APPROVAL_STALE 아래).
            raise _schema_invalid("compiled_digest 가 필요합니다.", "/compiled_digest")
        if recovery_of is not None and (not isinstance(recovery_of, str) or not recovery_of):
            raise _schema_invalid(
                "recovery_of 는 비어있지 않은 문자열이어야 합니다.", "/recovery_of"
            )

        request_for_fingerprint = {k: v for k, v in body.items() if k != "idempotency_key"}

        # 0. replay 는 재검사보다 먼저 — 그 사이 상태와 무관하게 최초 응답을
        # 그대로 돌려준다(계약 §9.7). recovery_of 검증도 재검사이므로 replay
        # 경로에는 적용하지 않는다 — 이미 커밋된 최초 응답을 그대로 돌려준다.
        replayed = self._journal.replay_if_exists(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request=request_for_fingerprint,
        )
        if replayed is not None:
            return replayed

        # M6 — recovery 대상은 partial/unknown 이어야 한다(REQ-LDPLUGIN-032).
        # ``status()`` 가 없는 execution_id 에는 NOT_FOUND 를 던진다 — 그대로
        # 전파한다.
        if recovery_of is not None:
            original_status = self._journal.status(recovery_of)
            if original_status not in (STATE_PARTIAL, STATE_UNKNOWN):
                raise _recovery_source_invalid(recovery_of, original_status)

        # 1. current bindings + 승인 신선도.
        binding = self._approvals.get(approval_id)
        if binding is None:
            raise _approval_not_found(approval_id)

        # path identity — URL 의 plan_id/revision 이 실제로 이 승인이 가리키는
        # plan_id/plan_revision 과 같아야 한다(결함4·5). 같은 프로젝트의 다른
        # plan 이 우연히 같은 revision 숫자를 가지는 경우까지 잡는다 — 이 검사가
        # 없으면 head_revision 조회 자체가 엉뚱한 plan_id 로 이뤄질 수 있었다.
        if binding.plan_id != plan_id:
            raise _identity_mismatch("plan_id", plan_id, binding.plan_id)
        if revision != binding.plan_revision:
            raise _identity_mismatch("revision", str(revision), str(binding.plan_revision))

        # 승인 단일 소비 — 이 approval_id 로 이미 만들어진 execution 이 있으면
        # 다른 idempotency_key 로도 재사용할 수 없다(계약 §10, 결함3). replay
        # 경로(0 단계)는 이미 위에서 갈렸으므로 여기 도달했다는 것 자체가
        # "이 정확한 request 는 처음"이라는 뜻이다 — 그런데도 approval_id 가
        # 이미 소비돼 있으면 그건 재사용 시도다. recovery_of 흐름은 항상 새
        # approval_id 를 쓰므로(plan.md M6) 이 검사와 부딪히지 않는다.
        existing_execution_id = self._journal.existing_execution_for_approval(approval_id)
        if existing_execution_id is not None:
            existing_state = self._journal.status(existing_execution_id)
            if existing_state in (STATE_PARTIAL, STATE_UNKNOWN):
                raise _recovery_required(approval_id, existing_execution_id)
            raise _invalid_state(approval_id, existing_execution_id)

        current_head = self._store.head_revision(project_id=project_id, plan_id=plan_id)
        reasons = check_validity(
            binding,
            current_head=current_head,
            current_context_digest=current_context_digest,
            current_compiled_digest=compiled_digest,
            now=_now(),
        )
        if reasons:
            raise _approval_stale(reasons)

        # 2. LiveLock.
        if self._gate.lock.is_active:
            raise _live_lock_active()

        # 3. destination occupancy — begin_execution 의 단일 transaction 안에서
        # create-only 로 예약된다(design.md §3). 이미 점유돼 있으면 여기서
        # TARGET_BUSY 로 거부되고 execution 행 자체가 남지 않는다 — 다른 빈
        # slot 으로 조용히 재선택하지 않는다.
        result = self._journal.begin_execution(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request=request_for_fingerprint,
            approval_id=approval_id,
            bundles=bundles,
            destination=destination,
        )
        if result.replayed:
            return result

        # M6 — recovery_of 가 있었으면 새로 만들어진 execution 을 원본과 연결한다.
        # 원본 execution 행(``executions``)은 여기서도 건드리지 않는다 — 별도
        # 테이블에 관계만 추가한다(record_recovery_link docstring).
        if recovery_of is not None:
            self._journal.record_recovery_link(
                recovery_execution_id=result.execution_id, original_execution_id=recovery_of
            )

        # 4. SafetyGate 연결 — director 는 execute_preapproved 만 부른다
        # (screen() 이 아니다). 이미 가진 ApprovalBinding 이 그 자리의 승인
        # 증거이므로 일반 ApprovalPort 재질문은 여기서도 일어나지 않는다.
        commands = [str(command) for bundle in bundles for command in bundle.get("commands", ())]
        decision = self._gate.execute_preapproved(commands)
        if not decision.cleared:
            # journal 은 이미 durable 하게 남았다(§ M4 doctrine — journal 이
            # 첫 write 보다 먼저다) — gate 거부는 그 execution 을 failed 로
            # 닫는다. 실제 송신은 시도된 적이 없다는 것이 이 분기에 도달했다는
            # 사실 자체로 확정되므로(execute_bundles 는 아직 호출되지 않았다),
            # destination 예약도 여기서 즉시 해제한다(결함7) — STATE_PARTIAL/
            # STATE_UNKNOWN 으로 끝나는 execute_bundles 의 실패는 콘솔에
            # 무엇이 도달했는지 불확실하므로 이 즉시 해제 대상이 아니다.
            self._journal.finalize_execution(result.execution_id, STATE_FAILED)
            self._journal.release_destination(
                project_id=project_id,
                show_id=str(destination["show_id"]),
                sequence_id=str(destination["sequence_id"]),
            )
            if decision.status == "blocked_target_busy":
                # 결함6 — 중재자(shared programmer lock) 충돌은 문법/안전
                # 위반이 아니라 재시도 가능한 점유 상태다. GATE_REJECTED(422,
                # 재시도 불가 신호)로 뭉개면 계약이 요구하는 TARGET_BUSY(409,
                # 재시도 가능 신호)를 잃는다.
                raise _target_busy(
                    decision.notice or "SafetyGate 중재자 lock 충돌로 apply 가 거부되었습니다.",
                    pointer="",
                    detail=decision.status,
                )
            raise _gate_rejected(decision)

        return result

    def revoke_clearances(self) -> None:
        """SPEC-LDSEND-001 REQ-LDSEND-005/006/013 — 순수 위임. ``apply()`` 의
        재검사 순서는 이 메서드로 바뀌지 않는다. :func:`run_director_apply` 가
        ``execute_bundles()`` 반환 직후(성공이든 예외든) ``finally`` 에서
        정확히 1회 호출한다."""
        self._gate.revoke_clearances()


# @MX:NOTE: [AUTO] the single director-apply entry point (SPEC-LDSEND-001
#   REQ-LDSEND-007/015) — director_api.py post_apply() (HTTP adapter) and the
#   M3~M4 observation tool both call ONLY this function to reach
#   ApplyCoordinator.apply() -> execute_bundles(); neither ever calls those
#   two pieces separately. Placed in this fastapi-free module deliberately so
#   the observation tool never has to import server.director.director_api.
def run_director_apply(
    *,
    coordinator: ApplyCoordinator,
    journal: ExecutionJournal | None,
    bundle_sender: BundleSender | None,
    interference: InterferenceDetector | None,
    project_id: str,
    plan_id: str,
    revision: int,
    principal_id: str,
    operation: str,
    current_context_digest: str,
    body: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    """``POST .../apply`` 의 판정 흐름 전체 — REQ-LDSEND-015 가 요구하는 공유
    함수. ``director_api.py`` 의 ``post_apply()``(HTTP adapter)와 관측 도구
    (SPEC-LDSEND-001 M3~M4, ``server/tools/director_apply_observe.py``) 양쪽의
    **유일한** apply 호출 지점이다(spec.md §2.0-마).

    ``fastapi`` 를 import 하지 않는 이 모듈에 둔 이유: 관측 도구가
    ``director_api.py`` 를 import 하지 않아도 되게 하기 위함이다(그 파일은
    ``fastapi`` 를 끌어온다).

    본문 — ``bind_session_key(new_session_key())`` 로 전용 세션을 얻고
    (REQ-LDSEND-013), ``coordinator.apply(...)`` 를 호출한다. 그 호출이
    :class:`server.director.models.ExchangeError` 를 던지면(APPROVAL_STALE·
    GATE_REJECTED 등) 이 함수는 그 예외를 그대로 전파한다 — ``director_api.py``
    의 기존 ``except ExchangeError`` 가 그대로 잡는다(REQ-LDSEND-015 행동
    보존). ``execute_bundles()`` 는 sender 가 배선돼 있고 이번 apply 가
    replay 가 아닐 때만 호출한다(기존 ``post_apply()`` 와 바이트 동일한
    조건). 성공이든 예외든 ``finally`` 에서 ``coordinator.revoke_clearances()``
    (REQ-LDSEND-005) 다음 ``reset_session_key(token)``(REQ-LDSEND-013)을
    정확히 1회씩 부른다.

    Returns:
        ``(response_body, response_status)`` — 호출자가 ``JSONResponse`` 로
        감싸기만 하면 되는 튜플(관측 도구는 그대로 읽기만 한다).
    """
    token = bind_session_key(new_session_key())
    try:
        result = coordinator.apply(
            project_id=project_id,
            plan_id=plan_id,
            revision=revision,
            principal_id=principal_id,
            operation=operation,
            current_context_digest=current_context_digest,
            body=body,
        )

        # 실제 bundle 전송은 이 SPEC 의 콘솔 게이트 경계다(spec.md §5) — sender
        # 가 배선되지 않았거나 이미 replay 된 응답이면 journal 커밋·gate 연결
        # 결과만 그대로 돌려준다(post_apply() 의 원래 조건과 바이트 동일).
        journal_ready = journal is not None
        if bundle_sender is not None and not result.replayed and journal_ready:
            bundles = body.get("bundles") or []
            outcome = execute_bundles(
                journal,
                execution_id=result.execution_id,
                bundles=bundles,
                sender=bundle_sender,
                interference=interference,
            )
            return ({**result.response_body, **outcome}, result.response_status)

        return (result.response_body, result.response_status)
    finally:
        coordinator.revoke_clearances()
        reset_session_key(token)


def execute_bundles(
    journal: ExecutionJournal,
    *,
    execution_id: str,
    bundles: Sequence[Mapping[str, Any]],
    sender: BundleSender,
    interference: InterferenceDetector | None = None,
) -> dict[str, Any]:
    """AC-LDPLUGIN-024 — 실패/간섭/불확실 전송 시 후속 bundle 을 전송하지 않는다.

    N 개 bundle 을 순서대로 :class:`BundleSender` 로 보낸다. k 번째가
    ``STATE_FAILED``/``STATE_UNKNOWN`` 이거나, 그 직전에 :class:`InterferenceDetector`
    가 개입(programmer 변경)을 감지하면, k+1 번째부터는 ``sender.send()`` 를
    **호출하지 않고** ``STATE_NOT_SENT`` 로 journal 에 남긴다 — blind retry 를
    하지 않는다.

    전체(aggregate) 상태 우선순위:

    1. interference 감지, 또는 하나라도 ``STATE_UNKNOWN`` 이면 → ``unknown``
       (``unknown`` 이 ``partial`` 보다 우선한다 — 계약 요구).
    2. confirmed(``sent``/``acknowledged``)와 그 외(``failed``/``not_sent``)가
       섞여 있으면 → ``partial``.
    3. 전부 confirmed 면 → ``sent``.
    4. 그 밖(confirmed 도 unknown 도 없음) → ``failed``.

    ``recovery_required`` 는 interference 감지 또는 ``unknown`` 전체 상태일 때
    ``True`` 다 — M6(운영 중단·recovery)의 recovery 흐름이 참조하는 신호다.
    """
    outcomes: list[str] = []
    stop = False
    interference_detected = False

    for index, bundle in enumerate(bundles):
        if not stop and interference is not None and interference.check():
            interference_detected = True
            stop = True

        if stop:
            journal.record_bundle_result(
                execution_id=execution_id, bundle_index=index, state=STATE_NOT_SENT
            )
            outcomes.append(STATE_NOT_SENT)
            continue

        # "socket send 직전" 을 디스크에 남긴다 — M4 doctrine (execution.py
        # 모듈 docstring): 이 커밋 이후 crash 하면 status() 가 unknown 을
        # 반환한다.
        journal.mark_sending(execution_id)
        outcome = sender.send(bundle)
        if outcome not in (STATE_SENT, STATE_ACKNOWLEDGED, STATE_FAILED, STATE_UNKNOWN):
            raise ValueError(f"sender.send() 가 알 수 없는 상태를 반환했습니다: {outcome!r}")
        journal.record_bundle_result(execution_id=execution_id, bundle_index=index, state=outcome)
        outcomes.append(outcome)
        if outcome not in (STATE_SENT, STATE_ACKNOWLEDGED):
            stop = True

    confirmed = {STATE_SENT, STATE_ACKNOWLEDGED}
    if interference_detected or STATE_UNKNOWN in outcomes:
        overall, recovery_required = STATE_UNKNOWN, True
    elif any(o in confirmed for o in outcomes) and any(o not in confirmed for o in outcomes):
        overall, recovery_required = STATE_PARTIAL, False
    elif outcomes and all(o in confirmed for o in outcomes):
        overall, recovery_required = STATE_SENT, False
    else:
        overall, recovery_required = STATE_FAILED, False

    journal.finalize_execution(execution_id, overall)
    return {
        "execution_id": execution_id,
        "state": overall,
        "recovery_required": recovery_required,
        "bundles": outcomes,
    }
