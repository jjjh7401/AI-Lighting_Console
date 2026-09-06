"""SPEC-COPILOT-BULKGATE-001 — 번들 위험 선언이 게이트의 단일 관문에 붙는다.

닫는 구멍. 감독이 곡 파일 하나를 올리면 명령 수십 건이 콘솔로 나가고 그 안에
`Store Sequence <N> Cue …` 와 `Store Timecode <slot>` 이 들어 있는데, 화면에는
승인 컨트롤이 없었다 — 2026-09-07 브라우저 실측에서 「명령 28개 · 실행 완료 25」
가 나갔고 감사 로그에 `approved` 항목은 없었다.

게이트가 죽은 게 아니다. `server/safety/classify.py` 는 명령 **텍스트**로
분류하고 `blacklist.yaml` 의 `Store` 항목 둘은 오브젝트 기준이라
(`Store /overwrite`, `Store Preset`) `Sequence` 도 `Timecode` 도 안 담긴다.
그 사실은 `test_writegate_merge_gap.py` 가 고정하고 있고, 이 SPEC 은 그 분류를
**의도적으로 안 움직인다** — 넓히면 룩 생성·FX·씬 컴파일에도 카드가 붙는다.

대신 아는 쪽이 선언한다: `SafetyGate.screen(commands, *, risk=BatchRisk(...))`.
이 파일은 그 선언 통로를 잰다.

한계. 여기서 재는 것은 **게이트 층**이다. 선언을 안 붙인 다른 디스패치 자리가
안전한지는 이 파일이 답하지 않는다 — 그 축은
`test_write_dispatch_census.py` 가 분류를 강제하는 자리다.
"""

from __future__ import annotations

from server.safety.audit import AuditLog
from server.safety.backup import BackupManager
from server.safety.gate import BatchRisk, SafetyGate
from server.safety.lock import LiveLock
from server.tests.test_safety_gate import FakeConsole, ScriptedApproval, _events

#: 오늘 전부 `safe` 로 분류되는 쇼파일 쓰기 — 선언이 없으면 카드가 안 뜬다.
#: `test_writegate_merge_gap.py` 가 그 판정을 고정하고 있다.
SONGCUE_BUNDLE = (
    "Store Sequence 210 Cue 1 /Merge",
    "Store Sequence 210 Cue 2 /Merge",
    "Store Sequence 210 Cue 3 /Merge",
    "Store Sequence 210",
    "Store Timecode 9",
)

SONGCUE_RISK = BatchRisk(
    reason=(
        "쇼파일 쓰기 — Sequence 210 에 큐 3건을 저장하고 Timecode 9 슬롯을 씁니다 "
        "(이 앱에는 시퀀스·타임코드 복원 경로가 없습니다)."
    ),
    kind="songcue",
)


def _gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or FakeConsole()
    audit = kwargs.pop("audit", None) or AuditLog(tmp_path / "audit")
    return SafetyGate(console=console, audit=audit, **kwargs), console, audit


class TestDeclarationSplitsTheVerdict:
    """AC-BULKGATE-002 — 같은 명령, 선언 유무만 다른 두 호출이 갈린다."""

    def test_without_the_declaration_the_bundle_clears(self, tmp_path):
        gate, _, _ = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[False]))
        decision = gate.screen(list(SONGCUE_BUNDLE))
        # 승인을 항상 거절하는 포트를 붙였는데도 청산된다 — 아무도 안 물었다는
        # 뜻이고, 이것이 2026-09-07 에 관측된 상태다.
        assert decision.cleared is True
        assert decision.approval_request is None

    def test_with_the_declaration_the_same_bundle_is_held(self, tmp_path):
        approval = ScriptedApproval(decisions=[False])
        gate, _, _ = _gate(tmp_path, approval_port=approval)
        decision = gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert decision.cleared is False
        assert decision.status == "rejected"
        assert len(approval.requests) == 1

    def test_the_card_carries_every_command_not_a_subset(self, tmp_path):
        # AC-BULKGATE-002 둘째 갈래. `held` 만 담으면 safe 로 분류된 명령이
        # 카드에서 빠지고 감독은 무엇을 수락하는지 못 본다.
        approval = ScriptedApproval(decisions=[True])
        gate, _, _ = _gate(tmp_path, approval_port=approval)
        gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert approval.requests[0].commands == SONGCUE_BUNDLE

    def test_the_declaration_reason_reaches_every_item(self, tmp_path):
        approval = ScriptedApproval(decisions=[True])
        gate, _, _ = _gate(tmp_path, approval_port=approval)
        gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        for item in approval.requests[0].items:
            assert SONGCUE_RISK.reason in item.risk_reasons


