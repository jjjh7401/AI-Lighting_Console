# ruff: noqa: E501 — 근거(URL·인용)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 바닥 워시 20대(401~410·421~430) 3D 회전 — 천정 방향으로.

감독 결정(리드 경유 2026-10-06): 「(바닥 워시 20대를) 천정방향으로 돌려줘」.

근거:
- 축 정의(공식 문서 Position Fixtures in the 3D Space, https://help.malighting.com/grandMA3/2.0/HTML/patch_position_fixtures.html):
  「Rot X: rotating the fixture around the fixture's own X-axis. A positive value is rotating the top of the fixture towards downstage.」
- 0/0/0 의 방향(공식 문서 3D Fixture Setup, https://help.malighting.com/grandMA3/2.0/HTML/qsg_3d_setup.html):
  「the fixture's insert point is usually its hanging point」 — 회전 0 은 매달린 자세(빔이 아래).
  감독 관찰도 같다: 「바닥 아래로 향하고 있어서 빛을 볼 수가 없어」.
- 그래서 X 축 180° 로 뒤집으면 빔이 위를 본다(추론, 안 잰 것). 1단계는 401 한 대만.
- 명령 형태: 이 저장소가 실기에서 잰 좌표 쓰기 `Set Fixture <fid> Posx '<v>'`(server/orchestrator/tools.py:1773-1781,
  rulebook 32_spatial_design.md:123-127)의 축 이름만 `Rotx` 로 바꾼다. 값은 작은따옴표로 싼다.
  `Rotx` 축 이름이 받아들여지는지는 안 잰 것이다 — 되읽기(ROTX)로 판정한다.
  공식 Set 키워드 문서(https://help.malighting.com/grandMA3/2.4/HTML/keyword_set.html)는 `Set [Object_Type] [Number] Property ["Name"] ["Value"]` 꼴만 적고 Fixture 예시는 없다.

단계: --stage 1 (401) · --stage 2 (나머지 19대) · --revert 를 붙이면 같은 대상을 0 으로 되돌린다.
사전 판독에서 대상의 ROTX/ROTY/ROTZ 가 기대값(돌리기 전 0/0/0, 되돌리기 전 180/0/0)이 아니면 멈춘다.
쇼 저장 없음(감독이 저장).
실행: uv run python .moai/reports/t516/floor_rotate.py <출력폴더> --stage 1 [--revert] [--rehearse | --approve <전부-거절 폴더>]
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
from rhythm_probe_v3 import FakeConsole  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

#: FID → 패치 경로(`diag7_patch.txt` 실기 판독: 401~410 → Fixtures/67~76, 421~430 → 77~86)
PATHS = {
    fid: f"Patch/Stages/1/Fixtures/{67 + i}"
    for i, fid in enumerate([*range(401, 411), *range(421, 431)])
}
STAGES = {1: [401], 2: [fid for fid in PATHS if fid != 401]}
UP = "180"
DOWN = "0"


def plan(stage: int, revert: bool) -> tuple[list[int], str, float]:
    targets = STAGES[stage]
    return targets, (DOWN if revert else UP), (180.0 if revert else 0.0)


def run(
    gate: SafetyGate, out: Path, *, stage: int, revert: bool, deny_all: bool, check: bool
) -> dict:
    probe = Probe(gate, out)
    targets, value, before_x = plan(stage, revert)
    result: dict = dict(stage=stage, revert=revert, targets=targets, pre={}, post={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    def rot(label: str, fid: int) -> dict:
        props = probe.read_props(label, PATHS[fid], ["NAME", "ROTX", "ROTY", "ROTZ"]) or {}
        return {r["n"]: r.get("v") for r in props.get("reads") or ()}

    for fid in targets:
        got = rot(f"pre_{fid}", fid)
        result["pre"][fid] = got
        if check:
            ok = (
                str(got.get("NAME", "")).endswith(str(fid))
                and abs(float(got.get("ROTX", "nan")) - before_x) < 1e-3
                and float(got.get("ROTY", "nan")) == 0.0
                and float(got.get("ROTZ", "nan")) == 0.0
            )
            if not ok:
                return stop(f"stopped: fixture {fid} pre-state {got} != ROTX {before_x}/0/0")
    tc_probe.RISK = BatchRisk(
        reason=f"t516 바닥 워시 3D 회전 {'되돌리기' if revert else '천정 방향'} — {len(targets)}대",
        kind="t516_floor_rotate",
    )
    fired = probe.fire("rotate", [f"Set Fixture {fid} Rotx '{value}'" for fid in targets])
    result["fired"] = fired
    if deny_all:
        return stop("deny-all: approval text recorded")
    for fid in targets:
        result["post"][fid] = rot(f"post_{fid}", fid)
    if not check:
        return stop("rehearsal: read-back not judged (fake console)")
    want = float(value)
    bad = [
        fid for fid in targets if abs(float(result["post"][fid].get("ROTX", "nan")) - want) > 1e-3
    ]
    return stop(
        f"ROTX read-back mismatch {bad}"
        if bad
        else f"ROTX read-back = {value} for all {len(targets)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--stage", type=int, choices=(1, 2), required=True)
    parser.add_argument("--revert", action="store_true")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    targets, value, _ = plan(args.stage, args.revert)
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([[f"Set Fixture {fid} Rotx '{value}'" for fid in targets]])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, stage=args.stage, revert=args.revert, deny_all=False, check=False)
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
                stage=args.stage,
                revert=args.revert,
                deny_all=pinned is None,
                check=True,
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
        json.dumps(
            {k: result.get(k) for k in ("verdict", "targets", "pre", "post")}, ensure_ascii=False
        )[:2500]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
