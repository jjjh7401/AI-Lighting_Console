# ruff: noqa: E501 — 근거(파일·줄)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 프로브 v4 — v3 감독 관찰로 좁힌 세 질문 + 다중 디머 확인.

v3 감독 관찰(원문, 리드 경유 2026-10-06): 「L0~L2 잘됨. L3 깜박였지만 느리지 않음. L4,L5 틸트는 안되고 팬이 되었으나 수직이라 표시가 나지 않음」.

A. 어느 축이 움직이나 (무빙 501~508, 기준 위치를 수직이 아닌 곳으로)
  234 A0 기준만: Dimmer 70 + `Attribute 'Tilt' At 45` (정적 대조. 프리셋 2.24 를 쓰지 않는다)
  235 A1 Pan: 기준 + 룰북 31:66-73 모양 그대로 `Attribute 'Pan' At Relative 30` → Phase 0 Thru 360 → Speed 112
  236 A2 Tilt: 같은 모양을 Tilt 로
  237 A3 Tilt 2단계: `Attribute 'Tilt' At Relative -30` → `Step 2` → `At Relative 30` → Phase → Speed 112
B. 박 주기를 바꾸는 수단 (무빙 501~508, v3 L1 에서 켜진 Dimmer 0↔100 2단계 모양)
  재생에서 먼저 229(v3 L1, Speed 112)를 다시 켜 기준으로 보여 준다 — Goto/Off 만
  238 B1 `At Speed 56` (절반)        239 B2 `At Speed 224` (두 배)
  240 B3 SpeedMaster 15 + `At Measure 4`   241 B4 SpeedMaster 15 + `At Measure 1`
  근거: 공식 문서 Phasers 「The optional Measure layer defines the number of beats in the repeating phaser loop」.
  가설(안 잰 것): 2단계 페이저의 기본 루프가 이미 2박이라 v3 L3 의 Measure 2 가 아무것도 바꾸지 않았다.
  제외: 다른 스피드 마스터에 56.175 BPM — 이미 있는 전역 마스터 값을 바꾸는 쓰기라 「새 번호만」 밖이다.
        Speed Scale(마스터 배수)은 문서에 있으나 명령줄 문법이 문서에 없다.
D. Aura XB 다중 디머 (BACK 201). 실기 판독: Fixture 201 아래 SubFixture 1개(`[Instance2#2]`),
  채널 Aura_Dimmer · Main Module_Dimmer. 문법 근거: 공식 문서 Fixture 키워드 `Fixture 10.5`(서브픽스처).
  242 D1 `Fixture 201 ; Attribute 'Dimmer' At 30` (v2 에서 어두웠던 모양, 대조)
  243 D2 `Fixture 201.1 ; Attribute 'Dimmer' At 30`
  244 D3 두 줄 모두(201 과 201.1 에 Dimmer 30)
  D 묶음은 거절돼도 멈추지 않는다(거절 자체가 답이다). 맨 끝에 둔다.

각 단계 8초 켜고 끈 뒤 2초. 이름 'RHYTHM PROBE v4 - <단계>'. 쓰는 번호 234~244 만. 쇼 저장 없음.
실행: uv run python .moai/reports/t516/rhythm_probe_v4.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
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
sys.path.insert(0, ".moai/reports/t516")
import tc_probe  # noqa: E402
from rhythm_probe_v3 import GAP, HOLD, POOL, FakeConsole  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(reason="t516 v4 — 빈 번호 234~244 생성·재생", kind="t516_probe_v4")
MOVERS = "Fixture " + " + ".join(str(i) for i in range(501, 509))
REF_SEQ = 229  # v3 L1 — Speed 112 기준(이미 있음, 재생만)


def name(item: str) -> str:
    return f"'RHYTHM PROBE v4 - {item}'"


BASE = [f"{MOVERS} ; Attribute 'Dimmer' At 70", f"{MOVERS} ; Attribute 'Tilt' At 45"]


def axis_wave(attr: str) -> list[str]:
    return [
        *BASE,
        f"{MOVERS} ; Attribute '{attr}' At Relative 30",
        f"Attribute '{attr}' At Phase 0 Thru 360",
        f"Attribute '{attr}' At Speed 112",
    ]


def pulse(*timing: str) -> list[str]:
    return [
        f"{MOVERS} ; Attribute 'Dimmer' At 0",
        "Step 2",
        "Attribute 'Dimmer' At 100",
        "Attribute 'Dimmer' At Phase 0",
        *(f"Attribute 'Dimmer' At {t}" for t in timing),
    ]


