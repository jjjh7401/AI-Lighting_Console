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
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from server.director.digest import canonical_digest
from server.director.models import Detail, ExchangeError

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


def _target_busy(message: str) -> ExchangeError:
    return ExchangeError("TARGET_BUSY", 409, message, (Detail("/destination", "already reserved"),))


def _not_found(message: str) -> ExchangeError:
    return ExchangeError("NOT_FOUND", 404, message)


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
