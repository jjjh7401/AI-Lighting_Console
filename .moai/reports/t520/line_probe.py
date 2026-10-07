# ruff: noqa: E501 — 한국어 머리말·안내 문구라 줄 길이 규칙을 끈다
"""t520 프로브 A — `Fixture` 목록 줄 꼴 셋을 가른다(Seq 252 큐 3개).

까닭: m2a 쓰기 1회에서 `Fixture 201 + 201.1 + … ;`(24·40개, 점 번호 포함) 4줄이 `Illegal object` 로 거절됐다.
실기 기록 전수(list_shapes.py)로는 「목록 안 점 번호」와 「목록 21개 이상」이 겹쳐 못 가른다.

큐 순서는 트래킹 오염을 피하려고 정했다 — 사람 눈으로 볼 「본체만」을 큐 1(앞 큐 없음)에 둔다:
  큐 1 'Main Only'      `Fixture 301 + 302 ; Attribute 'Dimmer' At 100` — 본체 선택만으로 SIDE 가 켜지나(감독 눈)
  큐 2 'Sub In List'    `Fixture 301.1 + 302.1 ; Attribute 'Dimmer' At 100` — 점 번호 목록이 받아들여지나(기계)
  큐 3 'Long List 24'   `Fixture 401 + … + 430 + 111 + 112 + 113 + 114 ; Attribute 'Dimmer' At 50` — 점 없이 24개(기계)
줄마다 OK / Illegal object 가 기계 판정이다. 재생은 큐마다 8초 켜고 끈 뒤 2초. 큐 2·3 은 트래킹으로 앞 큐 값이 섞여
눈 판정에 쓰지 않는다. 이름 'LINE SHAPE PROBE - <꼴>'. 쓰는 번호 252 만. 쇼 저장 없음.
사전 판독: 252 가 비어야 보낸다. B 에서 쓸 253·254·TC23 도 비었는지 같이 읽는다(읽기만).

실행: uv run python .moai/reports/t520/line_probe.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
import tc_probe  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 프로브 A — 빈 번호 252 생성·재생(줄 꼴 셋)", kind="t520_line_probe"
)
SEQ_NO = 252
POOL = "ShowData/DataPools/Default"
SEQ_PATH = f"{POOL}/Sequences/{SEQ_NO}"
B_SLOTS = [f"{POOL}/Sequences/253", f"{POOL}/Sequences/254", f"{POOL}/Timecodes/23"]
HOLD, GAP = 8.0, 2.0
LONG24 = [*range(401, 411), *range(421, 431), 111, 112, 113, 114]

#: (큐, 큐 이름, 값 줄, 감독 안내)
CUES: list[tuple[int, str, str, str]] = [
    (
        1,
        "Main Only",
        "Fixture 301 + 302 ; Attribute 'Dimmer' At 100",
        "큐 1 — 본체 301·302 만 Dimmer 100. SIDE-L 두 대가 켜지는가",
    ),
    (
        2,
        "Sub In List",
        "Fixture 301.1 + 302.1 ; Attribute 'Dimmer' At 100",
        "큐 2 — 점 번호 목록(기계 판정, 눈 판정 안 함)",
    ),
    (
        3,
        "Long List 24",
        "Fixture " + " + ".join(str(i) for i in LONG24) + " ; Attribute 'Dimmer' At 50",
        "큐 3 — 점 없이 24개(기계 판정, 바닥 워시 20대 + FOH 4대가 50%)",
    ),
]


def bundles() -> list[tuple[str, list[str], float, str]]:
    out: list[tuple[str, list[str], float, str]] = []
    for cue, label, line, _ in CUES:
        cmds = [
            "ChangeDestination Root",
            "ClearAll",
            line,
            f"Store Sequence {SEQ_NO} Cue {cue} '{label}'",
            "ClearAll",
        ]
        if cue == 1:
            cmds.append(f"Set Sequence {SEQ_NO} Property 'Name' 'LINE SHAPE PROBE - MAIN SUB LONG'")
        out.append((f"store_{cue}", cmds, 0.0, ""))
    for cue, _, _, say in CUES:
        out.append((f"on_{cue}", [f"Goto Cue {cue} Sequence {SEQ_NO}"], HOLD, say))
        out.append((f"off_{cue}", [f"Off Sequence {SEQ_NO}"], GAP, ""))
    return out


class FakeConsole:
    """번호 존재만 흉내 낸다. 줄 꼴 판정의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.exists = False

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if command.startswith(f"Store Sequence {SEQ_NO}"):
            self.exists = True
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        if (path == SEQ_PATH and not self.exists) or path in B_SLOTS:
            raise StateQueryError(f"path segment not found (in {path})")
        return dict(ok=True, path=path, node=dict(childCount=0), children=[], fake=True)

    def query_properties(self, path: str, names) -> dict:
        return dict(
            ok=True, path=path, reads=[dict(n=n, ok=True, v="fake") for n in names], fake=True
        )

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


def run(gate: SafetyGate, out: Path, *, deny_all: bool, pace: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(bundles={}, line_results={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    result["b_slots_taken"] = [p for p in B_SLOTS if probe.read_state("pre_b_slot", p) is not None]
    if probe.read_state("pre_slot", SEQ_PATH) is not None:
        return stop(f"stopped: {SEQ_PATH} not empty")
    for label, cmds, wait, say in bundles():
        if say:
            probe.note("watch", say=say)
        result["bundles"][label] = probe.fire(label, cmds)
        if pace:
            time.sleep(wait)
    if not deny_all:
        for row in probe.log:
            if row.get("kind") == "exec" and str(row.get("command", "")).startswith("Fixture "):
                result["line_results"][row["command"][:60]] = dict(
                    ok=row.get("ok"), detail=row.get("detail")
                )
        probe.read_state("post_seq", SEQ_PATH)
        probe.read_props("post_name", SEQ_PATH, ["NAME"])
    return stop(
        "deny-all: approval texts recorded" if deny_all else "ran — line results + director watch"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([b[1] for b in bundles()])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, deny_all=False, pace=False)
    else:
        from server.safety.bootstrap import build_console_stack
        from server.tools.probe_preflight import preflight

        pinned = None
        if args.approve:
            requests = json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
            pinned = [r["commands"] for r in requests]
        approval = RecordingApproval(pinned)
        stack = build_console_stack(
            send_host="127.0.0.1",
            send_port=8000,
            receive_host="127.0.0.1",
            receive_port=LISTEN_PORT,
            approval_port=approval,
            audit_dir=out / "audit",
            timeouts=LinkTimeouts(state_query_seconds=6.0),
            attempt_session_backup=False,
        )
        stack.backup._backup_action = lambda: skipped.append("SaveShow skipped (supervisor)")
        try:
            health = preflight(
                stack.gate, receive_host="127.0.0.1", receive_port=LISTEN_PORT, console_port=8000
            )
            if health.get("verdict") != "responder_ok":
                print(json.dumps(dict(preflight=health), ensure_ascii=False, indent=2))
                return 1
            result = run(stack.gate, out, deny_all=pinned is None, pace=pinned is not None)
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()
    result["approval_requests"] = len(approval.requests)
    result["approved"] = sum(1 for r in approval.requests if r["approved"])
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in ("verdict", "bundles", "line_results", "b_slots_taken", "approved")
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
