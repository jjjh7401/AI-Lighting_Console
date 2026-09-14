"""불변 저장 · revision CAS · 멱등 (SPEC-LDSTORE-001 M1 · AC-LDPLUGIN-015).

계약 §10 의 revision 규칙과 §9.7 의 idempotency fingerprint 를 기계로 고정한다.

계약 §10 의 핵심 셋:

1. ``expected_revision`` 과 ``plan.base_revision`` 이 **같아야** 한다. 새 ID 는 둘 다 0
   이며 서버 revision 1. 기존 ID 는 현재 head 와 같아야 하고 revision = head+1.
2. schema-invalid 는 revision 을 만들지 않는다.
3. 같은 key + 같은 fingerprint 는 최초 status·body 를 replay. 같은 key + 다른 request 는 409.

그리고 계약 §3: ``PlanRecord.plan`` 은 **제출 그대로**이며 ``base_revision`` 을 서버
revision 으로 덮어쓰지 않는다.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from server.director.digest import plan_digest
from server.director.models import ExchangeError
from server.director.store import DirectorStore

_EXAMPLES = (
    Path(__file__).resolve().parents[2] / ".moai" / "specs" / "SPEC-LDPLUGIN-001" / "examples"
)

_PRINCIPAL = "principal-0001"
_OPERATION = "PUT /api/director/v1/projects/p-0001/plans/plan-0001"


def _plan() -> dict:
    return json.loads((_EXAMPLES / "plan.json").read_text(encoding="utf-8"))


@pytest.fixture()
def store(tmp_path: Path) -> DirectorStore:
    return DirectorStore(tmp_path / "director.sqlite3")


class TestFirstSubmission:
    def test_new_plan_id_starts_at_revision_one(self, store: DirectorStore):
        plan = _plan()
        plan["base_revision"] = 0
        record = store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-0001",
        )
        assert record.revision == 1

    def test_expected_revision_must_equal_base_revision(self, store: DirectorStore):
        """계약 §10 — 둘이 어긋나면 저장하지 않는다."""
        plan = _plan()
        plan["base_revision"] = 0
        with pytest.raises(ExchangeError) as excinfo:
            store.submit(
                plan=plan,
                expected_revision=3,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-0002",
            )
        assert excinfo.value.code == "REVISION_CONFLICT"
        assert excinfo.value.http_status == 409

    def test_new_plan_id_with_nonzero_base_revision_is_rejected(self, store: DirectorStore):
        """계약 §10: *"새 ID 는 둘 다 0"*."""
        plan = _plan()
        plan["base_revision"] = 5
        with pytest.raises(ExchangeError) as excinfo:
            store.submit(
                plan=plan,
                expected_revision=5,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-0003",
            )
        assert excinfo.value.code == "REVISION_CONFLICT"


class TestRevisionCas:
    def _first(self, store: DirectorStore) -> None:
        plan = _plan()
        plan["base_revision"] = 0
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-first",
        )

    def test_second_submission_advances_head_by_one(self, store: DirectorStore):
        self._first(store)
        plan = _plan()
        plan["base_revision"] = 1
        record = store.submit(
            plan=plan,
            expected_revision=1,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-second",
        )
        assert record.revision == 2

    def test_stale_expected_revision_is_revision_conflict(self, store: DirectorStore):
        self._first(store)
        plan = _plan()
        plan["base_revision"] = 0
        with pytest.raises(ExchangeError) as excinfo:
            store.submit(
                plan=plan,
                expected_revision=0,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-stale",
            )
        assert excinfo.value.code == "REVISION_CONFLICT"

    def test_exactly_one_of_two_racing_submitters_wins(self, store: DirectorStore):
        """같은 expected_revision 두 제출 → 하나만 N+1, 다른 하나는 REVISION_CONFLICT.

        둘 다 성공하거나 둘 다 실패하면 FAIL이다. 순차 호출로도 CAS 의 본질(head 를
        읽고 쓰는 사이에 남이 끼어들 수 있다)은 재현된다 — 두 번째가 같은
        expected_revision 을 들고 오는 상황이 바로 그것이다.
        """
        self._first(store)
        outcomes = []
        for key in ("key-race-a", "key-race-b"):
            plan = _plan()
            plan["base_revision"] = 1
            try:
                record = store.submit(
                    plan=plan,
                    expected_revision=1,
                    principal_id=_PRINCIPAL,
                    operation=_OPERATION,
                    idempotency_key=key,
                )
                outcomes.append(("ok", record.revision))
            except ExchangeError as error:
                outcomes.append(("error", error.code))

        successes = [item for item in outcomes if item[0] == "ok"]
        failures = [item for item in outcomes if item[0] == "error"]
        assert len(successes) == 1, f"정확히 하나만 성공해야 한다: {outcomes}"
        assert successes[0][1] == 2
        assert failures[0][1] == "REVISION_CONFLICT"


class TestCasBackstopIsTheDatabaseNotJustTheHeadCheck:
    """head 를 읽고 INSERT 하는 사이에 남이 끼어드는 경로.

    위 `TestRevisionCas` 는 **순차** 호출이라 애플리케이션의 head 검사에서 걸린다.
    그 검사만으로는 진짜 인터리빙을 막지 못한다 — 두 요청이 같은 head 를 읽은 뒤
    둘 다 INSERT 하는 창이 남는다. 그 창을 닫는 것은 DB 의 PRIMARY KEY 다. 그것이
    실제로 존재하고 발사되는지 따로 잰다.
    """

    def test_primary_key_rejects_a_duplicate_revision(self, store: DirectorStore, tmp_path: Path):
        plan = _plan()
        plan["base_revision"] = 0
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-pk",
        )
        # head 검사를 우회해 DB 에 직접 같은 revision 을 밀어넣는다 — 인터리빙의 결과와
        # 같은 상태다. DB 가 막아야 한다.
        with sqlite3.connect(store.path) as connection, pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO plan_revisions (project_id, plan_id, revision, plan_json, "
                "plan_digest, base_revision, state, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    plan["project_id"],
                    plan["plan_id"],
                    1,
                    b"{}",
                    "sha256:" + "0" * 64,
                    0,
                    "submitted",
                    "2026-09-14T00:00:00Z",
                ),
            )

    def test_two_connections_racing_the_same_revision_yield_one_winner(self, tmp_path: Path):
        """두 연결이 같은 expected_revision 으로 동시에 들어오면 하나만 이긴다.

        DirectorStore 두 개(= 두 연결)를 쓴다. 실제 서버에서 두 요청이 각자 연결을
        갖는 것과 같은 모양이다.
        """
        import threading

        path = tmp_path / "race.sqlite3"
        seed = _plan()
        seed["base_revision"] = 0
        DirectorStore(path).submit(
            plan=seed,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-seed",
        )

        results: list[tuple[str, object]] = []
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def attempt(key: str) -> None:
            store = DirectorStore(path)
            plan = _plan()
            plan["base_revision"] = 1
            barrier.wait()
            try:
                record = store.submit(
                    plan=plan,
                    expected_revision=1,
                    principal_id=_PRINCIPAL,
                    operation=_OPERATION,
                    idempotency_key=key,
                )
                outcome: tuple[str, object] = ("ok", record.revision)
            except ExchangeError as error:
                outcome = ("error", error.code)
            except sqlite3.OperationalError as error:  # lock 경합은 실패가 아니라 재시도 사유
                outcome = ("busy", str(error))
            finally:
                store.close()
            with lock:
                results.append(outcome)

        threads = [threading.Thread(target=attempt, args=(f"key-race-{i}",)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        successes = [item for item in results if item[0] == "ok"]
        conflicts = [item for item in results if item[0] == "error"]
        busy = [item for item in results if item[0] == "busy"]

        assert len(results) == 2, f"두 시도가 모두 끝나야 한다: {results}"

        # 단언을 `<= 1` 로 느슨하게 두면 **둘 다 실패해도 통과**해 시험이 공허해진다.
        # 실측(12회 시행): 매번 정확히 ('error', 'ok') — 한쪽이 이기고 다른 쪽이
        # REVISION_CONFLICT 였고 lock 경합(`busy`)은 한 번도 없었다. 그래서 경합이
        # 없었다면 **정확히 하나**가 이겨야 한다고 단언한다.
        if not busy:
            assert len(successes) == 1, f"정확히 하나만 이겨야 한다: {results}"
            assert conflicts[0][1] == "REVISION_CONFLICT", f"패자의 사유가 다르다: {results}"
            assert successes[0][1] == 2

        # 중복 revision 이 남지 않았다.
        final = DirectorStore(path)
        head = final.head_revision(project_id=seed["project_id"], plan_id=seed["plan_id"])
        final.close()
        assert head == (2 if successes else 1)


class TestImmutability:
    def test_stored_plan_is_returned_exactly_as_submitted(self, store: DirectorStore):
        """계약 §3: *"plan 은 제출 그대로이며 base_revision 을 서버 revision 으로
        덮어쓰지 않는다."*
        """
        plan = _plan()
        plan["base_revision"] = 0
        submitted_digest = plan_digest(plan)
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-immutable",
        )
        record = store.get(project_id=plan["project_id"], plan_id=plan["plan_id"], revision=1)
        assert record.plan["base_revision"] == 0, "서버 revision 으로 덮어쓰였다"
        assert record.plan_digest == submitted_digest

    def test_past_revision_survives_reopening_the_same_file(self, tmp_path: Path):
        """재시작 후 **같은 파일에서 되읽어** 불변인지 확인한다.

        DB 를 지우고 다시 만드는 방식으로는 불변을 확인할 수 없다.
        """
        path = tmp_path / "director.sqlite3"
        plan = _plan()
        plan["base_revision"] = 0
        expected_digest = plan_digest(plan)

        first = DirectorStore(path)
        first.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-restart",
        )
        first.close()

        reopened = DirectorStore(path)
        record = reopened.get(project_id=plan["project_id"], plan_id=plan["plan_id"], revision=1)
        assert record.plan_digest == expected_digest
        assert record.plan["base_revision"] == 0
        assert record.plan == plan

    def test_head_is_returned_when_revision_is_omitted(self, store: DirectorStore):
        """계약 §3: *"최신 revision 생략 GET 은 head 를 반환한다."*"""
        for revision, base in ((1, 0), (2, 1)):
            plan = _plan()
            plan["base_revision"] = base
            store.submit(
                plan=plan,
                expected_revision=base,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key=f"key-head-{revision}",
            )
        plan = _plan()
        record = store.get(project_id=plan["project_id"], plan_id=plan["plan_id"])
        assert record.revision == 2


class TestInvalidSubmissionWritesNothing:
    def test_rejected_submission_creates_no_revision(self, store: DirectorStore):
        """계약 §10: *"schema-invalid 는 revision 을 만들지 않는다."*"""
        plan = _plan()
        plan["base_revision"] = 7  # 새 ID 인데 0 이 아니다 → 거부
        with pytest.raises(ExchangeError):
            store.submit(
                plan=plan,
                expected_revision=7,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-nowrite",
            )
        assert store.head_revision(project_id=plan["project_id"], plan_id=plan["plan_id"]) == 0

    def test_positive_control_a_valid_submission_does_write(self, store: DirectorStore):
        """음성 대조의 짝 — 거부만 확인하면 "아무것도 안 쓰는 저장소"도 통과한다."""
        plan = _plan()
        plan["base_revision"] = 0
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-control",
        )
        assert store.head_revision(project_id=plan["project_id"], plan_id=plan["plan_id"]) == 1


class TestIdempotency:
    """계약 §9.7 · §10."""

    def test_same_key_and_same_request_replays_the_first_result(self, store: DirectorStore):
        plan = _plan()
        plan["base_revision"] = 0
        first = store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-replay",
        )
        second = store.submit(
            plan=_plan() | {"base_revision": 0},
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-replay",
        )
        assert second.revision == first.revision, "replay 가 새 revision 을 만들었다"
        assert store.head_revision(project_id=plan["project_id"], plan_id=plan["plan_id"]) == 1

    def test_same_key_with_different_request_is_idempotency_conflict(self, store: DirectorStore):
        plan = _plan()
        plan["base_revision"] = 0
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation=_OPERATION,
            idempotency_key="key-collide",
        )
        different = _plan()
        different["base_revision"] = 0
        different["title"] = "다른 내용"
        with pytest.raises(ExchangeError) as excinfo:
            store.submit(
                plan=different,
                expected_revision=0,
                principal_id=_PRINCIPAL,
                operation=_OPERATION,
                idempotency_key="key-collide",
            )
        assert excinfo.value.code == "IDEMPOTENCY_CONFLICT"
        assert excinfo.value.http_status == 409

    def test_key_is_scoped_per_principal(self, store: DirectorStore):
        """계약 §9.7: unique index 는 (project_id, principal_id, operation, key) 다.

        다른 principal 이 같은 key 를 써도 남의 결과를 replay 받지 않는다.
        """
        plan = _plan()
        plan["base_revision"] = 0
        store.submit(
            plan=plan,
            expected_revision=0,
            principal_id="principal-A",
            operation=_OPERATION,
            idempotency_key="shared-key",
        )
        other = _plan()
        other["base_revision"] = 1
        record = store.submit(
            plan=other,
            expected_revision=1,
            principal_id="principal-B",
            operation=_OPERATION,
            idempotency_key="shared-key",
        )
        assert record.revision == 2, "다른 principal 의 key 가 replay 로 처리됐다"


class TestSchemaIsMigratedNotAssumed:
    def test_tables_exist_after_construction(self, tmp_path: Path):
        path = tmp_path / "director.sqlite3"
        DirectorStore(path).close()
        with sqlite3.connect(path) as connection:
            names = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        assert {"plan_revisions", "idempotency_keys"} <= names

    def test_constructing_twice_is_safe(self, tmp_path: Path):
        """마이그레이션이 두 번 돌아도 깨지지 않아야 한다."""
        path = tmp_path / "director.sqlite3"
        DirectorStore(path).close()
        DirectorStore(path).close()
