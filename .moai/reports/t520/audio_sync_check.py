# ruff: noqa: E501 — 한국어 머리말
"""t520 — m2a_play.py 음원 맞추기 경로를 가짜 콘솔로 시험한다(콘솔 0, 소리 0).

가짜 CURSOR = `Go Timecode` 를 받은 뒤 흐른 초 + 인위 지연(읽기 왕복 0.03~0.08초). 음원 경로는 없는 파일이라
afplay 는 바로 오류로 끝난다(소리 없음). 판정: 추정한 띄운 TC 시각이 LEAD(3.0) ± 0.1 안인지.
실행: uv run python .moai/reports/t520/audio_sync_check.py
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import m2a_play as play  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.backup import BackupManager  # noqa: E402
from server.safety.gate import SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402


class CursorConsole(play.FakeConsole):
    def __init__(self) -> None:
        super().__init__()
        self.go_at = None

    def execute(self, command: str):
        if command.startswith("Go Timecode"):
            self.go_at = time.monotonic() + 0.04  # 콘솔이 Go 를 받기까지 지연
        return super().execute(command)

    def query_properties(self, path: str, names) -> dict:
        if "CURSOR" in names and self.go_at is not None:
            time.sleep(random.uniform(0.015, 0.04))  # 왕복 절반
            v = max(0.0, time.monotonic() - self.go_at)
            time.sleep(random.uniform(0.015, 0.04))
            return dict(ok=True, path=path, reads=[dict(n="CURSOR", ok=True, v=f"{v:.2f}")])
        return super().query_properties(path, names)


play.gen.configure(269, 270, 24, "M2a B2", "group", None)
play.retarget()
play.MUSIC_END = 0.0
out = Path(".moai/reports/t520/audio_sync_check")
out.mkdir(parents=True, exist_ok=True)
results = []
for _ in range(5):
    console = CursorConsole()
    gate = SafetyGate(
        console=console,
        audit=AuditLog(out / "audit"),
        ruleset=load_ruleset(),
        approval_port=play.RecordingApproval([cmds for _, cmds in play.BUNDLES]),
        backup=BackupManager(backup_action=lambda: None),
    )
    r = play.run(gate, out, deny_all=False, audio="/nonexistent/silent.mp3")
    a = r["audio"]
    results.append(a["spawned_tc_estimate"])
    print(a)
print(
    "spawned_tc_estimate",
    results,
    "all within ±0.1:",
    all(abs(x - play.LEAD) <= 0.1 for x in results),
)
