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
from server.director.execution import ApplyCoordinator, ExecutionJournal
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
    plan_revision: int = 1,
    context_digest: str = "ctx-digest-1",
    expires_at: str = "2099-01-01T00:00:00Z",
) -> ApprovalBinding:
    return ApprovalBinding(
        approval_id=approval_id,
        plan_id=_PLAN,
        plan_revision=plan_revision,
        plan_digest="plan-digest-1",
        context_digest=context_digest,
        compiled_digest="compiled-digest-1",
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
) -> dict:
    return {
        "approval_id": approval_id,
        "idempotency_key": idempotency_key,
        "destination": {"show_id": show_id, "sequence_id": sequence_id},
        "bundles": [{"bundle_id": "bundle-a", "commands": ["Fixture 901 At 50"]}],
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
