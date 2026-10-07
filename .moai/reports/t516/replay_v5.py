"""t516 v5 다시 보기 재생 — 쓰기 없음.

리드 지시(2026-10-07, 감독 「5개만 다시 보여줘」): v5 실기 1회와 같은 재생 순서를 다시 보여 준다.
Goto/Off 만 보낸다(Store/Set/Assign/Master/ClearAll/Save 0줄). 맨 앞 5초 여유 →
245(8초) → Off → 2초 → 246 → Off → 2초 → 245 켠 채 247(8초) → 247·245 Off → 2초
→ 248 → Off → 2초 → 249 → Off.
순서는 `rhythm_probe_v5.PLAYBACK` 을 그대로 쓴다.
이름 사전 판독이 v5 가 붙인 이름과 다르면 재생하지 않는다.
🔴 리드의 「실행」 메시지가 올 때까지 실기 승인 모드로 돌리지 않는다.

실행: uv run python .moai/reports/t516/replay_v5.py <출력폴더>
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
from rhythm_probe_v3 import POOL, FakeConsole  # noqa: E402
from rhythm_probe_v5 import LEVELS, PLAYBACK, name  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(reason="t516 v5 다시 보기 — 재생만(쓰기 없음)", kind="t516_replay_v5")
LEAD_IN = 5.0

#: (묶음 이름, 명령, 보낸 뒤 기다릴 초, 감독 안내) — v5 실기 재생과 같은 순서·간격
TIMELINE: list[tuple[str, list[str], float, str]] = list(PLAYBACK)
#: 콘솔에 남은 이름 — 이름이 다르면 재생할 대상이 아니다
EXPECTED = {seq: name(label).strip("'") for seq, label, *_ in LEVELS}


def run(gate: SafetyGate, out: Path, *, deny_all: bool, pace: bool, check_names: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(bundles={}, marks=[], pre_names={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    for seq, want in EXPECTED.items():
        props = probe.read_props(f"pre_seq_{seq}", f"{POOL}/{seq}", ["NAME"])
        got = next(
            (r.get("v") for r in (props or {}).get("reads") or () if r.get("n") == "NAME"), None
        )
        result["pre_names"][seq] = got
        if check_names and got != want:
            return stop(f"stopped: sequence {seq} name {got!r} != {want!r}")
    if pace:
        time.sleep(LEAD_IN)
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
    return stop("replayed — judge by director watch")


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
        console.exists.update(f"{POOL}/{seq}" for seq in EXPECTED)
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
                stack.gate, out, deny_all=pinned is None, pace=pinned is not None, check_names=True
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
    print(json.dumps({k: result.get(k) for k in ("verdict", "pre_names")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
