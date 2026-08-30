"""t182 뮤테이션 — 새로 만든 단언마다 경계를 옮겨 빨강을 확인한다.

규약 §3: 축 하나씩 · 회차마다 assert mutated != original ·
PYTHONDONTWRITEBYTECODE=1 로 돌린다.

자리가 둘이라 파일도 둘이다 — catch 는 tools.py, 개념은 patchplan.py.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

TOOLS = pathlib.Path("server/orchestrator/tools.py")
PLAN = pathlib.Path("server/vwx/patchplan.py")
TARGET = "server/tests/test_lxseq_group_section_request.py"

CATCH = "        except StateQueryError:\n"
CALL = "            fid_read = unreadable_root()\n"
HELPER_RET = "    return ExistingFidRead(attempted=True, root_unreadable=True)\n"
NOTOK_RET = "        return unreadable_root()\n"

MUTATIONS = [
    ("M1 catch 통째로 제거", "수리 자리", TOOLS, "drop-catch", "침묵 검사 2건"),
    ("M2 except Exception 으로 넓힘", "예외 종류", TOOLS, "broaden", "넓히기 방지 1건"),
    ("M3 catch 가 헬퍼 대신 손조립", "개념의 주인", TOOLS, "handroll", "사유 단언 2건"),
    ("M4 헬퍼 반환을 바꿈", "사유 문면", PLAN, "helper", "사유 단언 3건"),
    ("M5 ok=False 갈래만 딴 값", "두 형태의 수렴", PLAN, "diverge", "팔 B 1건"),
]


def mutate(src, kind):
    if kind == "drop-catch":
        block = re.search(re.escape(CATCH) + r"(?:.*\n)*?" + re.escape(CALL), src)
        assert block is not None, "catch 블록을 못 찾았다"
        body = "        fid_read = read_existing_fids(_InventoryPort(state_port, property_port))\n"
        head = src[: block.start()]
        head = head.replace(
            "        try:\n"
            "            fid_read = read_existing_fids("
            "_InventoryPort(state_port, property_port))\n",
            body,
        )
        return head + src[block.end() :]
    if kind == "broaden":
        return src.replace(CATCH, "        except Exception:\n")
    if kind == "handroll":
        return src.replace(
            CALL,
            "            fid_read = ExistingFidRead(attempted=True)\n",
        ).replace(
            "from server.vwx.patchplan import (\n",
            "from server.vwx.patchplan import (\n    ExistingFidRead,\n",
        )
    if kind == "helper":
        return src.replace(HELPER_RET, "    return ExistingFidRead(attempted=True)\n")
    if kind == "diverge":
        return src.replace(NOTOK_RET, "        return ExistingFidRead(attempted=True)\n")
    raise AssertionError("unknown " + kind)


results = []
for name, axis, path, kind, expectation in MUTATIONS:
    original = path.read_text(encoding="utf-8")
    mutated = mutate(original, kind)
    assert mutated != original, name + ": 적용 안 됨 - 치환 문자열이 안 맞는다"
    path.write_text(mutated, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", TARGET],
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "checkout", "--", str(path)], check=True)
    assert path.read_text(encoding="utf-8") == original, name + ": 복원 실패"
    failed = sorted(set(re.findall(r"^FAILED \S+::\S*?(\w+)(?:\[|\s|$)", proc.stdout, re.M)))
    tail = [ln for ln in proc.stdout.splitlines() if " passed" in ln or " failed" in ln]
    results.append((name, axis, expectation, tail[-1] if tail else "?", failed))

print("=" * 70)
for name, axis, expectation, tail, failed in results:
    verdict = "KILL" if "failed" in tail or "error" in tail else "🔴 SURVIVED"
    print(verdict + "  " + name)
    print("        축   : " + axis)
    print("        기대 : " + expectation)
    print("        결과 : " + tail)
    print("        죽은 검사: " + (", ".join(failed) if failed else "(없음)"))
    print()
