"""t325 Phase 4 프로브 — 확대 전/후를 같은 명령으로 잰다.

`server/safety/` 를 고치지 않는다. 배치된 `blacklist.yaml` 을 그대로 읽으므로
확대 전에 한 번, 확대 후에 한 번 돌리면 두 회차가 바로 대조가 된다.

Phase 1~3 과 **다른 점**: 이 회차가 넣는 둘은 `Store` 형태가 **아니다**.
동사가 `Assign` · `Copy` 라 기존 항목 어느 것에도 안 닿았고, 그래서
`SEAL_DEFENCE` 의 seal-only 두 자리가 Phase 3 뒤에도 남아 있었다.

실행:  uv run python reports/classifygap-t325-p4/probe_p4.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import server
from server.safety.audit import AuditLog
from server.safety.classify import classify_command
from server.safety.gate import BatchRisk, SafetyGate
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

#: Phase 4 가 닫는 둘. 남은 seal-only 두 자리가 실어 나르는 바로 그 줄이다
#: (`_offer_fx_executor_assignment` · `_setlist_mode`).
P4_TARGETS = (
    "Assign Sequence 201 At Executor 101",
    "Copy Sequence 300 At 210",
)

#: Phase 1~3 이 이미 닫은 넷. 그대로 걸려 있어야 한다(회귀 확인).
ALREADY_CLOSED = (
    "Store Group 3",
    "Store Timecode 9",
    "Store Sequence 210 Cue 3 /Merge",
    "Store Cue 1",
)

#: 안 걸려야 하는 둘 — 프로그래머 값·선택 명령.
MUST_STAY_SAFE = ("Fixture 1 At 50", "Group 4")

#: 이 확대의 **경계**. 같은 동사인데 오브젝트가 `Sequence` 가 아니라서 안 걸려야
#: 하는 줄들. `UNCHANGED_SAFE` 가 계속 비준하는 자리이므로 함께 잰다.
SAME_VERB_MUST_STAY_SAFE = (
    "Copy Page 1 At Page 4",
    "Assign Preset 4.1 At Executor 101",
)

#: 같은 동사 + `Sequence` 오브젝트라 **걸려야** 하는 변형들. 잡는 것이 옵션이
#: 아니라 오브젝트라는 것을 문면으로 보여 준다.
TARGET_VARIANTS = (
    "Assign Sequence 4 Page 1.201",
    "Assign Sequence 3 At Timecode 7",
    "Copy Sequence 115 At 210",
)

POSITIVE_CONTROLS = ("Store Preset 4.101", "Delete Sequence 5")

# acceptance.md AC-CG-002 의 아홉 문장 — 프로그래머 트래픽. 전부 risky=False 여야 한다.
NEGATIVE_CONTROLS = (
    "Fixture 20 ; Attribute 'Pan' At 12",
    "At 100",
    "Group 4",
    "Fixture 1 Thru 12",
    "Set Selection MAtricks 'PhaseFromX' 0",
    "Label Group 3 'Vocals'",
    "Go+ Sequence 5",
    "Off Fixture 11",
    "ChangeDestination Root",
)


class _FakeConsole:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.safety.console import ExecOutcome

        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        raise RuntimeError(f"no such path: {path}")


class _CountingApproval:
    """승인 요청을 세는 포트. 항상 거절해서 「아무도 안 물었다」와 구분한다."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return False


def _classify(text: str):
    return classify_command(validate(text).parsed, load_ruleset())


def _line(text: str) -> str:
    f = _classify(text)
    return (
        f"  {text!r:52} -> matched_entry={f.matched_entry!r} "
        f"category={f.category!r} risky={f.risky}"
    )


def _gate(approval):
    tmp = Path(tempfile.mkdtemp(prefix="t325p4-"))
    return SafetyGate(console=_FakeConsole(), audit=AuditLog(tmp / "audit"), approval_port=approval)


