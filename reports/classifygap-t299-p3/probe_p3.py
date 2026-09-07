"""t299 Phase 3 프로브 — 확대 전/후를 같은 명령으로 잰다.

`server/safety/` 를 고치지 않는다. 배치된 `blacklist.yaml` 을 그대로 읽으므로
확대 전에 한 번, 확대 후에 한 번 돌리면 두 회차가 바로 대조가 된다.

Phase 2(`probe_p2.py`)와 다른 점은 대상 구분이다. 이 회차가 넣는 것은
`Store Cue` 하나이고, 그것이 **마지막 구멍**이다 — 확대 뒤에는 네 `Store` 형태가
전부 걸려야 하고, 프로그래머 값 둘(`Fixture 1 At 50` · `Group 4`)은 그대로
안 걸려야 한다.

실행:  uv run python reports/classifygap-t299-p3/probe_p3.py
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

#: Phase 3 가 닫는 명령. 이 회차의 유일한 대상이고, SPEC 의 마지막 구멍이다.
P3_TARGET = "Store Cue 1"

#: Phase 1·2 가 이미 닫은 셋. 그대로 걸려 있어야 한다(회귀 확인).
ALREADY_CLOSED = (
    "Store Group 3",
    "Store Timecode 9",
    "Store Sequence 210 Cue 3 /Merge",
)

#: 배차서가 못 박은 음성 대조군 둘. 프로그래머 값·선택 명령이라 확대 뒤에도
#: 안 걸려야 한다. `Group 4` 는 동사가 `Group` 이라 `Store` 항목에 안 닿고,
#: `Fixture 1 At 50` 은 패치 쓰기가 아니라 프로그래머 값이다.
MUST_STAY_SAFE = ("Fixture 1 At 50", "Group 4")

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
    tmp = Path(tempfile.mkdtemp(prefix="t299p3-"))
    return SafetyGate(console=_FakeConsole(), audit=AuditLog(tmp / "audit"), approval_port=approval)


def main() -> None:
    rs = load_ruleset()
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset ver : {rs.version}")
    print(f"blacklist   : {list(rs.blacklist)}")

    print("\n[A] 배차서가 지정한 여섯 명령 — 이 순서 그대로")
    for c in (*ALREADY_CLOSED, P3_TARGET, *MUST_STAY_SAFE):
        print(_line(c))

    print("\n[A-검산] 이 회차가 지켜야 하는 성질")
    p3 = _classify(P3_TARGET)
    print(f"  Phase 3 대상이 걸린다        : {p3.risky} (matched={p3.matched_entry!r})")
    for c in ALREADY_CLOSED:
        f = _classify(c)
        print(f"  Phase 1·2 회귀 없음          : {c!r} risky={f.risky} matched={f.matched_entry!r}")
    for c in MUST_STAY_SAFE:
        f = _classify(c)
        print(f"  프로그래머/선택은 안 걸린다  : {c!r} risky={f.risky} matched={f.matched_entry!r}")

    print("\n[B] AC-CG-001 — 네 명령 전부 risky=True 이고 matched_entry is not None")
    four = (*ALREADY_CLOSED, P3_TARGET)
    ok = []
    for c in four:
        f = _classify(c)
        good = f.risky and f.matched_entry is not None
        ok.append(good)
        print(f"  {c!r:52} -> {'PASS' if good else 'FAIL'} (matched={f.matched_entry!r})")
    print(f"  => AC-CG-001: {sum(ok)}/4")

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

    print("\n[D-2] 배차서가 못 박은 두 문장도 같이 (must-pass 음성 대조군)")
    bad2 = []
    for c in MUST_STAY_SAFE:
        print(_line(c))
        f = _classify(c)
        if f.risky or f.matched_entry is not None:
            bad2.append(c)
    print(f"  => risky 로 잘못 판정된 문장: {len(bad2)} {bad2}")

    print("\n[E] 흐름 단위 음성 대조군 (AC-CG-003: 승인 요청 0건, cleared=True)")
    approval = _CountingApproval()
    gate = _gate(approval)
    bundle = [*NEGATIVE_CONTROLS[:5], *MUST_STAY_SAFE]
    decision = gate.screen(bundle)
    print(f"  bundle           : {bundle}")
    print(f"  approval requests: {len(approval.requests)}")
    print(f"  cleared          : {decision.cleared}  status={decision.status!r}")

    # AC-CG-003 의 번들은 [E] 다. 아래는 **AC 가 아니라** 아홉 문장을 흐름으로
    # 통과시킨 참고 측정이다. 아홉 문장에는 호출 동사(`Go+ Sequence 5` ·
    # `Off Fixture 11`, category='invoking')가 둘 들어 있고, 그 둘은 확대와
    # 무관하게 expand-or-hold 규칙(REQ-MVP-026)으로 보류된다. 그래서 이 줄의
    # 카드 수는 0 이 아니며, 그것이 정상이다 — 확대 전/후 값이 **같아야** 한다는
    # 것이 이 측정의 요점이다(확대가 이 자리를 움직이면 안 된다).
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
        P3_TARGET,
        "Store Sequence 210 Cue 3 /Merge",
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
