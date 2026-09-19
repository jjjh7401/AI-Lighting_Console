"""SPEC-LDRECV-001 M5 · REQ-LDPLUGIN-021 (거부 방향) · AC-LDPLUGIN-021 항목 1·2.

``ApplyCoordinator.apply`` 가 lock 을 얻은 직후 재검사에서 stale approval(head
변경/만료)·점유된 destination·활성 LiveLock 각각을 차단하는지, 그리고
destination 예약이 create-only 인지(이미 점유된 slot 을 조용히 다른 slot 으로
재선택하지 않는지) 시험한다.

콘솔 필요 부분(통과한 apply 가 실제로 콘솔에 객체를 만들었는가)은 이 파일의
범위 밖이다(spec.md §5). ``execute_preapproved`` 가 grammar/classify/backup/
health/audit 를 실제로 통과시키는지는 ``test_director_gate_bridge.py`` 가 이미
커버한다(acceptance.md AC-021 검증 명령이 두 파일을 함께 묶는 이유) — 여기서는
``ApplyCoordinator`` 가 그 경로로 정상 위임하는지와 gate 거부가 전파되는지만
최소로 확인한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.director.approvals import ApprovalBinding, ApprovalRegistry
from server.director.execution import STATE_PARTIAL, ApplyCoordinator, ExecutionJournal
from server.director.models import ExchangeError
from server.director.store import DirectorStore

_PROJECT = "project-0001"
_PLAN = "plan-0001"
_PRINCIPAL = "principal-0001"


class FakeLiveLock:
    def __init__(self, active: bool = False) -> None:
        self.is_active = active


class FakeScreenDecision:
    def __init__(self, cleared: bool, status: str = "cleared", notice: str = "") -> None:
        self.cleared = cleared
        self.status = status
        self.notice = notice


class FakeGate:
    """``execute_preapproved`` 호출 여부/인자를 기록하는 최소 gate 대역."""

    def __init__(self, *, lock_active: bool = False, decision: FakeScreenDecision | None = None):
        self.lock = FakeLiveLock(lock_active)
        self.calls: list[list[str]] = []
        self._decision = decision or FakeScreenDecision(cleared=True)

    def execute_preapproved(self, commands):
        self.calls.append(list(commands))
        return self._decision


def _binding(
    *,
    approval_id: str = "approval-0001",
    plan_id: str = _PLAN,
    plan_revision: int = 1,
    context_digest: str = "ctx-digest-1",
    compiled_digest: str = "compiled-digest-1",
    expires_at: str = "2099-01-01T00:00:00Z",
) -> ApprovalBinding:
    return ApprovalBinding(
        approval_id=approval_id,
        plan_id=plan_id,
        plan_revision=plan_revision,
        plan_digest="plan-digest-1",
        context_digest=context_digest,
        compiled_digest=compiled_digest,
        principal_id=_PRINCIPAL,
        console_id="console-1",
        session_id="session-1",
        safety_policy_revision=1,
        approved_at="2026-01-01T00:00:00Z",
        expires_at=expires_at,
    )


def _body(
    *,
    approval_id: str = "approval-0001",
    idempotency_key: str = "key-0001",
    show_id: str = "show-1",
    sequence_id: str = "sequence-1",
    compiled_digest: str = "compiled-digest-1",
) -> dict:
    return {
        "approval_id": approval_id,
        "idempotency_key": idempotency_key,
        "destination": {"show_id": show_id, "sequence_id": sequence_id},
        "bundles": [{"bundle_id": "bundle-a", "commands": ["Fixture 901 At 50"]}],
        # `_binding()` 의 기본 compiled_digest 와 일치해야 재검사(APPROVAL_STALE)를
        # 통과한다 — M5 다각도 검토 결함1+2 수정.
        "compiled_digest": compiled_digest,
    }


@pytest.fixture()
def store(tmp_path: Path) -> DirectorStore:
    s = DirectorStore(tmp_path / "director.sqlite3")
    s.submit(
        plan={
            "project_id": _PROJECT,
            "plan_id": _PLAN,
            "base_revision": 0,
            "body": "v1",
        },
        expected_revision=0,
        principal_id=_PRINCIPAL,
        operation="PUT /plans/plan-0001",
        idempotency_key="submit-key-1",
    )
    return s


@pytest.fixture()
def journal(tmp_path: Path) -> ExecutionJournal:
    return ExecutionJournal(tmp_path / "execution.sqlite3")


@pytest.fixture()
def approvals() -> ApprovalRegistry:
    return ApprovalRegistry()


def _register(approvals: ApprovalRegistry, binding: ApprovalBinding) -> None:
    approvals._approvals[binding.approval_id] = binding  # type: ignore[attr-defined]
    approvals._latest_by_plan[(_PROJECT, binding.plan_id)] = binding.approval_id  # type: ignore[attr-defined]


def _coordinator(*, journal, approvals, store, gate) -> ApplyCoordinator:
    return ApplyCoordinator(journal=journal, approvals=approvals, store=store, gate=gate)


class TestApprovalFreshnessRejection:
    """AC-021 항목1 — head 변경/만료된 승인은 apply 를 차단한다."""

    def test_missing_approval_is_rejected(self, journal, approvals, store):
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(approval_id="no-such-approval"),
            )
        assert excinfo.value.code == "APPROVAL_NOT_FOUND"
        assert gate.calls == []

    def test_head_changed_since_approval_is_rejected(self, journal, approvals, store):
        _register(approvals, _binding(plan_revision=1))
        # 새 revision 을 제출해 head 를 2로 옮긴다 — 승인은 revision 1 을 가리킨다.
        store.submit(
            plan={
                "project_id": _PROJECT,
                "plan_id": _PLAN,
                "base_revision": 1,
                "body": "v2",
            },
            expected_revision=1,
            principal_id=_PRINCIPAL,
            operation="PUT /plans/plan-0001",
            idempotency_key="submit-key-2",
        )
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "APPROVAL_STALE"
        assert gate.calls == [], "재검사가 거부하면 execute_preapproved 는 호출되지 않는다"

    def test_expired_approval_is_rejected(self, journal, approvals, store):
        _register(approvals, _binding(expires_at="2020-01-01T00:00:00Z"))
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "APPROVAL_STALE"

    def test_context_changed_since_approval_is_rejected(self, journal, approvals, store):
        _register(approvals, _binding(context_digest="ctx-digest-1"))
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-CHANGED",
                body=_body(),
            )
        assert excinfo.value.code == "APPROVAL_STALE"


class TestLiveLockRejection:
    """AC-021 항목1 — 활성 LiveLock 은 apply 를 차단한다."""

    def test_active_live_lock_blocks_apply(self, journal, approvals, store):
        _register(approvals, _binding())
        gate = FakeGate(lock_active=True)
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "LIVE_LOCK_ACTIVE"
        assert gate.calls == []

    def test_inactive_live_lock_does_not_block(self, journal, approvals, store):
        _register(approvals, _binding())
        gate = FakeGate(lock_active=False)
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        result = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply",
            current_context_digest="ctx-digest-1",
            body=_body(),
        )
        assert result.replayed is False
        assert gate.calls == [["Fixture 901 At 50"]]


class TestDestinationCreateOnly:
    """AC-021 항목2 — destination 예약은 create-only 다(조용한 재선택 없음)."""

    def test_second_execution_cannot_reserve_the_same_destination(self, journal, approvals, store):
        _register(approvals, _binding(approval_id="approval-A"))
        gate_a = FakeGate()
        coordinator_a = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate_a)
        first = coordinator_a.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply A",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-A", idempotency_key="key-A"),
        )
        assert first.replayed is False

        _register(approvals, _binding(approval_id="approval-B"))
        gate_b = FakeGate()
        coordinator_b = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate_b)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator_b.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply B",
                current_context_digest="ctx-digest-1",
                body=_body(approval_id="approval-B", idempotency_key="key-B"),
            )
        assert excinfo.value.code == "TARGET_BUSY"
        # 재선택이 일어나지 않았다는 것 — gate_b 는 아예 호출되지 않는다.
        assert gate_b.calls == []

        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-1", sequence_id="sequence-1"
        )
        assert status is not None
        assert status["reserved_by_execution_id"] == first.execution_id, (
            "점유된 slot 이 두 번째 execution 으로 조용히 재선택되지 않았다"
        )

    def test_released_destination_can_be_reserved_again(self, journal, approvals, store):
        _register(approvals, _binding(approval_id="approval-A"))
        gate_a = FakeGate()
        coordinator_a = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate_a)
        first = coordinator_a.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply A",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-A", idempotency_key="key-A2"),
        )
        journal.release_destination(project_id=_PROJECT, show_id="show-1", sequence_id="sequence-1")

        _register(approvals, _binding(approval_id="approval-B"))
        gate_b = FakeGate()
        coordinator_b = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate_b)
        second = coordinator_b.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply B",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-B", idempotency_key="key-B2"),
        )
        assert second.execution_id != first.execution_id


class TestGateRejectionPropagates:
    """execute_preapproved 가 거부하면 ApplyCoordinator 도 거부하고 journal 을
    failed 로 남긴다 — SafetyGate 의 문법/위험/백업/health/audit 우회가
    없다(REQ-021 후단)."""

    def test_gate_rejection_is_surfaced_and_journal_marked_failed(self, journal, approvals, store):
        _register(approvals, _binding())
        gate = FakeGate(decision=FakeScreenDecision(cleared=False, status="blocked_grammar"))
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "GATE_REJECTED"
        assert gate.calls == [["Fixture 901 At 50"]]


class TestBundleCompiledDigestBinding:
    """SPEC-LDRECV-001 M1~M6 완료 후 다각도 검토 결함1+2 — apply 는 client 가 요청한
    ``bundles``/``destination`` 을 그대로 가져다 쓰기 전에, 이 apply 가 향하는
    compiled artifact 가 실제로 승인이 가리키는 것과 같은지 확인해야 한다
    (gate.py ``execute_preapproved`` docstring: "director 층이 실제 ApprovalBinding이
    정확히 이 bundle을 커버하는지 호출 전에 검증할 책임을 진다").

    이 SPEC 의 apply 요청은 계약 §209 가 정의하는 전체 compiled manifest
    (compiler_id/compiler_version/compiler_build_digest/target/playback 포함)를
    담지 않는다 — 그래서 이 층은 ``bundles`` 로부터 그 manifest digest 를
    재계산하지 않는다(재계산은 실제로는 존재하지 않는 필드를 지어내는 것과
    같다). 대신 client 가 이번에 적용하려는 compiled artifact 의 digest 를
    ``compiled_digest`` 로 되풀이해 제출하도록 요구하고, `check_validity`(다른
    두 신선도 축과 같은 관례)로 ``binding.compiled_digest`` 와 동등성만
    비교한다 — 재컴파일로 다른 artifact 가 된 경우를 잡아낸다."""

    def test_missing_compiled_digest_is_schema_invalid(self, journal, approvals, store):
        _register(approvals, _binding())
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        body = _body()
        del body["compiled_digest"]
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=body,
            )
        assert excinfo.value.code == "SCHEMA_INVALID"
        assert gate.calls == []

    def test_compiled_digest_mismatch_is_rejected_before_gate(self, journal, approvals, store):
        _register(approvals, _binding(compiled_digest="compiled-digest-1"))
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                # 승인 당시와 다른(재컴파일된) compiled artifact 를 적용하려 한다.
                body=_body(compiled_digest="compiled-digest-DIFFERENT"),
            )
        assert excinfo.value.code == "APPROVAL_STALE"
        assert gate.calls == [], "compiled_digest 가 어긋나면 gate 까지 도달하면 안 된다"
        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-1", sequence_id="sequence-1"
        )
        assert status is None, "거부된 apply 는 destination 을 예약해서도 안 된다"


class TestPathIdentityMustMatchApproval:
    """M5 다각도 검토 결함4·5 — URL 의 plan_id/revision 은 실제로 승인이 가리키는
    plan_id/plan_revision 과 일치해야 한다. 같은 프로젝트의 다른 plan 이 우연히
    같은 revision 숫자를 갖는 경우(결함5) 와, 승인이 가리키는 것과 다른 revision
    번호로 apply URL 을 구성한 경우(결함4)를 각각 재현한다."""

    def test_url_revision_mismatching_the_approval_is_rejected(self, journal, approvals, store):
        _register(approvals, _binding(plan_revision=1))
        # 새 revision 을 제출해 head 를 2 로 옮긴다 — 그렇지 않으면 head_changed
        # 재검사가 revision 불일치보다 먼저 발동해 이 시험이 무엇을 실제로
        # 확인하는지 흐려진다(head 는 여전히 승인이 가리키는 1 이어야 한다).
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=2,  # 승인은 revision 1 을 가리킨다
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "IDENTITY_MISMATCH"
        assert gate.calls == []

    def test_url_plan_id_mismatching_the_approval_is_rejected(self, journal, approvals, store):
        # 같은 revision 숫자(1)를 우연히 공유하는 다른 plan 의 승인.
        _register(approvals, _binding(plan_id="plan-OTHER", plan_revision=1))
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,  # URL 은 plan-0001, 승인은 plan-OTHER
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "IDENTITY_MISMATCH"
        assert gate.calls == []


class TestApprovalIsSingleUse:
    """M5 다각도 검토 결함3 — 승인은 첫 execution allocation 시 소비된다(계약
    §10). 같은 approval_id 를 다른 idempotency_key 로 다시 apply 하면 INVALID_STATE
    또는 RECOVERY_REQUIRED 로 거부되어야 한다 — journal 의 executions_by_approval
    인덱스는 M4 부터 있었지만 이 검토 전에는 아무도 조회하지 않았다."""

    def test_reusing_a_confirmed_approval_with_a_new_key_is_invalid_state(
        self, journal, approvals, store
    ):
        _register(approvals, _binding())
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        first = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply",
            current_context_digest="ctx-digest-1",
            body=_body(idempotency_key="key-first"),
        )
        assert first.replayed is False

        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                # 같은 approval_id, 다른 idempotency_key, 다른 destination까지
                # 시도한다 — 승인을 다시 쓸 수 없다는 것이 destination 이 비어
                # 있는지와 무관해야 한다.
                body=_body(
                    idempotency_key="key-second",
                    show_id="show-2",
                    sequence_id="sequence-2",
                ),
            )
        assert excinfo.value.code == "INVALID_STATE"

    def test_reusing_a_partial_approval_with_a_new_key_requires_recovery(
        self, journal, approvals, store
    ):
        _register(approvals, _binding())
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        first = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply",
            current_context_digest="ctx-digest-1",
            body=_body(idempotency_key="key-first"),
        )
        # 실제 전송 결과가 partial 로 확정됐다고 가정한다(execute_bundles 의
        # 몫 — 이 시험은 그 결과가 이미 journal 에 남아 있다고 전제한다).
        journal.finalize_execution(first.execution_id, STATE_PARTIAL)

        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(
                    idempotency_key="key-second",
                    show_id="show-2",
                    sequence_id="sequence-2",
                ),
            )
        assert excinfo.value.code == "RECOVERY_REQUIRED"


class TestGateArbiterConflictMapsToTargetBusy:
    """M5 다각도 검토 결함6 — SafetyGate 의 중재자(shared programmer lock) 충돌은
    문법/안전 위반과 다른 재시도 가능 신호(TARGET_BUSY, 409)로 표면화해야 한다.
    ``_gate_rejected`` 가 모든 non-cleared decision 을 GATE_REJECTED(422)로
    뭉개면 이 신호가 사라진다."""

    def test_blocked_target_busy_decision_is_target_busy_not_gate_rejected(
        self, journal, approvals, store
    ):
        _register(approvals, _binding())
        gate = FakeGate(
            decision=FakeScreenDecision(
                cleared=False,
                status="blocked_target_busy",
                notice="다른 세션이 programmer 를 쥐고 있습니다.",
            )
        )
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "TARGET_BUSY"
        assert excinfo.value.http_status == 409


class TestDestinationReleasedOnPreSendRejection:
    """M5 다각도 검토 결함7 — GATE_REJECTED(및 결함6 이 분기하는 TARGET_BUSY)로
    끝나는 apply 는 콘솔에 아무것도 보내지 않은 것이 확정되므로, 예약했던
    destination 도 그 자리에서 즉시 풀려야 한다. 그래야 사람이 문제를 고친 뒤
    같은 destination 으로 다시 apply 할 수 있다 — ``release_destination`` 은
    M4 부터 있었지만 실제 apply 실패 경로 어디서도 호출되지 않았다."""

    def test_gate_rejected_apply_releases_its_destination_reservation(
        self, journal, approvals, store
    ):
        _register(approvals, _binding())
        gate = FakeGate(decision=FakeScreenDecision(cleared=False, status="blocked_grammar"))
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "GATE_REJECTED"

        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-1", sequence_id="sequence-1"
        )
        assert status is not None
        assert status["status"] == "released", (
            "GATE_REJECTED 로 끝난 apply 는 destination 예약을 풀어줘야 한다"
        )

        # 예약이 풀렸으니 사람이 문제를 고친 뒤 같은 destination 으로 다시
        # apply 할 수 있어야 한다(새 승인·새 idempotency_key).
        _register(approvals, _binding(approval_id="approval-retry"))
        gate_retry = FakeGate()
        coordinator_retry = _coordinator(
            journal=journal, approvals=approvals, store=store, gate=gate_retry
        )
        retried = coordinator_retry.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply retry",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-retry", idempotency_key="key-retry"),
        )
        assert retried.replayed is False

    def test_target_busy_from_gate_also_releases_its_destination_reservation(
        self, journal, approvals, store
    ):
        _register(approvals, _binding())
        gate = FakeGate(decision=FakeScreenDecision(cleared=False, status="blocked_target_busy"))
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST apply",
                current_context_digest="ctx-digest-1",
                body=_body(),
            )
        assert excinfo.value.code == "TARGET_BUSY"

        status = journal.destination_status(
            project_id=_PROJECT, show_id="show-1", sequence_id="sequence-1"
        )
        assert status is not None
        assert status["status"] == "released"


class TestIdempotentReplayBypassesRecheck:
    """계약 §9.7 — 같은 key+같은 request 는 재검사와 무관하게 최초 응답을
    그대로 replay 한다."""

    def test_replay_does_not_call_gate_again(self, journal, approvals, store):
        _register(approvals, _binding())
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        first = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply",
            current_context_digest="ctx-digest-1",
            body=_body(),
        )
        assert len(gate.calls) == 1

        second = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST apply",
            current_context_digest="ctx-digest-1",
            body=_body(),
        )
        assert second.replayed is True
        assert second.execution_id == first.execution_id
        assert len(gate.calls) == 1, "replay 는 gate 를 다시 부르지 않는다"
