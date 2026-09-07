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

#: 곡→콘솔 흐름이 실제로 보내는 쇼파일 쓰기 번들. 2026-09-07 실측의 그 번들이다.
#:
#: 갱신 기록 (t299 / SPEC-COPILOT-CLASSIFYGAP-001 Phase 1): 이 상수의 주석은
#: 「오늘 전부 `safe` 로 분류된다」였다. **더는 전부가 아니다** — 블랙리스트 v5 가
#: `Store Timecode` 를 넣었으므로 마지막 줄은 선언이 없어도 분류 층이 잡는다.
#: 앞의 `Store Sequence` 네 줄은 아직 `safe` 다(Phase 2 가 그것을 받는다).
#: 즉 이 번들은 이제 **섞인** 번들이고, 그 사실이 아래 두 검사를 갱신하게 만든다.
SONGCUE_BUNDLE = (
    "Store Sequence 210 Cue 1 /Merge",
    "Store Sequence 210 Cue 2 /Merge",
    "Store Sequence 210 Cue 3 /Merge",
    "Store Sequence 210",
    "Store Timecode 9",
)

#: 분류 층이 **원리적으로** 조용한 번들 — 프로그래머 값과 선택뿐이고 쇼파일을
#: 안 고친다.
#:
#: 왜 상수가 하나 더 필요한가. 「선언이 갈래를 만든다」를 재려면 분류 층이 조용한
#: 번들이 필요하다. v5 이후 `SONGCUE_BUNDLE` 은 그 조건을 잃었다.
#:
#: 갱신 근거 (t299 Phase 2): Phase 1 은 이 상수를 `SONGCUE_BUNDLE[:4]`
#: (`Store Sequence` 계열)로 뒀고, 「Phase 2 가 `Store Sequence` 를 넣으면 이
#: 상수도 조건을 잃는다」고 스스로 예고했다. 그 날이 왔다. 그래서 이번에는 **남은
#: 구멍으로 옮기지 않는다** — 다음 리비전에 또 잃기 때문이다. 대신 폐집합이
#: 원리적으로 안 담는 계열로 옮긴다: 폐집합은 쇼파일 **쓰기** 오브젝트만 담고
#: (`blacklist.yaml` 헤더), 아래 세 줄은 프로그래머 값·대상 선택·목적지 지정이라
#: 어떤 리비전도 담지 않는다. 리터럴을 또 바꾸지 않아도 되는 자리다.
#:
#: `Store` 로 시작하는 줄이 하나도 없는 것이 핵심이다 — 다른 `Store` 오브젝트로
#: 옮기는 것은 충돌을 다음 리비전으로 미루는 것일 뿐이다(Phase 1 이 배운 것).
PROGRAMMER_ONLY_BUNDLE = (
    "ChangeDestination Root",
    "Group 11",
    "Attribute 'Dimmer' At 80",
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
        """갱신 근거 (t299 Phase 2): 대상 번들이 `PROGRAMMER_ONLY_BUNDLE` 로 바뀐다.

        재는 축은 그대로 「선언 유무만 다른 두 호출이 갈리는가」다. 바뀐 것은
        분류 층이고, v6 이 `Store Sequence` 를 잡으므로 Phase 1 이 골라 둔
        `Store Sequence` 계열로는 이 축을 더는 못 잰다 — 청산되지 않는 이유가
        선언 부재가 아니라 분류가 되기 때문이다. 그러면 이 검사는 초록/빨강과
        무관하게 **무엇을 재는지 모르는 검사**가 된다.

        Phase 1 은 남은 구멍으로 옮겼고 한 리비전 만에 다시 잃었다. 그래서 이번에는
        폐집합이 원리적으로 안 담는 계열(프로그래머 값)로 옮긴다 —
        `PROGRAMMER_ONLY_BUNDLE` docstring 에 근거를 적었다.

        **A/B 를 한 번들로 되돌린다.** Phase 1 이 대상만 바꾼 결과 「선언 없음」과
        「선언 있음」을 서로 **다른** 번들로 재게 됐고, 그러면 갈래가 선언 때문인지
        번들 때문인지 구별되지 않는다. 아래는 같은 번들을 두 번 지나게 해서 차이가
        선언 하나뿐이게 만든다.
        """
        gate, _, _ = _gate(tmp_path, approval_port=ScriptedApproval(decisions=[False]))
        decision = gate.screen(list(PROGRAMMER_ONLY_BUNDLE))
        # 승인을 항상 거절하는 포트를 붙였는데도 청산된다 — 아무도 안 물었다는 뜻이다.
        assert decision.cleared is True
        assert decision.approval_request is None

        # 같은 번들 + 선언 → 보류. 차이는 선언 하나뿐이므로 갈래를 만든 것이
        # 선언임이 이 짝으로 확정된다(비공허성).
        declared_gate, _, _ = _gate(
            tmp_path / "declared", approval_port=ScriptedApproval(decisions=[False])
        )
        declared = declared_gate.screen(
            list(PROGRAMMER_ONLY_BUNDLE),
            risk=BatchRisk(reason="선언 축 대조군", kind="probe"),
        )
        assert declared.cleared is False
        assert declared.approval_request is not None

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

    def test_every_production_screen_surface_accepts_the_declaration(self):
        """부품이 초록이어도 경로는 안 이어질 수 있다 — 실측으로 잡힌 결함.

        `SafetyGate.screen` 만 고치고 브라우저를 돌렸더니
        `TypeError: _ObservingBundleGate.screen() got an unexpected keyword
        argument 'risk'` 가 났다. 프로덕션은 게이트를 **감싼 래퍼**를 통해
        들어가는데 그 래퍼가 선언을 못 받았다. 단위 검사는 날것의 게이트를
        써서 이 자리를 못 봤다.

        그래서 여기서는 인스턴스가 아니라 **프로덕션 소스 전수**를 본다:
        `screen(self, commands, ...)` 를 정의하는 모든 자리가 `risk` 를
        키워드로 받아야 한다. 새 래퍼가 생겨도 같은 자리에서 걸린다.
        """
        import ast
        from pathlib import Path

        offenders: list[str] = []
        for path in sorted(Path("server").rglob("*.py")):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef) or node.name != "screen":
                    continue
                positional = [a.arg for a in node.args.args]
                if positional[:2] != ["self", "commands"]:
                    continue
                keyword_only = {a.arg for a in node.args.kwonlyargs}
                if "risk" not in keyword_only:
                    offenders.append(f"{path}:{node.lineno}")
        assert not offenders, (
            "선언을 못 받는 screen 표면이 있습니다 — 프로덕션 경로에서 "
            f"TypeError 로 터집니다: {offenders}"
        )

    def test_an_undeclared_safe_bundle_still_skips_the_backup(self, tmp_path):
        """갱신 근거 (t299 Phase 2): 검사 이름이 요구하는 것은 **safe 번들**이고,
        v6 이후 Phase 1 이 골라 둔 `Store Sequence` 계열도 safe 번들이 아니다.

        그래서 대상만 `PROGRAMMER_ONLY_BUNDLE` 로 바꾼다. 단언은 바이트 그대로다 —
        재는 것은 「위험하지 않은 번들에는 백업이 안 돈다」이고 그 성질은 안
        바뀌었다. 잡히는 번들로 계속 재면 백업이 도는 것이 **정상**인 상태에서
        「안 돈다」를 단언하게 되고, 그것은 이 검사가 지키려는 성질과 반대다.

        이번 대상은 폐집합이 원리적으로 안 담는 계열이라 다음 리비전에 또 바꾸지
        않아도 된다(`PROGRAMMER_ONLY_BUNDLE` docstring).
        """
        backup_calls: list[str] = []
        backup = BackupManager(backup_action=lambda: backup_calls.append("b"))
        gate, _, _ = _gate(
            tmp_path, approval_port=ScriptedApproval(decisions=[True]), backup=backup
        )
        gate.screen(list(PROGRAMMER_ONLY_BUNDLE))
        assert backup_calls == []
