"""t299 Phase 1 프로브 — 확대 전/후를 같은 명령으로 잰다.

`server/safety/` 를 고치지 않는다. 배치된 `blacklist.yaml` 을 그대로 읽으므로
확대 전에 한 번, 확대 후에 한 번 돌리면 두 회차가 바로 대조가 된다.

실행:  uv run python reports/classifygap-t299-p1/probe_p1.py
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

# Phase 1 이 닫는 두 명령. Sequence·Cue 는 Phase 2·3 이므로 대조로만 찍는다.
P1_TARGETS = ("Store Group 3", "Store Timecode 9")
P2P3_TARGETS = ("Store Sequence 210 Cue 3 /Merge", "Store Cue 1")
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
    tmp = Path(tempfile.mkdtemp(prefix="t299p1-"))
    return SafetyGate(console=_FakeConsole(), audit=AuditLog(tmp / "audit"), approval_port=approval)


def main() -> None:
    rs = load_ruleset()
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset ver : {rs.version}")
    print(f"blacklist   : {list(rs.blacklist)}")

    print("\n[A] Phase 1 대상 두 명령 (확대 후 risky=True 여야 한다)")
    for c in P1_TARGETS:
        print(_line(c))

    print("\n[B] Phase 2·3 대상 (이 카드에서는 안 건드린다 — 열린 채로 남아야 한다)")
    for c in P2P3_TARGETS:
        print(_line(c))

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

    print("\n[E] 흐름 단위 음성 대조군 (AC-CG-003: 승인 요청 0건, cleared=True)")
    approval = _CountingApproval()
    gate = _gate(approval)
    decision = gate.screen(list(NEGATIVE_CONTROLS[:5]))
    print(f"  bundle           : {list(NEGATIVE_CONTROLS[:5])}")
    print(f"  approval requests: {len(approval.requests)}")
    print(f"  cleared          : {decision.cleared}  status={decision.status!r}")

    print("\n[F] 봉합 + 확대 동시 투입 (AC-CG-004: 요청 정확히 1건, 사유 병기)")
    sealed_bundle = [
        "Store Group 3",
        "Store Timecode 9",
        "Fixture 20 ; Attribute 'Pan' At 12",
    ]
    approval2 = _CountingApproval()
    gate2 = _gate(approval2)
    gate2.screen(
        sealed_bundle,
        risk=BatchRisk(reason="SEAL-REASON", kind="songcue"),
    )
    print(f"  approval requests: {len(approval2.requests)}")
    if approval2.requests:
        req = approval2.requests[0]
        print(f"  items in request : {len(req.items)}")
        for item in req.items:
            print(f"    {item.command!r:52} | {item.risk_reasons}")


if __name__ == "__main__":
    main()
