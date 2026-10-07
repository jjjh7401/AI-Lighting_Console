"""t516 다시 보기 재생 — 쓰기 없음.

감독이 1회차 실행(12:53:53~12:55:16 KST)을 못 봐서 만든 재생 전용 판이다.

리드 지시(2026-10-06): 재생만(Go/Goto/Off), `Master 3.15 At BPM 112.35` 재설정은 허용(이미 그 값).
Store/Set/Assign/Delete/ClearAll/Save 0줄. 원래 실행과 같은 순서·구간 길이, 구간 사이 2초 여유.
🔴 리드의 「실행」 메시지가 올 때까지 실기 승인 모드로 돌리지 않는다.

1회차와 다른 점 하나: 겹침 구간(⑤)을 타임코드 대신 `Goto Cue 1 Sequence 220/221` 로 1초·2초에 연다.
1회차 뒤 타임코드 20 의 커서가 `Off` 뒤에도 10.00(끝)으로 읽혀 `Go Timecode 20` 이 0초부터 다시
도는지 확인되지 않았기 때문이다. 타임코드 트랙 둘(④)은 1회차에서 기계로 이미 PASS 했다.

실행: uv run python .moai/reports/t516/replay_probe.py <출력폴더>
      [--rehearse | --approve <전부-거절 폴더>]
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
from rhythm_probe import SEQ, FakeConsole  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(reason="t516 다시 보기 — 재생만(쓰기 없음)", kind="t516_replay")
NAMES = {
    220: "RHYTHM PROBE - OVERLAP SCENE",
    221: "RHYTHM PROBE - SPEEDMASTER MEASURE",
    222: "RHYTHM PROBE - NEW SHAPES",
}
GAP = 2.0
HOLD = 8.0

#: (묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내) — 시간 순서 그대로
TIMELINE: list[tuple[str, list[str], float, str]] = [
    ("bpm", ["Master 3.15 At BPM 112.35"], GAP, "① Speed15 BPM 표시가 112.35 인지"),
    ("scene_on", ["Goto Cue 1 Sequence 220"], 1.0, "⑤ BACK 30% 켜짐"),
    ("beat_on", ["Goto Cue 1 Sequence 221"], 4.0, "⑤ BACK 이 1박마다 깜빡임(장면 위에 박자)"),
    ("beat_off", ["Off Sequence 221"], 4.0, "⑤ 깜빡임이 멈추고 BACK 30% 로 돌아오는지"),
    ("scene_off", ["Off Sequence 220"], GAP, ""),
    (
        "measure_1",
        ["Goto Cue 1 Sequence 221"],
        HOLD + GAP,
        "② Measure 1 — 1박에 한 번(8초에 약 15번)",
    ),
    ("measure_2", ["Goto Cue 2 Sequence 221"], HOLD + GAP, "② Measure 2 — 2박에 한 번(약 7번)"),
    (
        "measure_3",
        ["Goto Cue 3 Sequence 221"],
        HOLD + GAP,
        "② Measure 0.5 — 반 박에 한 번(약 30번)",
    ),
    ("measure_off", ["Off Sequence 221"], GAP, ""),
    (
        "shape_1",
        ["Goto Cue 1 Sequence 222"],
        HOLD + GAP,
        "③ 팬 웨이브 — 줄지어 따라가는 파도, 2박 한 바퀴",
    ),
    ("shape_2", ["Goto Cue 2 Sequence 222"], HOLD + GAP, "③ 엇갈린 팬 웨이브 — ODD/EVEN 반대, 1박"),
    ("shape_3", ["Goto Cue 3 Sequence 222"], HOLD + GAP, "③ 가속 스윕 4박"),
    ("shape_4", ["Goto Cue 4 Sequence 222"], HOLD + GAP, "③ 가속 스윕 2박"),
    ("shape_5", ["Goto Cue 5 Sequence 222"], HOLD + GAP, "③ 가속 스윕 1박"),
    ("shape_off", ["Off Sequence 222"], 0.0, ""),
]


def run(gate: SafetyGate, out: Path, *, deny_all: bool, pace: bool, check_names: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(bundles={}, marks=[])

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    # 사전 판독 — 1회차가 만든 세 시퀀스가 그 이름으로 있는지(없으면 재생할 것이 없다)
    for n, p in SEQ.items():
        props = probe.read_props(f"pre_seq_{n}", p, ["NAME"])
        got = next(
            (r.get("v") for r in (props or {}).get("reads") or () if r.get("n") == "NAME"), None
        )
        if check_names and got != NAMES[n]:
            return stop(f"stopped: sequence {n} name {got!r} != {NAMES[n]!r}")
        result.setdefault("pre_names", {})[n] = got
    t0 = time.monotonic()
    for label, cmds, wait, say in TIMELINE:
        if say:
            probe.note("watch", say=say)
        result["bundles"][label] = probe.fire(label, cmds)
        result["marks"].append(dict(label=label, t=round(time.monotonic() - t0, 2)))
        if pace:
            time.sleep(wait)
    if deny_all:
        return stop("deny-all: approval texts recorded, nothing sent")
    return stop("replayed — ②③⑤ and ① display by director watch")


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
        console.exists.update(SEQ.values())
        approval = RecordingApproval([cmds for _, cmds, _, _ in TIMELINE])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, deny_all=False, pace=False, check_names=False)
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
            result = run(
                stack.gate,
                out,
                deny_all=pinned is None,
                pace=pinned is not None,
                check_names=True,
            )
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps({k: v for k, v in result.items() if k != "fake_sent"}, ensure_ascii=False)[:3000]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
