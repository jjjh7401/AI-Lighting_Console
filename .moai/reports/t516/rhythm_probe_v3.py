# ruff: noqa: E501 — 근거(파일·줄)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 프로브 v3 — 사다리: 어느 단계에서 끊기는지로 「페이저가 아예 안 도는가」를 가른다.

v2 감독 관찰(원문): 「내가 본 건 227만 불이 켜졌다는 거야. 하지만 8대 조명장비만 불이 들어오고 어떤 변화도 없었어」.
리드 가설: 우리가 큐에 저장한 페이저가 돌지 않는다. 대상은 보이는 무빙 MOVER-U 501~508(Robin MegaPointe,
패치 판독상 Dimmer 1개 · Shutter 기본값 open — `diag7_patch_table.txt`, `diag11.txt`, `diag12.txt`).

  L0(228) Dimmer 100 정적 — 켜지면 출력·Goto 정상
  L1(229) Dimmer 0↔100 2단계 페이저, `At Speed 112` (스피드 마스터 없이)
  L2(230) L1 과 같되 속도 줄만 `At SpeedMaster 15`
  L3(231) L2 + `At Measure 2` (줄 순서 Measure → SpeedMaster, server/fx/instantiate.py `_timing_lines`)
  L4(232) Tilt 움직임 — position_fx `wave` 줄 그대로: `Fixture … ; At Preset 2.24`(Center) →
          `Attribute 'Tilt' At Relative 12` → `Attribute 'Tilt' At Phase 0 Thru 360` → `Attribute 'Tilt' At Speed 112`.
          그 앞에 `Fixture … ; Attribute 'Dimmer' At 70` 한 줄(보이게)
  L5(233) L4 와 같되 속도 줄만 `At SpeedMaster 15`
페이저 줄 모양은 앱 FXGEN(실기 관측 V1~V7)과 같다: 단계 값 → `Step 2`(단독 줄) → 단계 값 → `At Phase` → 속도 줄.
선택 줄은 v2 에서 켜진 모양(`Fixture 목록 ; Attribute …` 한 줄).

각 단계는 따로 시퀀스(트래킹 섞임 없음), 재생은 8초 켜고 끈 뒤 2초. 이름 'RHYTHM PROBE v3 - <단계>'.
쓰는 번호 228~233 만. 마스터 BPM 은 건드리지 않는다(15 는 이미 112 표시). 쇼 저장 없음.
실행: uv run python .moai/reports/t516/rhythm_probe_v3.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
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

tc_probe.RISK = BatchRisk(reason="t516 v3 사다리 — 빈 번호 228~233 생성·재생", kind="t516_probe_v3")
MOVERS_U = list(range(501, 509))
SEL = "Fixture " + " + ".join(str(i) for i in MOVERS_U)
SM = "SpeedMaster 15"
POOL = "ShowData/DataPools/Default/Sequences"
HOLD, GAP = 8.0, 2.0


def name(item: str) -> str:
    return f"'RHYTHM PROBE v3 - {item}'"


def pulse(speed_line: str, *extra: str) -> list[str]:
    return [
        f"{SEL} ; Attribute 'Dimmer' At 0",
        "Step 2",
        "Attribute 'Dimmer' At 100",
        "Attribute 'Dimmer' At Phase 0",
        *extra,
        f"Attribute 'Dimmer' At {speed_line}",
    ]


def tilt_wave(speed_line: str) -> list[str]:
    return [
        f"{SEL} ; Attribute 'Dimmer' At 70",
        f"{SEL} ; At Preset 2.24",
        "Attribute 'Tilt' At Relative 12",
        "Attribute 'Tilt' At Phase 0 Thru 360",
        f"Attribute 'Tilt' At {speed_line}",
    ]


#: (시퀀스, 단계 이름, 값 줄)
LEVELS: list[tuple[int, str, list[str]]] = [
    (228, "L0 STATIC 100", [f"{SEL} ; Attribute 'Dimmer' At 100"]),
    (229, "L1 PULSE SPEED 112", pulse("Speed 112")),
    (230, "L2 PULSE SPEEDMASTER", pulse(SM)),
    (231, "L3 PULSE SPEEDMASTER MEASURE 2", pulse(SM, "Attribute 'Dimmer' At Measure 2")),
    (232, "L4 TILT WAVE SPEED 112", tilt_wave("Speed 112")),
    (233, "L5 TILT WAVE SPEEDMASTER", tilt_wave(SM)),
]
SAY = {
    228: "L0 — 무빙 501~508 이 100% 로 켜지는가(대조)",
    229: "L1 — 켜짐/꺼짐이 1박(약 0.53초)마다 깜빡이는가 (At Speed 112)",
    230: "L2 — 같은 깜빡임, 속도만 스피드 마스터 15",
    231: "L3 — L2 와 같되 2박에 한 번(느리게)",
    232: "L4 — 70% 로 켜진 채 Tilt 가 위아래로 파도처럼 움직이는가 (At Speed 112)",
    233: "L5 — L4 와 같은 움직임, 속도만 스피드 마스터 15",
}


def bundles() -> list[tuple[str, list[str], float, str]]:
    """(묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내) — 쓰기 먼저, 재생은 단계 순서대로."""
    out: list[tuple[str, list[str], float, str]] = []
    for seq, label, values in LEVELS:
        out.append(
            (
                f"store_{seq}",
                [
                    "ChangeDestination Root",
                    "ClearAll",
                    *values,
                    f"Store Sequence {seq} Cue 1 '{label.title()}'",
                    "ClearAll",
                    f"Set Sequence {seq} Property 'Name' {name(label)}",
                ],
                0.0,
                "",
            )
        )
    for seq, _, _ in LEVELS:
        out.append((f"on_{seq}", [f"Goto Cue 1 Sequence {seq}"], HOLD, SAY[seq]))
        out.append((f"off_{seq}", [f"Off Sequence {seq}"], GAP, ""))
    return out


class FakeConsole:
    """번호 존재만 흉내 내는 얕은 모형(리허설 전용). 콘솔 의미론의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.exists: set[str] = set()

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        if command.startswith("Store Sequence"):
            self.exists.add(f"{POOL}/{command.split()[2]}")
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path.startswith(POOL + "/") and path not in self.exists:
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
    result: dict = dict(bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    taken = [s for s, _, _ in LEVELS if probe.read_state("pre_slot", f"{POOL}/{s}") is not None]
    if taken:
        return stop(f"stopped: slots not empty {taken}")
    for label, cmds, wait, say in bundles():
        if say:
            probe.note("watch", say=say)
        ok = probe.fire(label, cmds)
        result["bundles"][label] = ok
        if not deny_all and label.startswith("store_") and not ok:
            return stop(f"{label} not executed")
        if pace:
            time.sleep(wait)
    if not deny_all:
        for seq, _, _ in LEVELS:
            probe.read_props(f"post_part_{seq}", f"{POOL}/{seq}/3/1", ["NAME", "MEMORYFOOTPRINT"])
    return stop(
        "deny-all: approval texts recorded" if deny_all else "ran — judge by director watch"
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
        approval = RecordingApproval([cmds for _, cmds, _, _ in bundles()])
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
        result["fake_sent"] = console.sent
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
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({k: result.get(k) for k in ("verdict", "bundles")}, ensure_ascii=False)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
