"""t482 — 가드 변이 검사. 고친 곳을 하나씩 틀린 모양으로 바꿔 해당 시험이
실패하는지 본다. 각 변이 뒤 `git checkout -- <file>` 로 커밋(258d7f3b) 상태 복원.
실행: 워크트리 루트에서 `python3 .moai/reports/t482/mutate.py`
"""

import subprocess
from pathlib import Path

PY = "uv run pytest -q -p no:cacheprovider server/tests/test_concept_glance_t482.py"
UI = "npm --prefix ui exec -- vitest run --root ui src/components/conceptGlance.test.ts"

MUTANTS = [
    (
        "강조에 마지막 후렴까지 넣음(규칙 위반)",
        "server/concept/session_bridge.py",
        'buckets["강조"] = list(range(first, before_last + 1))',
        'buckets["강조"] = list(range(first, last + 1))',
        PY,
    ),
    (
        "역할 없는 구간이 있어도 배정",
        "server/concept/session_bridge.py",
        "if not roles or any(role is None for role in roles):",
        "if not roles:",
        PY,
    ),
    (
        "큐 설명 대신 고정 문장",
        "server/concept/session_bridge.py",
        '"description": description,',
        '"description": "밝게 빛난다",',
        PY,
    ),
    (
        "카드 밝기를 구간 값 대신 상수로",
        "ui/src/components/conceptGlance.ts",
        "const levels = picked.flatMap(sectionLevels);",
        "const levels = [50, 100];",
        UI,
    ),
    (
        "카드 색을 시트와 다른 원천(팔레트 이름)으로",
        "ui/src/components/conceptGlance.ts",
        "const hex = sectionHex(section, timeline.palette_legend);",
        "const hex = section.palette[0] ?? null;",
        UI,
    ),
    (
        "출처 표식 제거",
        "ui/src/components/conceptGlance.ts",
        '{ title: "무대에서", text: row.description, source: DESCRIPTION_SOURCE }',
        '{ title: "무대에서", text: row.description }',
        UI,
    ),
]

for name, path, old, new, command in MUTANTS:
    text = Path(path).read_text(encoding="utf-8")
    assert text.count(old) >= 1, (name, "anchor missing")
    Path(path).write_text(text.replace(old, new, 1), encoding="utf-8")
    run = subprocess.run(command, shell=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "--", path], check=True)
    out = run.stdout + run.stderr
    tail = [line.strip() for line in out.splitlines() if "passed" in line or "failed" in line]
    verdict = "CAUGHT" if run.returncode != 0 else "MISSED"
    print(f"{verdict}  {name}  exit={run.returncode}  {tail[-1] if tail else ''}")

status = subprocess.run(
    ["git", "status", "--short", "server", "ui/src"], capture_output=True, text=True
).stdout
print("restored (tracked changes after run):", repr(status.strip()))
