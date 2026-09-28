"""t490 — 새 단언에 거는 뮤테이션. 원본은 매 회차 복원한다.

실행: 워크트리 루트에서 `uv run python .moai/reports/t490/mutate.py`
"""

import subprocess
from pathlib import Path

TEST = "src/components/nullFade.t490.test.tsx"
MUTANTS = [
    (
        "M1 CUE SHEET 가 undefined 만 막는다(원래 결함)",
        Path("ui/src/components/CueSheetTimeline.tsx"),
        "{section.fade_seconds == null",
        "{section.fade_seconds === undefined",
    ),
    (
        "M2 Fade/Track 줄이 undefined 만 막는다",
        Path("ui/src/components/SongTimeline.tsx"),
        "section.fade_seconds != null ? `${section.fade_seconds}s`",
        "section.fade_seconds !== undefined ? `${section.fade_seconds}s`",
    ),
    (
        "M3 수정 요청 이전 값이 undefined 만 막는다",
        Path("ui/src/components/PlanCueRequestGenerator.tsx"),
        "section.fade_seconds != null ? `${section.fade_seconds}초`",
        "section.fade_seconds !== undefined ? `${section.fade_seconds}초`",
    ),
]

for name, path, old, new in MUTANTS:
    original = path.read_text(encoding="utf-8")
    assert original.count(old) == 1, f"{name}: 치환 대상이 정확히 한 번 있어야 한다"
    mutated = original.replace(old, new)
    assert mutated != original, f"{name}: 적용 안 됨"
    path.write_text(mutated, encoding="utf-8")
    try:
        result = subprocess.run(
            ["npx", "vitest", "run", TEST], cwd="ui", capture_output=True, text=True
        )
    finally:
        path.write_text(original, encoding="utf-8")
    failed = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("×")]
    verdict = "CAUGHT" if result.returncode != 0 else "SURVIVED"
    print(f"{name}: {verdict}")
    for line in failed:
        print(f"    {line}")

clean = subprocess.run(
    ["git", "status", "--porcelain", "ui/src/components"], capture_output=True, text=True
)
print("restored:", clean.stdout.strip() == "")
