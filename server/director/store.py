"""Immutable plan storage + revision CAS + idempotency (SPEC-LDSTORE-001 M1, REQ-LDPLUGIN-015).

Contract Section 10 revision rules and Section 9.7 idempotency fingerprint, enforced as a
single SQLite transaction. Immutability is not an application-layer discipline but an
*access pattern*: `plan_revisions` is INSERT-only, never UPDATE, and CAS is enforced by
PRIMARY KEY collision.

What this layer does not do: validation. Contract Section 3 `SubmitResult` includes a
`ValidationReport`, but producing it is `SPEC-LDCOMPILE-001` ownership. Here we only store,
and state starts from the `submitted` value Section 10 defines.

SPEC-LDWIRE-001 M2 extends this module with `ValidationReport` persistence (design.md
section "na" alternative A) -- a `validations` table keyed by a deterministic
`validation_id`, so `POST .../approvals` can resolve the id it is handed back to the
exact report a `PUT plan` submission produced.
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

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
#: DirectorStore owns exactly these two migration files -- NOT a directory glob. The
#: sibling ExecutionJournal (execution.py) applies every "*.sql" file it finds because it
#: legitimately shares the physical file with 002/003; DirectorStore stays scoped to its
#: own two files so a bare DirectorStore instance never silently creates
#: ExecutionJournal-owned tables (002/003 stay ExecutionJournal ownership).
_MIGRATIONS = (
    _MIGRATIONS_DIR / "001_initial.sql",
    _MIGRATIONS_DIR / "004_validations.sql",
)

#: Contract Section 10 -- the durable internal state right after storage. The state
#: before validation has finished.
STATE_SUBMITTED = "submitted"

#: Contract Section 3 -- 201 for a new record, 200 for a replay.
_STATUS_CREATED = 201
_STATUS_REPLAYED = 200


@dataclass(frozen=True, slots=True)
class PlanRecord:
    """The part of contract Section 3 PlanRecord that M1 fills.

    validation_id / approval_id / execution_id are omitted -- that relationship does not
    exist yet (contract Section 3: "an omitted linking ID means the relationship does not
    exist yet").
    """

    plan: dict[str, Any]
    revision: int
    state: str
    plan_digest: str


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    """SPEC-LDWIRE-001 M2 -- a persisted ValidationReport, keyed by validation_id.

    diagnostics/compiled are plain JSON-serializable structures (lists/dicts), matching
    what PipelineValidator.validate()/NotInstalledValidator.validate() already return --
    this record does not reshape them, only stores and returns them verbatim.
    """

    validation_id: str
    project_id: str
    plan_id: str
    plan_digest: str
    context_digest: str
    compiled_digest: str
    outcome: str
    diagnostics: list[dict[str, Any]]
    compiled: dict[str, Any]
    created_at: str
    expires_at: str


def compute_validation_id(*, plan_digest: str, revision: int, context_digest: str) -> str:
    """A deterministic validation_id (design.md section "na" alternative A).

    Same input (plan_digest, revision, context_digest) always yields the same id -- the
    same discipline store.py already uses for its own idempotency fingerprint. A retried
    PUT plan submission with the identical plan/context therefore reissues the SAME
    validation_id, and DirectorStore.save_validation is a no-op on a repeat (ON CONFLICT
    DO NOTHING) rather than a silent overwrite of the first report.
    """
    digest = canonical_digest(
        dict(plan_digest=plan_digest, revision=revision, context_digest=context_digest)
    )
    return "validation-" + digest.removeprefix("sha256:")[:32]


def _revision_conflict(message: str, pointer: str = "/base_revision") -> ExchangeError:
    return ExchangeError("REVISION_CONFLICT", 409, message, (Detail(pointer, "revision conflict"),))


class DirectorStore:
    """Plan revision storage. One instance per file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    @property
    def path(self) -> Path:
        """This store DB file. Use it to open another connection to the same file."""
        return self._path

    def _migrate(self) -> None:
        """Applies both owned migration files in order. Each is IF NOT EXISTS-safe."""
        for migration in _MIGRATIONS:
            self._connection.executescript(migration.read_text(encoding="utf-8"))

    def close(self) -> None:
        self._connection.close()

    # ---------------------------------------------------------------- reads

    def head_revision(self, *, project_id: str, plan_id: str) -> int:
        """Current head revision. 0 if none exists yet (contract Section 10: a new ID
        starts at 0)."""
        row = self._connection.execute(
            "SELECT MAX(revision) AS head FROM plan_revisions WHERE project_id = ? AND plan_id = ?",
            (project_id, plan_id),
        ).fetchone()
        return int(row["head"] or 0)

    def get(self, *, project_id: str, plan_id: str, revision: int | None = None) -> PlanRecord:
        """Re-reads one revision. Omitted means head (contract Section 3).

        Returns the stored ORIGINAL bytes parsed -- not a value the server re-serialized.
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
            raise ExchangeError("NOT_FOUND", 404, "No such plan revision.")
        return PlanRecord(
            plan=json.loads(bytes(row["plan_json"]).decode("utf-8")),
            revision=int(row["revision"]),
            state=str(row["state"]),
            plan_digest=str(row["plan_digest"]),
        )

    # ---------------------------------------------------------------- submission

    def submit(
        self,
        *,
        plan: dict[str, Any],
        expected_revision: int,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> PlanRecord:
        """Stores one plan as a new revision.

        Raises:
            ExchangeError: REVISION_CONFLICT (CAS failure or base_revision mismatch),
                IDEMPOTENCY_CONFLICT (same key, different request).
        """
        project_id = str(plan["project_id"])
        plan_id = str(plan["plan_id"])
        base_revision = int(plan["base_revision"])

        if expected_revision != base_revision:
            raise _revision_conflict(
                f"expected_revision({expected_revision}) does not match "
                f"plan.base_revision({base_revision})."
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
        plan_bytes = json.dumps(plan, ensure_ascii=False).encode("utf-8")
        created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._connection:  # BEGIN ... COMMIT / ROLLBACK
            head = self.head_revision(project_id=project_id, plan_id=plan_id)
            if base_revision != head:
                raise _revision_conflict(
                    f"base_revision({base_revision}) does not match current head({head})."
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
                raise _revision_conflict(f"revision {revision} already exists.") from error

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

    # ---------------------------------------------------------------- internal

    @staticmethod
    def _fingerprint(
        *,
        operation: str,
        project_id: str,
        principal_id: str,
        plan: dict[str, Any],
        expected_revision: int,
    ) -> str:
        """Contract Section 9.7 request fingerprint.

        sha256(JCS(dict(operation, project_id, principal_id, request))) where request is
        the HTTP body with only idempotency_key removed. The body follows contract Section
        3 ld_submit_plan shape, so this rebuilds that shape here.
        """
        request = dict(plan=plan, expected_revision=expected_revision)
        return canonical_digest(
            dict(
                operation=operation,
                project_id=project_id,
                principal_id=principal_id,
                request=request,
            )
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
        """Replays or conflicts when the same key already exists (contract Section 10)."""
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
                "A different request arrived with the same idempotency_key.",
                (Detail("", "idempotency key reused with a different request"),),
            )

        return self.get(
            project_id=project_id,
            plan_id=str(row["result_plan_id"]),
            revision=int(row["result_revision"]),
        )

    # ---------------------------------------------------------------- validations (M2)

    def save_validation(self, record: ValidationRecord) -> None:
        """SPEC-LDWIRE-001 M2 -- persists a ValidationReport, keyed by validation_id.

        ON CONFLICT DO NOTHING: validation_id is deterministic (compute_validation_id), so
        a retried submission with the identical inputs recomputes the SAME id -- this is a
        no-op replay, never a silent overwrite of the first-saved report.
        """
        self._connection.execute(
            "INSERT INTO validations "
            "(validation_id, project_id, plan_id, plan_digest, context_digest, "
            " compiled_digest, outcome, diagnostics_json, compiled_json, created_at, "
            " expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (validation_id) DO NOTHING",
            (
                record.validation_id,
                record.project_id,
                record.plan_id,
                record.plan_digest,
                record.context_digest,
                record.compiled_digest,
                record.outcome,
                json.dumps(record.diagnostics, ensure_ascii=False),
                json.dumps(record.compiled, ensure_ascii=False),
                record.created_at,
                record.expires_at,
            ),
        )

    def get_validation(self, *, project_id: str, validation_id: str) -> ValidationRecord | None:
        """SPEC-LDWIRE-001 M2 -- resolves validation_id back to its ValidationReport.

        Scoped to project_id -- a validation_id issued for one project never resolves
        under a different project_id, even if the row exists (REQ-LDWIRE-007: honest
        rejection of a mismatched project, never a promoted guess).
        """
        row = self._connection.execute(
            "SELECT * FROM validations WHERE project_id = ? AND validation_id = ?",
            (project_id, validation_id),
        ).fetchone()
        if row is None:
            return None
        return ValidationRecord(
            validation_id=str(row["validation_id"]),
            project_id=str(row["project_id"]),
            plan_id=str(row["plan_id"]),
            plan_digest=str(row["plan_digest"]),
            context_digest=str(row["context_digest"]),
            compiled_digest=str(row["compiled_digest"]),
            outcome=str(row["outcome"]),
            diagnostics=json.loads(str(row["diagnostics_json"])),
            compiled=json.loads(str(row["compiled_json"])),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
        )
