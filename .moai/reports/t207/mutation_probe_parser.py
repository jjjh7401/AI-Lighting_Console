"""t207 갈래 E 뮤테이션 — 정확 집합 검사의 경계를 옮긴다."""

import pathlib
import subprocess
import sys

SRC = pathlib.Path("server/lxseq/cue_parser.py")
ORIG = SRC.read_text(encoding="utf-8")
TESTS = "server/tests/test_lxseq_cue_parser.py"
PYTEST_ARGV = [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header", "-p", "no:cacheprovider"]

GUARD = "    if unexpected:\n        raise UnexpectedCueColumnsError(unexpected)\n"
KLASS_OLD = "class UnexpectedCueColumnsError(CueColumnSetError):"
KLASS_NEW = "class UnexpectedCueColumnsError(ValueError):"

MUTANTS = [
    ("E1 남는 열 검사 제거", GUARD, ""),
    ("E2 사유 문자열 통합", '"unexpected_columns: "', '"missing_columns: "'),
    ("E3 조상 분리", KLASS_OLD, KLASS_NEW),
]


def main() -> None:
    for name, old, new in MUTANTS:
        assert old in ORIG, name + ": 치환 문자열 불일치"
        mutated = ORIG.replace(old, new, 1)
        assert mutated != ORIG, name + ": 적용 안 됨"
        SRC.write_text(mutated, encoding="utf-8")
        try:
            proc = subprocess.run(
                PYTEST_ARGV,
                capture_output=True,
                text=True,
            )
            tail = [
                ln
                for ln in proc.stdout.splitlines()
                if "passed" in ln or "failed" in ln or "error" in ln
            ]
            print(name + ": exit=" + str(proc.returncode) + " | " + (tail[-1] if tail else "?"))
        finally:
            SRC.write_text(ORIG, encoding="utf-8")
    assert SRC.read_text(encoding="utf-8") == ORIG, "복원 실패"
    print("복원 확인: 원본과 바이트 동일")


main()
