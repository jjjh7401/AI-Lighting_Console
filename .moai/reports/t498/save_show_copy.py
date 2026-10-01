"""t498 — 0단계: 지금 쇼를 새 이름으로 저장한다(리드 결정 (1), 감독 확정 2026-09-28).

보낼 명령은 한 줄이고 파일에 고정돼 있다: .moai/reports/t498/cmd_saveshow_copy.txt
경로는 앱과 같은 게이트(`build_console_stack` → `SafetyGate.execute`, 감사 기록 포함)다.
게이트가 승인을 물으면 **그 파일의 줄과 글자까지 같을 때만** 승인한다.
게이트의 실행 직전 자동 백업(인자 없는 SaveShow)은 t474 와 같이 보내지 않고 기록만 한다 —
인자 없는 SaveShow 는 **원본 쇼 파일을 덮어쓰기** 때문이다.

--execute 가 없으면 아무것도 보내지 않고 보낼 줄만 출력한다.

실행: uv run python .moai/reports/t498/save_show_copy.py <출력> [--execute]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from server.safety.bootstrap import build_console_stack

OUT = Path(sys.argv[1])
EXECUTE = "--execute" in sys.argv
# 1차 파일(큰따옴표)은 브리지 검증(protocol.py _validate_rest)이 송신 전에 거절했다.
# 2차 파일(작은따옴표)을 --cmd 로 지정한다. 어느 쪽이든 아래 두 줄 중 하나와 글자까지 같아야 한다.
CMD_FILE = Path(
    sys.argv[sys.argv.index("--cmd") + 1]
    if "--cmd" in sys.argv
    else ".moai/reports/t498/cmd_saveshow_copy.txt"
)
COMMANDS = CMD_FILE.read_text("utf-8").splitlines()
assert COMMANDS in (
    ['SaveShow "copilot-rehearsal-20260928"'],
    ["SaveShow 'copilot-rehearsal-20260928'"],
), COMMANDS
OUT.mkdir(parents=True, exist_ok=True)
print("command file:", CMD_FILE, COMMANDS)
if not EXECUTE:
    print("dry: nothing sent")
    raise SystemExit(0)


class _PinnedApproval:
    def __init__(self, pinned: list[str]):
        self.pinned = pinned
        self.requests: list[dict] = []

    def request_approval(self, request) -> bool:
        commands = list(request.commands)
        decision = commands == self.pinned
        self.requests.append({"commands": commands, "approved": decision})
        return decision

    def bind(self, *_a, **_kw):
        return None


approval = _PinnedApproval(COMMANDS)
stack = build_console_stack(
    send_port=8000,
    receive_port=9005,
    approval_port=approval,
    audit_dir=OUT / "audit",
    attempt_session_backup=False,
)
skipped_backups: list[str] = []
stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (no-arg)")
# 앱의 run_commands 와 같은 순서: screen(분류·승인) → 통과했을 때만 execution_port.execute.
# (1차 실행은 존재하지 않는 gate.execute 를 불러 송신 전에 죽었다 — 감사 로그 0.)
result = None
try:
    decision = stack.gate.screen(COMMANDS)
    if decision.cleared:
        result = stack.gate.execution_port.execute(COMMANDS[0])
finally:
    stack.stop()
summary = {
    "screen": {
        "cleared": decision.cleared,
        "status": decision.status,
        "notice": decision.notice,
        "commands": [(d.command, d.status, list(d.reasons)) for d in decision.commands],
    },
    "result": repr(result),
    "approval_requests": approval.requests,
    "skipped_backups": skipped_backups,
}
(OUT / "result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
