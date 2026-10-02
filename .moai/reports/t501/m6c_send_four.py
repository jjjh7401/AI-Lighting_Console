"""t501 M6c — 감독 승인(2026-10-02)된 4종 페이저 사전 생성을 앱 경로로 보낸다.

m6_send_wave_cm.py 와 같은 경로·같은 위험 선언 kind 로, m6c_pregen_commands_rain.txt
의 네 묶음을 순서대로 하나씩 보낸다. 묶음마다 승인은 그 묶음의 명령 목록과 **글자까지
같을 때만** 한다. 🔴 한 묶음이라도 실패(거절·오류)하면 나머지는 보내지 않고 멈춘다
— 복합 줄이 스텝 값에 처음 쓰이기 때문이다(리드 지시).
쇼 저장: 게이트의 실행 직전 SaveShow 는 보내지 않고 기록만 한다(감독이 콘솔에서 저장).

실행: uv run python .moai/reports/t501/m6c_send_four.py <출력 폴더>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.safety.bootstrap import build_console_stack
from server.safety.gate import BatchRisk
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(".moai/reports/t501/m6c_pregen_commands_rain.txt")
HEADER = re.compile(r"^# (?P<label>.+) -> Preset (?P<preset>\d+\.\d+)$")


def bundles() -> list[tuple[str, str, list[str]]]:
    found: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for line in SOURCE.read_text("utf-8").splitlines():
        match = HEADER.match(line)
        if match:
            current = (match["label"], match["preset"], [])
            found.append(current)
        elif not line.strip():
            current = None
        elif current is not None:
            current[2].append(line)
    return found


BUNDLES = bundles()
assert [b[1] for b in BUNDLES] == ["4.10", "4.11", "21.7", "21.8"], [b[1] for b in BUNDLES]
for label, preset, commands in BUNDLES:
    assert f"Store Preset {preset} '{label}' /Universal" in commands, (label, preset)


class _PinnedApproval:
    def __init__(self):
        self.pinned: list[str] | None = None
        self.requests: list[dict] = []

    def request_approval(self, request) -> bool:
        commands = list(request.commands)
        decision = self.pinned is not None and commands == self.pinned
        self.requests.append({"commands": commands, "approved": decision})
        return decision

    def bind(self, *_a, **_kw):
        return None


class _Provider:
    def complete(self, *_a, **_kw):  # pragma: no cover
        raise AssertionError("이 경로는 모델을 부르지 않는다")


approval = _PinnedApproval()
stack = build_console_stack(
    send_port=8000,
    receive_port=9005,
    approval_port=approval,
    audit_dir=OUT / "audit",
    attempt_session_backup=False,
)
skipped_backups: list[str] = []
stack.backup._backup_action = lambda: skipped_backups.append("SaveShow skipped (supervisor)")
results: list[dict] = []
stopped_at: str | None = None
try:
    session = ChatSession(
        gate=stack.gate,
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=stack.audit,
        send_event=lambda *_a, **_kw: None,
        approval_channel=ApprovalChannel(timeout_seconds=5.0),
    )
    for label, preset, commands in BUNDLES:
        approval.pinned = list(commands)
        executed = session._dispatch_declared(
            ToolCall(
                id=f"t501-m6c-pregen-{preset}",
                name="run_commands",
                arguments={"commands": list(commands)},
            ),
            risk=BatchRisk(
                reason=f"'{label}' 카탈로그 페이저 사전 생성 — t501 M6c 감독 승인 2026-10-02",
                kind="song_design_fx_pregen",
            ),
        )
        content = executed.result.content
        ok_count = str(content).count("executed_ok")
        all_ok = (not executed.result.is_error) and '"all_ok": true' in str(content)
        results.append(
            {
                "label": label,
                "preset": preset,
                "lines": len(commands),
                "is_error": executed.result.is_error,
                "all_ok": all_ok,
                "executed_ok": ok_count,
                "content": content,
            }
        )
        print(f"{label} -> {preset}: all_ok={all_ok} executed_ok={ok_count}/{len(commands)}")
        if not all_ok or ok_count != len(commands):
            stopped_at = label
            break
finally:
    stack.stop()

summary = {
    "stopped_at": stopped_at,
    "results": results,
    "approval_requests": approval.requests,
    "skipped_backups": skipped_backups,
}
(OUT / "result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8")
print(
    f"stopped_at={stopped_at} sent={len(results)} "
    f"approval_requests={len(approval.requests)} "
    f"approved={sum(1 for r in approval.requests if r['approved'])} "
    f"skipped_saveshow={len(skipped_backups)}"
)