def main() -> None:
    rs = load_ruleset()
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset ver : {rs.version}")
    print(f"blacklist   : {list(rs.blacklist)}")

    print("\n[A] 카드가 지정한 두 동사 — 이 회차의 대상")
    for c in P4_TARGETS:
        print(_line(c))

    print("\n[A-2] Phase 1~3 의 네 명령 — 회귀 확인")
    for c in ALREADY_CLOSED:
        print(_line(c))

    print("\n[A-3] 프로그래머 값·선택 — 안 걸려야 한다")
    for c in MUST_STAY_SAFE:
        print(_line(c))

    print("\n[A-4] 같은 동사인데 오브젝트가 `Sequence` 가 아니다 — 안 걸려야 한다")
    for c in SAME_VERB_MUST_STAY_SAFE:
        print(_line(c))

    print("\n[A-5] 같은 동사 + `Sequence` 변형 — 걸려야 한다 (잡는 것은 오브젝트다)")
    for c in TARGET_VARIANTS:
        print(_line(c))

    print("\n[B] AC-CG-001 확대판 — 여섯 명령 전부 risky=True")
    six = (*ALREADY_CLOSED, *P4_TARGETS)
    ok = []
    for c in six:
        f = _classify(c)
        good = f.risky and f.matched_entry is not None
        ok.append(good)
        print(f"  {c!r:52} -> {'PASS' if good else 'FAIL'} (matched={f.matched_entry!r})")
    print(f"  => AC-CG-001 (Phase 4 확대판): {sum(ok)}/6")

    print("\n[C] 양성 대조군 (원래 걸리던 것 — 그대로 걸려야 한다)")
    for c in POSITIVE_CONTROLS:
        print(_line(c))

    print("\n[D] 음성 대조군 — 프로그래머 트래픽 (AC-CG-002: 전부 risky=False)")
    bad = []
    for c in NEGATIVE_CONTROLS:
        print(_line(c))
        f = _classify(c)
        if f.risky or f.matched_entry is not None:
            bad.append(c)
    print(f"  => risky 로 잘못 판정된 문장: {len(bad)} {bad}")

    print("\n[D-2] 안 걸려야 하는 넷을 한 자리에 (must-pass 음성 대조군)")
    bad2 = []
    for c in (*MUST_STAY_SAFE, *SAME_VERB_MUST_STAY_SAFE):
        print(_line(c))
        f = _classify(c)
        if f.risky or f.matched_entry is not None:
            bad2.append(c)
    print(f"  => risky 로 잘못 판정된 문장: {len(bad2)} {bad2}")

    print("\n[E] 흐름 단위 음성 대조군 (AC-CG-003: 승인 요청 0건, cleared=True)")
    approval = _CountingApproval()
    gate = _gate(approval)
    bundle = [*NEGATIVE_CONTROLS[:5], *MUST_STAY_SAFE, *SAME_VERB_MUST_STAY_SAFE]
    decision = gate.screen(bundle)
    print(f"  bundle           : {bundle}")
    print(f"  approval requests: {len(approval.requests)}")
    print(f"  cleared          : {decision.cleared}  status={decision.status!r}")

    # AC-CG-003 의 번들은 [E] 다. 아래는 **AC 가 아니라** 아홉 문장을 흐름으로
    # 통과시킨 참고 측정이다. 아홉 문장에는 호출 동사(`Go+ Sequence 5` ·
    # `Off Fixture 11`, category='invoking')가 둘 들어 있고, 그 둘은 확대와
    # 무관하게 expand-or-hold 규칙(REQ-MVP-026)으로 보류된다. Phase 3 이 한 번
    # 「AC-CG-003 위반」처럼 적었다가 스스로 정정한 자리다 — 카드 수는 0 이
    # 아니며, 확대 전/후 값이 **같아야** 한다는 것이 이 측정의 요점이다.
    print("\n[E-2] 참고 — 아홉 문장 전부를 흐름으로 (호출 동사 둘 때문에 0 이 아니다)")
    approval1b = _CountingApproval()
    gate1b = _gate(approval1b)
    decision1b = gate1b.screen(list(NEGATIVE_CONTROLS))
    print(f"  approval requests: {len(approval1b.requests)}  (확대 전/후 같아야 한다)")
    print(f"  cleared          : {decision1b.cleared}  status={decision1b.status!r}")
    if approval1b.requests:
        for item in approval1b.requests[0].items:
            print(f"    보류된 줄: {item.command!r:44} | {item.risk_reasons}")

    print("\n[F] 봉합 + 확대 동시 투입 (AC-CG-004: 요청 정확히 1건, 사유 병기)")
    sealed_bundle = [
        *P4_TARGETS,
        "Fixture 20 ; Attribute 'Pan' At 12",
    ]
    approval2 = _CountingApproval()
    gate2 = _gate(approval2)
    gate2.screen(
        sealed_bundle,
        risk=BatchRisk(reason="SEAL-REASON", kind="setlist"),
    )
    print(f"  approval requests: {len(approval2.requests)}")
    if approval2.requests:
        req = approval2.requests[0]
        print(f"  items in request : {len(req.items)}")
        for item in req.items:
            print(f"    {item.command!r:52} | {item.risk_reasons}")


if __name__ == "__main__":
    main()
