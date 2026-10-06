# ruff: noqa: E501 — 근거(경로·판독값)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 바닥 워시 1b·2단계 — 천정 방향으로 뒤집은 뒤 바닥에 내려놓기.

감독 관찰(1단계 뒤, 리드 경유): 「위를 보고 있는데 바닥에 붙어있지 않아」.

계산 근거(실기 판독, `rot1b_reads2~4.txt`):
- 유형 9(Rush Par 2 RGBW Zoom) Body 모델 HEIGHT 0.293 m, LENGTH 0.260, WIDTH 0.293.
- Body 지오메트리 위치 0/0/0(기구 원점) · 그 아래 빔 `Main Module` POSZ -0.2783 m.
  → 몸체는 원점에서 아래로 약 0.28~0.29 m 걸린다. 원점은 몸체 꼭대기, 곧 매다는 지점이다.
- Stage 1 POSZ 0. 401 지금 POSZ 0.3, ROTX 180(1단계 결과).
- X 축 180° 뒤집으면 몸체는 [Posz, Posz + 0.293] 에 놓인다. 바닥(Z 0)에 닿으려면 Posz = 0.
  지금은 [0.3, 0.593] 이라 0.3 m 떠 있다 — 감독 관찰과 맞는다.
- 「바닥 = Z 0」 과 「모델 원점이 꼭대기」 는 판독값에서 낸 추론이다. 감독이 3D 에서 본다.

명령 형태: `Set Fixture <fid> Posz '<v>'`(server/orchestrator/tools.py:1773-1781 실기 측정 꼴, 작은따옴표 필수),
`Set Fixture <fid> Rotx '<v>'`(1단계 실기 측정: 401 ROTX 0 → 179.99999860565).

단계(--stage):
  1b         401 Posz '0'            사전 ROTX 180·POSZ 0.3 → 사후 POSZ 0
  1b-revert  401 Posz '0.3'          사전 POSZ 0 → 사후 0.3
  2          19대 Rotx '180'+Posz '0' 사전 0/0/0·POSZ 0.3 → 사후 ROTX 180·POSZ 0
  2-revert   19대 Rotx '0'+Posz '0.3' 사전 ROTX 180·POSZ 0 → 사후 ROTX 0·POSZ 0.3
쇼 저장 없음(감독이 저장).
실행: uv run python .moai/reports/t516/floor_place.py <출력폴더> --stage 1b [--rehearse | --approve <폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t516")
import tc_probe  # noqa: E402
from floor_rotate import PATHS  # noqa: E402
from rhythm_probe_v3 import FakeConsole  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

REST = [fid for fid in PATHS if fid != 401]
#: 단계 → (대상, 보낼 (축, 값) 목록, 사전 기대 {축: 값}, 사후 기대 {축: 값})
STAGES: dict[str, tuple[list[int], list[tuple[str, str]], dict[str, float], dict[str, float]]] = {
    "1b": ([401], [("Posz", "0")], {"ROTX": 180.0, "POSZ": 0.3}, {"ROTX": 180.0, "POSZ": 0.0}),
    "1b-revert": (
        [401],
        [("Posz", "0.3")],
        {"ROTX": 180.0, "POSZ": 0.0},
        {"ROTX": 180.0, "POSZ": 0.3},
    ),
    "2": (
        REST,
        [("Rotx", "180"), ("Posz", "0")],
        {"ROTX": 0.0, "POSZ": 0.3},
        {"ROTX": 180.0, "POSZ": 0.0},
    ),
    "2-revert": (
        REST,
        [("Rotx", "0"), ("Posz", "0.3")],
        {"ROTX": 180.0, "POSZ": 0.0},
        {"ROTX": 0.0, "POSZ": 0.3},
    ),
}
TOL = 1e-3  # 콘솔은 float32 로 저장한다(180 → 179.99999860565, 0.3 → 0.30000001192093)


def commands(stage: str) -> list[str]:
    targets, axes, _, _ = STAGES[stage]
    return [f"Set Fixture {fid} {axis} '{value}'" for fid in targets for axis, value in axes]


def matches(got: dict, want: dict[str, float]) -> bool:
    try:
        return all(abs(float(got.get(k, "nan")) - v) < TOL for k, v in want.items()) and all(
            float(got.get(k, "nan")) == 0.0 for k in ("ROTY", "ROTZ")
        )
    except ValueError:
        return False


def run(gate: SafetyGate, out: Path, *, stage: str, deny_all: bool, check: bool) -> dict:
    probe = Probe(gate, out)
    targets, _, before, after = STAGES[stage]
    result: dict = dict(stage=stage, targets=targets, pre={}, post={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    def read(label: str, fid: int) -> dict:
        props = probe.read_props(label, PATHS[fid], ["NAME", "POSZ", "ROTX", "ROTY", "ROTZ"]) or {}
        return {r["n"]: r.get("v") for r in props.get("reads") or ()}

    for fid in targets:
        got = read(f"pre_{fid}", fid)
        result["pre"][fid] = got
        if check and not (str(got.get("NAME", "")).endswith(str(fid)) and matches(got, before)):
            return stop(f"stopped: fixture {fid} pre-state {got} != {before}")
    tc_probe.RISK = BatchRisk(
        reason=f"t516 바닥 워시 {stage} — {len(targets)}대", kind="t516_floor_place"
    )
    result["fired"] = probe.fire(stage, commands(stage))
    if deny_all:
        return stop("deny-all: approval text recorded")
    for fid in targets:
        result["post"][fid] = read(f"post_{fid}", fid)
    if not check:
        return stop("rehearsal: read-back not judged (fake console)")
    bad = [fid for fid in targets if not matches(result["post"][fid], after)]
    return stop(
        f"read-back mismatch {bad}" if bad else f"read-back = {after} for all {len(targets)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([commands(args.stage)])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, stage=args.stage, deny_all=False, check=False)
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
            result = run(stack.gate, out, stage=args.stage, deny_all=pinned is None, check=True)
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
        json.dumps(
            {k: result.get(k) for k in ("verdict", "targets", "pre", "post")}, ensure_ascii=False
        )[:2500]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
