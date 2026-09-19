"""SPEC-LDSEND-001 M1 (REQ-LDSEND-013/015) — the shared apply-path function.

``run_director_apply()`` (server/director/execution.py) is the single
function ``director_api.py`` `post_apply()`(HTTP adapter) and the M3~M4
observation tool both call. This file pins:

- session isolation — apply always runs under a fresh, dedicated
  ``SessionKey`` distinct from whatever the caller's own ambient session is,
  and that dedicated session is restored to the caller's original session
  when the function returns (success or exception) (REQ-LDSEND-013);
- the replay short-circuit — ``result.replayed=True`` skips
  ``execute_bundles()`` entirely (REQ-LDSEND-015 단위 시험);
- the gate-rejected short-circuit — an ``ExchangeError`` raised by
  ``coordinator.apply()`` propagates BEFORE ``execute_bundles()`` is ever
  called, and the session/clearance close still happens exactly once
  (REQ-LDSEND-015 단위 시험);
- an exception raised from *inside* ``execute_bundles()`` (a console-link
  failure the M2 sender did not itself swallow) still closes the session
  exactly once — no self-loop, no leaked session (REQ-LDSEND-013);
- cross-session clearance isolation against a fake caller that never binds
  a session key at all (mimicking ``server/measurement/runner.py``, which
  shares ``DEFAULT_SESSION_KEY`` with everyone else today) — apply's own
  revoke must never touch that caller's clearance, and vice versa
  (AC-LDSEND-006, plan.md §2.0-나 D2).

Behavior-preservation regression for the ``post_apply()`` extraction itself
(REQ-LDSEND-015, byte-identical response/journal) is covered separately by
re-running the EXISTING ``test_director_ops_lifecycle.py`` /
``test_director_apply_rejection.py`` files unmodified — this file does not
duplicate that coverage.
"""

from __future__ import annotations

import contextvars
from pathlib import Path
from typing import Any

import pytest

from server.director.approvals import ApprovalBinding, ApprovalRegistry
from server.director.execution import (
    STATE_ACKNOWLEDGED,
    STATE_SENT,
    ApplyCoordinator,
    ExecutionJournal,
    run_director_apply,
)
from server.director.execution import (
    ExecutionResult as ApplyExecutionResult,
)
from server.director.models import ExchangeError
from server.director.store import DirectorStore
from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate
from server.safety.session_context import DEFAULT_SESSION_KEY, current_session_key

_PROJECT = "project-0001"
_PLAN = "plan-0001"
_PRINCIPAL = "principal-0001"


# ---------------------------------------------------------------------------
# fakes — coordinator/sender level (session-binding + control-flow tests)
# ---------------------------------------------------------------------------


