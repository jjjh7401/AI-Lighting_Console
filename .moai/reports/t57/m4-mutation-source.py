"""M4 뮤테이션 매트릭스 — 적용 확인 → 실행 → 복원 → 체크섬. 출력이 증거다."""

import hashlib
import pathlib
import shutil
import subprocess
import sys

target = pathlib.Path("server/tests/test_ws_wait_guard.py")
backup = pathlib.Path("/tmp/t57_guard_backup.py")
shutil.copy(target, backup)
baseline = hashlib.sha256(target.read_bytes()).hexdigest()
print("BASELINE sha256 = " + baseline)

cases = [
    ("unmutated", None, None),
    (
        "site1-lever",
        "            frame = recv_frame(ws)\n",
        '            frame = drain_until(ws, "error")\n',
    ),
    (
        "site2-lever",
        "                event = recv_frame(ws)\n",
        '                event = drain_until(ws, "error")\n',
    ),
    (
        "site1-degenerate",
        "            frame = recv_frame(ws)\n",
        '            frame = drain_until(ws, "status")\n',
    ),
]

for name, old, new in cases:
    if old is not None:
        text = target.read_text()
        if text.count(old) != 1:
            print("CASE " + name + " -> ANCHOR NOT UNIQUE, ABORT")
            sys.exit(1)
        target.write_text(text.replace(old, new, 1))
        applied = new in target.read_text() and old not in target.read_text()
        print("CASE " + name + " applied=" + str(applied))
        if not applied:
            print("  APPLIED-CHECK FAILED — 결과를 판독하지 않는다")
            shutil.copy(backup, target)
            sys.exit(1)
    else:
        print("CASE " + name + " applied=n/a (원본)")
    run = subprocess.run(
        [".venv/bin/python", "-m", "pytest", str(target), "-q", "-p", "no:randomly"],
        capture_output=True,
        text=True,
    )
    tail = [ln for ln in run.stdout.strip().splitlines() if "passed" in ln or "failed" in ln]
    verdict = "SURVIVED" if run.returncode == 0 else "KILLED"
    print("  -> " + verdict + "  |  " + (tail[-1] if tail else "no summary"))
    for ln in run.stdout.splitlines():
        if ln.startswith("FAILED "):
            print("     " + ln)
    shutil.copy(backup, target)
    restored = hashlib.sha256(target.read_bytes()).hexdigest()
    print("  restored sha256 match = " + str(restored == baseline))