#: (시퀀스, 단계 이름, 값 줄, 감독 안내, 거절돼도 계속?)
LEVELS: list[tuple[int, str, list[str], str, bool]] = [
    (
        234,
        "A0 BASE TILT 45",
        BASE,
        "A0 — 무빙 501~508 이 70% 로 켜지고 수직이 아닌 기울어진 자리에 섬(움직임 없음)",
        False,
    ),
    (
        235,
        "A1 PAN RELATIVE 30",
        axis_wave("Pan"),
        "A1 — 기울어진 자리에서 좌우(Pan)로 흔들리는가",
        False,
    ),
    (
        236,
        "A2 TILT RELATIVE 30",
        axis_wave("Tilt"),
        "A2 — 같은 자리에서 위아래(Tilt)로 흔들리는가",
        False,
    ),
    (
        237,
        "A3 TILT 2 STEPS",
        [
            *BASE,
            f"{MOVERS} ; Attribute 'Tilt' At Relative -30",
            "Step 2",
            "Attribute 'Tilt' At Relative 30",
            "Attribute 'Tilt' At Phase 0 Thru 360",
            "Attribute 'Tilt' At Speed 112",
        ],
        "A3 — 2단계로 만든 Tilt — 위아래로 흔들리는가",
        False,
    ),
    (
        238,
        "B1 PULSE SPEED 56",
        pulse("Speed 56"),
        "B1 — 깜빡임이 기준(229)의 절반 빠르기인가",
        False,
    ),
    (239, "B2 PULSE SPEED 224", pulse("Speed 224"), "B2 — 기준의 두 배 빠르기인가", False),
    (
        240,
        "B3 PULSE SPEEDMASTER MEASURE 4",
        pulse("Measure 4", "SpeedMaster 15"),
        "B3 — 스피드 마스터 + Measure 4 — 기준보다 느린가",
        False,
    ),
    (
        241,
        "B4 PULSE SPEEDMASTER MEASURE 1",
        pulse("Measure 1", "SpeedMaster 15"),
        "B4 — 스피드 마스터 + Measure 1 — 기준보다 빠른가",
        False,
    ),
    (
        242,
        "D1 AURA FIXTURE DIMMER",
        ["Fixture 201 ; Attribute 'Dimmer' At 30"],
        "D1 — BACK 201 한 대가 켜지는가(대조, v2 에선 어두웠음)",
        True,
    ),
    (
        243,
        "D2 AURA SUBFIXTURE DIMMER",
        ["Fixture 201.1 ; Attribute 'Dimmer' At 30"],
        "D2 — 201.1(서브픽스처)만 30 — 켜지는가",
        True,
    ),
    (
        244,
        "D3 AURA BOTH DIMMERS",
        ["Fixture 201 ; Attribute 'Dimmer' At 30", "Fixture 201.1 ; Attribute 'Dimmer' At 30"],
        "D3 — 201 과 201.1 둘 다 30 — 켜지는가",
        True,
    ),
]


def bundles() -> list[tuple[str, list[str], float, str, bool]]:
    """(묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내, 거절돼도 계속?) — 쓰기 먼저, 재생은 단계 순서대로."""
    out: list[tuple[str, list[str], float, str, bool]] = []
    for seq, label, values, _, soft in LEVELS:
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
                soft,
            )
        )
    for seq, _, _, say, soft in LEVELS:
        if seq == 238:
            out.append(
                (
                    f"on_{REF_SEQ}",
                    [f"Goto Cue 1 Sequence {REF_SEQ}"],
                    HOLD,
                    "B 기준 — v3 L1(Speed 112) 깜빡임",
                    True,
                )
            )
            out.append((f"off_{REF_SEQ}", [f"Off Sequence {REF_SEQ}"], GAP, "", True))
        out.append((f"on_{seq}", [f"Goto Cue 1 Sequence {seq}"], HOLD, say, soft))
        out.append((f"off_{seq}", [f"Off Sequence {seq}"], GAP, "", soft))
    return out


def run(gate: SafetyGate, out: Path, *, deny_all: bool, pace: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(bundles={}, marks=[])

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    taken = [s for s, *_ in LEVELS if probe.read_state("pre_slot", f"{POOL}/{s}") is not None]
    if taken:
        return stop(f"stopped: slots not empty {taken}")
    t0 = None
    for label, cmds, wait, say, soft in bundles():
        if t0 is None and label.startswith("on_"):
            t0 = time.monotonic()
        if say:
            probe.note("watch", say=say)
        ok = probe.fire(label, cmds)
        result["bundles"][label] = ok
        if t0 is not None:
            result["marks"].append(dict(label=label, t=round(time.monotonic() - t0, 2)))
        if not deny_all and label.startswith("store_") and not ok and not soft:
            return stop(f"{label} not executed")
        if pace:
            time.sleep(wait)
    if not deny_all:
        for seq, *_ in LEVELS:
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
        console.exists.add(f"{POOL}/{REF_SEQ}")
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
