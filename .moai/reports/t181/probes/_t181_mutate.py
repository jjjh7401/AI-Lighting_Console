"""t181 뮤테이션 — 새로 만든 단언마다 경계를 옮겨 빨강을 확인한다.

규약 §3:
  - 축을 하나씩만 건드린다. 두 축을 걸치면 어느 축에 답한 빨강인지 안 갈린다.
  - 매 회차 `assert mutated != original` — 「적용 안 됨」이 생존으로 기록되는 것을 막는다.
  - PYTHONDONTWRITEBYTECODE=1 로 돌린다. 낡은 pyc 가 거짓 사망까지 낸다.

각 회차: 치환 -> 적용 단언 -> pytest -> 죽은 검사 이름 수집 -> git 으로 복원.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

TOOLS = pathlib.Path("server/orchestrator/tools.py")
TARGET = "server/tests/test_lxseq_tool.py"

CATCH = "        except StateQueryError as error:\n"
MSG = '                call, f"console did not answer — fixture inventory unread: {error}"\n'
INV_MSG = '            return _error_result(call, f"fixture inventory unreadable: {error}")\n'

# (이름, 축, 무엇을 바꾸나, 몇 번째 자리만, 기대)
MUTATIONS = [
    ("M1 자리1 catch 제거", "site-1 coverage", "drop-catch", 0, "patch_fixtures 침묵 3건만 빨강"),
    (
        "M2 자리2 catch 제거",
        "site-2 coverage",
        "drop-catch",
        1,
        "import_lxseq_patch 침묵 3건만 빨강",
    ),
    (
        "M3 문면에서 콘솔을 뺀다",
        "문면이 콘솔을 가리킴",
        "strip-console",
        None,
        "이름 단언 6건 빨강",
    ),
    ("M4 except Exception 으로 넓힌다", "예외 종류 명시", "broaden", None, "넓히기 방지 2건 빨강"),
    ("M5 포트 사유를 뺀다", "포트 사유 보존", "strip-detail", None, "detail 단언 6건 빨강"),
    ("M6 인벤토리 갈래도 콘솔이라 말한다", "두 사유 분리", "merge-reasons", None, "팔 B 2건 빨강"),
]


def mutate(src: str, kind: str, which):
    if kind == "drop-catch":
        # 자리 하나만 - 해당 except 블록(catch 줄 + 주석 5줄 + return 3줄)을 지운다
        blocks = [m for m in re.finditer(re.escape(CATCH) + r"(?:.*\n)*?            \)\n", src)]
        assert len(blocks) == 2, f"catch 블록이 2개가 아니다: {len(blocks)}"
        b = blocks[which]
        return src[: b.start()] + src[b.end() :]
    if kind == "strip-console":
        return src.replace(MSG, '                call, f"fixture inventory unread: {error}"\n')
    if kind == "broaden":
        return src.replace(CATCH, "        except Exception as error:\n")
    if kind == "strip-detail":
        return src.replace(
            MSG, '                call, "console did not answer — fixture inventory unread"\n'
        )
    if kind == "merge-reasons":
        return src.replace(
            INV_MSG,
            "            return _error_result(\n"
            '                call, f"console did not answer — '
            'fixture inventory unreadable: {error}"\n'
            "            )\n",
        )
    raise AssertionError("unknown kind " + kind)


def restore():
    subprocess.run(["git", "checkout", "--", str(TOOLS)], check=True)


original = TOOLS.read_text(encoding="utf-8")
results = []
for name, axis, kind, which, expectation in MUTATIONS:
    mutated = mutate(original, kind, which)
    assert mutated != original, f"{name}: 적용 안 됨 - 치환 문자열이 안 맞는다"
    TOOLS.write_text(mutated, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", TARGET],
        capture_output=True,
        text=True,
    )
    restore()
    assert TOOLS.read_text(encoding="utf-8") == original, f"{name}: 복원 실패"
    failed = sorted(set(re.findall(r"^FAILED \S+::(\S+?)(?:\[|\s|$)", proc.stdout, re.M)))
    tail = [ln for ln in proc.stdout.splitlines() if " passed" in ln or " failed" in ln]
    results.append((name, axis, expectation, tail[-1] if tail else "?", failed))

print("=" * 72)
for name, axis, expectation, tail, failed in results:
    verdict = "KILL" if "failed" in tail else "🔴 SURVIVED"
    print(f"{verdict}  {name}")
    print(f"        축   : {axis}")
    print(f"        기대 : {expectation}")
    print(f"        결과 : {tail}")
    print(f"        죽은 검사: {', '.join(failed) if failed else '(없음)'}")
    print()
