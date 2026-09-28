"""t486 — 새 단언에 거는 뮤테이션. 원본은 매 회차 복원한다.

실행: `PYTHONDONTWRITEBYTECODE=1 uv run python .moai/reports/t486/mutate.py`
"""

import subprocess
from pathlib import Path

RENDER = Path("server/design/song_cue_render.py")
BRIDGE = Path("server/concept/session_bridge.py")
NAME_TESTS = "server/tests/test_split_cue_console_name_t486.py"
DESC_TESTS = "server/tests/test_concept_description_no_brightness_t486.py"

MUTANTS = [
    (
        "M1 분할 접미사 변환 제거",
        RENDER,
        '    label = _SPLIT_SUFFIX.sub(r"\\1 of \\2", label)\n',
        "",
        NAME_TESTS,
    ),
    (
        "M2 허용 문자 표에 괄호·빗금 추가",
        RENDER,
        'r"[A-Za-z0-9 _-]+"',
        'r"[A-Za-z0-9 _()/-]+"',
        NAME_TESTS,
    ),
    (
        "M3 화면 설명이 describe() 원문 그대로",
        BRIDGE,
        '    kept = [part for part in text.split(" · ") if not part.startswith("최대 ")]\n',
        '    kept = text.split(" · ")\n',
        DESC_TESTS,
    ),
    (
        "M4 빈 문장 대체 문구 제거",
        BRIDGE,
        '    return " · ".join(kept) or _NO_GROUP_OR_COLOR_CHANGE\n',
        '    return " · ".join(kept)\n',
        DESC_TESTS,
    ),
]

for name, path, old, new, tests in MUTANTS:
    original = path.read_text(encoding="utf-8")
    assert original.count(old) == 1, f"{name}: 치환 대상이 정확히 한 번 있어야 한다"
    mutated = original.replace(old, new)
    assert mutated != original, f"{name}: 적용 안 됨"
    path.write_text(mutated, encoding="utf-8")
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", tests],
            capture_output=True,
            text=True,
        )
    finally:
        path.write_text(original, encoding="utf-8")
    tail = result.stdout.strip().splitlines()[-1]
    verdict = "CAUGHT" if result.returncode != 0 else "SURVIVED"
    print(f"{name}: {verdict} — {tail}")

clean = subprocess.run(
    ["git", "status", "--porcelain", str(RENDER), str(BRIDGE)], capture_output=True, text=True
)
print("restored:", clean.stdout.strip() == "")