class TestOneCardPerBundle:
    """AC-BULKGATE-004 — 명령 N 건에 카드는 한 장이다."""

    def test_twenty_plus_commands_raise_exactly_one_request(self, tmp_path):
        approval = ScriptedApproval(decisions=[True])
        gate, _, _ = _gate(tmp_path, approval_port=approval)
        commands = [f"Store Sequence 210 Cue {n} /Merge" for n in range(1, 25)]
        gate.screen(commands, risk=SONGCUE_RISK)
        # N 회도 2회(선언 경로 + 분류 경로)도 아니다.
        assert len(approval.requests) == 1
        assert len(approval.requests[0].items) == len(commands)

    def test_a_classified_risky_command_keeps_its_own_reasons(self, tmp_path):
        # 분류가 이미 risky 로 본 명령이 섞여도 카드는 한 장이고, 그 항목이
        # 분류에서 받은 사유를 **잃지 않는다**.
        approval = ScriptedApproval(decisions=[True])
        gate, _, _ = _gate(tmp_path, approval_port=approval)
        mixed = [*SONGCUE_BUNDLE, "Store Preset 4.1"]
        gate.screen(mixed, risk=SONGCUE_RISK)
        assert len(approval.requests) == 1
        by_command = {item.command: item for item in approval.requests[0].items}
        preset = by_command["Store Preset 4.1"]
        assert preset.risk_reasons[0] == SONGCUE_RISK.reason
        # 선언 사유 뒤에 분류 사유가 그대로 남는다.
        assert len(preset.risk_reasons) > 1


class TestAuditRecordsTheDecision:
    """AC-BULKGATE-003 — 「executed N, approved 0」이 이 경로에서 재현되지 않는다."""

    def test_acceptance_writes_one_approved_event_with_the_kind(self, tmp_path):
        gate, _, audit = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[True]))
        gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        approved = _events(audit, "approved")
        assert len(approved) == 1
        assert approved[0]["kind"] == "songcue"
        assert approved[0]["commands"] == list(SONGCUE_BUNDLE)

    def test_rejection_writes_one_rejected_event_with_the_kind(self, tmp_path):
        gate, _, audit = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[False]))
        gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        rejected = _events(audit, "rejected")
        assert len(rejected) == 1
        assert rejected[0]["kind"] == "songcue"

    def test_an_undeclared_bundle_writes_no_kind(self, tmp_path):
        # REQ-BULKGATE-001 — 기본값에서 감사 문면도 오늘과 같다.
        gate, _, audit = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[True]))
        gate.screen(["Store Preset 4.1"])
        approved = _events(audit, "approved")
        assert len(approved) == 1
        assert "kind" not in approved[0]


class TestRefusalSendsNothing:
    """AC-BULKGATE-005 — 거절·미결선 어느 쪽도 0건이다."""

    def test_rejection_clears_nothing(self, tmp_path):
        gate, console, _ = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[False]))
        decision = gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert decision.cleared is False
        # 청산 토큰이 없으니 실행 포트가 한 건도 안 보낸다.
        for command in SONGCUE_BUNDLE:
            assert gate.execution_port.execute(command).ok is False
        assert console.executed == []

    def test_an_unwired_channel_denies_all(self, tmp_path):
        # 승인 포트를 아예 안 붙인 회차 — `DenyAllApprovalPort` 가 기본값이다.
        gate, console, _ = _gate(tmp_path)
        decision = gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert decision.cleared is False
        assert console.executed == []


class TestLockAndBackupStayBetweenApprovalAndClearance:
    """AC-BULKGATE-005 둘째 갈래 — 선언은 분기가 아니라 입력이다."""

    def test_a_lock_raised_during_approval_still_wins(self, tmp_path):
        # lock-FIRST (REQ-MVP-035): 승인 대기 중에 락이 켜지면 발사 0건.
        lock = LiveLock()
        approval = ScriptedApproval(decisions=[True], on_request=lambda _: lock.activate())
        gate, console, _ = _gate(tmp_path, approval_port=approval, lock=lock)
        decision = gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert decision.cleared is False
        assert console.executed == []

    def test_the_risky_path_backup_runs_before_clearance(self, tmp_path):
        backup_calls: list[str] = []
        backup = BackupManager(backup_action=lambda: backup_calls.append("b"))
        gate, _, _ = _gate(
            tmp_path, approval_port=ScriptedApproval(decisions=[True]), backup=backup
        )
        decision = gate.screen(list(SONGCUE_BUNDLE), risk=SONGCUE_RISK)
        assert decision.cleared is True
        # 선언 없이 같은 번들을 보내면 safe 경로라 백업이 안 돈다 — 그 대조가
        # 이 단언이 선언 경로 때문임을 보인다.
        assert backup_calls == ["b"]

    def test_an_undeclared_safe_bundle_still_skips_the_backup(self, tmp_path):
        backup_calls: list[str] = []
        backup = BackupManager(backup_action=lambda: backup_calls.append("b"))
        gate, _, _ = _gate(
            tmp_path, approval_port=ScriptedApproval(decisions=[True]), backup=backup
        )
        gate.screen(list(SONGCUE_BUNDLE))
        assert backup_calls == []
