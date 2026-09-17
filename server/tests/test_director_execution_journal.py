"""durable execution journal · idempotency · destination 예약 (SPEC-LDRECV-001 M4 ·
AC-LDPLUGIN-023).

계약 §9.7·§10 이 단일 원본이다. 핵심 셋:

1. 같은 ``(project_id, principal_id, operation, idempotency_key)`` + 같은 request
   fingerprint 재제출 → 최초 status·body 그대로 replay (재실행 아님).
2. 같은 key + 다른 request → ``IDEMPOTENCY_CONFLICT``(409).
3. socket send 후 DB commit 전 crash(합성) → 재시작 후 조회 시 그 execution 은
   ``unknown`` 이며 blind 하게 success/failed 로 확정하지 않는다.

fingerprint 계산은 형제 ``SPEC-LDSTORE-001`` ``store.py``/``AC-LDPLUGIN-015`` 와 같은
알고리즘(``sha256(JCS({operation,project_id,principal_id,request}))``)이다 —
``server.director.digest.canonical_digest`` 를 그대로 재사용한다.

**주의(계약 §10·형제 LDSTORE 주의와 동일)**: durability 는 DB 파일을 지우고 다시
만드는 방식으로 확인하지 않는다. 프로세스 재시작은 **같은 파일**을 가리키는 새
:class:`ExecutionJournal` 인스턴스로 재현하고, 그 인스턴스로 되읽어 확인한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from server.director.execution import (
    RESERVATION_RELEASED,
    RESERVATION_RESERVED,
    STATE_PLANNED,
    STATE_UNKNOWN,
    ExecutionJournal,
)
from server.director.models import ExchangeError

_PROJECT = "project-0001"
_PRINCIPAL = "principal-0001"
_OPERATION = "POST /api/director/v1/projects/project-0001/plans/plan-0001/apply"
_APPROVAL = "approval-0001"


def _bundles() -> list[dict[str, str]]:
    return [{"bundle_id": "bundle-a"}, {"bundle_id": "bundle-b"}]


@pytest.fixture()
def journal(tmp_path: Path) -> ExecutionJournal:
    return ExecutionJournal(tmp_path / "execution.sqlite3")


class TestIdempotentReplay:
    """AC-LDPLUGIN-023 — 같은 key+같은 request 는 최초 응답을 그대로 replay."""

    def test_same_key_and_same_request_replays_the_first_response(self, journal: ExecutionJournal):
        request = {"plan_id": "plan-0001", "plan_revision": 1}
        first = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-replay",
            request=request,
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        second = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-replay",
            request=dict(request),
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        assert second.replayed is True
        assert second.execution_id == first.execution_id
        assert second.response_status == first.response_status
        assert second.response_body == first.response_body

    def test_replay_does_not_create_a_second_execution_row(self, journal: ExecutionJournal):
        request = {"plan_id": "plan-0001", "plan_revision": 1}
        journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-single",
            request=request,
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-single",
            request=dict(request),
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        with sqlite3.connect(journal.path) as connection:
            (count,) = connection.execute("SELECT COUNT(*) FROM executions").fetchone()
        assert count == 1, "replay 가 새 execution 을 만들었다"

    def test_same_key_with_different_request_is_idempotency_conflict(
        self, journal: ExecutionJournal
    ):
        journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-collide",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        with pytest.raises(ExchangeError) as excinfo:
            journal.begin_execution(
                project_id=_PROJECT,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-collide",
                request={"plan_id": "plan-0001", "plan_revision": 2},
                approval_id=_APPROVAL,
                bundles=_bundles(),
            )
        assert excinfo.value.code == "IDEMPOTENCY_CONFLICT"
        assert excinfo.value.http_status == 409

    def test_key_is_scoped_per_principal(self, journal: ExecutionJournal):
        """계약 §9.7: unique index 는 (project_id, principal_id, operation, key) 다."""
        request = {"plan_id": "plan-0001", "plan_revision": 1}
        first = journal.begin_execution(
            project_id=_PROJECT,
            principal_id="principal-A",
            operation=_OPERATION,
            idempotency_key="shared-key",
            request=request,
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        second = journal.begin_execution(
            project_id=_PROJECT,
            principal_id="principal-B",
            operation=_OPERATION,
            idempotency_key="shared-key",
            request=request,
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        assert second.execution_id != first.execution_id, "다른 principal 의 key 가 replay 됐다"

    def test_positive_control_two_different_keys_create_two_executions(
        self, journal: ExecutionJournal
    ):
        """음성 대조의 짝 — 거부/충돌만 확인하면 "아무것도 안 쓰는 journal" 도 통과한다."""
        first = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-a",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        second = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-b",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        assert first.execution_id != second.execution_id


class TestFingerprintAlgorithmMatchesLdstore:
    """fingerprint 는 형제 LDSTORE 와 동일 알고리즘이어야 한다 (계약 §9.7)."""

    def test_fingerprint_uses_canonical_digest_of_the_same_shape(self, journal: ExecutionJournal):
        from server.director.digest import canonical_digest

        request = {"plan_id": "plan-0001", "plan_revision": 1}
        expected = canonical_digest(
            {
                "operation": _OPERATION,
                "project_id": _PROJECT,
                "principal_id": _PRINCIPAL,
                "request": request,
            }
        )
        journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-fp",
            request=request,
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        with sqlite3.connect(journal.path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT request_fingerprint FROM idempotency_records WHERE idempotency_key = ?",
                ("key-fp",),
            ).fetchone()
        assert row is not None
        assert str(row["request_fingerprint"]) == expected


class TestCrashSimulationYieldsUnknown:
    """AC-LDPLUGIN-023 — socket send 후 DB commit 전 crash(합성) → unknown.

    실제 프로세스를 죽이지 않는다 — "socket send 후" 에 해당하는 코드 경로
    (``mark_sending``) 를 커밋한 뒤, 그 다음 커밋(``finalize_execution``)을
    **호출하지 않는 것**으로 crash 를 합성한다. 재시작은 같은 파일을 가리키는 새
    :class:`ExecutionJournal` 인스턴스로 재현한다.
    """

    def test_crash_after_send_before_commit_reads_as_unknown(self, tmp_path: Path):
        path = tmp_path / "execution.sqlite3"
        journal = ExecutionJournal(path)
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-crash",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        assert result.status == STATE_PLANNED

        # "socket send 직전" 상태를 디스크에 커밋한다 (계약 §10: "planned→sending(디스크
        # commit)"). 이 커밋 자체는 살아남는다 — crash 는 이 다음 지점에서 일어난다.
        journal.mark_sending(result.execution_id)

        # crash 합성: 실제 socket send 이후 결과를 기록하는 커밋(finalize_execution)이
        # 일어나지 않는다. 프로세스가 여기서 죽었다고 가정하고 journal 을 닫지 않은 채
        # 버린다 — 새 연결로 "재시작"을 재현한다.
        del journal

        restarted = ExecutionJournal(path)
        try:
            assert restarted.status(result.execution_id) == STATE_UNKNOWN
        finally:
            restarted.close()

    def test_a_completed_execution_does_not_read_as_unknown(self, tmp_path: Path):
        """양성 대조 — sending 에서 멈추지 않고 끝까지 커밋되면 unknown 이 아니다."""
        path = tmp_path / "execution.sqlite3"
        journal = ExecutionJournal(path)
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-complete",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        journal.mark_sending(result.execution_id)
        journal.finalize_execution(result.execution_id, "sent")

        assert journal.status(result.execution_id) == "sent"

        restarted = ExecutionJournal(path)
        try:
            assert restarted.status(result.execution_id) == "sent"
        finally:
            restarted.close()
        journal.close()

    def test_an_execution_still_in_planned_state_is_not_unknown(self, journal: ExecutionJournal):
        """양성 대조 — sending 에 진입하지 않았으면 (아직 전송 시도 전) unknown 이 아니다."""
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-planned",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        assert journal.status(result.execution_id) == STATE_PLANNED

    def test_querying_an_unknown_execution_id_is_not_found(self, journal: ExecutionJournal):
        with pytest.raises(ExchangeError) as excinfo:
            journal.status("execution-does-not-exist")
        assert excinfo.value.code == "NOT_FOUND"
        assert excinfo.value.http_status == 404


class TestDurabilitySurvivesReopeningTheSameFile:
    """형제 LDSTORE AC-LDPLUGIN-015 와 동일 주의 — DB 를 지우고 다시 만드는 방식으로
    durability 를 확인하지 않는다. 같은 파일을 재시작 후 되읽는다."""

    def test_past_execution_survives_reopening_the_same_file(self, tmp_path: Path):
        path = tmp_path / "execution.sqlite3"
        first = ExecutionJournal(path)
        result = first.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-restart",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        first.mark_sending(result.execution_id)
        first.finalize_execution(result.execution_id, "acknowledged")
        first.close()

        reopened = ExecutionJournal(path)
        try:
            assert reopened.status(result.execution_id) == "acknowledged"
            replay = reopened.begin_execution(
                project_id=_PROJECT,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-restart",
                request={"plan_id": "plan-0001", "plan_revision": 1},
                approval_id=_APPROVAL,
                bundles=_bundles(),
            )
            assert replay.replayed is True
            assert replay.execution_id == result.execution_id
        finally:
            reopened.close()


class TestDestinationReservation:
    """design.md §3 — destination_reservations, create-only (LD-TARGET-001)."""

    def test_reserve_is_create_only_and_rejects_a_second_reservation(
        self, journal: ExecutionJournal
    ):
        journal.reserve_destination(
            project_id=_PROJECT,
            show_id="show-0001",
            sequence_id="sequence-0001",
            execution_id="execution-a",
        )
        with pytest.raises(ExchangeError) as excinfo:
            journal.reserve_destination(
                project_id=_PROJECT,
                show_id="show-0001",
                sequence_id="sequence-0001",
                execution_id="execution-b",
            )
        assert excinfo.value.code == "TARGET_BUSY"
        assert excinfo.value.http_status == 409

    def test_reservation_does_not_silently_reselect_a_different_slot(
        self, journal: ExecutionJournal
    ):
        """create-only — 점유된 slot 을 조용히 다른 빈 slot 으로 재선택하지 않는다."""
        journal.reserve_destination(
            project_id=_PROJECT,
            show_id="show-0001",
            sequence_id="sequence-0001",
            execution_id="execution-a",
        )
        with pytest.raises(ExchangeError):
            journal.reserve_destination(
                project_id=_PROJECT,
                show_id="show-0001",
                sequence_id="sequence-0001",
                execution_id="execution-b",
            )
        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-0001", sequence_id="sequence-0001"
        )
        assert status is not None
        assert status["reserved_by_execution_id"] == "execution-a", (
            "거부된 두 번째 요청이 예약을 가로챘다 — silent reselection"
        )

    def test_release_then_reserve_again_succeeds(self, journal: ExecutionJournal):
        journal.reserve_destination(
            project_id=_PROJECT,
            show_id="show-0002",
            sequence_id="sequence-0002",
            execution_id="execution-a",
        )
        journal.release_destination(
            project_id=_PROJECT, show_id="show-0002", sequence_id="sequence-0002"
        )
        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-0002", sequence_id="sequence-0002"
        )
        assert status is not None
        assert status["status"] == RESERVATION_RELEASED

        journal.reserve_destination(
            project_id=_PROJECT,
            show_id="show-0002",
            sequence_id="sequence-0002",
            execution_id="execution-c",
        )
        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-0002", sequence_id="sequence-0002"
        )
        assert status is not None
        assert status["status"] == RESERVATION_RESERVED
        assert status["reserved_by_execution_id"] == "execution-c"

    def test_an_unreserved_slot_has_no_status(self, journal: ExecutionJournal):
        assert (
            journal.destination_status(
                project_id=_PROJECT, show_id="show-empty", sequence_id="sequence-empty"
            )
            is None
        )

    def test_reservation_scoped_by_project(self, journal: ExecutionJournal):
        """다른 project 의 같은 show/sequence id 는 별개 slot 이다."""
        journal.reserve_destination(
            project_id="project-x",
            show_id="show-shared",
            sequence_id="sequence-shared",
            execution_id="execution-x",
        )
        # 다른 project 에서는 같은 show/sequence 조합이 비어 있어야 한다 — 충돌 없음.
        journal.reserve_destination(
            project_id="project-y",
            show_id="show-shared",
            sequence_id="sequence-shared",
            execution_id="execution-y",
        )


class TestSchemaIsMigratedSequentially:
    """001_initial.sql 뒤에 002_execution_journal.sql 이 순서대로 적용되는지 —
    EXTEND(스키마 재정의 아님)."""

    def test_both_migrations_tables_exist_after_construction(self, tmp_path: Path):
        path = tmp_path / "execution.sqlite3"
        ExecutionJournal(path).close()
        with sqlite3.connect(path) as connection:
            names = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        # 001 의 테이블(형제 LDSTORE 소유, 재정의 아님 — 다시 적용해도 안전해야 한다)
        assert {"plan_revisions", "idempotency_keys"} <= names
        # 002 가 새로 추가하는 테이블
        assert {
            "executions",
            "execution_bundles",
            "idempotency_records",
            "destination_reservations",
        } <= names

    def test_constructing_twice_is_safe(self, tmp_path: Path):
        path = tmp_path / "execution.sqlite3"
        ExecutionJournal(path).close()
        ExecutionJournal(path).close()

    def test_001_initial_sql_is_not_modified_by_this_migration(self):
        """PRESERVE — 001_initial.sql 은 이 SPEC 이 손대지 않는다."""
        migration_001 = (
            Path(__file__).resolve().parents[2]
            / "server"
            / "director"
            / "migrations"
            / "001_initial.sql"
        )
        content = migration_001.read_text(encoding="utf-8")
        assert "plan_revisions" in content
        assert "idempotency_keys" in content
        # 002 가 소유하는 테이블 이름이 001 안에 있으면 안 된다 — 재정의가 아니라
        # 이어붙이기여야 한다.
        assert "destination_reservations" not in content
        assert "CREATE TABLE IF NOT EXISTS executions" not in content

    def test_bundle_journal_records_one_row_per_bundle(self, journal: ExecutionJournal):
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-bundles",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        with sqlite3.connect(journal.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT bundle_id, state FROM execution_bundles WHERE execution_id = ? "
                "ORDER BY bundle_index",
                (result.execution_id,),
            ).fetchall()
        assert [dict(row) for row in rows] == [
            {"bundle_id": "bundle-a", "state": STATE_PLANNED},
            {"bundle_id": "bundle-b", "state": STATE_PLANNED},
        ]

    def test_approval_id_is_stored_on_the_execution_row(self, journal: ExecutionJournal):
        """승인 소비의 durable 기록 — execution 행이 approval_id 를 갖는다."""
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-approval",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        with sqlite3.connect(journal.path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT approval_id FROM executions WHERE execution_id = ?",
                (result.execution_id,),
            ).fetchone()
        assert row is not None
        assert str(row["approval_id"]) == _APPROVAL


class TestOneTransactionForFirstWrite:
    """M4 의 핵심 불변식 — 승인 소비·execution·bundle journal·fingerprint·destination
    예약이 하나의 transaction 이다. 하나라도 실패하면 전부 롤백된다."""

    def test_a_rejected_destination_reservation_after_begin_execution_does_not_orphan_it(
        self, journal: ExecutionJournal
    ):
        """destination 재검사는 apply 호출자(M5)의 책임이지만, begin_execution 이후
        reserve_destination 을 별도로 호출하는 순서에서도 execution 행 자체는 이미
        커밋되어 있어야 한다(fail-closed 재검사는 M5 가 사용하는 조합이다) — 이 시험은
        그 조합이 이 계층에서 깨지지 않는지만 확인한다."""
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-combo",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
        )
        journal.reserve_destination(
            project_id=_PROJECT,
            show_id="show-0003",
            sequence_id="sequence-0003",
            execution_id=result.execution_id,
        )
        assert journal.status(result.execution_id) == STATE_PLANNED
        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-0003", sequence_id="sequence-0003"
        )
        assert status is not None
        assert status["status"] == RESERVATION_RESERVED

    def test_begin_execution_commits_destination_reservation_atomically(self, tmp_path: Path):
        """begin_execution 에 destination 을 함께 넘기면 같은 transaction 으로 커밋된다."""
        path = tmp_path / "execution.sqlite3"
        journal = ExecutionJournal(path)
        result = journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-atomic",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
            destination={"show_id": "show-0004", "sequence_id": "sequence-0004"},
        )
        journal.close()

        reopened = ExecutionJournal(path)
        try:
            status = reopened.destination_status(
                project_id=_PROJECT, show_id="show-0004", sequence_id="sequence-0004"
            )
            assert status is not None
            assert status["status"] == RESERVATION_RESERVED
            assert status["reserved_by_execution_id"] == result.execution_id
        finally:
            reopened.close()

    def test_a_second_begin_execution_with_an_already_reserved_destination_is_target_busy(
        self, tmp_path: Path
    ):
        path = tmp_path / "execution.sqlite3"
        journal = ExecutionJournal(path)
        journal.begin_execution(
            project_id=_PROJECT,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-first",
            request={"plan_id": "plan-0001", "plan_revision": 1},
            approval_id=_APPROVAL,
            bundles=_bundles(),
            destination={"show_id": "show-0005", "sequence_id": "sequence-0005"},
        )
        with pytest.raises(ExchangeError) as excinfo:
            journal.begin_execution(
                project_id=_PROJECT,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-second",
                request={"plan_id": "plan-0001", "plan_revision": 2},
                approval_id=_APPROVAL,
                bundles=_bundles(),
                destination={"show_id": "show-0005", "sequence_id": "sequence-0005"},
            )
        assert excinfo.value.code == "TARGET_BUSY"

        # 실패한 두 번째 시도는 execution 행도 남기지 않는다 — 하나의 transaction.
        with sqlite3.connect(path) as connection:
            (count,) = connection.execute("SELECT COUNT(*) FROM executions").fetchone()
        assert count == 1, "실패한 begin_execution 이 부분적으로 커밋됐다"
        journal.close()
