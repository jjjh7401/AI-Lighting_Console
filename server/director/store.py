"""불변 plan 저장 · revision CAS · 멱등 (SPEC-LDSTORE-001 M1 · REQ-LDPLUGIN-015).

계약 §10 의 revision 규칙과 §9.7 의 idempotency fingerprint 를 SQLite transaction 하나로
집행한다. 불변성은 애플리케이션 규율이 아니라 **접근 패턴**으로 구현한다: `plan_revisions`
에는 INSERT 만 하고 UPDATE 를 하지 않으며, CAS 는 PRIMARY KEY 충돌이 담당한다.

이 층이 하지 않는 것: 검증. 계약 §3 의 `SubmitResult` 가 `ValidationReport` 를 포함하지만
그것을 만드는 것은 `SPEC-LDCOMPILE-001` 이다. 여기서는 저장까지이고 상태는 계약 §10 이
정의한 `submitted` 에서 출발한다.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from server.director.digest import canonical_digest, plan_digest
from server.director.models import Detail, ExchangeError

_MIGRATION = Path(__file__).resolve().parent / "migrations" / "001_initial.sql"

#: 계약 §10 — 저장 직후의 durable 내부 상태. 검증이 끝나기 전의 자리다.
STATE_SUBMITTED = "submitted"

#: 계약 §3 — 신규 생성 201, 후속(replay) 200.
_STATUS_CREATED = 201
_STATUS_REPLAYED = 200


@dataclass(frozen=True, slots=True)
class PlanRecord:
    """계약 §3 의 `PlanRecord` 중 M1 이 채우는 부분.

    `validation_id` · `approval_id` · `execution_id` 는 아직 없는 관계이므로 생략된다 —
    계약 §3: *"생략된 연결 ID 는 아직 없는 관계다."*
    """

    plan: dict[str, Any]
    revision: int
    state: str
    plan_digest: str


def _revision_conflict(message: str, pointer: str = "/base_revision") -> ExchangeError:
    return ExchangeError("REVISION_CONFLICT", 409, message, (Detail(pointer, "revision conflict"),))


class DirectorStore:
    """plan revision 저장소. 한 파일에 대해 한 인스턴스를 쓴다."""

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
        """마이그레이션은 여러 번 돌아도 안전하다 (`IF NOT EXISTS`)."""
        self._connection.executescript(_MIGRATION.read_text(encoding="utf-8"))

    def close(self) -> None:
        self._connection.close()

    # ---------------------------------------------------------------- 조회

    def head_revision(self, *, project_id: str, plan_id: str) -> int:
        """현재 head revision. 아직 없으면 0 이다 (계약 §10: 새 ID 는 0 에서 출발)."""
        row = self._connection.execute(
            "SELECT MAX(revision) AS head FROM plan_revisions WHERE project_id = ? AND plan_id = ?",
            (project_id, plan_id),
        ).fetchone()
        return int(row["head"] or 0)

    def get(self, *, project_id: str, plan_id: str, revision: int | None = None) -> PlanRecord:
        """revision 하나를 되읽는다. 생략하면 head (계약 §3).

        저장된 **원문 bytes** 를 파싱해 돌려준다 — 서버가 재직렬화한 값이 아니다.
        """
        if revision is None:
            query = (
                "SELECT * FROM plan_revisions WHERE project_id = ? AND plan_id = ? "
                "ORDER BY revision DESC LIMIT 1"
            )
            parameters: tuple[Any, ...] = (project_id, plan_id)
        else:
            query = (
                "SELECT * FROM plan_revisions WHERE project_id = ? AND plan_id = ? AND revision = ?"
            )
            parameters = (project_id, plan_id, revision)

        row = self._connection.execute(query, parameters).fetchone()
        if row is None:
            raise ExchangeError("NOT_FOUND", 404, "해당 plan revision 이 없습니다.")
        return PlanRecord(
            plan=json.loads(bytes(row["plan_json"]).decode("utf-8")),
            revision=int(row["revision"]),
            state=str(row["state"]),
            plan_digest=str(row["plan_digest"]),
        )

    # ---------------------------------------------------------------- 제출

    def submit(
        self,
        *,
        plan: dict[str, Any],
        expected_revision: int,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> PlanRecord:
        """계획 하나를 새 revision 으로 저장한다.

        Raises:
            ExchangeError: ``REVISION_CONFLICT`` (CAS 실패 또는 base_revision 불일치),
                ``IDEMPOTENCY_CONFLICT`` (같은 key 에 다른 request).
        """
        project_id = str(plan["project_id"])
        plan_id = str(plan["plan_id"])
        base_revision = int(plan["base_revision"])

        # 계약 §10 — 둘이 같아야 한다. 이 검사가 CAS 보다 먼저다: 제출자가 무엇을
        # 기대했는지와 계획이 무엇을 주장하는지가 어긋나면 어느 쪽을 믿을지 알 수 없다.
        if expected_revision != base_revision:
            raise _revision_conflict(
                f"expected_revision({expected_revision}) 과 "
                f"plan.base_revision({base_revision}) 이 다릅니다."
            )

        fingerprint = self._fingerprint(
            operation=operation,
            project_id=project_id,
            principal_id=principal_id,
            plan=plan,
            expected_revision=expected_revision,
        )

        replayed = self._replay(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed

        digest = plan_digest(plan)
        # 제출 원문을 그대로 보관한다. `sort_keys` 를 쓰지 않는 것이 의도다 — 계약 §3 의
        # "제출 그대로" 를 지키려면 서버가 형태를 손대지 않아야 한다.
        plan_bytes = json.dumps(plan, ensure_ascii=False).encode("utf-8")
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._connection:  # BEGIN … COMMIT / ROLLBACK
            head = self.head_revision(project_id=project_id, plan_id=plan_id)
            if base_revision != head:
                raise _revision_conflict(
                    f"base_revision({base_revision}) 이 현재 head({head}) 와 다릅니다."
                )
            revision = head + 1

            try:
                self._connection.execute(
                    "INSERT INTO plan_revisions "
                    "(project_id, plan_id, revision, plan_json, plan_digest, "
                    " base_revision, state, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        project_id,
                        plan_id,
                        revision,
                        plan_bytes,
                        digest,
                        base_revision,
                        STATE_SUBMITTED,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as error:
                # PRIMARY KEY 충돌 — 우리가 head 를 읽은 뒤 남이 같은 revision 을 썼다.
                # 이것이 CAS 의 실패 경로다.
                raise _revision_conflict(f"revision {revision} 이 이미 존재합니다.") from error

            self._connection.execute(
                "INSERT INTO idempotency_keys "
                "(project_id, principal_id, operation, idempotency_key, request_fingerprint, "
                " result_plan_id, result_revision, result_status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    principal_id,
                    operation,
                    idempotency_key,
                    fingerprint,
                    plan_id,
                    revision,
                    _STATUS_CREATED,
                    created_at,
                ),
            )

        return PlanRecord(
            plan=json.loads(plan_bytes.decode("utf-8")),
            revision=revision,
            state=STATE_SUBMITTED,
            plan_digest=digest,
        )

    # ---------------------------------------------------------------- 내부

    @staticmethod
    def _fingerprint(
        *,
        operation: str,
        project_id: str,
        principal_id: str,
        plan: dict[str, Any],
        expected_revision: int,
    ) -> str:
        """계약 §9.7 의 request fingerprint.

        `sha256(JCS({operation, project_id, principal_id, request}))` 이고 ``request`` 는
        HTTP body 에서 ``idempotency_key`` 만 제거한 객체다. body 는 계약 §3 의
        `ld_submit_plan` 형태이므로 여기서 그 형태를 다시 만든다.
        """
        request = {"plan": plan, "expected_revision": expected_revision}
        return canonical_digest(
            {
                "operation": operation,
                "project_id": project_id,
                "principal_id": principal_id,
                "request": request,
            }
        )

    def _replay(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> PlanRecord | None:
        """같은 key 가 이미 있으면 replay 하거나 충돌을 낸다 (계약 §10)."""
        row = self._connection.execute(
            "SELECT * FROM idempotency_keys WHERE project_id = ? AND principal_id = ? "
            "AND operation = ? AND idempotency_key = ?",
            (project_id, principal_id, operation, idempotency_key),
        ).fetchone()
        if row is None:
            return None

        if str(row["request_fingerprint"]) != fingerprint:
            raise ExchangeError(
                "IDEMPOTENCY_CONFLICT",
                409,
                "같은 idempotency_key 에 다른 요청이 들어왔습니다.",
                (Detail("", "idempotency key reused with a different request"),),
            )

        return self.get(
            project_id=project_id,
            plan_id=str(row["result_plan_id"]),
            revision=int(row["result_revision"]),
        )
