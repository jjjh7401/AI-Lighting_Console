"""t514 — t511 초안(6de980be) 대 수정본의 표 행을 대조한다.

카드 조건: 기존 행의 시각·강조 순서는 유지하고 움직임 효과만 더한다(바꾸면 이유).
- 기존 행마다 같은 시각(괄호 안 「N회」 접미사는 뺀 값)의 행이 수정본에 있는가
- 강조 행이 글자까지 같은가, 순서가 같은가
- 내용이 바뀐 기존 행과 새로 생긴 행을 나열한다

실행: uv run python .moai/reports/t514/diff_rows.py
"""

import re
import subprocess
from pathlib import Path

PATH = ".moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md"
BASE = "6de980be"


def rows(text: str) -> list[list[str]]:
    lines = text.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| 시각 | 층 |"))
    out = []
    for ln in lines[start + 2 :]:
        if not ln.startswith("|"):
            break
        out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def when(r: list[str]) -> str:
    return re.sub(r", [\d+]+회\)", ")", r[0])


old = rows(
    subprocess.run(
        ["git", "show", f"{BASE}:{PATH}"], capture_output=True, text=True, check=True
    ).stdout
)
new = rows(Path(PATH).read_text(encoding="utf-8"))
print(f"rows old {len(old)} new {len(new)}")

new_keys = [(when(r), r[1]) for r in new]
missing = [r for r in old if (when(r), r[1]) not in new_keys]
print("old rows whose time+layer is gone:", len(missing))
for r in missing:
    print("  MISSING", r[0])

old_acc = [r for r in old if r[1] == "강조"]
new_acc = [r for r in new if r[1] == "강조"]
print("accent rows identical and same order:", old_acc == new_acc, len(old_acc), len(new_acc))

HEAD = ["시각", "층", "모멘트", "연출", "잇는", "이유"]
used: set[int] = set()
changed = []
for r in old:
    same_key = [
        i for i, n in enumerate(new) if i not in used and (when(n), n[1]) == (when(r), r[1])
    ]
    # 같은 시각의 행이 둘이면(펄스 행 + 새 움직임 행) 연출 첫 범주가 같은 쪽을 짝으로 고른다
    pick = next(
        (i for i in same_key if new[i][3][:6] == r[3][:6]), same_key[0] if same_key else None
    )
    if pick is None:
        continue
    used.add(pick)
    if new[pick] != r:
        cols = [h for h, a, b in zip(HEAD, r, new[pick], strict=True) if a != b]
        changed.append((r[0], cols, r[3][:40], new[pick][3][:40]))
print("changed existing rows:", len(changed))
for t, cols, a, b in changed:
    print(f"  {t} | {cols} | {a} → {b}")

added = [n for i, n in enumerate(new) if i not in used]
print("added rows:", len(added))
for n in added:
    print("  ADDED", n[0], "|", n[3][:40])
