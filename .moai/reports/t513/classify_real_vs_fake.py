"""t513 — 실기 전부-거절 승인 요청 4(본 큐 묶음) 대 가짜 콘솔 송신(run1_fake) 차이 전량 분류.

기구 목록은 `<SET>` 으로 바꿔 비교한다(t498 classify_diff.py 와 같은 방식 — 가짜 좌표 대역은 실기 86대 번호).
실행: uv run python .moai/reports/t513/classify_real_vs_fake.py
"""

import difflib
import re
from pathlib import Path

D = Path(".moai/reports/t513")
real = (D / "run3_real_denyall/approval_request_4.txt").read_text("utf-8").splitlines()
fake = (D / "run1_fake/console_commands_sent.txt").read_text("utf-8").splitlines()


def norm(line: str) -> str:
    return re.sub(r"^Fixture [\d +]+ ;", "Fixture <SET> ;", line)


r, f = [norm(x) for x in real], [norm(x) for x in fake]
print(f"real={len(r)} fake={len(f)}")
only_real, only_fake = [], []
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=f, b=r, autojunk=False).get_opcodes():
    if tag in ("replace", "delete"):
        only_fake.extend(f[i1:i2])
    if tag in ("replace", "insert"):
        only_real.extend(r[j1:j2])


def kind(line: str) -> str:
    if "ColorRGB_W" in line and line.endswith("'ColorRGB_W' At 0"):
        return "W-zero line"
    if "At Preset 4." in line or "At Preset 21." in line:
        return "phaser recall"
    return "OTHER"


print("only in real:", len(only_real))
for k in sorted({kind(x) for x in only_real}):
    rows = [x for x in only_real if kind(x) == k]
    print(f"  {k}: {len(rows)}")
    for x in rows[:3]:
        print("     ", x[:200])
print("only in fake:", len(only_fake))
for x in only_fake[:10]:
    print("     ", x[:200])
