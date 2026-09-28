"""t485 가드 변이 — 새 단언이 각 결함을 잡는지 본다.

실행: 워크트리 루트에서 ``uv run python .moai/reports/t485/mutate.py``.
파일은 매 회차 끝에 원본 바이트로 되돌린다(finally).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIDGE = "server/concept/session_bridge.py"
SESSION = "server/web/session.py"
BULLET_TS = "ui/src/components/conceptBullet.ts"
PY_TEST = ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"]
PY_TEST.append("server/tests/test_concept_bullet_t485.py")
UI_TEST = ["npx", "vitest", "run", "src/components/conceptBullet.test.ts"]

MUTANTS = [
    (
        "S1 호출 지점이 기록을 안 넘김",
        SESSION,
        "            interview_records=state.records,\n",
        "",
        PY_TEST,
    ),
    (
        "S2 자동 초안도 원문으로 인정",
        BRIDGE,
        'if origin_label is None or not getattr(record, "confirmed", False):',
        "if False:",
        PY_TEST,
    ),
    (
        "S3 감독 입력 대신 해석값",
        BRIDGE,
        'text = free_text if isinstance(free_text, str) else str(getattr(record, "value", ""))',
        'text = str(getattr(record, "value", ""))',
        PY_TEST,
    ),
    (
        "S4 원문 공백 접기(윤문)",
        BRIDGE,
        '"text": render_concept_bullet(text),',
        '"text": " ".join(text.split()),',
        PY_TEST,
    ),
    (
        "U1 화면에서 줄 앞뒤 공백 깎기",
        BULLET_TS,
        '.split("\\n").filter(',
        '.split("\\n").map((line) => line.trim()).filter(',
        UI_TEST,
    ),
    (
        "U2 배지 문자열 변경",
        BULLET_TS,
        'VERBATIM_BADGE = "원문 그대로"',
        'VERBATIM_BADGE = "원문"',
        UI_TEST,
    ),
]


def run(cmd: list[str], cwd: Path) -> tuple[int, list[str]]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    out = done.stdout + done.stderr
    failed = [line.strip() for line in out.splitlines() if line.startswith("FAILED")]
    failed += [line.strip() for line in out.splitlines() if line.strip().startswith("×")]
    return done.returncode, failed


def main() -> None:
    caught = 0
    for name, rel, old, new, cmd in MUTANTS:
        path = ROOT / rel
        original = path.read_bytes()
        text = original.decode()
        assert text.count(old) == 1, f"{name}: 치환 대상이 정확히 1곳이 아니다"
        mutated = text.replace(old, new)
        assert mutated != text, f"{name}: 적용 안 됨"
        try:
            path.write_text(mutated)
            cwd = ROOT / "ui" if cmd is UI_TEST else ROOT
            code, failed = run(cmd, cwd)
        finally:
            path.write_bytes(original)
        verdict = "CAUGHT" if code != 0 else "SURVIVED"
        caught += code != 0
        print(f"{verdict}  {name}  (exit={code})")
        for line in failed:
            print(f"    {line}")
    print(f"{caught}/{len(MUTANTS)} CAUGHT")


if __name__ == "__main__":
    main()
