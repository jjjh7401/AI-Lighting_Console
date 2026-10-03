"""t501 M6 — 감독 승인(2026-10-02)된 Wave CM 사전 생성 21줄을 앱 경로로 보낸다.

경로: ChatSession._dispatch_declared → run_commands → gate.screen() (앱의
`_pregenerate_missing_phasers` 와 같은 호출, 같은 위험 선언 kind).
승인: 게이트 승인 요청의 명령 목록이 m6_pregen_commands_rain.txt 의 Wave CM 블록과
**글자까지 같을 때만** 승인한다(t498 real_console.py 의 고정 승인 방식).
쇼 저장: 게이트의 실행 직전 SaveShow 는 보내지 않고 기록만 한다(감독이 콘솔에서 저장).

실행: uv run python .moai/reports/t501/m6_send_wave_cm.py <출력 폴더>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.safety.bootstrap import build_console_stack
from server.safety.gate import BatchRisk
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(".moai/reports/t501/m6_pregen_commands_rain.txt")


def wave_cm_block() -> list[str]:
    lines = SOURCE.read_text("utf-8").splitlines()
    start = lines.index("# Wave CM -> Preset 4.9") + 1
    block: list[str] = []
    for line in lines[start:]:
        if not line.strip():
            break
        block.append(line)
    return block


COMMANDS = wave_cm_block()
assert len(COMMANDS) == 21, len(COMMANDS)
assert COMMANDS[-3] == "Store Preset 4.9 'Wave CM' /Universal", COMMANDS[-3]


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


class _Provider:
    def complete(self, *_a, **_kw):  # pragma: no cover
        raise AssertionError("이 경로는 모델을 부르지 않는다")


approval = _PinnedApproval(COMMANDS)
stack = build_console_stack(
    send_port=8000,
    receive_port=9005,
    approval_port=approval,
    audit_dir=OUT / "audit",
    attempt_session_backup=False,
)
skipped_backups: list[str] = []
stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (supervisor)")
try:
    session = ChatSession(
        gate=stack.gate,
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=stack.audit,
        send_event=lambda *_a, **_kw: None,
        approval_channel=ApprovalChannel(timeout_seconds=5.0),
    )
    executed = session._dispatch_declared(
        ToolCall(
            id="t501-m6-pregen-wave-cm-4.9",
            name="run_commands",
            arguments={"commands": list(COMMANDS)},
        ),
        risk=BatchRisk(
            reason="'Wave CM' 카탈로그 페이저 사전 생성 — t501 M6 감독 승인 2026-10-02",
            kind="song_design_fx_pregen",
        ),
    )
finally:
    stack.stop()

result = {
    "is_error": executed.result.is_error,
    "content": executed.result.content,
    "approval_requests": approval.requests,
    "skipped_backups": skipped_backups,
}
(OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), "utf-8")
print(
    f"is_error={executed.result.is_error} "
    f"approval_requests={len(approval.requests)} "
    f"approved={sum(1 for r in approval.requests if r['approved'])} "
    f"skipped_saveshow={len(skipped_backups)}"
)
print("CONTENT:", str(executed.result.content)[:1500])
