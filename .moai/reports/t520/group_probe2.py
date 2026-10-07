# ruff: noqa: E501 — 한국어 머리말·안내 문구라 줄 길이 규칙을 끈다
"""t520 프로브 G2 — 그룹 선택(255) + 뒤 점 선택(256), 시퀀스를 나눠 트래킹이 섞이지 않게.

  Seq 255 큐1 'Group Five'     `Group 5 ; Attribute 'Dimmer' At 100`                — 기존 그룹 5(SIDE-L)
  Seq 256 큐1 'Trailing Dot'   `Fixture 301 Thru 302. ; Attribute 'Dimmer' At 100`  — 공식 문서 「Fixture 301 Thru 303.」= 본체 + 서브픽스처 전부
이름 'GROUP PROBE - GROUP 5 SIDE-L' · 'GROUP PROBE - TRAILING DOT 301-302'. 쓰는 번호 255·256 만. 쇼 저장 없음.

리드가 재생 직전마다 한 줄씩 알리라고 해서 실행을 단계로 나눈다(같은 전부-거절 폴더의 문면으로 승인):
  --phase store : 사전 판독(255·256 빔) → 저장 2묶음
  --phase p255  : 사전 판독(255 이름) → `Goto Cue 1 Sequence 255` 15초 → `Off Sequence 255`
  --phase p256  : 사전 판독(256 이름) → `Goto Cue 1 Sequence 256` 15초 → `Off Sequence 256`
  --phase all   : 전부(리허설·전부-거절용)
송신 대조는 단계별 감사 로그를 audit-1/2/3 으로 모아 t512 비교기에 넣는다.

실행: uv run python .moai/reports/t520/group_probe2.py <출력폴더> --phase <단계> [--rehearse | --approve <전부-거절 폴더>]
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
    reason="t520 프로브 G2 — 빈 번호 255·256 생성·재생(그룹·뒤 점 선택)", kind="t520_group_probe2"
)
POOL = "ShowData/DataPools/Default/Sequences"
HOLD = 15.0
#: (시퀀스, 큐 이름, 값 줄, 시퀀스 이름)
PROBES = [
    (255, "Group Five", "Group 5 ; Attribute 'Dimmer' At 100", "GROUP PROBE - GROUP 5 SIDE-L"),
    (
        256,
        "Trailing Dot",
        "Fixture 301 Thru 302. ; Attribute 'Dimmer' At 100",
        "GROUP PROBE - TRAILING DOT 301-302",
    ),
]


def bundles(phase: str) -> list[tuple[str, list[str], float]]:
    store = [
        (
            f"store_{seq}",
            [
                "ChangeDestination Root",
                "ClearAll",
                line,
                f"Store Sequence {seq} Cue 1 '{cue}'",
                "ClearAll",
                f"Set Sequence {seq} Property 'Name' '{nm}'",
            ],
            0.0,
        )
        for seq, cue, line, nm in PROBES
    ]
    play = {
        seq: [
            (f"on_{seq}", [f"Goto Cue 1 Sequence {seq}"], HOLD),
            (f"off_{seq}", [f"Off Sequence {seq}"], 0.0),
        ]
        for seq, *_ in PROBES
    }
    return {
        "store": store,
        "p255": play[255],
        "p256": play[256],
        "all": store + play[255] + play[256],
    }[phase]


class FakeConsole:
    """번호 존재·이름만 흉내 낸다. 선택 문법·점등의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self, exists: set[int]) -> None:
        self.sent: list[str] = []
        self.exists = set(exists)

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if command.startswith("Store Sequence"):
            self.exists.add(int(command.split()[2]))
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path.startswith(POOL + "/") and int(path.rsplit("/", 1)[1]) not in self.exists:
            raise StateQueryError(f"path segment not found (in {path})")
        return dict(ok=True, path=path, node=dict(childCount=0), children=[], fake=True)

    def query_properties(self, path: str, names) -> dict:
        nm = {f"{POOL}/{s}": n for s, _, _, n in PROBES}.get(path, "fake")
        return dict(
            ok=True,
            path=path,
            reads=[dict(n=n, ok=True, v=nm if n == "NAME" else "fake") for n in names],
            fake=True,
        )

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


def _name(payload: dict | None):
    for read in (payload or {}).get("reads") or ():
        if read.get("n") == "NAME" and read.get("ok"):
            return read.get("v")
    return None


def run(gate: SafetyGate, out: Path, phase: str, *, deny_all: bool, pace: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(phase=phase, bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    if phase in ("store", "all"):
        taken = [s for s, *_ in PROBES if probe.read_state("pre_slot", f"{POOL}/{s}") is not None]
        if taken:
            return stop(f"stopped: slots not empty {taken}")
    else:
        seq = int(phase[1:])
        want = next(n for s, _, _, n in PROBES if s == seq)
        got = _name(probe.read_props("pre_name", f"{POOL}/{seq}", ["NAME"]))
        result["pre_name"] = got
        if got != want:
            return stop(f"stopped: name {got!r} != {want!r}")
    for label, cmds, wait in bundles(phase):
        ok = probe.fire(label, cmds)
        result["bundles"][label] = ok
        if pace:
            time.sleep(wait)
    if not deny_all:
        result["exec"] = [
            dict(command=r["command"], ok=r.get("ok"), detail=r.get("detail"))
            for r in probe.log
            if r.get("kind") == "exec"
        ]
    return stop("deny-all: approval texts recorded" if deny_all else f"ran phase {phase}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--phase", choices=("all", "store", "p255", "p256"), required=True)
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole(set() if args.phase in ("all", "store") else {255, 256})
        approval = RecordingApproval([cmds for _, cmds, _ in bundles("all")])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, args.phase, deny_all=False, pace=False)
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
            result = run(
                stack.gate, out, args.phase, deny_all=pinned is None, pace=pinned is not None
            )
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()
    result["approved"] = sum(1 for r in approval.requests if r["approved"])
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {k: result.get(k) for k in ("verdict", "bundles", "pre_name", "exec", "approved")},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
