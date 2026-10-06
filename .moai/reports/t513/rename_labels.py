"""t513 — 감독 요청(2026-10-06): 시퀀스 219 · 타임코드 19 이름 붙이기, 2줄만.

t506 tc_probe.py 의 발사 방식(gate.screen → execution_port.execute 한 줄씩)을 따른다.
묶음은 BatchRisk 로 「쇼파일 쓰기」를 선언해 승인 대상으로 만든다.

두 모드:
    (기본) 전부-거절  승인 요청만 뜨고 거절 — 송신 0. 게이트가 승인 없이 통과시켜도
                      이 모드에서는 **보내지 않는다**(이중 안전망).
    --approve <파일>  묶음이 그 파일과 글자까지 같고 게이트가 승인 뒤 통과시킬 때만 보낸다.

쇼 저장: 게이트의 실행 직전 백업(SaveShow)은 보내지 않고 기록만 한다(t498 · t506 과 같다).
실행: uv run python .moai/reports/t513/rename_labels.py <출력폴더> [--approve <파일>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from server.safety.bootstrap import build_console_stack
from server.safety.gate import BatchRisk

COMMANDS = [
    "Set Sequence 219 Property 'Name' 'LOVE ATTACK - OLD APP'",
    "Set Timecode 19 Property 'Name' 'LOVE ATTACK - OLD APP TC'",
]
RISK = BatchRisk(
    reason="t513 감독 요청: 시퀀스 219 · 타임코드 19 이름 붙이기(2줄, 이름 속성만)",
    kind="t513_rename",
)
READS = [
    ("ShowData/DataPools/Default/Sequences/219", ["NO", "NAME"]),
    ("ShowData/DataPools/Default/Timecodes/19", ["NO", "NAME"]),
]


class _PinnedApproval:
    def __init__(self, pinned: list[str] | None):
        self.pinned = pinned
        self.requests: list[dict] = []

    def request_approval(self, request) -> bool:
        commands = list(request.commands)
        decision = self.pinned is not None and commands == self.pinned
        self.requests.append({"commands": commands, "approved": decision})
        return decision

    def bind(self, *_a, **_kw):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pinned = Path(args.approve).read_text("utf-8").splitlines() if args.approve else None
    approval = _PinnedApproval(pinned)
    stack = build_console_stack(
        send_port=8000,
        receive_port=9005,
        approval_port=approval,
        audit_dir=out / "audit",
        attempt_session_backup=False,
    )
    skipped_backups: list[str] = []
    stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (supervisor)")
    log: list[dict] = []
    try:
        state = stack.gate.state_port
        for path, names in READS:
            log.append(
                {"step": "before", "path": path, "reply": state.query_properties(path, names)}
            )
        decision = stack.gate.screen(COMMANDS, risk=RISK)
        log.append({"step": "screen", "cleared": decision.cleared})
        fire = decision.cleared and pinned is not None and pinned == COMMANDS
        for command in COMMANDS:
            if not fire:
                log.append({"step": "exec", "command": command, "fired": False})
                continue
            result = stack.gate.execution_port.execute(command)
            log.append(
                {
                    "step": "exec",
                    "command": command,
                    "fired": True,
                    "ok": result.ok,
                    "detail": result.detail,
                }
            )
        for path, names in READS:
            log.append(
                {"step": "after", "path": path, "reply": state.query_properties(path, names)}
            )
    finally:
        stack.stop()
    (out / "approval_request_1.txt").write_text("\n".join(COMMANDS) + "\n", "utf-8")
    (out / "approval_requests.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=1), "utf-8"
    )
    (out / "log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1, default=str), "utf-8"
    )
    (out / "skipped_backups.json").write_text(json.dumps(skipped_backups), "utf-8")
    fired = [row for row in log if row["step"] == "exec" and row["fired"]]
    print(
        f"mode={'pinned' if pinned is not None else 'deny-all'} cleared={decision.cleared} "
        f"approval_requests={len(approval.requests)} "
        f"approved={sum(r['approved'] for r in approval.requests)} fired={len(fired)} "
        f"ok={sum(bool(r.get('ok')) for r in fired)} skipped_saveshow={len(skipped_backups)}"
    )
    for row in log:
        if row["step"] in ("before", "after"):
            reads = {r["n"]: r.get("v") for r in (row["reply"] or {}).get("reads", [])}
            print(row["step"], row["path"].rsplit("/", 2)[-2:], reads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
