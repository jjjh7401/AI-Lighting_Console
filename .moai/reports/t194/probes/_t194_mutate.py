"""t194 뮤테이션 — 새로 만든 단언에 경계를 옮겨 걸어본다(규약 3.3).

회차마다 `assert mutated != original` 을 들고 간다 — 치환이 안 맞으면 파일이
원본 그대로 돌아가고 그 통과가 **생존으로 기록**되기 때문이다.
전부 PYTHONDONTWRITEBYTECODE=1 로 돌린다(3.4 계기 오염).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TARGET = Path("server/vwx/patchplan.py")
TESTFILE = "server/tests/test_lxseq_group_section_request.py"
PY = "/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ/.venv/bin/python"

ORIGINAL = TARGET.read_text(encoding="utf-8")

MUTANTS = [
    (
        "M1 수리 제거 — try/except 를 통째로 지우고 원래 호출로",
        "        try:\n"
        "            response = fid_property_port.query_property(\n"
        '                f"{FID_FIXTURE_ROOT}/{child_index}", FID_PROPERTY_NAME\n'
        "            )\n"
        "        except StateQueryError:",
        "        if True:\n"
        "            response = fid_property_port.query_property(\n"
        '                f"{FID_FIXTURE_ROOT}/{child_index}", FID_PROPERTY_NAME\n'
        "            )\n"
        "        if False:",
    ),
    (
        "M2 넓히기 — except StateQueryError -> except Exception",
        "        except StateQueryError:",
        "        except Exception:",
    ),
    (
        "M3 조용히 삼키기 — 세지 않고 넘어간다",
        "            response = {}",
        "            read_slots.add(child_index)\n            continue",
    ),
    (
        "M4 값을 지어내기 — 빈 응답 대신 가짜 FID",
        "            response = {}",
        '            response = dict(ok=True, value="1")',
    ),
    (
        "M5 사유 문구 변경 — 열거된 슬롯 -> 확인된 슬롯",
        '"열거된 슬롯 {self.unreadable_fids}개의 FID 값을 얻지 못했다"',
        '"확인된 슬롯 {self.unreadable_fids}개의 FID 값을 얻지 못했다"',
    ),
    (
        "M6 구별 접기 — 루트 실패도 슬롯 사유로 낸다",
        "    state = fid_property_port.query_state(FID_FIXTURE_ROOT)",
        "    try:\n"
        "        state = fid_property_port.query_state(FID_FIXTURE_ROOT)\n"
        "    except StateQueryError:\n"
        "        return ExistingFidRead(attempted=True, unreadable_fids=1)",
    ),
]

env = dict(os.environ)
env["PYTHONDONTWRITEBYTECODE"] = "1"


def run_suite() -> tuple[int, list]:
    proc = subprocess.run(  # noqa: S603
        [PY, "-m", "pytest", TESTFILE, "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    failed = []
    for line in proc.stdout.split("\n"):
        if line.startswith("FAILED "):
            failed.append(line.split("::")[-1].split(" ")[0])
    return proc.returncode, failed


base_rc, base_failed = run_suite()
print("기준선(수리 적용 상태): rc=" + str(base_rc) + " 실패=" + str(base_failed))
if base_rc != 0:
    print("🔴 기준선이 초록이 아니다. 중단.")
    sys.exit(1)
print()

try:
    for label, old, new in MUTANTS:
        count = ORIGINAL.count(old)
        if count != 1:
            print(label)
            print("    🔴 앵커가 " + str(count) + "회 — 1이어야 한다. 건너뜀(적용 안 됨).")
            print()
            continue
        mutated = ORIGINAL.replace(old, new)
        assert mutated != ORIGINAL, label + " — 적용 안 됨"
        TARGET.write_text(mutated, encoding="utf-8")
        rc, failed = run_suite()
        verdict = "KILL" if rc != 0 else "🔴 생존"
        print(label)
        print("    " + verdict + "  죽은 검사 " + str(len(failed)) + "개: " + str(failed))
        print()
finally:
    TARGET.write_text(ORIGINAL, encoding="utf-8")
    print("복원 완료: " + str(TARGET.read_text(encoding="utf-8") == ORIGINAL))
