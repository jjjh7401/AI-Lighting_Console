"""SPEC-LDRECV-001 M5 · REQ-LDPLUGIN-024 · AC-LDPLUGIN-024.

``execute_bundles`` — bundle 시퀀스 중 하나가 실패/간섭/불확실 전송되면 이후
bundle 을 전송하지 않고(``not_sent`` 로 receipt 에 보존) ``failed``/``partial``/
``unknown`` 을 정확히 구분한다. blind retry 나 atomic OSC rollback 을 주장하지
않는다 — 이 파일은 실제 콘솔 송신을 흉내내지 않고, 주입 가능한
:class:`~server.director.execution.BundleSender` seam 을 fake 로 대체해
분류 로직만 검사한다(``server/bridge/osc.py`` 는 import 하지 않는다).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.director.execution import (
    STATE_ACKNOWLEDGED,
    STATE_FAILED,
    STATE_NOT_SENT,
    STATE_PARTIAL,
    STATE_SENT,
    STATE_UNKNOWN,
    ExecutionJournal,
    execute_bundles,
)

_PROJECT = "project-0001"
_PRINCIPAL = "principal-0001"
_OPERATION = "POST apply"
_APPROVAL = "approval-0001"


class ScriptedSender:
    """순서대로 미리 정해둔 상태를 반환하는 fake sender — 호출 횟수를 기록한다."""

    def __init__(self, outcomes: list[str]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict] = []

    def send(self, bundle) -> str:
        self.calls.append(dict(bundle))
        return self._outcomes.pop(0)


class ScriptedInterference:
    """지정한 호출 순번에서 개입을 감지했다고 보고하는 fake."""

    def __init__(self, trigger_at: int | None) -> None:
        self._trigger_at = trigger_at
        self._calls = 0

    def check(self) -> bool:
        triggered = self._calls == self._trigger_at
        self._calls += 1
        return triggered


def _bundles(n: int) -> list[dict]:
    return [{"bundle_id": f"bundle-{i}", "commands": [f"cmd-{i}"]} for i in range(n)]


@pytest.fixture()
def journal(tmp_path: Path) -> ExecutionJournal:
    j = ExecutionJournal(tmp_path / "execution.sqlite3")
    j.begin_execution(
        project_id=_PROJECT,
        principal_id=_PRINCIPAL,
        operation=_OPERATION,
        idempotency_key="key-1",
        request={"plan_id": "plan-1"},
        approval_id=_APPROVAL,
        bundles=_bundles(4),
    )
    return j


def _execution_id(journal: ExecutionJournal) -> str:
    row = journal._connection.execute(  # noqa: SLF001 — 시험 전용 내부 조회
        "SELECT execution_id FROM executions LIMIT 1"
    ).fetchone()
    return str(row["execution_id"])


class TestSubsequentBundlesNotSentAfterFailure:
    def test_failure_stops_subsequent_sends(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_FAILED, STATE_SENT, STATE_SENT])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(4), sender=sender
        )
        assert result["bundles"] == [STATE_SENT, STATE_FAILED, STATE_NOT_SENT, STATE_NOT_SENT]
        assert len(sender.calls) == 2, "실패 이후 bundle 은 실제로 호출되지 않는다"

    def test_unknown_transmission_stops_subsequent_sends(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_UNKNOWN, STATE_SENT, STATE_SENT])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(4), sender=sender
        )
        assert result["bundles"] == [STATE_SENT, STATE_UNKNOWN, STATE_NOT_SENT, STATE_NOT_SENT]
        assert len(sender.calls) == 2


class TestStatePriority:
    """상태 우선순위 — 확인 불가(unknown) 항목이 하나라도 있으면 unknown 이
    partial 보다 우선한다."""

    def test_unknown_beats_partial(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_UNKNOWN])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(2), sender=sender
        )
        assert result["state"] == STATE_UNKNOWN
        assert result["recovery_required"] is True

    def test_partial_when_some_confirmed_and_some_not_sent(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_FAILED])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(2), sender=sender
        )
        assert result["state"] == STATE_PARTIAL

    def test_failed_when_nothing_confirmed_and_no_unknown(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_FAILED, STATE_FAILED])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(2), sender=sender
        )
        assert result["state"] == STATE_FAILED
        assert result["recovery_required"] is False

    def test_all_confirmed_is_not_failed_or_partial(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_ACKNOWLEDGED])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(2), sender=sender
        )
        assert result["state"] not in (STATE_FAILED, STATE_PARTIAL, STATE_UNKNOWN)
        assert result["bundles"] == [STATE_SENT, STATE_ACKNOWLEDGED]

    def test_partial_with_explicit_failed_recovery_required_stays_false(self, journal):
        """SPEC-LDRELEASE-001 §3 REQ-LDRELEASE-007 (1차 plan-audit D2 반영) —
        characterization/regression pin, RED-first 아님. ``partial`` 결과에
        명시적 ``failed`` 가 섞여도 ``recovery_required`` 는 오늘처럼 ``False``
        로 남는다 — ``recovery_required=True`` 는 ``unknown``(간섭 감지 포함)
        결과에만 결부된 계약이며, 이 SPEC 은 그 계약을 코드로 바꾸지 않고
        문서로만 확정한다(D2). 이 시험은 오늘 코드에서 이미 통과한다 — 새
        동작을 드라이브하는 것이 아니라 기존 계약을 고정하는 회귀 핀이다."""
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_ACKNOWLEDGED, STATE_FAILED])
        result = execute_bundles(
            journal, execution_id=execution_id, bundles=_bundles(2), sender=sender
        )
        assert result["state"] == STATE_PARTIAL
        assert result["recovery_required"] is False


class TestOperatorInterference:
    """operator 개입(programmer 변경) 감지 시 진행 중이던 execution 이
    unknown+recovery_required 로 전환된다."""

    def test_interference_mid_execution_converts_to_unknown_recovery_required(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_SENT])  # 2번째부터는 호출되면 안 된다
        interference = ScriptedInterference(trigger_at=1)
        result = execute_bundles(
            journal,
            execution_id=execution_id,
            bundles=_bundles(3),
            sender=sender,
            interference=interference,
        )
        assert result["state"] == STATE_UNKNOWN
        assert result["recovery_required"] is True
        assert result["bundles"] == [STATE_SENT, STATE_NOT_SENT, STATE_NOT_SENT]
        assert len(sender.calls) == 1, "개입 감지 이후 bundle 은 전송되지 않는다"

    def test_no_interference_never_reported_does_not_alter_outcome(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_SENT, STATE_SENT])
        interference = ScriptedInterference(trigger_at=None)
        result = execute_bundles(
            journal,
            execution_id=execution_id,
            bundles=_bundles(2),
            sender=sender,
            interference=interference,
        )
        assert result["recovery_required"] is False
        assert result["bundles"] == [STATE_SENT, STATE_SENT]


class TestJournalPersistence:
    """receipt 이 journal 에 실제로 not_sent 로 보존되는지 — 반환값이 아니라
    되읽어 확인한다."""

    def test_not_sent_bundles_are_persisted_in_the_journal(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_FAILED, STATE_SENT])
        execute_bundles(journal, execution_id=execution_id, bundles=_bundles(2), sender=sender)

        rows = journal._connection.execute(  # noqa: SLF001 — 시험 전용 내부 조회
            "SELECT bundle_index, state FROM execution_bundles "
            "WHERE execution_id = ? ORDER BY bundle_index",
            (execution_id,),
        ).fetchall()
        states = {int(row["bundle_index"]): str(row["state"]) for row in rows}
        assert states[0] == STATE_FAILED
        assert states[1] == STATE_NOT_SENT

    def test_overall_execution_state_is_finalized_in_the_journal(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender([STATE_FAILED, STATE_FAILED])
        execute_bundles(journal, execution_id=execution_id, bundles=_bundles(2), sender=sender)
        assert journal.status(execution_id) == STATE_FAILED


class TestUnknownSenderOutcomeRejected:
    def test_sender_returning_an_unrecognized_state_raises(self, journal):
        execution_id = _execution_id(journal)
        sender = ScriptedSender(["not-a-real-state"])
        with pytest.raises(ValueError):
            execute_bundles(journal, execution_id=execution_id, bundles=_bundles(1), sender=sender)