class _FakeApplyCoordinator:
    """``.apply()``/``.revoke_clearances()`` 호출을 그대로 기록하는 최소 대역.

    ``run_director_apply()`` 자신의 세션 바인딩·제어 흐름만 재려는 시험에서
    쓴다 — 실제 재검사 로직(``ApplyCoordinator.apply`` 본체)은 이미
    ``test_director_apply_rejection.py`` 가 커버한다.
    """

    def __init__(
        self,
        *,
        result: ApplyExecutionResult | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self.result = result
        self.raise_error = raise_error
        self.apply_calls: list[dict[str, Any]] = []
        self.revoke_calls = 0
        self.session_key_at_apply: object | None = None

    def apply(self, **kwargs: Any) -> ApplyExecutionResult:
        self.apply_calls.append(kwargs)
        self.session_key_at_apply = current_session_key()
        if self.raise_error is not None:
            raise self.raise_error
        assert self.result is not None
        return self.result

    def revoke_clearances(self) -> None:
        self.revoke_calls += 1


class _FakeBundleSender:
    """``BundleSender`` protocol 대역 — 보낸 bundle 을 기록하고, 원하면
    ``send()`` 자체가 예외를 던지게 한다(콘솔 링크 실패 시나리오)."""

    def __init__(self, *, outcome: str = STATE_ACKNOWLEDGED, raise_error: Exception | None = None):
        self.outcome = outcome
        self.raise_error = raise_error
        self.sent_bundles: list[Any] = []

    def send(self, bundle: Any) -> str:
        self.sent_bundles.append(bundle)
        if self.raise_error is not None:
            raise self.raise_error
        return self.outcome


def _body(*, bundle_id: str = "bundle-a") -> dict[str, Any]:
    return {
        "approval_id": "approval-0001",
        "idempotency_key": "key-0001",
        "destination": {"show_id": "show-1", "sequence_id": "sequence-1"},
        "bundles": [{"bundle_id": bundle_id, "commands": ["Fixture 901 At 50"]}],
        "compiled_digest": "compiled-digest-1",
    }


def _kwargs(**overrides: Any) -> dict[str, Any]:
    base = dict(
        project_id=_PROJECT,
        plan_id=_PLAN,
        revision=1,
        principal_id=_PRINCIPAL,
        operation="POST apply",
        current_context_digest="ctx-digest-1",
        body=_body(),
    )
    base.update(overrides)
    return base


class TestSessionBindingAroundApply:
    def test_apply_runs_under_a_dedicated_session_key_and_restores_after(self, tmp_path: Path):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        result = ApplyExecutionResult(
            execution_id="exec-1",
            status="planned",
            response_status=201,
            response_body={"execution_id": "exec-1"},
            replayed=False,
        )
        coordinator = _FakeApplyCoordinator(result=result)
        sender = _FakeBundleSender()
        before = current_session_key()

        _, status = run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        assert status == 201
        # 전용 세션은 호출 전의 세션과 달라야 한다(REQ-LDSEND-013) — 이 시험이
        # 세션을 바인딩하지 않았다면 그 값은 DEFAULT_SESSION_KEY 다.
        assert coordinator.session_key_at_apply is not None
        assert coordinator.session_key_at_apply != before
        # 반환 후에는 호출 전 세션으로 정확히 되돌아온다.
        assert current_session_key() == before
        assert coordinator.revoke_calls == 1

    def test_revoke_then_reset_happens_exactly_once_on_the_success_path(self, tmp_path: Path):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        result = ApplyExecutionResult(
            execution_id="exec-1b",
            status="planned",
            response_status=201,
            response_body={"execution_id": "exec-1b"},
            replayed=False,
        )
        coordinator = _FakeApplyCoordinator(result=result)
        sender = _FakeBundleSender()

        run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        assert coordinator.revoke_calls == 1
        assert len(coordinator.apply_calls) == 1


class TestReplaySkipsExecuteBundles:
    def test_replayed_result_never_reaches_the_bundle_sender(self, tmp_path: Path):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        canned_body = {"execution_id": "exec-2", "state": "acknowledged"}
        result = ApplyExecutionResult(
            execution_id="exec-2",
            status="acknowledged",
            response_status=200,
            response_body=canned_body,
            replayed=True,
        )
        coordinator = _FakeApplyCoordinator(result=result)
        sender = _FakeBundleSender()

        response_body, status = run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        assert sender.sent_bundles == []
        assert response_body == canned_body
        assert status == 200
        # 세션 바인딩/회수는 replay 경로에서도 정확히 1회씩 일어난다(REQ-013).
        assert coordinator.revoke_calls == 1


class TestExecuteBundlesCalledOnFreshApply:
    def test_bundle_sender_is_invoked_and_its_outcome_is_merged_into_the_response(
        self, tmp_path: Path
    ):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        result = ApplyExecutionResult(
            execution_id="exec-3",
            status="planned",
            response_status=201,
            response_body={"execution_id": "exec-3", "state": "planned"},
            replayed=False,
        )
        coordinator = _FakeApplyCoordinator(result=result)
        sender = _FakeBundleSender(outcome=STATE_ACKNOWLEDGED)

        response_body, status = run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        assert len(sender.sent_bundles) == 1
        # execute_bundles() 의 집계 우선순위(모두 confirmed → STATE_SENT) 그대로
        # 응답에 병합된다 — run_director_apply() 는 그 값을 가공하지 않는다.
        assert response_body["state"] == STATE_SENT
        assert status == 201


class TestGateRejectedRaisesBeforeExecuteBundles:
    def test_exchange_error_propagates_and_still_closes_the_session_once(self, tmp_path: Path):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        error = ExchangeError("GATE_REJECTED", 422, "rejected by the safety gate")
        coordinator = _FakeApplyCoordinator(raise_error=error)
        sender = _FakeBundleSender()
        before = current_session_key()

        with pytest.raises(ExchangeError) as excinfo:
            run_director_apply(
                coordinator=coordinator,
                journal=journal,
                bundle_sender=sender,
                interference=None,
                **_kwargs(),
            )

        assert excinfo.value.code == "GATE_REJECTED"
        # apply() 자체가 거부됐으므로 execute_bundles() 는 절대 호출되지 않는다.
        assert sender.sent_bundles == []
        assert coordinator.revoke_calls == 1
        assert current_session_key() == before


class TestExceptionInsideExecuteBundlesStillClosesTheSession:
    def test_a_console_link_failure_propagates_but_session_is_still_reset(self, tmp_path: Path):
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        result = ApplyExecutionResult(
            execution_id="exec-4",
            status="planned",
            response_status=201,
            response_body={"execution_id": "exec-4"},
            replayed=False,
        )
        coordinator = _FakeApplyCoordinator(result=result)
        sender = _FakeBundleSender(raise_error=RuntimeError("console link exploded"))
        before = current_session_key()

        with pytest.raises(RuntimeError, match="console link exploded"):
            run_director_apply(
                coordinator=coordinator,
                journal=journal,
                bundle_sender=sender,
                interference=None,
                **_kwargs(),
            )

        # execute_bundles() 내부에서 난 예외도 finally 를 거친다 — 다음 요청이
        # 이 세션을 물려받지 않는다(REQ-LDSEND-013 예외 경로).
        assert coordinator.revoke_calls == 1
        assert current_session_key() == before


# ---------------------------------------------------------------------------
# cross-session clearance isolation — REAL SafetyGate (AC-LDSEND-006)
# ---------------------------------------------------------------------------


class _AlwaysOkConsole:
    """실제 ``SafetyGate`` 를 감사 배관까지 통과시키기 위한 최소 콘솔 대역."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecOutcome:
        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict[str, Any]:  # pragma: no cover - 이 시험은 안 씀
        raise RuntimeError(f"no such path: {path}")


def _binding() -> ApprovalBinding:
    return ApprovalBinding(
        approval_id="approval-0001",
        plan_id=_PLAN,
        plan_revision=1,
        plan_digest="plan-digest-1",
        context_digest="ctx-digest-1",
        compiled_digest="compiled-digest-1",
        principal_id=_PRINCIPAL,
        console_id="console-1",
        session_id="session-1",
        safety_policy_revision=1,
        approved_at="2026-01-01T00:00:00Z",
        expires_at="2099-01-01T00:00:00Z",
    )


def _register(approvals: ApprovalRegistry, binding: ApprovalBinding) -> None:
    # 시험 전용 지름길 — plan.md §2.0-마가 관측 도구(M3) 자신은 이 지름길을
    # 쓰지 않고 공개 ``approve()`` API 만 쓴다고 명시한다; 이 파일은 도구가
    # 아니라 M1 단위 시험이므로 test_director_ops_lifecycle.py 와 같은
    # 지름길을 그대로 재사용한다.
    approvals._approvals[binding.approval_id] = binding  # type: ignore[attr-defined]
    approvals._latest_by_plan[(_PROJECT, binding.plan_id)] = binding.approval_id  # type: ignore[attr-defined]


class TestCrossSessionClearanceIsolationDuringRunDirectorApply:
    """AC-LDSEND-006 — 세션 키를 바인딩하지 않는 fake 호출자
    (``server/measurement/runner.py`` 흉내, ``DEFAULT_SESSION_KEY`` 공유)가
    남긴 클리어런스는 apply 의 전용 세션 회수로 지워지지 않는다."""

    def test_a_default_session_callers_clearance_survives_applys_own_revoke(self, tmp_path: Path):
        console = _AlwaysOkConsole()
        gate = SafetyGate(console=console, audit=AuditLog(tmp_path / "audit"))
        store = DirectorStore(tmp_path / "director.sqlite3")
        store.submit(
            plan={"project_id": _PROJECT, "plan_id": _PLAN, "base_revision": 0, "body": "v1"},
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation="PUT /plans/plan-0001",
            idempotency_key="submit-key-1",
        )
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        approvals = ApprovalRegistry()
        _register(approvals, _binding())
        coordinator = ApplyCoordinator(journal=journal, approvals=approvals, store=store, gate=gate)

        # 측정기 흉내 — 세션 키를 바인딩하지 않고 DEFAULT_SESSION_KEY 로 자신의
        # 클리어런스를 남긴다(plan.md §2.0-나 D2 실측: server/measurement/
        # runner.py 는 오늘 어떤 세션 키도 바인딩하지 않는다).
        assert current_session_key() == DEFAULT_SESSION_KEY
        default_caller_line = "Fixture 9001 At 50"
        gate.screen([default_caller_line])

        sender = _FakeBundleSender(outcome=STATE_ACKNOWLEDGED)
        run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        # apply 는 자신의 전용 세션에서만 revoke_clearances() 를 불렀다 —
        # DEFAULT 세션의 클리어런스는 그대로 살아 있어야 한다.
        assert current_session_key() == DEFAULT_SESSION_KEY
        result = gate.execution_port.execute(default_caller_line)
        assert result.ok is True
        assert console.executed[-1] == default_caller_line

    def test_applys_clearance_survives_a_default_session_callers_revoke(self, tmp_path: Path):
        # AC-LDSEND-006 역방향 — apply 가 전용 세션에서 클리어런스를 받은 뒤,
        # 송신 직전에 DEFAULT 세션 호출자가 revoke_clearances() 를 불러도
        # apply 의 클리어런스는 지워지지 않아야 한다. revoke_clearances() 가
        # 호출 세션만이 아니라 전체를 비우도록 퇴행하면 이 시험이 깨진다.
        console = _AlwaysOkConsole()
        gate = SafetyGate(console=console, audit=AuditLog(tmp_path / "audit"))
        store = DirectorStore(tmp_path / "director.sqlite3")
        store.submit(
            plan={"project_id": _PROJECT, "plan_id": _PLAN, "base_revision": 0, "body": "v1"},
            expected_revision=0,
            principal_id=_PRINCIPAL,
            operation="PUT /plans/plan-0001",
            idempotency_key="submit-key-1",
        )
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        approvals = ApprovalRegistry()
        _register(approvals, _binding())
        coordinator = ApplyCoordinator(journal=journal, approvals=approvals, store=store, gate=gate)

        interloper_keys: list[object] = []

        def _default_caller_revokes() -> None:
            # 빈 Context 에서 돌리면 ContextVar 기본값, 곧 DEFAULT_SESSION_KEY 다
            # — 세션 키를 바인딩하지 않는 측정기 흉내.
            interloper_keys.append(current_session_key())
            gate.revoke_clearances()

        class _InterleavingSender:
            def __init__(self) -> None:
                self.results: list[Any] = []

            def send(self, bundle: Any) -> str:
                contextvars.Context().run(_default_caller_revokes)
                for command in bundle["commands"]:
                    self.results.append(gate.execution_port.execute(command))
                return STATE_ACKNOWLEDGED

        sender = _InterleavingSender()
        run_director_apply(
            coordinator=coordinator,
            journal=journal,
            bundle_sender=sender,
            interference=None,
            **_kwargs(),
        )

        # 끼어든 쪽이 정말 DEFAULT 세션이었는지(대조) — 아니면 이 시험은 공허하다.
        assert interloper_keys == [DEFAULT_SESSION_KEY]
        assert [r.ok for r in sender.results] == [True]
        assert console.executed == ["Fixture 901 At 50"]
