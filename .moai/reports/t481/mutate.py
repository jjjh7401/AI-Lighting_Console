"""t481 — 가드 변이 검사. 고친 줄을 하나씩 옛 모양으로 되돌려 해당 시험이
실패하는지 본다. 각 변이 뒤 `git checkout -- <file>` 로 커밋(31c93714) 상태로 복원.
실행: 워크트리 루트에서 `python3 .moai/reports/t481/mutate.py`
"""

import subprocess
from pathlib import Path

MUTANTS = [
    (
        "한 칸 밀림 되살림",
        "ui/src/components/SongTimeline.tsx",
        "conceptRowForSection(conceptReport, sectionPosition(section, allSections))",
        "conceptRowForSection(conceptReport, section.index)",
        "src/components/SongTimeline.test.tsx",
    ),
    (
        "리저브를 행 번호로 비교",
        "ui/src/components/cueRequestWarnings.ts",
        "if (item.screen_position === null || position >= item.screen_position) return null;",
        "if (position >= item.released_q) return null;",
        "src/components/PlanCueRequestGenerator.test.tsx src/components/cueRequestWarnings.test.ts",
    ),
    (
        "카드 줄 가로 스크롤 제거",
        "ui/src/styles.css",
        "  overflow-x: auto;\n}",
        "}",
        "src/styles.test.ts",
    ),
    (
        "생성기 카드 폭 되돌림",
        "ui/src/styles.css",
        ".song-timeline-section.has-generator { min-width: 280px; }",
        "",
        "src/styles.test.ts",
    ),
    (
        "has-generator 클래스 제거",
        "ui/src/components/SongTimeline.tsx",
        '${!onConsole && onGeneratorSend ? " has-generator" : ""}',
        "",
        "src/components/SongTimeline.test.tsx",
    ),
]

for name, path, old, new, tests in MUTANTS:
    text = Path(path).read_text(encoding="utf-8")
    assert text.count(old) >= 1, (name, "anchor missing")
    Path(path).write_text(text.replace(old, new, 1), encoding="utf-8")
    run = subprocess.run(
        f"npm --prefix ui exec -- vitest run --root ui {tests}",
        shell=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "checkout", "--", path], check=True)
    tail = [line.strip() for line in run.stdout.splitlines() if "Tests " in line]
    verdict = "CAUGHT" if run.returncode != 0 else "MISSED"
    print(f"{verdict}  {name}  exit={run.returncode}  {tail[-1] if tail else ''}")

status = subprocess.run(
    ["git", "status", "--short", "ui/src"], capture_output=True, text=True
).stdout
print("restored (tracked ui/src changes after run):", repr(status.strip()))
