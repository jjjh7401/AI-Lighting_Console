"""t207 뮤테이션 프로브 — 새 게이트의 단언에 경계를 옮겨 빨강을 확인한다.

규약 §3.3: 「적용 안 됨」은 눈이 아니라 단언으로 잰다.
규약 §3.4: PYTHONDONTWRITEBYTECODE=1 로 돌리고 끝난 뒤 캐시를 지운다.
"""

import pathlib
import subprocess
import sys

SRC = pathlib.Path("server/lxseq/cue_mapper.py")
ORIG = SRC.read_text(encoding="utf-8")
TESTS = "server/tests/test_lxseq_cue_mapper.py"
PYTEST_ARGV = [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header", "-p", "no:cacheprovider"]

GATE = "    if held:\n        return CueMapResult(\n            planned=(),"
GONE = "    if False:\n        return CueMapResult(\n            planned=(),"
WIDE = "    if len(held) > 1:\n        return CueMapResult(\n            planned=(),"

MUTANTS = [
    ("M1 게이트 통째 제거", GATE, GONE),
    ("M2 경계 이동 1행->2행", GATE, WIDE),
    ("M3 사유 요약 공백화", '    return "; ".join(lines)', '    return ""'),
    ("M4 사유에서 그룹명 제거", "        + item.group\n", '        + ""\n'),
    ("M5 사유에서 클래스 제거", '", ".join(item.hold_classes)', '""'),
]


def main() -> None:
    for name, old, new in MUTANTS:
        if old not in ORIG:
            print(name + ": 치환 문자열 불일치 — 적용 안 됨")
            continue
        mutated = ORIG.replace(old, new, 1)
        assert mutated != ORIG, name + ": 적용 안 됨"
        SRC.write_text(mutated, encoding="utf-8")
        try:
            proc = subprocess.run(
                PYTEST_ARGV,
                capture_output=True,
                text=True,
            )
            tail = [ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln]
            summary = tail[-1] if tail else proc.stdout[-200:]
            print(name + ": exit=" + str(proc.returncode) + " | " + summary)
        finally:
            SRC.write_text(ORIG, encoding="utf-8")
    assert SRC.read_text(encoding="utf-8") == ORIG, "복원 실패"
    print("복원 확인: 원본과 바이트 동일")


main()
