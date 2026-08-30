"""t194 뮤테이션 — 새로 만든 단언에 경계를 옮겨 걸어본다 (규약 3.3).

회차마다 `assert mutated != ORIGINAL` 을 들고 간다 — 치환이 안 맞으면 파일이
원본 그대로 돌아가고 그 통과가 **생존으로 기록**되기 때문이다.

🔴 계기 수정 [t194 2회차]: 이전 판은 `PY` 에 **다른 트리의 venv** 경로를 박아
뒀다(`/Users/studiox/orca/workspaces/.../LX-SEQ/.venv`). 그 탓에 1회차에서
`test_tree_identity` 가 `ModuleNotFoundError` 로 가짜로 죽어 "7 failed" 가 났고,
그것을 코드 결함으로 오진할 뻔했다. 이제 `sys.executable` 을 쓰고, 그것이 이 트리
안에 있는지 **단언**한다 — 남의 트리를 빌리면 여기서 멈춘다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
PP = Path("server/vwx/patchplan.py")
TL = Path("server/orchestrator/tools.py")
TESTFILE = "server/tests/test_lxseq_group_section_request.py"
PY = sys.executable

# 계기는 인터프리터 **바이너리**가 아니라 **환경**을 봐야 한다. `.venv/bin/python`
# 은 uv 가 설치한 실물로 가는 심볼릭 링크라 resolve() 하면 트리 밖으로 나간다 —
# 그것을 오염으로 읽으면 멀쩡한 트리에서 멈춘다(이 가드의 1차 판이 그랬다).
# `sys.prefix` 는 venv 루트라 링크를 안 탄다.
VENV = Path(sys.prefix).resolve()
if ROOT not in VENV.parents and VENV != ROOT:
    print("🔴 계기 오염: venv " + str(VENV) + " 가 이 트리(" + str(ROOT) + ") 밖이다.")
    print("   uv run python 으로 돌려라. 남의 트리 venv 는 가짜 실패를 만든다.")
    sys.exit(1)

ORIGINAL = {PP: PP.read_text(encoding="utf-8"), TL: TL.read_text(encoding="utf-8")}

_ADAPTER_HEAD = (
    "    def query_property(self, path: str, property_name: str) -> dict:\n"
    "        try:\n"
    "            return self._inner.query_property(path, property_name)\n"
    "        except StateQueryError:"
)
_SWEEP_COND = '            if probe.get("ok") is True or probe.get("unreachable") is True:'

MUTANTS = [
    (
        TL,
        "M1 어댑터 무력화 — 번역을 끄면 슬롯 실패가 다시 루트 사유로 접힌다",
        _ADAPTER_HEAD,
        (
            "    def query_property(self, path: str, property_name: str) -> dict:\n"
            "        if True:\n"
            "            return self._inner.query_property(path, property_name)\n"
            "        if False:"
        ),
    ),
    (
        TL,
        "M2 넓히기 — except StateQueryError -> except Exception",
        "        except StateQueryError:\n            return {",
        "        except Exception:\n            return {",
    ),
    (
        TL,
        "M3 표식 제거 — unreachable 없이 ok=False 로만 번역한다",
        '                "unreachable": True,\n',
        "",
    ),
    (
        TL,
        "M4 값 지어내기 — 못 읽은 슬롯에 가짜 FID 를 준다",
        '            return {\n                "ok": False,',
        '            return {\n                "ok": True,\n                "value": "1",',
    ),
    (
        PP,
        "M5 스윕 계수 되돌리기 — unreachable 을 안 센다 (수용 기준 3 파괴)",
        _SWEEP_COND,
        '            if probe.get("ok") is True:',
    ),
    (
        PP,
        "M6 스윕 과다계수 — ok=False(부재)까지 전송 실패로 센다",
        _SWEEP_COND,
        "            if True:",
    ),
    (
        PP,
        "M7 사유 문구 변경 — 열거된 슬롯 -> 확인된 슬롯",
        '"열거된 슬롯 {self.unreadable_fids}개의 FID 값을 얻지 못했다"',
        '"확인된 슬롯 {self.unreadable_fids}개의 FID 값을 얻지 못했다"',
    ),
    (
        PP,
        "M8 구별 접기 — 루트 실패도 슬롯 사유로 낸다",
        "    state = fid_property_port.query_state(FID_FIXTURE_ROOT)",
        (
            "    try:\n"
            "        state = fid_property_port.query_state(FID_FIXTURE_ROOT)\n"
            "    except Exception:\n"
            "        return ExistingFidRead(attempted=True, unreadable_fids=1)"
        ),
    ),
    (
        TL,
        "M9 어댑터 과다적용 — query_state 까지 번역한다 (채택 안 한 오설계)",
        (
            "    def query_state(self, path: str) -> dict:\n"
            "        return self._inner.query_state(path)"
        ),
        (
            "    def query_state(self, path: str) -> dict:\n"
            "        try:\n"
            "            return self._inner.query_state(path)\n"
            "        except StateQueryError:\n"
            '            return {"ok": False, "path": path, "unreachable": True}'
        ),
    ),
]

env = dict(os.environ)
env["PYTHONDONTWRITEBYTECODE"] = "1"


def run_suite():
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
print("")

killed = 0
try:
    for target, label, old, new in MUTANTS:
        source = ORIGINAL[target]
        count = source.count(old)
        if count != 1:
            print(label)
            print("    🔴 앵커가 " + str(count) + "회 — 1이어야 한다. 건너뜀(적용 안 됨).")
            print("")
            continue
        mutated = source.replace(old, new)
        assert mutated != source, label + " — 적용 안 됨"
        target.write_text(mutated, encoding="utf-8")
        rc, failed = run_suite()
        target.write_text(source, encoding="utf-8")
        verdict = "KILL" if rc != 0 else "🔴 생존"
        if rc != 0:
            killed += 1
        print(label + "  [" + target.name + "]")
        print("    " + verdict + "  죽은 검사 " + str(len(failed)) + "개: " + str(failed))
        print("")
finally:
    for target, source in ORIGINAL.items():
        target.write_text(source, encoding="utf-8")
    restored = all(t.read_text(encoding="utf-8") == s for t, s in ORIGINAL.items())
    print("복원 완료: " + str(restored))

print("판정: " + str(killed) + "/" + str(len(MUTANTS)) + " KILL")
