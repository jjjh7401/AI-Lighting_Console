# ruff: noqa: E501 — 근거(판독값·인용)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 프로브 v5 — 남은 미해결 둘만 가르는 최소 시험.

v4 감독 관찰(원문): 「235 좌우로 흔들리는 걸 확인 못했어. 수직으로 있어서 좌우 흔들림이 안 보인 것일 수도 있어.
틸트가 조금 되어있으면 확실하게 보일거야. 그리고 242~244까지 조명 켜진거 없어.」 · 「나머지는 모두 확인했어」.

① 기준 Tilt 45 가 페이저 큐에서 빠진다(A1/A2 큐 3216B < A0 3432B — 잰 것. 왜 빠지는지는 안 잰 것).
   공식 문서(Programmer Layers)는 absolute·relative 층이 따로 있고 relative 가 absolute 에 더해진다고 적는다 —
   「relative 가 absolute 를 지운다」는 문서 근거가 없다. 그래서 세 갈래를 눈으로 가른다(무빙 501~508):
   245 E0 Dimmer 70 + Tilt 45 정적(A0 재현 — 이번엔 「기울었나」를 묻는다)
   246 E1 Pan 2단계 **절대값** 페이저: 단계마다 Pan -30/30 과 Tilt 45 를 같이 넣는다(Tilt 가 단계 값 안에 있다)
   247 E2 Pan 2단계 **상대값** 페이저만 — 재생 때 245 를 켜 둔 채 위에 겹친다(기준은 다른 시퀀스)
   속도는 v4 에서 확인된 `At Speed 56`(느리게, 좌우가 잘 보이게).
② Aura XB 무점등. 실기 판독(v5_reads2.txt): Aura RGB 기본값 `<FFFFFF>`(최대) — 「색 0 이라 검정」 가설은 RGB 로는 맞지 않는다.
   COLORMIXER 기본값 `<000000>`, Dimmer 둘 다 `<000000>`. 앱 Seq 219 는 BACK 에 Dimmer 와 함께
   `ColorRGB_R/G/B` 를 한 줄로 준다(t513 approve 파일 grep). BACK 이 219 에서 켜졌다는 기록은 없다.
   248 F1 Dimmer 100(201·201.1·301·301.1 각각) — v4 D3 은 30 이었다
   249 F2 F1 + ColorRGB_R/G/B 100(219 와 같은 꼴)
   SIDE-L 301(같은 Aura XB, 높이 1.2)을 같이 넣어 「BACK 자리 문제인가, 기종 문제인가」를 한 번에 본다.

각 단계 8초 켜고 끈 뒤 2초. 이름 'RHYTHM PROBE v5 - <단계>'. 쓰는 번호 245~249 만. 쇼 저장 없음.
실행: uv run python .moai/reports/t516/rhythm_probe_v5.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
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

tc_probe.RISK = BatchRisk(reason="t516 v5 — 빈 번호 245~249 생성·재생", kind="t516_probe_v5")
MOVERS = "Fixture " + " + ".join(str(i) for i in range(501, 509))
AURA = ["201", "201.1", "301", "301.1"]
RGB = (
    "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 100"
)


def name(item: str) -> str:
    return f"'RHYTHM PROBE v5 - {item}'"


#: (시퀀스, 단계 이름, 값 줄, 거절돼도 계속?)
LEVELS: list[tuple[int, str, list[str], bool]] = [
    (
        245,
        "E0 BASE TILT 45",
        [f"{MOVERS} ; Attribute 'Dimmer' At 70", f"{MOVERS} ; Attribute 'Tilt' At 45"],
        False,
    ),
    (
        246,
        "E1 PAN ABSOLUTE STEPS TILT 45",
        [
            # 디머·Tilt 를 두 단계에 똑같이 넣는다 — 한 단계에만 있으면 그 속성도 단계마다 바뀐다
            f"{MOVERS} ; Attribute 'Dimmer' At 70 ; Attribute 'Pan' At -30 ; Attribute 'Tilt' At 45",
            "Step 2",
            "Attribute 'Dimmer' At 70 ; Attribute 'Pan' At 30 ; Attribute 'Tilt' At 45",
            "Attribute 'Pan' At Phase 0",
            "Attribute 'Pan' At Speed 56",
        ],
        False,
    ),
    (
        247,
        "E2 PAN RELATIVE STEPS ONLY",
        [
            f"{MOVERS} ; Attribute 'Pan' At Relative -30",
            "Step 2",
            "Attribute 'Pan' At Relative 30",
            "Attribute 'Pan' At Phase 0",
            "Attribute 'Pan' At Speed 56",
        ],
        False,
    ),
    (248, "F1 AURA DIMMER 100", [f"Fixture {f} ; Attribute 'Dimmer' At 100" for f in AURA], True),
    (
        249,
        "F2 AURA DIMMER 100 RGB 100",
        [f"Fixture {f} ; Attribute 'Dimmer' At 100 ; {RGB}" for f in AURA],
        True,
    ),
]

#: 재생 — (묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내)
PLAYBACK: list[tuple[str, list[str], float, str]] = [
    (
        "on_245",
        ["Goto Cue 1 Sequence 245"],
        HOLD,
        "E0 — 무빙 501~508 이 70% 로 켜지고 수직이 아니라 기울어졌는가",
    ),
    ("off_245", ["Off Sequence 245"], GAP, ""),
    (
        "on_246",
        ["Goto Cue 1 Sequence 246"],
        HOLD,
        "E1 — 기울어진 채 좌우로 느리게 흔들리는가(Tilt 45 를 단계 값에 넣음)",
    ),
    ("off_246", ["Off Sequence 246"], GAP, ""),
    ("base_245", ["Goto Cue 1 Sequence 245"], 0.0, ""),
    (
        "on_247",
        ["Goto Cue 1 Sequence 247"],
        HOLD,
        "E2 — 245(기울기)를 켜 둔 채 247(좌우 상대값)을 겹침 — 기울어진 채 흔들리는가",
    ),
    ("off_247", ["Off Sequence 247"], 0.0, ""),
    ("base_off_245", ["Off Sequence 245"], GAP, ""),
    (
        "on_248",
        ["Goto Cue 1 Sequence 248"],
        HOLD,
        "F1 — BACK 201 과 SIDE-L 301 이 켜지는가(Dimmer 100)",
    ),
    ("off_248", ["Off Sequence 248"], GAP, ""),
    ("on_249", ["Goto Cue 1 Sequence 249"], HOLD, "F2 — 같은 두 대에 RGB 100 을 더하면 켜지는가"),
    ("off_249", ["Off Sequence 249"], GAP, ""),
]


def bundles() -> list[tuple[str, list[str], float, str, bool]]:
    """(묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내, 거절돼도 계속?) — 쓰기 먼저, 재생은 PLAYBACK 순서."""
    soft = {seq: s for seq, _, _, s in LEVELS}
    out: list[tuple[str, list[str], float, str, bool]] = []
    for seq, label, values, s in LEVELS:
        cmds = ["ChangeDestination Root", "ClearAll", *values]
        cmds += [f"Store Sequence {seq} Cue 1 '{label.title()}'", "ClearAll"]
        cmds += [f"Set Sequence {seq} Property 'Name' {name(label)}"]
        out.append((f"store_{seq}", cmds, 0.0, "", s))
    for label, cmds, wait, say in PLAYBACK:
        out.append((label, cmds, wait, say, soft[int(cmds[0].split()[-1])]))
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
        if t0 is None and not label.startswith("store_"):
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
